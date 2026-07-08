"""
笔记/知识库 API 路由
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, distinct

from app.database import get_db
from app.models.note import Note
from app.schemas.note_schema import NoteCreate, NoteUpdate, NoteResponse, NoteListResponse
from app import search_index

router = APIRouter(prefix="/notes", tags=["笔记管理"])


@router.get("", response_model=NoteListResponse)
def list_notes(
    folder: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    paper_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """获取笔记列表，支持按文件夹/标签/关键词筛选"""
    query = db.query(Note)

    if folder:
        query = query.filter(Note.folder == folder)
    if paper_id:
        query = query.filter(Note.paper_id == paper_id)
    if search:
        query = query.filter(
            or_(Note.title.contains(search), Note.content.contains(search))
        )

    items = query.order_by(Note.is_pinned.desc(), Note.updated_at.desc()).all()

    # 标签筛选在Python层处理
    if tag:
        items = [n for n in items if tag in (n.tags or [])]

    # 获取所有文件夹
    folders = [f[0] for f in db.query(distinct(Note.folder)).all()]

    return NoteListResponse(items=items, total=len(items), folders=folders)


@router.post("", response_model=NoteResponse)
def create_note(note_data: NoteCreate, db: Session = Depends(get_db)):
    """创建笔记"""
    note = Note(**note_data.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    search_index.index_note(db, note)
    return note


@router.get("/{note_id}", response_model=NoteResponse)
def get_note(note_id: int, db: Session = Depends(get_db)):
    """获取笔记详情"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return note


@router.put("/{note_id}", response_model=NoteResponse)
def update_note(note_id: int, note_data: NoteUpdate, db: Session = Depends(get_db)):
    """更新笔记"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    for key, value in note_data.model_dump(exclude_unset=True).items():
        setattr(note, key, value)

    db.commit()
    db.refresh(note)
    search_index.index_note(db, note)
    return note


@router.delete("/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    """删除笔记"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    db.delete(note)
    db.commit()
    search_index.delete_note_index(db, note_id)
    return {"message": "删除成功"}


@router.get("/tags/all")
def get_all_tags(db: Session = Depends(get_db)):
    """获取所有笔记标签"""
    notes = db.query(Note).all()
    tags = set()
    for note in notes:
        if note.tags:
            tags.update(note.tags)
    return {"tags": sorted(list(tags))}
