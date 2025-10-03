#!/usr/bin/env python3
"""
CAPI - Orchestrator Factory
===========================
Ruta: /Backend/src/presentation/orchestrator_factory.py
Descripción: Factory para crear instancias del Orquestador respetando arquitectura
hexagonal. Mantiene imports unidireccionales - Backend/src NO importa ia_workspace
Estado: ✅ ARQUITECTURA CORE - Factory pattern de orquestadores
Dependencias: Dynamic imports, ia_workspace/orchestrator
Propósito: Creación controlada de orquestadores manteniendo separación arquitectónica
Patrón: Factory Method para abstracción de creación de objetos
"""

import sys
import os
import importlib
from pathlib import Path
from typing import Any, Literal
import os
from src.core.logging import get_logger

logger = get_logger(__name__)


class OrchestratorFactory:
    """Factory to create the LangGraph orchestrator without direct imports"""

    @staticmethod
    def create_orchestrator(
        memory_window: int = 20,
        memory_ttl_minutes: int = 120,
        enable_narrative: bool = False,
        confidence_threshold: float = 0.6,
        orchestrator_type: Literal["default", "langgraph"] = "langgraph",
        api_port: str = "8000"
    ) -> Any:
        """
        Creates orchestrator instance without direct import dependency

        Args:
            memory_window: Size of conversation memory window
            memory_ttl_minutes: TTL for session cleanup
            enable_narrative: Enable conversational narrative
            confidence_threshold: Confidence threshold for intents
            orchestrator_type: Type of orchestrator to create. Ignored; LangGraph is always used.
            api_port: Port number for API token recording endpoints

        Returns:
            Orchestrator instance
        """
        # LangGraph is the single orchestrator; keep explicit selection log
        orchestrator_type = "langgraph"
        logger.info({"event": "orchestrator_selection", "type": orchestrator_type})

        # Instantiate LangGraph adapter with config from env
        try:
            from src.infrastructure.langgraph.adapters.orchestrator_adapter import (
                LangGraphOrchestratorAdapter,
            )
            config = {
                "checkpoint_ttl_seconds": int(os.getenv("USE_LANGGRAPH_CHECKPOINT_TTL_SECONDS", "3600")),
                "max_steps": int(os.getenv("USE_LANGGRAPH_MAX_STEPS", "50")),
                "api_port": api_port,
            }
            return LangGraphOrchestratorAdapter(config=config)
        except ImportError as e:
            raise RuntimeError(f"Could not create LangGraph orchestrator: {e}")