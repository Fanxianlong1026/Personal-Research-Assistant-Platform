"""
任务管理 API 路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task import Task
from app.schemas.task_schema import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskBoardResponse,
    TaskReorderRequest,
)

router = APIRouter(prefix="/tasks", tags=["任务管理"])


@router.get("/board", response_model=TaskBoardResponse)
def get_task_board(db: Session = Depends(get_db)):
    """获取看板视图：按状态分组的任务"""
    todo = db.query(Task).filter(Task.status == "todo").order_by(Task.sort_order).all()
    in_progress = db.query(Task).filter(Task.status == "in_progress").order_by(Task.sort_order).all()
    done = db.query(Task).filter(Task.status == "done").order_by(Task.sort_order).all()
    return TaskBoardResponse(todo=todo, in_progress=in_progress, done=done)


@router.post("/reorder")
def reorder_tasks(data: TaskReorderRequest, db: Session = Depends(get_db)):
    """拖拽后批量更新各列任务的状态与排序（索引即 sort_order）。"""
    for status, ids in (
        ("todo", data.todo),
        ("in_progress", data.in_progress),
        ("done", data.done),
    ):
        for index, task_id in enumerate(ids):
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = status
                task.sort_order = index
    db.commit()
    return {"message": "排序已更新"}


@router.get("")
def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取任务列表"""
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    return query.order_by(Task.created_at.desc()).all()


@router.post("", response_model=TaskResponse)
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    """创建任务"""
    task = Task(**data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取任务详情"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    """更新任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.delete(task)
    db.commit()
    return {"message": "删除成功"}
