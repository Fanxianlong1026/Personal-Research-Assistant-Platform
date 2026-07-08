"""
实验组 API 路由
管理实验分组、多次运行对比、消融实验
"""
from typing import Optional, List
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.experiment import ExperimentGroup, Experiment
from app.schemas.experiment_schema import (
    ExperimentGroupCreate, ExperimentGroupUpdate,
    ExperimentGroupResponse, ExperimentGroupDetailResponse,
    ExperimentResponse,
)

router = APIRouter(prefix="/experiment-groups", tags=["实验组管理"])


def _compute_comparison_summary(runs: List[Experiment], compare_metrics: List[str]) -> dict:
    """
    自动计算对比摘要：
    - 每个指标的 均值、最大值、最小值、标准差
    - 最佳运行（按第一个 compare_metric）
    - 参数差异检测（哪些参数在不同 run 之间变化了）
    """
    if not runs:
        return {}

    summary = {}

    # 指标统计
    metrics_list = compare_metrics or _collect_all_metric_keys(runs)
    for metric in metrics_list:
        values = []
        for run in runs:
            v = (run.metrics or {}).get(metric)
            if v is not None:
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    pass
        if values:
            mean = sum(values) / len(values)
            summary[metric] = {
                "mean": round(mean, 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "std": round((sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5, 4),
                "count": len(values),
            }

    # 最佳运行
    if metrics_list and summary.get(metrics_list[0]):
        best_metric = metrics_list[0]
        best_run = None
        best_val = float("-inf")
        for run in runs:
            v = (run.metrics or {}).get(best_metric)
            if v is not None:
                try:
                    fv = float(v)
                    if fv > best_val:
                        best_val = fv
                        best_run = run
                except (ValueError, TypeError):
                    pass
        if best_run:
            summary["best_run"] = {
                "id": best_run.id,
                "variant": best_run.variant or best_run.title,
                "run_number": best_run.run_number,
                "value": best_val,
            }

    # 参数差异检测：找出哪些参数在不同 run 之间变化了
    if len(runs) > 1:
        all_params = [run.parameters or {} for run in runs]
        all_keys = set()
        for p in all_params:
            all_keys.update(p.keys())

        diff_params = []
        for key in all_keys:
            values = set(str(p.get(key, "N/A")) for p in all_params)
            if len(values) > 1:
                diff_params.append({
                    "key": key,
                    "values": [p.get(key, "N/A") for p in all_params],
                })
        if diff_params:
            summary["parameter_differences"] = diff_params

    return summary


def _collect_all_metric_keys(runs: List[Experiment]) -> List[str]:
    """收集所有运行中出现的指标 key"""
    keys = set()
    for run in runs:
        if run.metrics:
            keys.update(run.metrics.keys())
    return sorted(keys)


# ========== CRUD ==========

@router.get("", response_model=List[ExperimentGroupResponse])
def list_groups(db: Session = Depends(get_db)):
    """获取所有实验组"""
    return db.query(ExperimentGroup).order_by(ExperimentGroup.created_at.desc()).all()


@router.post("", response_model=ExperimentGroupResponse)
def create_group(data: ExperimentGroupCreate, db: Session = Depends(get_db)):
    """创建实验组"""
    group = ExperimentGroup(**data.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/{group_id}", response_model=ExperimentGroupDetailResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    """获取实验组详情（含所有运行记录和对比摘要）"""
    group = db.query(ExperimentGroup).filter(ExperimentGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="实验组不存在")

    runs = sorted(group.runs, key=lambda r: r.run_number)
    comparison_summary = _compute_comparison_summary(runs, group.compare_metrics or [])

    return ExperimentGroupDetailResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        base_parameters=group.base_parameters or {},
        compare_metrics=group.compare_metrics or [],
        runs=runs,
        comparison_summary=comparison_summary,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@router.put("/{group_id}", response_model=ExperimentGroupResponse)
def update_group(group_id: int, data: ExperimentGroupUpdate, db: Session = Depends(get_db)):
    """更新实验组"""
    group = db.query(ExperimentGroup).filter(ExperimentGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="实验组不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(group, key, value)

    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    """删除实验组（同时删除组内所有运行记录）"""
    group = db.query(ExperimentGroup).filter(ExperimentGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="实验组不存在")
    db.delete(group)
    db.commit()
    return {"message": "删除成功"}


# ========== 对比功能 ==========

@router.get("/{group_id}/compare")
def compare_runs(group_id: int, db: Session = Depends(get_db)):
    """
    获取对比数据：以表格形式返回所有 run 的参数和指标
    方便前端渲染对比表格
    """
    group = db.query(ExperimentGroup).filter(ExperimentGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="实验组不存在")

    runs = sorted(group.runs, key=lambda r: r.run_number)
    all_metric_keys = _collect_all_metric_keys(runs)
    all_param_keys = set()
    for run in runs:
        if run.parameters:
            all_param_keys.update(run.parameters.keys())
    all_param_keys = sorted(all_param_keys)

    # 构建对比行
    rows = []
    for run in runs:
        row = {
            "id": run.id,
            "run_number": run.run_number,
            "variant": run.variant or run.title,
            "status": run.status,
            "date": str(run.experiment_date),
        }
        # 参数
        row["parameters"] = {k: (run.parameters or {}).get(k, "N/A") for k in all_param_keys}
        # 指标
        row["metrics"] = {k: (run.metrics or {}).get(k, "N/A") for k in all_metric_keys}
        rows.append(row)

    return {
        "group_id": group.id,
        "group_name": group.name,
        "base_parameters": group.base_parameters or {},
        "param_keys": all_param_keys,
        "metric_keys": all_metric_keys,
        "rows": rows,
        "summary": _compute_comparison_summary(runs, group.compare_metrics or []),
    }


@router.post("/{group_id}/add-run", response_model=ExperimentResponse)
def add_run_to_group(group_id: int, db: Session = Depends(get_db)):
    """
    向实验组添加一次新的运行
    自动计算 run_number（当前最大 + 1）
    """
    group = db.query(ExperimentGroup).filter(ExperimentGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="实验组不存在")

    # 计算下一个 run_number
    max_run = max((r.run_number for r in group.runs), default=0)
    next_run = max_run + 1

    # 创建新实验，继承组的基准参数
    exp = Experiment(
        title=f"{group.name} - Run {next_run}",
        group_id=group_id,
        run_number=next_run,
        parameters=group.base_parameters.copy() if group.base_parameters else {},
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp
