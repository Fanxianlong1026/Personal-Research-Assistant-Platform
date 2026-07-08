"""
任务管理数据模型
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, JSON

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, default="")
    status = Column(String(50), default="todo")  # todo, in_progress, done, cancelled
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    due_date = Column(Date, nullable=True)  # 截止日期
    tags = Column(JSON, default=list)
    related_paper_id = Column(Integer, nullable=True)  # 可关联论文
    related_note_id = Column(Integer, nullable=True)  # 可关联笔记
    sort_order = Column(Integer, default=0)  # 看板排序
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title[:50]}')>"
