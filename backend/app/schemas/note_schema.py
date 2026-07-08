"""笔记请求/响应模型"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class NoteCreate(BaseModel):
    title: str
    content: str = ""
    folder: str = "default"
    tags: List[str] = []
    paper_id: Optional[int] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    folder: Optional[str] = None
    tags: Optional[List[str]] = None
    paper_id: Optional[int] = None
    is_pinned: Optional[int] = None


class NoteResponse(BaseModel):
    id: int
    title: str
    content: str
    folder: str
    tags: list
    paper_id: Optional[int]
    is_pinned: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    items: List[NoteResponse]
    total: int
    folders: List[str]  # 所有文件夹列表
