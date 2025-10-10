from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Dict, List, Protocol

from src.core.logging import get_logger


logger = get_logger(__name__)


class AgentConfigRepository(Protocol):
    """Port for persisting agent enabled/disabled configuration."""

    def load(self) -> Dict[str, bool]:
        ...

    def save(self, data: Dict[str, bool]) -> None:
        ...


DEFAULT_AGENTS: Dict[str, bool] = {
    # Keep canonical names aligned with IA/ARCHITECTURE.md and existing agents
    "capi_gus": True,
    "branch": True,
    "anomaly": True,
    "capi_desktop": True,
    "capi_datab": True,
    "capi_noticias": False,
    "agente_g": True,
}


@dataclass
class AgentStatus:
    name: str
    enabled: bool


class AgentConfigService:
    """Use-case service to manage agent enable/disable configuration.

    Thread-safe, with lazy-loading cache and repository persistence.
    """

    def __init__(self, repo: AgentConfigRepository):
        self._repo = repo
        self._lock = RLock()
        self._cache: Dict[str, bool] | None = None

    def _ensure_loaded(self) -> None:
        if self._cache is not None:
            return
        with self._lock:
            if self._cache is None:
                try:
                    data = self._repo.load()
                    # merge with defaults to avoid missing keys
                    merged = {**DEFAULT_AGENTS, **(data or {})}
                    self._cache = {k: bool(v) for k, v in merged.items()}
                except Exception as e:
                    logger.error({"event": "agent_config_load_error", "error": str(e)})
                    self._cache = DEFAULT_AGENTS.copy()

    def list_status(self) -> List[AgentStatus]:
        self._ensure_loaded()
        assert self._cache is not None
        return [AgentStatus(name=k, enabled=v) for k, v in sorted(self._cache.items())]

    def is_enabled(self, name: str) -> bool:
        """Check if agent is enabled with fallback validation."""
        self._ensure_loaded()
        assert self._cache is not None

        # Normalize name for lookup
        normalized_name = name.strip().lower()

        # Check cache first
        if normalized_name in self._cache:
            enabled = self._cache[normalized_name]
            logger.debug({"event": "agent_status_check", "agent": normalized_name, "enabled": enabled})
            return enabled

        # Fallback for critical agents
        critical_agents = {"capi_desktop", "capi_datab", "capi_gus", "summary", "branch", "anomaly"}
        if normalized_name in critical_agents:
            logger.warning({"event": "critical_agent_missing_config", "agent": normalized_name, "defaulting_to": True})
            return True

        logger.warning({"event": "unknown_agent_check", "agent": normalized_name, "defaulting_to": False})
        return False

    def set_enabled(self, name: str, enabled: bool) -> Dict[str, bool]:
        self._ensure_loaded()
        with self._lock:
            assert self._cache is not None
            # normalize known canonical names
            key = name.strip().lower()
            self._cache[key] = bool(enabled)
            try:
                self._repo.save(self._cache)
                logger.info({"event": "agent_toggled", "agent": key, "enabled": bool(enabled)})
            except Exception as e:
                logger.error({"event": "agent_config_save_error", "error": str(e)})
            return self._cache.copy()



