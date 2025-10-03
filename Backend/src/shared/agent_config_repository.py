from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from src.core.logging import get_logger


logger = get_logger(__name__)


class FileAgentConfigRepository:
    """JSON-file based repository for agent enable/disable configuration."""

    def __init__(self, base_dir: str | Path = None, filename: str = "agents_config.json") -> None:
        if base_dir is None:
            # ARCHITECTURE.md compliance: shared/ no debe acceder a ia_workspace
            # Usar directorio temporal en memoria para configuración de agentes
            import tempfile
            base_dir = Path(tempfile.gettempdir()) / "capi_agents"
        self._path = Path(base_dir) / filename
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, bool]:
        if not self._path.exists():
            return {}
        try:
            text = self._path.read_text(encoding="utf-8")
            if not text.strip():
                return {}
            data = json.loads(text)
            if isinstance(data, dict):
                # Ensure bool casting
                return {str(k).lower(): bool(v) for k, v in data.items()}
            logger.warning({"event": "agent_config_invalid_format", "path": str(self._path)})
            return {}
        except Exception as e:
            logger.error({"event": "agent_config_load_error", "error": str(e), "path": str(self._path)})
            return {}

    def save(self, data: Dict[str, bool]) -> None:
        try:
            self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        except Exception as e:
            logger.error({"event": "agent_config_save_error", "error": str(e), "path": str(self._path)})
            raise
