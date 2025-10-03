"""Minimal task scheduler primitives for workspace API compatibility."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Dict, Optional, List


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskRecord:
    task_id: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    extra: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            **self.extra,
        }


class WorkspaceTaskScheduler:
    """In-memory scheduler stub for testing and offline environments."""

    def __init__(self) -> None:
        self.is_running = True
        self._tasks: Dict[str, TaskRecord] = {}

    def schedule_task(self, task: TaskRecord) -> None:
        self._tasks[task.task_id] = task

    def list_tasks(self, status_filter: Optional[TaskStatus] = None, limit: int = 50) -> List[Dict[str, str]]:
        tasks = list(self._tasks.values())
        if status_filter:
            tasks = [task for task in tasks if task.status == status_filter]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return [task.to_dict() for task in tasks[:limit]]

    def get_task_status(self, task_id: str) -> Optional[Dict[str, str]]:
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED}:
            return False
        task.status = TaskStatus.CANCELLED
        return True

    def get_scheduler_stats(self) -> Dict[str, int | bool]:
        counts: Dict[str, int] = {status.value: 0 for status in TaskStatus}
        for task in self._tasks.values():
            counts[task.status.value] += 1
        return {
            "running": self.is_running,
            **counts,
            "total_tasks": len(self._tasks),
        }

    def stop_scheduler(self) -> None:
        self.is_running = False

__all__ = [
    "TaskPriority",
    "TaskStatus",
    "TaskRecord",
    "WorkspaceTaskScheduler",
]
