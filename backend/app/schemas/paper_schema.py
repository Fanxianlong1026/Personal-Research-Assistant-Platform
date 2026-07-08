"""论文请求/响应模型"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class PaperCreate(BaseModel):
    title: str
    authors: str = ""
    abstract: str = ""
    journal: str = ""
    year: Optional[int] = None
    doi: str = ""
    url: str = ""
    tags: List[str] = []
    status: str = "unread"
    rating: Optional[int] = None


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = None
    notes_text: Optional[str] = None
    status: Optional[str] = None
    rating: Optional[int] = None


class PaperResponse(BaseModel):
    id: int
    title: str
    authors: str
    abstract: str
    journal: str
    year: Optional[int]
    doi: str
    url: str
    tags: list
    file_path: str
    notes_text: str
    status: str
    rating: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaperListResponse(BaseModel):
    items: List[PaperResponse]
    total: int
    page: int
    page_size: int


class PaperImportRequest(BaseModel):
    identifier: str


class BibtexImportRequest(BaseModel):
    content: str


class PdfDownloadRequest(BaseModel):
    url: str
