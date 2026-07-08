"""
论文管理 API 路由
"""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import PlainTextResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.paper import Paper
from app.schemas.paper_schema import (
    PaperCreate,
    PaperUpdate,
    PaperResponse,
    PaperListResponse,
    PaperImportRequest,
    BibtexImportRequest,
    PdfDownloadRequest,
)
from app.config import settings
from app import search_index, paper_import, bibtex, pdf_extract

router = APIRouter(prefix="/papers", tags=["论文管理"])


@router.get("", response_model=PaperListResponse)
def list_papers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取论文列表，支持搜索和筛选"""
    query = db.query(Paper)

    if search:
        query = query.filter(
            or_(
                Paper.title.contains(search),
                Paper.authors.contains(search),
                Paper.abstract.contains(search),
            )
        )
    if status:
        query = query.filter(Paper.status == status)

    total = query.count()
    items = query.order_by(Paper.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # 按标签筛选需要在Python层处理（SQLite JSON支持有限）
    if tag:
        items = [p for p in items if tag in (p.tags or [])]
        total = len(items)

    return PaperListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/import")
async def import_paper_metadata(data: PaperImportRequest):
    """根据 DOI 或 arXiv 标识拉取论文元数据（不落库，供前端填表预览）。"""
    try:
        return await paper_import.fetch_metadata(data.identifier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=502, detail="拉取元数据失败，请检查网络或稍后重试")


@router.get("/export/bibtex", response_class=PlainTextResponse)
def export_bibtex(ids: Optional[str] = None, db: Session = Depends(get_db)):
    """导出 BibTeX。ids 为逗号分隔的论文 id（留空导出全部）。"""
    query = db.query(Paper)
    if ids:
        id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
        query = query.filter(Paper.id.in_(id_list)) if id_list else query
    papers = query.order_by(Paper.created_at.desc()).all()
    return bibtex.to_bibtex(papers)


@router.post("/import-bibtex")
def import_bibtex(data: BibtexImportRequest, db: Session = Depends(get_db)):
    """解析 .bib 文本并批量建库，返回新建数量。"""
    parsed = bibtex.parse_bibtex(data.content)
    created = 0
    for fields in parsed:
        paper = Paper(**fields)
        db.add(paper)
        db.commit()
        db.refresh(paper)
        search_index.index_paper(db, paper)
        created += 1
    return {"created": created, "parsed": len(parsed)}


@router.post("", response_model=PaperResponse)
def create_paper(paper_data: PaperCreate, db: Session = Depends(get_db)):
    """创建论文记录"""
    paper = Paper(**paper_data.model_dump())
    db.add(paper)
    db.commit()
    db.refresh(paper)
    search_index.index_paper(db, paper)
    return paper


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    """获取论文详情"""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    return paper


@router.put("/{paper_id}", response_model=PaperResponse)
def update_paper(paper_id: int, paper_data: PaperUpdate, db: Session = Depends(get_db)):
    """更新论文信息"""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")

    update_data = paper_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(paper, key, value)

    db.commit()
    db.refresh(paper)
    search_index.index_paper(db, paper)
    return paper


@router.delete("/{paper_id}")
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    """删除论文"""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")

    # 删除关联的PDF文件
    if paper.file_path:
        file = Path(paper.file_path)
        if file.exists():
            file.unlink()

    db.delete(paper)
    db.commit()
    search_index.delete_paper_index(db, paper_id)
    return {"message": "删除成功"}


@router.post("/{paper_id}/upload", response_model=PaperResponse)
async def upload_paper_file(paper_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传论文PDF文件"""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")

    # 验证文件类型
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持PDF文件")

    # 生成唯一文件名
    file_ext = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    file_path = settings.PAPERS_DIR / unique_name

    # 保存文件
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="文件过大，最大支持50MB")

    file_path.write_bytes(content)
    paper.file_path = str(file_path)

    # 提取 PDF 正文，写入 fulltext 并刷新全文索引（缺 PyMuPDF 时返回空串，不影响上传）
    paper.fulltext = pdf_extract.extract_text(str(file_path))

    db.commit()
    db.refresh(paper)
    search_index.index_paper(db, paper)
    return paper


@router.post("/{paper_id}/extract")
def extract_paper_fulltext(paper_id: int, db: Session = Depends(get_db)):
    """为已上传 PDF 的论文（重新）提取正文并刷新全文索引。返回提取字符数。"""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    if not paper.file_path or not Path(paper.file_path).exists():
        raise HTTPException(status_code=404, detail="该论文未上传 PDF")
    if not pdf_extract.is_available():
        raise HTTPException(status_code=503, detail="服务端未安装 PyMuPDF，无法提取正文")

    paper.fulltext = pdf_extract.extract_text(paper.file_path)
    db.commit()
    db.refresh(paper)
    search_index.index_paper(db, paper)
    return {"chars": len(paper.fulltext or "")}


@router.post("/{paper_id}/download-pdf", response_model=PaperResponse)
async def download_paper_pdf(paper_id: int, data: PdfDownloadRequest, db: Session = Depends(get_db)):
    """从给定 URL 下载 PDF 存入论文目录、关联到该论文，并提取正文进全文索引。"""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")

    try:
        content = await paper_import.download_pdf(data.url, settings.MAX_UPLOAD_SIZE)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    unique_name = f"{uuid.uuid4().hex}.pdf"
    file_path = settings.PAPERS_DIR / unique_name
    file_path.write_bytes(content)
    paper.file_path = str(file_path)
    paper.fulltext = pdf_extract.extract_text(str(file_path))

    db.commit()
    db.refresh(paper)
    search_index.index_paper(db, paper)
    return paper


@router.get("/{paper_id}/fulltext")
def get_paper_fulltext(paper_id: int, db: Session = Depends(get_db)):
    """返回该论文已提取的 PDF 正文（fulltext 列内容）。"""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    text_ = paper.fulltext or ""
    return {"fulltext": text_, "chars": len(text_)}


@router.get("/{paper_id}/file")
def get_paper_file(paper_id: int, db: Session = Depends(get_db)):
    """返回论文 PDF 文件，供前端打开/下载。"""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    if not paper.file_path or not Path(paper.file_path).exists():
        raise HTTPException(status_code=404, detail="该论文未上传 PDF")
    # content_disposition_type="inline"：让浏览器内嵌渲染（iframe 阅读），而非强制下载
    return FileResponse(
        paper.file_path,
        media_type="application/pdf",
        filename=Path(paper.file_path).name,
        content_disposition_type="inline",
    )


@router.get("/tags/all")
def get_all_tags(db: Session = Depends(get_db)):
    """获取所有已使用的标签"""
    papers = db.query(Paper).all()
    tags = set()
    for paper in papers:
        if paper.tags:
            tags.update(paper.tags)
    return {"tags": sorted(list(tags))}
