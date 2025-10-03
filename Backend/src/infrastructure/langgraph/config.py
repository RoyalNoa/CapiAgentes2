"""
Configuration for LangGraph runtime, reading from environment or application settings.
This module exposes a small, stable interface consumed by the builder and runtime.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LangGraphConfig:
    enabled: bool = False
    checkpoint_enabled: bool = True
    checkpoint_backend: str = "memory"  # memory | redis | file
    checkpoint_ttl_seconds: int = 3600
    max_steps: int = 50
    emit_frontend_events: bool = True


def from_env(prefix: str = "USE_LANGGRAPH_") -> LangGraphConfig:
    def _bool(name: str, default: bool) -> bool:
        val = os.getenv(prefix + name)
        if val is None:
            return default
        return val.strip().lower() in {"1", "true", "yes", "on"}

    def _int(name: str, default: int) -> int:
        try:
            val = os.getenv(prefix + name)
            return int(val) if val is not None else default
        except Exception:
            return default

    return LangGraphConfig(
        enabled=_bool("ENABLED", False),
        checkpoint_enabled=_bool("CHECKPOINT_ENABLED", True),
        checkpoint_backend=os.getenv(prefix + "CHECKPOINT_BACKEND", "memory"),
        checkpoint_ttl_seconds=_int("CHECKPOINT_TTL_SECONDS", 3600),
        max_steps=_int("MAX_STEPS", 50),
        emit_frontend_events=_bool("EMIT_FRONTEND_EVENTS", True),
    )
