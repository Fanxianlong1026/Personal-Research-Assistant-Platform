"""
实验记录数据模型
支持实验分组（多次重复实验/消融实验对比）
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class ExperimentGroup(Base):
    """
    实验组 - 将多个实验运行归为一组进行对比
    场景：重复实验验证稳定性、消融实验对比不同配置
    """
    __tablename__ = "experiment_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text, default="")
    base_parameters = Column(JSON, default=dict)  # 基准参数（消融实验的 baseline）
    compare_metrics = Column(JSON, default=list)  # 关注的对比指标 ["accuracy", "f1"]
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联：一个实验组包含多个实验运行
    runs = relationship("Experiment", back_populates="group", cascade="all, delete-orphan",
                        order_by="Experiment.run_number")

    def __repr__(self):
        return f"<ExperimentGroup(id={self.id}, name='{self.name[:50]}')>"


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, default="")
    experiment_date = Column(DateTime, default=datetime.now)
    parameters = Column(JSON, default=dict)  # 实验参数 {"lr": 0.001, "batch_size": 32}
    results = Column(Text, default="")
    metrics = Column(JSON, default=dict)  # 量化指标 {"accuracy": 0.95, "loss": 0.05}
    attachments = Column(JSON, default=list)
    status = Column(String(50), default="running")
    tags = Column(JSON, default=list)

    # 实验分组字段
    group_id = Column(Integer, ForeignKey("experiment_groups.id"), nullable=True)  # 所属实验组
    run_number = Column(Integer, default=1)  # 组内运行编号 (Run 1, Run 2, ...)
    variant = Column(String(200), default="")  # 变体名称，如 "w/o Attention", "lr=0.01"
    notes = Column(Text, default="")  # 本次运行的特别备注

    # 关联关系
    group = relationship("ExperimentGroup", back_populates="runs")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Experiment(id={self.id}, title='{self.title[:50]}', run={self.run_number})>"
