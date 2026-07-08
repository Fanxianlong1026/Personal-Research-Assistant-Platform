"""
全文搜索 API 路由（SQLite FTS5）
跨论文 + 笔记、跨字段检索，返回按相关度排序的结果与上下文片段。
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import search_index

router = APIRouter(prefix="/search", tags=["全文搜索"])


@router.get("")
def full_text_search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    type: str = Query("all", description="all / paper / note"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """全文检索论文与笔记。"""
    if type == "paper":
        types = {"papers"}
    elif type == "note":
        types = {"notes"}
    else:
        types = {"papers", "notes"}

    results = search_index.search(db, q.strip(), types, limit)
    return {"query": q, "total": len(results), "results": results}
