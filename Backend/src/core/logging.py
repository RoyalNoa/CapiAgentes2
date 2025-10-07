"""
CAPI - Sistema de Logging Unificado (Version Definitiva)
=======================================================
Configuracion unica de logging para todo el sistema.
Elimina conflictos entre uvicorn, FastAPI y la aplicacion principal.

ARCHITECTURE.md Compliance:
- Logs almacenados en la carpeta raíz logs/
- Sin duplicacion de configuraciones
- Sistema limpio y claro para IA
"""

from __future__ import annotations

import asyncio
import builtins
import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

try:
    from pythonjsonlogger.json import JsonFormatter as _JsonFormatterBase  # type: ignore[attr-defined]
except ImportError:
    try:
        from pythonjsonlogger import jsonlogger as _legacy_jsonlogger  # type: ignore
    except ImportError:
        _JsonFormatterBase = None  # type: ignore[assignment]
    else:
        _JsonFormatterBase = _legacy_jsonlogger.JsonFormatter  # type: ignore[attr-defined]
else:
    _legacy_jsonlogger = None


LOG_FILE_NAME = "backend.log"
SERVICE_NAME = os.getenv("SERVICE_NAME", "backend")
LOG_PREFIX = "[Backend]"
DEFAULT_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
DEFAULT_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))


class UnifiedFormatter(logging.Formatter):
    """Formateador legible para entornos locales."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname.upper()
        logger_name = record.name
        message = record.getMessage()

        context_parts: list[str] = []
        for key in ("request_id", "session_id", "client_id", "trace_id", "agent_name"):
            value = getattr(record, key, None)
            if value is not None:
                context_parts.append(f"{key}={value}")

        log_context = getattr(record, "log_context", None)
        if log_context:
            context_parts.append(str(log_context))

        context_segment = (" | " + " ".join(context_parts)) if context_parts else ""
        return f"[{timestamp}] {LOG_PREFIX} [{level}] [{logger_name}] {message}{context_segment}"


if _JsonFormatterBase is not None:

    class JsonFormatter(_JsonFormatterBase):
        """Formatter JSON compatible con Elastic y Loki."""

        def add_fields(
            self,
            log_record: Dict[str, Any],
            record: logging.LogRecord,
            message_dict: Dict[str, Any],
        ) -> None:  # type: ignore[override]
            super().add_fields(log_record, record, message_dict)

            if "timestamp" not in log_record:
                log_record["timestamp"] = datetime.fromtimestamp(record.created).isoformat(timespec="milliseconds")
            log_record.setdefault("service", SERVICE_NAME)
            log_record.setdefault("logger", record.name)
            log_record.setdefault("level", record.levelname.upper())

            message = log_record.get("message")
            if isinstance(message, (dict, list)):
                log_record["message"] = json.dumps(message, ensure_ascii=False)

            for key in ("request_id", "session_id", "client_id", "trace_id", "agent_name", "log_context"):
                value = getattr(record, key, None)
                if value is not None and key not in log_record:
                    log_record[key] = value

            if "exc_info" in log_record and isinstance(log_record["exc_info"], str) and not log_record["exc_info"]:
                log_record.pop("exc_info", None)


    class JsonConsoleFormatter(JsonFormatter):
        """Formatter JSON compacto para consola."""

        def process_log_record(self, log_record: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
            return log_record

else:

    class JsonFormatter(UnifiedFormatter):
        """Fallback formatter cuando python-json-logger no esta disponible."""

    class JsonConsoleFormatter(JsonFormatter):  # type: ignore[misc]
        pass


_logging_configured = False


def _build_log_file_path() -> Path:
    env_dir = os.getenv('CAPI_LOG_DIR')
    if env_dir:
        base_path = Path(env_dir)
    elif os.name != 'nt' and os.path.exists('/app'):
        base_path = Path('/app/logs')
    else:
        base_path = Path(__file__).resolve().parents[3] / 'logs'
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path / LOG_FILE_NAME



_exceptions_hooked = False


def _install_exception_hooks() -> None:
    global _exceptions_hooked
    if _exceptions_hooked:
        return

    def handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.getLogger('backend.uncaught').error('Uncaught exception', exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        def handle_async_exception(_loop, context) -> None:
            message = context.get('message', 'Unhandled asyncio exception')
            exception = context.get('exception')
            logger = logging.getLogger('backend.asyncio')
            if exception is not None:
                logger.error(message, exc_info=exception)
            else:
                logger.error(message, extra={'context': context})

        loop.set_exception_handler(handle_async_exception)

    _exceptions_hooked = True


def _configure_print_redirect(logger: logging.Logger) -> None:
    original_print = builtins.print

    def logging_print(
        *values: object,
        sep: str = " ",
        end: str = "\n",
        file: object | None = None,
        flush: bool = False,
    ) -> None:
        if file not in (None, sys.stdout, sys.stderr):
            original_print(*values, sep=sep, end=end, file=file, flush=flush)
            return

        message = sep.join(str(v) for v in values)
        normalized_end = "" if end in ("", "\n", "\r", "\r\n") else end
        payload = f"{message}{normalized_end}" if normalized_end else message

        try:
            logger.info(payload, extra={"log_context": "stdout"})
        except Exception:
            original_print(*values, sep=sep, end=end, file=file, flush=flush)

        if flush:
            for handler in logger.handlers:
                handler.flush()

    builtins.print = logging_print


def setup_unified_logging() -> None:
    global _logging_configured

    log_format = os.getenv("LOG_FORMAT", "text").lower()
    use_json = log_format == "json" and _JsonFormatterBase is not None

    log_file_path = _build_log_file_path()
    formatter: logging.Formatter = JsonFormatter(fmt="%(message)s") if use_json else UnifiedFormatter()
    console_formatter: logging.Formatter = JsonConsoleFormatter(fmt="%(message)s") if use_json else UnifiedFormatter()

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=DEFAULT_MAX_BYTES,
        backupCount=DEFAULT_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    _install_exception_hooks()
    logging.getLogger("uvicorn").propagate = True
    logging.getLogger("uvicorn.access").propagate = True
    logging.getLogger("uvicorn.error").propagate = True
    logging.getLogger("fastapi").propagate = True

    _configure_print_redirect(logging.getLogger("Backend.console"))
    _logging_configured = True


def ensure_logging_configured() -> None:
    if not _logging_configured:
        setup_unified_logging()


def get_logger(name: str) -> logging.Logger:
    ensure_logging_configured()
    return logging.getLogger(name)


# Configurar automaticamente al importar
ensure_logging_configured()


def setup_logging() -> None:
    setup_unified_logging()




