"""任务请求/响应模型"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[date] = None
    tags: List[str] = []
    related_paper_id: Optional[int] = None
    related_note_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    tags: Optional[List[str]] = None
    sort_order: Optional[int] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    due_date: Optional[date]
    tags: list
    related_paper_id: Optional[int]
    related_note_id: Optional[int]
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskBoardResponse(BaseModel):
    todo: List[TaskResponse]
    in_progress: List[TaskResponse]
    done: List[TaskResponse]


class TaskReorderRequest(BaseModel):
    """看板拖拽后各列的任务 id 顺序，索引即新的 sort_order，列名即新状态。"""
    todo: List[int] = []
    in_progress: List[int] = []
    done: List[int] = []
