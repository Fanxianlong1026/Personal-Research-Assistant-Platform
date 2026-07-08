"""AI对话请求/响应模型"""
from datetime import datetime
from typing import List
from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str = ""
    message: str
    context: str = ""  # 可选的上下文（如论文内容）


class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    session_id: str
    messages: List[ChatMessageResponse]
    last_message: str
    created_at: datetime
