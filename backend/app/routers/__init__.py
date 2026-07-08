"""API路由统一注册"""
from app.routers import papers, notes, experiments, experiment_groups, tasks, ai

__all__ = ["papers", "notes", "experiments", "experiment_groups", "tasks", "ai"]
