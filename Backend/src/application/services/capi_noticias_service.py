"""Capi Noticias scheduler service."""
from __future__ import annotations

import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from src.core.logging import get_logger

CURRENT_DIR = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_DIR.parents[3]
IA_WORKSPACE = BACKEND_ROOT / "ia_workspace"
if str(IA_WORKSPACE) not in sys.path:
    sys.path.append(str(IA_WORKSPACE))

from agentes.capi_noticias.handler import CapiNoticiasAgent, CapiNoticiasConfigManager  # noqa: E402

logger = get_logger(__name__)


class CapiNoticiasSchedulerService:
    """Gestiona la ejecucion automatica del agente Capi Noticias."""

    def __init__(self) -> None:
        self.agent = CapiNoticiasAgent()
        self.config_manager = CapiNoticiasConfigManager()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._next_run: Optional[datetime] = None
        self._last_result: Optional[Dict[str, Any]] = None
        self._last_error: Optional[str] = None
        self._last_trigger: Optional[str] = None
        self._is_executing = False

    # ------------------------------------------------------------------
    # Control de scheduler
    # ------------------------------------------------------------------
    def start(self) -> None:
        with self._lock:
            config = self.config_manager.load_config()
            if not config.get("enabled", True):
                self.config_manager.save_config({"enabled": True})
            if self._thread and self._thread.is_alive():
                logger.info("[capi_noticias] Scheduler already running")
                return
            self._stop_event.clear()
            self.refresh_schedule()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="capi-noticias-scheduler",
                daemon=True,
            )
            self._thread.start()
            logger.info("[capi_noticias] Scheduler started")

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
            self._thread = None
            logger.info("[capi_noticias] Scheduler stopped")

    def refresh_schedule(self) -> None:
        with self._lock:
            config = self.config_manager.load_config()
            interval = max(5, config.get("interval_minutes", 60))
            self._next_run = datetime.utcnow() + timedelta(minutes=interval)
            logger.info("[capi_noticias] Next run scheduled at %s", self._next_run.isoformat())

    # ------------------------------------------------------------------
    # Ejecucion manual
    # ------------------------------------------------------------------
    def trigger_run(
        self,
        *,
        trigger: str = "manual",
        source_urls: Optional[Iterable[str]] = None,
        max_articles_per_source: Optional[int] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            result = self._execute_cycle(
                trigger=trigger,
                override_interval=None,
                source_override=list(source_urls) if source_urls else None,
                per_source_override=max_articles_per_source,
            )
            return result or {}

    # ------------------------------------------------------------------
    # Configuracion
    # ------------------------------------------------------------------
    def update_configuration(
        self,
        *,
        interval_minutes: Optional[int] = None,
        source_urls: Optional[Iterable[str]] = None,
        max_articles_per_source: Optional[int] = None,
        enabled: Optional[bool] = None,
        segments: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if interval_minutes is not None:
            payload["interval_minutes"] = max(5, int(interval_minutes))
        if max_articles_per_source is not None:
            payload["max_articles_per_source"] = max(1, int(max_articles_per_source))
        if source_urls is not None:
            payload["source_urls"] = [
                url.strip() for url in source_urls if isinstance(url, str) and url.strip()
            ]
        if enabled is not None:
            payload["enabled"] = bool(enabled)
        if segments is not None:
            payload["segments"] = segments

        if payload:
            config = self.config_manager.save_config(payload)
            logger.info("[capi_noticias] Configuration updated: %s", payload)
            self.refresh_schedule()
        else:
            config = self.config_manager.load_config()
        return config

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        config = self.config_manager.load_config()
        status = self.config_manager.load_status()
        with self._lock:
            next_run = self._next_run.isoformat() if self._next_run else status.get("next_run")
            return {
                "config": config,
                "status": {
                    **status,
                    "next_run": next_run,
                    "is_executing": self._is_executing,
                    "last_error": self._last_error,
                    "last_result": self._last_result,
                    "last_trigger": self._last_trigger,
                },
            }

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------
    def _run_loop(self) -> None:
        logger.info("[capi_noticias] Scheduler loop started")
        while not self._stop_event.is_set():
            config = self.config_manager.load_config()
            if not config.get("enabled", True):
                time.sleep(10)
                continue

            with self._lock:
                now = datetime.utcnow()
                interval = max(5, config.get("interval_minutes", 60))
                if self._next_run is None or now >= self._next_run:
                    logger.info("[capi_noticias] Executing scheduled run at %s", now.isoformat())
                    self._execute_cycle(
                        trigger="scheduler",
                        override_interval=interval,
                        source_override=None,
                        per_source_override=None,
                    )
                wait_seconds = max(5.0, min(60.0, (self._next_run - now).total_seconds())) if self._next_run else 30.0

            self._stop_event.wait(wait_seconds)

        logger.info("[capi_noticias] Scheduler loop ended")

    def _execute_cycle(
        self,
        *,
        trigger: str,
        override_interval: Optional[int],
        source_override: Optional[Iterable[str]],
        per_source_override: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        if self._is_executing:
            logger.info("[capi_noticias] Execution already in progress, skipping trigger=%s", trigger)
            return None

        self._is_executing = True
        try:
            result = self.agent.run_cycle(
                trigger=trigger,
                source_override=source_override,
                per_source_override=per_source_override,
            )
            with self._lock:
                self._last_result = result
                self._last_error = None
                self._last_trigger = trigger
                if override_interval is not None:
                    self._next_run = datetime.utcnow() + timedelta(minutes=max(5, override_interval))
                else:
                    config = self.config_manager.load_config()
                    interval = max(5, config.get("interval_minutes", 60))
                    self._next_run = datetime.utcnow() + timedelta(minutes=interval)
            return result
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("[capi_noticias] Error during run: %s", exc)
            with self._lock:
                self._last_error = str(exc)
                self._last_trigger = trigger
            return None
        finally:
            self._is_executing = False


_scheduler_instance: Optional[CapiNoticiasSchedulerService] = None


def get_capi_noticias_scheduler() -> CapiNoticiasSchedulerService:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = CapiNoticiasSchedulerService()
    return _scheduler_instance
