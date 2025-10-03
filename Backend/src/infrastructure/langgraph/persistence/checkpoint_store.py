"""
Checkpoint store abstractions for LangGraph runtime.
Default in-memory implementation; extensible for Redis or file-backed.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class CheckpointStore(ABC):
    @abstractmethod
    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def save(self, session_id: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, session_id: str) -> None:
        raise NotImplementedError


class InMemoryCheckpointStore(CheckpointStore):
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}
        self._expiry: Dict[str, datetime] = {}
        self._ttl = ttl_seconds

    def _sweep(self) -> None:
        now = datetime.now()
        expired = [sid for sid, exp in self._expiry.items() if exp < now]
        for sid in expired:
            self._data.pop(sid, None)
            self._expiry.pop(sid, None)

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        self._sweep()
        return self._data.get(session_id)

    def save(self, session_id: str, data: Dict[str, Any]) -> None:
        self._sweep()
        self._data[session_id] = data
        self._expiry[session_id] = datetime.now() + timedelta(seconds=self._ttl)

    def delete(self, session_id: str) -> None:
        self._data.pop(session_id, None)
        self._expiry.pop(session_id, None)
