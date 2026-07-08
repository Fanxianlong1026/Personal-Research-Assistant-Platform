"""实验记录请求/响应模型"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ========== 实验运行 Schema（必须定义在 ExperimentGroupDetailResponse 之前） ==========

class ExperimentCreate(BaseModel):
    title: str
    description: str = ""
    experiment_date: Optional[datetime] = None
    parameters: Dict[str, Any] = {}
    results: str = ""
    metrics: Dict[str, Any] = {}
    status: str = "running"
    tags: List[str] = []
    group_id: Optional[int] = None
    run_number: int = 1
    variant: str = ""
    notes: str = ""


class ExperimentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    experiment_date: Optional[datetime] = None
    parameters: Optional[Dict[str, Any]] = None
    results: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    group_id: Optional[int] = None
    run_number: Optional[int] = None
    variant: Optional[str] = None
    notes: Optional[str] = None


class ExperimentResponse(BaseModel):
    id: int
    title: str
    description: str
    experiment_date: datetime
    parameters: dict
    results: str
    metrics: dict
    attachments: list
    status: str
    tags: list
    group_id: Optional[int]
    run_number: int
    variant: str
    notes: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExperimentListResponse(BaseModel):
    items: List[ExperimentResponse]
    total: int


# ========== 实验组 Schema ==========

class ExperimentGroupCreate(BaseModel):
    name: str
    description: str = ""
    base_parameters: Dict[str, Any] = {}
    compare_metrics: List[str] = []


class ExperimentGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_parameters: Optional[Dict[str, Any]] = None
    compare_metrics: Optional[List[str]] = None


class ExperimentGroupResponse(BaseModel):
    id: int
    name: str
    description: str
    base_parameters: dict
    compare_metrics: list
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExperimentGroupDetailResponse(BaseModel):
    """实验组详情（含所有运行记录）"""
    id: int
    name: str
    description: str
    base_parameters: dict
    compare_metrics: list
    runs: List[ExperimentResponse]
    comparison_summary: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
