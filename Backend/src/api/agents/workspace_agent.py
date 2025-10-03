"""Lightweight workspace agent stub for API endpoints and testing."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from src.core.logging import get_logger
from src.workspace.task_scheduler import (
    WorkspaceTaskScheduler,
    TaskPriority,
    TaskStatus,
    TaskRecord,
)

logger = get_logger(__name__)


@dataclass
class _FileRecord:
    path: Path
    created_at: datetime
    metadata: Dict[str, Any]


class _InMemoryFileManager:
    """Simplified file manager; stores metadata in-memory for testing."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._files: Dict[str, _FileRecord] = {}

    def list_files(
        self,
        directory: Optional[str] = None,
        file_type: Optional[str] = None,
        include_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for record in self._files.values():
            if directory and not str(record.path).startswith(directory):
                continue
            if file_type and not record.path.suffix.lstrip('.') == file_type:
                continue
            entry = {
                "path": str(record.path.relative_to(self._workspace_root)),
                "created_at": record.created_at.isoformat(),
            }
            if include_metadata:
                entry["metadata"] = record.metadata
            results.append(entry)
        return sorted(results, key=lambda item: item["path"])

    def get_workspace_stats(self) -> Dict[str, Any]:
        total_size = sum(record.metadata.get("size", 0) for record in self._files.values())
        return {
            "total_files": len(self._files),
            "total_size_bytes": total_size,
            "workspace_root": str(self._workspace_root),
        }

    def delete_file(self, relative_path: str) -> bool:
        return self._files.pop(relative_path, None) is not None

    def create_or_replace(self, relative_path: str, content: Dict[str, Any]) -> Dict[str, Any]:
        record = _FileRecord(
            path=self._workspace_root / relative_path,
            created_at=datetime.utcnow(),
            metadata={
                "size": len(str(content)),
                "summary": content.get("summary"),
            },
        )
        self._files[relative_path] = record
        return {
            "path": relative_path,
            "created_at": record.created_at.isoformat(),
            "metadata": record.metadata,
        }


class _SimpleMemoryManager:
    """Minimal memory manager stub."""

    def __init__(self) -> None:
        self._stats = {
            "total_memories": 0,
            "recently_accessed": 0,
            "last_refresh": datetime.utcnow().isoformat(),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "timestamp": datetime.utcnow().isoformat()}


class WorkspaceAgent:
    """Fallback workspace agent for on-prem and testing environments."""

    def __init__(self, workspace_name: str, root: Optional[Path] = None) -> None:
        self.workspace_name = workspace_name
        self.workspace_root = root or Path.cwd() / "workspace"
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        self.file_manager = _InMemoryFileManager(self.workspace_root)
        self.task_scheduler = WorkspaceTaskScheduler()
        self.memory_manager = _SimpleMemoryManager()

        logger.info(
            {
                "event": "workspace_agent_initialized",
                "workspace": workspace_name,
                "root": str(self.workspace_root),
            }
        )

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def create_analysis_file(
        self,
        analysis_data: Dict[str, Any],
        filename: Optional[str] = None,
        file_type: str = "json",
    ) -> Dict[str, Any]:
        filename = filename or f"analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        relative_path = f"{filename}.{file_type}" if file_type else filename
        record = self.file_manager.create_or_replace(relative_path, analysis_data)
        return {
            "success": True,
            "message": "Analysis file stored",
            "file": record,
        }

    # ------------------------------------------------------------------
    # Knowledge and workspace summaries
    # ------------------------------------------------------------------

    def get_workspace_summary(self) -> Dict[str, Any]:
        stats = self.file_manager.get_workspace_stats()
        return {
            "workspace": self.workspace_name,
            "files": stats,
            "task_scheduler": self.task_scheduler.get_scheduler_stats(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    def organize_knowledge(self) -> Dict[str, Any]:
        return {
            "workspace": self.workspace_name,
            "actions": ["normalize_metadata", "update_indexes"],
            "timestamp": datetime.utcnow().isoformat(),
        }

    def create_template(
        self,
        template_content: str,
        template_name: str,
        template_type: str = "analysis",
    ) -> Dict[str, Any]:
        rel_path = f"templates/{template_type}/{template_name}.txt"
        record = self.file_manager.create_or_replace(rel_path, {"content": template_content})
        return {
            "success": True,
            "template": record,
        }

    def read_previous_work(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        files = self.file_manager.list_files()
        return files[:limit]

    # ------------------------------------------------------------------
    # Convenience helpers used by health checks/tests
    # ------------------------------------------------------------------

    def as_health_component(self) -> Dict[str, Any]:
        return {
            "workspace_root": str(self.workspace_root),
            "files_cached": len(self.file_manager._files),
            "scheduler_running": self.task_scheduler.is_running,
        }


__all__ = ["WorkspaceAgent"]
