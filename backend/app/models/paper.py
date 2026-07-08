"""
论文数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    authors = Column(String(1000), default="")
    abstract = Column(Text, default="")
    journal = Column(String(500), default="")
    year = Column(Integer, nullable=True)
    doi = Column(String(200), default="")
    url = Column(String(1000), default="")
    tags = Column(JSON, default=list)  # 存储标签列表 ["机器学习", "NLP"]
    file_path = Column(String(1000), default="")  # PDF文件存储路径
    fulltext = Column(Text, default="")  # PDF 提取的正文（仅供全文搜索，不返回前端）
    notes_text = Column(Text, default="")  # 快速笔记
    status = Column(String(50), default="unread")  # unread, reading, finished, archived
    rating = Column(Integer, nullable=True)  # 1-5 评分
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联关系
    notes = relationship("Note", back_populates="paper", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Paper(id={self.id}, title='{self.title[:50]}')>"
