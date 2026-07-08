"""
AI 问答 API 路由
支持本地 Qwen2.5 模型推理（流式输出）和远程 OpenAI 兼容 API
"""
import json
import uuid
import asyncio
import logging
from typing import AsyncGenerator, List
from functools import partial

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chat import ChatMessage
from app.schemas.chat_schema import ChatRequest, ChatMessageResponse, ChatSessionResponse
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI问答"])

SYSTEM_PROMPT = """你是一个专业的科研助手，能够帮助用户：
1. 论文解读：解释论文的核心方法、实验设计和结论
2. 文献综述：帮助梳理研究脉络和相关工作
3. 实验建议：对实验设计、参数选择提供建议
4. 写作辅助：帮助润色论文、撰写摘要等
5. 代码调试：帮助解决科研编程中的问题

请用中文回答，保持专业和准确。"""

# ========================
# 本地模型全局变量（懒加载）
# ========================
_model = None
_tokenizer = None
_model_loaded = False
_model_loading = False


def _load_local_model():
    """加载本地 Qwen2.5 模型（首次调用时执行）"""
    global _model, _tokenizer, _model_loaded, _model_loading

    if _model_loaded or _model_loading:
        return

    _model_loading = True
    try:
        logger.info(f"正在加载本地模型: {settings.AI_LOCAL_MODEL_PATH}")

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = settings.AI_LOCAL_DEVICE
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        _tokenizer = AutoTokenizer.from_pretrained(
            settings.AI_LOCAL_MODEL_PATH,
            trust_remote_code=True,
        )

        _model = AutoModelForCausalLM.from_pretrained(
            settings.AI_LOCAL_MODEL_PATH,
            dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map=device if device == "cuda" else None,
            trust_remote_code=True,
        )

        if device == "cpu":
            _model = _model.to(device)

        _model.eval()
        _model_loaded = True
        logger.info(f"模型加载完成，设备: {device}")
    finally:
        _model_loading = False


def _generate_stream(prompt_text: str):
    """同步生成函数，在后台线程中运行"""
    import torch
    from transformers import TextIteratorStreamer
    from threading import Thread

    streamer = TextIteratorStreamer(
        _tokenizer, skip_prompt=True, skip_special_tokens=True
    )

    inputs = _tokenizer(prompt_text, return_tensors="pt")
    inputs = {k: v.to(_model.device) for k, v in inputs.items()}

    gen_kwargs = dict(
        **inputs,
        max_new_tokens=settings.AI_MAX_NEW_TOKENS,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
        streamer=streamer,
    )

    thread = Thread(target=_model.generate, kwargs=gen_kwargs)
    thread.start()

    # 从 streamer 中逐 token 读取并 yield
    for token_text in streamer:
        yield token_text

    thread.join()


async def _local_stream_chat(messages: list, session_id: str, db: Session) -> AsyncGenerator:
    """本地模型流式推理"""
    full_response = ""

    # 首次调用时加载模型（在线程中执行，避免阻塞事件循环）
    if not _model_loaded:
        loading_payload = json.dumps({"content": "正在加载本地模型，请稍候（首次约需数十秒）...\n\n"})
        yield f"data: {loading_payload}\n\n"
        try:
            await asyncio.to_thread(_load_local_model)
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            yield f"data: {json.dumps({'error': f'模型加载失败: {str(e)}'})}\n\n"
            return

    try:
        # 使用 tokenizer 的 chat template 构建 prompt
        prompt = _tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    except Exception:
        # 如果模型没有 chat template，手动拼接
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == "user":
                prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"

    loop = asyncio.get_event_loop()

    try:
        # 在后台线程中运行生成，避免阻塞事件循环
        gen_func = partial(_generate_stream, prompt)

        def run_generator():
            results = []
            for token in gen_func():
                results.append(token)
            return results

        # 使用队列在后台线程和异步生成器之间传递 token
        queue = asyncio.Queue()

        def thread_worker():
            try:
                for token in gen_func():
                    asyncio.run_coroutine_threadsafe(queue.put(token), loop)
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # 结束信号
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(str(e)), loop)
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        worker_thread = __import__("threading").Thread(target=thread_worker)
        worker_thread.start()

        while True:
            token = await queue.get()
            if token is None:
                break
            if isinstance(token, str) and token.startswith("Error"):
                yield f"data: {json.dumps({'error': token})}\n\n"
                return
            full_response += token
            yield f"data: {json.dumps({'content': token})}\n\n"

        worker_thread.join(timeout=1)
        yield f"data: {json.dumps({'done': True})}\n\n"

    except Exception as e:
        logger.error(f"模型推理错误: {e}")
        yield f"data: {json.dumps({'error': f'模型推理错误: {str(e)}'})}\n\n"
        return

    # 保存助手回复
    if full_response:
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=full_response,
        )
        db.add(assistant_msg)
        db.commit()


