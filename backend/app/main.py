"""
科研助手平台 - FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import papers, notes, experiments, experiment_groups, tasks, ai, search

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="科研助手平台 API - 论文管理、知识库笔记、实验记录、任务管理、AI问答",
    version="1.0.0",
)

# ============================================================
# 【踩坑提醒】CORS 中间件配置
# 必须放在所有路由注册之前！
# 忘记配置 CORS 会导致前端所有跨域请求失败（403/Network Error）
# origins 不能用 "*" 和 allow_credentials=True 同时使用
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite 开发服务器
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(papers.router, prefix=settings.API_PREFIX)
app.include_router(notes.router, prefix=settings.API_PREFIX)
app.include_router(experiments.router, prefix=settings.API_PREFIX)
app.include_router(experiment_groups.router, prefix=settings.API_PREFIX)
app.include_router(tasks.router, prefix=settings.API_PREFIX)
app.include_router(ai.router, prefix=settings.API_PREFIX)
app.include_router(search.router, prefix=settings.API_PREFIX)


def _migrate_papers_fulltext(db):
    """为旧库补 papers.fulltext 列（create_all 不会给已存在的表加列）。"""
    from sqlalchemy import text
    cols = [r[1] for r in db.execute(text("PRAGMA table_info(papers)")).fetchall()]
    if "fulltext" not in cols:
        db.execute(text("ALTER TABLE papers ADD COLUMN fulltext TEXT DEFAULT ''"))
        db.commit()


def _backfill_fulltext(db):
    """为已上传 PDF 但 fulltext 为空的论文回填正文（仅在 PyMuPDF 可用时）。"""
    from app import pdf_extract
    if not pdf_extract.is_available():
        return
    from app.models.paper import Paper
    papers = db.query(Paper).filter(
        Paper.file_path != "", (Paper.fulltext == "") | (Paper.fulltext.is_(None))
    ).all()
    for p in papers:
        text_ = pdf_extract.extract_text(p.file_path)
        if text_:
            p.fulltext = text_
    if papers:
        db.commit()


@app.on_event("startup")
async def startup():
    """应用启动时自动创建数据库表"""
    # 导入所有模型以确保它们被注册
    from app.models import Paper, Note, Experiment, ExperimentGroup, Task, ChatMessage  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # 构建全文搜索索引（FTS5），保证索引与现有数据一致
    from app.database import SessionLocal
    from app import search_index
    db = SessionLocal()
    try:
        _migrate_papers_fulltext(db)   # 补列
        _backfill_fulltext(db)         # 回填已有 PDF 的正文
        search_index.rebuild_all(db)   # 重建索引（含 fulltext）
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "科研助手平台 API 运行中", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
