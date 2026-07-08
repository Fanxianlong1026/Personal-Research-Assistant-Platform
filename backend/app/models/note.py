"""
笔记/知识库数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, default="")  # Markdown 内容
    folder = Column(String(200), default="default")  # 文件夹分类
    tags = Column(JSON, default=list)  # 标签列表
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=True)  # 可关联论文
    is_pinned = Column(Integer, default=0)  # 是否置顶
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联关系
    paper = relationship("Paper", back_populates="notes")

    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title[:50]}')>"