async def _api_stream_chat(messages: list, session_id: str, db: Session) -> AsyncGenerator:
    """远程 API 流式调用（原有逻辑）"""
    import httpx

    full_response = ""

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{settings.AI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.AI_MODEL,
                    "messages": messages,
                    "stream": True,
                },
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"data: {json.dumps({'error': error_text.decode()})}\n\n"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_response += content
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

        except httpx.ConnectError:
            yield f"data: {json.dumps({'error': '无法连接AI服务，请检查配置'})}\n\n"
            return

    # 保存助手回复
    if full_response:
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=full_response,
        )
        db.add(assistant_msg)
        db.commit()


@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """AI 对话接口（SSE流式响应）"""
    if settings.AI_MODE == "api":
        if not settings.AI_API_KEY:
            raise HTTPException(status_code=400, detail="请先在 .env 中配置 AI_API_KEY")

    session_id = request.session_id or uuid.uuid4().hex

    # 构建消息历史
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if request.context:
        messages.append({"role": "system", "content": f"参考上下文：\n{request.context}"})

    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": request.message})

    # 保存用户消息
    user_msg = ChatMessage(session_id=session_id, role="user", content=request.message)
    db.add(user_msg)
    db.commit()

    # 根据模式选择推理方式
    if settings.AI_MODE == "local":
        stream_fn = _local_stream_chat
    else:
        stream_fn = _api_stream_chat

    return StreamingResponse(
        stream_fn(messages, session_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Session-Id": session_id,
        },
    )


@router.get("/model/status")
async def model_status():
    """获取当前 AI 模型状态"""
    return {
        "mode": settings.AI_MODE,
        "model_loaded": _model_loaded,
        "model_path": settings.AI_LOCAL_MODEL_PATH if settings.AI_MODE == "local" else None,
        "api_model": settings.AI_MODEL if settings.AI_MODE == "api" else None,
    }


@router.post("/model/load")
async def load_model():
    """手动预加载本地模型"""
    if settings.AI_MODE != "local":
        raise HTTPException(status_code=400, detail="当前为 API 模式，无需加载本地模型")
    if _model_loaded:
        return {"message": "模型已加载", "status": "ready"}
    _load_local_model()
    return {"message": "模型加载完成", "status": "ready"}


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    """获取所有对话会话"""
    from sqlalchemy import func, desc

    sessions = (
        db.query(
            ChatMessage.session_id,
            func.min(ChatMessage.created_at).label("created_at"),
            func.max(ChatMessage.content).label("last_message"),
        )
        .group_by(ChatMessage.session_id)
        .order_by(desc("created_at"))
        .all()
    )

    return [
        {
            "session_id": s.session_id,
            "created_at": str(s.created_at),
            "last_message": (s.last_message or "")[:100],
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=List[ChatMessageResponse])
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    """获取指定会话的所有消息"""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return messages


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """删除对话会话"""
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.commit()
    return {"message": "删除成功"}
