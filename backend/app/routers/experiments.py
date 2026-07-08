"""
实验记录 API 路由
"""
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.experiment import Experiment
from app.schemas.experiment_schema import (
    ExperimentCreate, ExperimentUpdate, ExperimentResponse, ExperimentListResponse
)
from app.config import settings

router = APIRouter(prefix="/experiments", tags=["实验记录"])


@router.get("", response_model=ExperimentListResponse)
def list_experiments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    group_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """获取实验记录列表"""
    query = db.query(Experiment)

    if status:
        query = query.filter(Experiment.status == status)
    if search:
        query = query.filter(Experiment.title.contains(search))
    if group_id is not None:
        query = query.filter(Experiment.group_id == group_id)

    total = query.count()
    items = (
        query.order_by(Experiment.experiment_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ExperimentListResponse(items=items, total=total)


@router.post("", response_model=ExperimentResponse)
def create_experiment(data: ExperimentCreate, db: Session = Depends(get_db)):
    """创建实验记录"""
    exp = Experiment(**data.model_dump())
    if not exp.experiment_date:
        exp.experiment_date = datetime.now()
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


@router.get("/{exp_id}", response_model=ExperimentResponse)
def get_experiment(exp_id: int, db: Session = Depends(get_db)):
    """获取实验详情"""
    exp = db.query(Experiment).filter(Experiment.id == exp_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="实验记录不存在")
    return exp


@router.put("/{exp_id}", response_model=ExperimentResponse)
def update_experiment(exp_id: int, data: ExperimentUpdate, db: Session = Depends(get_db)):
    """更新实验记录"""
    exp = db.query(Experiment).filter(Experiment.id == exp_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="实验记录不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(exp, key, value)

    db.commit()
    db.refresh(exp)
    return exp


@router.delete("/{exp_id}")
def delete_experiment(exp_id: int, db: Session = Depends(get_db)):
    """删除实验记录"""
    exp = db.query(Experiment).filter(Experiment.id == exp_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="实验记录不存在")
    db.delete(exp)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{exp_id}/upload", response_model=ExperimentResponse)
async def upload_experiment_attachment(
    exp_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """上传实验附件"""
    exp = db.query(Experiment).filter(Experiment.id == exp_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="实验记录不存在")

    file_ext = Path(file.filename).suffix if file.filename else ""
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    file_path = settings.EXPERIMENTS_DIR / unique_name

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="文件过大")

    file_path.write_bytes(content)

    # 添加附件记录
    attachments = exp.attachments or []
    attachments.append({"name": file.filename, "path": str(file_path)})
    exp.attachments = attachments

    db.commit()
    db.refresh(exp)
    return exp
