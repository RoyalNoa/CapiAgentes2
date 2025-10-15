"""Capi DataB agent: executes ABMC operations against PostgreSQL and exports results."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import asyncpg

from src.domain.agents.agent_protocol import BaseAgent
from src.domain.contracts.agent_io import AgentTask, AgentResult, TaskStatus
from src.domain.agents.agent_models import IntentType
from src.core.logging import get_logger
from src.domain.utils.branch_identifier import BranchIdentifier, validate_table
from src.infrastructure.langgraph.utils.capi_datab_formatter import compose_success_message, extract_branch_descriptor, relax_branch_filters
from src.infrastructure.workspace.session_storage import resolve_workspace_root
from src.application.reasoning.llm_reasoner import LLMReasoner
from src.infrastructure.agents.progress_emitter import agent_progress

logger = get_logger(__name__)


ALLOWED_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


_BRANCH_ANALYST_PROMPT = """
Eres un analista de datos bancarios. Tu tarea es interpretar la instrucción del usuario y extraer, si corresponde, la sucursal bancaria a consultar.
Responde SIEMPRE un JSON con la forma:
{
  "task": "branch_balance" o "other",
  "branch": {
    "name": string o null,
    "number": número entero o null,
    "id": string o null,
    "raw_text": texto original de la sucursal o null
  },
  "table": nombre de la tabla o vista recomendada (si aplica),
  "confidence": número entre 0 y 1,
  "reasoning": explicación breve
}
Si no encuentras información suficiente para identificar la sucursal, utiliza "task": "other" y deja el objeto branch vacío.
No inventes datos y evita tablas no listadas.
"""

@dataclass
class DbOperation:
    """Sanitized representation of a database operation."""

    operation: str  # select, insert, update, delete
    sql: str
    parameters: List[Any]
    output_format: str
    table: Optional[str]
    requires_approval: bool
    description: str
    raw_request: str
    metadata: Optional[Dict[str, Any]] = None

    def preview(self) -> Dict[str, Any]:
        preview_params: List[Any] = []
        for value in self.parameters:
            if isinstance(value, (int, float)):
                preview_params.append(value)
            elif value is None:
                preview_params.append(None)
            else:
                text = str(value)
                preview_params.append(text[:64] + ('…' if len(text) > 64 else ''))
        preview = {
            "operation": self.operation,
            "table": self.table,
            "sql": self.sql,
            "parameters": preview_params,
            "output_format": self.output_format,
            "requires_approval": self.requires_approval,
        }
        if self.metadata:
            preview["metadata"] = self.metadata
        return preview


@dataclass
class ExecutionResult:
    """Outcome of a database execution."""

    rows: Optional[List[Dict[str, Any]]] = None
    rowcount: int = 0
    status_text: Optional[str] = None
    returning: bool = False


class CapiDataBAgent(BaseAgent):
    """Agent specialized in structured database operations."""

    AGENT_NAME = "capi_datab"
    SUPPORTED_FORMATS = {"json", "csv", "txt"}

    def __init__(self, *, llm_reasoner: Optional[LLMReasoner] = None) -> None:
        super().__init__(self.AGENT_NAME)
        self._logger = logger
        if llm_reasoner is not None:
            self._reasoner = llm_reasoner
        else:
            try:
                self._reasoner = LLMReasoner(model="gpt-4.1-mini", temperature=0.1, max_tokens=350)
            except Exception as exc:  # pragma: no cover - defensive
                self._logger.warning({"event": "capi_datab_reasoner_fallback", "error": str(exc)})
                self._reasoner = LLMReasoner(model="gpt-4.1", temperature=0.1, max_tokens=350)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def supported_intents(self) -> List[IntentType]:
        return [IntentType.DB_OPERATION, IntentType.QUERY]

    def process(self, task: AgentTask) -> AgentResult:
        start = datetime.now()
        operation = self.prepare_operation(task.query)
        result = self.execute_operation(
            operation,
            task_id=task.task_id,
            user_id=task.user_id,
            session_id=task.session_id,
        )
        result.processing_time = (datetime.now() - start).total_seconds()
        return result

    def prepare_operation(self, raw_command: str) -> DbOperation:
        instruction = (raw_command or "").strip()
        if not instruction:
            raise ValueError("La instrucción para Capi DataB está vacía")

        # Try structured JSON first
        try:
            payload = json.loads(instruction)
        except json.JSONDecodeError:
            payload = None

        if isinstance(payload, dict):
            return self._parse_structured_payload(payload, instruction)

        lowered = instruction.lower()
        if lowered.startswith(("select", "insert", "update", "delete")):
            return self._parse_raw_sql(instruction)

        return self._parse_natural_language(instruction)

    def execute_operation(
        self,
        operation: DbOperation,
        *,
        task_id: Optional[str] = None,
        user_id: str = "system",
        session_id: str = "default",
    ) -> AgentResult:
        start_time = datetime.now()
        planner_meta: Dict[str, Any] = dict(getattr(operation, "metadata", {}) or {})
        if planner_meta:
            operation.metadata = planner_meta
        try:
            operation_preview = operation.preview()
        except Exception:
            operation_preview = {
                "operation": operation.operation,
                "sql": operation.sql,
            }
        branch_hint = extract_branch_descriptor(
            operation_preview,
            planner_meta,
            {"parameters": operation.parameters},
            getattr(operation, "metadata", None),
        )
        relax_branch_filters(operation, branch_hint)

        agent_progress.start(
            self.AGENT_NAME,
            session_id,
            query=getattr(operation, 'raw_request', None) or operation.description,
            operation=operation.operation,
            table=operation.table,
            branch=branch_hint,
            extra={'user_id': user_id},
        )

        try:
            execution = self._run_sync(self._run_operation(operation))
            file_path = self._export_result(operation, execution, session_id=session_id)
            data_payload: Dict[str, Any] = {
                "operation": operation.operation,
                "table": operation.table,
                "sql": operation.sql,
                "parameters": operation.parameters,
                "output_format": operation.output_format,
                "file_path": str(file_path),
                "rowcount": execution.rowcount,
                "rows": execution.rows,
                "requires_approval": operation.requires_approval,
            }
            if execution.status_text:
                data_payload["status_text"] = execution.status_text
            if planner_meta:
                data_payload["planner_metadata"] = planner_meta
            metadata_bucket: Dict[str, Any] = dict(getattr(operation, "metadata", {}) or {})
            if branch_hint:
                metadata_bucket["branch_descriptor"] = branch_hint
            if metadata_bucket:
                data_payload["metadata"] = metadata_bucket

            fallback_message = self._build_message(operation, execution, file_path)
            message = compose_success_message(
                operation=operation,
                data_payload=data_payload,
                planner_meta=planner_meta,
                export_file=str(file_path),
                fallback_message=fallback_message,
            )
            data_payload["summary_message"] = message
            duration = (datetime.now() - start_time).total_seconds()
            agent_progress.success(
                self.AGENT_NAME,
                session_id,
                detail=message,
                rowcount=execution.rowcount,
                branch=branch_hint,
                extra={"operation": operation.operation, "table": operation.table, "file": str(file_path)},
            )
            return AgentResult(
                task_id=task_id or f"datab_{session_id}_{start_time.timestamp():.0f}",
                agent_name=self.AGENT_NAME,
                status=TaskStatus.COMPLETED,
                data=data_payload,
                message=message,
                processing_time=duration,
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.error({
                "event": "capi_datab_error",
                "error": str(exc),
                "operation": operation.preview(),
            })
            agent_progress.error(
                self.AGENT_NAME,
                session_id,
                detail=str(exc),
                extra={"operation": operation.operation, "table": operation.table},
            )
            duration = (datetime.now() - start_time).total_seconds()
            return AgentResult(
                task_id=task_id or f"datab_{session_id}_{start_time.timestamp():.0f}",
                agent_name=self.AGENT_NAME,
                status=TaskStatus.FAILED,
                data={
                    "operation": operation.operation,
                    "sql": operation.sql,
                },
                message=f"Error al ejecutar la operación de base de datos: {exc}",
                processing_time=duration,
            )

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_structured_payload(self, payload: Dict[str, Any], raw: str) -> DbOperation:
        operation_value = str(payload.get("operation") or payload.get("action") or "").lower()
        if not operation_value and payload.get("sql"):
            operation_value = self._infer_operation(str(payload["sql"]))
        if operation_value not in {"select", "insert", "update", "delete"}:
            raise ValueError("El campo 'operation' debe ser select/insert/update/delete")

        output_format = self._normalize_format(payload.get("output_format"))
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None

        if "sql" in payload:
            sql = str(payload["sql"]).strip()
            self._validate_sql(sql)
            parameters = list(payload.get("parameters") or [])
            return DbOperation(
                operation=operation_value,
                sql=sql,
                parameters=parameters,
                output_format=output_format,
                table=payload.get("table"),
                requires_approval=self._requires_approval(operation_value),
                description="Consulta estructurada proporcionada por el usuario",
                raw_request=raw,
                metadata=metadata,
            )

        table = self._sanitize_identifier(str(payload.get("table", "")).strip())
        if not table:
            raise ValueError("Se requiere el nombre de la tabla para la operación")

        builder = SqlBuilder(operation_value)

        if operation_value == "select":
            columns = payload.get("columns") or ["*"]
            builder.set_columns(columns)
            builder.set_conditions(payload.get("conditions"))
            builder.set_order_by(payload.get("order_by"))
            builder.set_limit(payload.get("limit"), payload.get("offset"))
        elif operation_value == "insert":
            builder.set_values(payload.get("values"))
            builder.set_returning(payload.get("returning"))
        elif operation_value == "update":
            builder.set_values(payload.get("values"))
            builder.set_conditions(payload.get("conditions"), require=True)
            builder.set_returning(payload.get("returning"))
        elif operation_value == "delete":
            builder.set_conditions(payload.get("conditions"), require=True)
            builder.set_returning(payload.get("returning"))

        sql, parameters = builder.build(table)
        return DbOperation(
            operation=operation_value,
            sql=sql,
            parameters=parameters,
            output_format=output_format,
            table=table,
            requires_approval=self._requires_approval(operation_value),
            description="Consulta estructurada generada a partir de JSON",
            raw_request=raw,
            metadata=metadata,
        )

    def _parse_raw_sql(self, sql: str) -> DbOperation:
        sanitized = sql.strip()
        self._validate_sql(sanitized)
        operation_value = self._infer_operation(sanitized)
        return DbOperation(
            operation=operation_value,
            sql=sanitized,
            parameters=[],
            output_format="json",
            table=None,
            requires_approval=self._requires_approval(operation_value),
            description="Instrucción SQL directa",
            raw_request=sql,
        )

    def _parse_natural_language(self, instruction: str) -> DbOperation:
        lowered = instruction.lower()
        format_hint = self._detect_format_hint(lowered)

        branch_operation = self._branch_balance_from_llm(instruction, format_hint)
        if branch_operation:
            return branch_operation

        insert_match = re.match(r"(?:insertar|inserta|agregar|añadir)\s+en\s+([a-zA-Z0-9_]+)\s+(.+)", lowered)
        if insert_match:
            table = self._sanitize_identifier(insert_match.group(1))
            values_text = instruction[insert_match.start(2):]
            values = self._parse_key_value_pairs(values_text)
            builder = SqlBuilder("insert")
            builder.set_values(values)
            sql, params = builder.build(table)
            return DbOperation(
                operation="insert",
                sql=sql,
                parameters=params,
                output_format=format_hint,
                table=table,
                requires_approval=False,
                description="Inserción interpretada desde lenguaje natural",
                raw_request=instruction,
            )

        update_match = re.match(r"(?:actualiza|actualizar|update)\s+([a-zA-Z0-9_]+)\s+set\s+(.+?)\s+(?:donde|where)\s+(.+)", lowered)
        if update_match:
            table = self._sanitize_identifier(update_match.group(1))
            set_text = instruction[update_match.start(2):update_match.end(2)]
            where_text = instruction[update_match.start(3):]
            values = self._parse_key_value_pairs(set_text)
            conditions = self._parse_key_value_pairs(where_text)
            builder = SqlBuilder("update")
            builder.set_values(values)
            builder.set_conditions(conditions, require=True)
            sql, params = builder.build(table)
            return DbOperation(
                operation="update",
                sql=sql,
                parameters=params,
                output_format=format_hint,
                table=table,
                requires_approval=True,
                description="Actualización interpretada desde lenguaje natural",
                raw_request=instruction,
            )

        delete_match = re.match(r"(?:elimina|eliminar|borra|delete)\s+de\s+([a-zA-Z0-9_]+)\s+(?:donde|where)\s+(.+)", lowered)
        if delete_match:
            table = self._sanitize_identifier(delete_match.group(1))
            where_text = instruction[delete_match.start(2):]
            conditions = self._parse_key_value_pairs(where_text)
            builder = SqlBuilder("delete")
            builder.set_conditions(conditions, require=True)
            sql, params = builder.build(table)
            return DbOperation(
                operation="delete",
                sql=sql,
                parameters=params,
                output_format=format_hint,
                table=table,
                requires_approval=True,
                description="Eliminación interpretada desde lenguaje natural",
                raw_request=instruction,
            )

        select_match = re.match(r"(?:consulta|consultar|listar|muestra|selecciona)\s+(?:la\s+tabla\s+)?([a-zA-Z0-9_]+)(?:\s+(?:donde|where)\s+(.+))?", lowered)
        if select_match:
            table = self._sanitize_identifier(select_match.group(1))
            conditions_text = select_match.group(2)
            conditions = self._parse_key_value_pairs(conditions_text) if conditions_text else None
            builder = SqlBuilder("select")
            builder.set_columns(["*"])
            builder.set_conditions(conditions)
            sql, params = builder.build(table)
            return DbOperation(
                operation="select",
                sql=sql,
                parameters=params,
                output_format=format_hint,
                table=table,
                requires_approval=False,
                description="Consulta SELECT interpretada desde lenguaje natural",
                raw_request=instruction,
            )

        raise ValueError("No se pudo interpretar la consulta de base de datos. Provide SQL o JSON estructurado.")

    def _branch_balance_from_llm(self, instruction: str, format_hint: str) -> Optional[DbOperation]:
        result = self._llm_branch_identifier(instruction)
        if result is None:
            return None

        identifier = BranchIdentifier.from_payload(result.get("branch"), fallback_text=instruction)
        if identifier is None:
            return None

        table_name = validate_table(result.get("table") or "public.saldos_sucursal")
        columns = [
            "sucursal_id",
            "sucursal_numero",
            "sucursal_nombre",
            "saldo_total_sucursal",
            "caja_teorica_sucursal",
            "total_atm",
            "total_ats",
            "total_tesoro",
            "total_cajas_ventanilla",
            "total_buzon_depositos",
            "total_recaudacion",
            "total_caja_chica",
            "total_otros",
            "medido_en",
        ]
        condition, params = identifier.build_condition()
        sql = (
            "SELECT "
            + ", ".join(columns)
            + f" FROM {table_name} "
            + f"WHERE {condition} "
            + "ORDER BY medido_en DESC LIMIT 1"
        )
        description = result.get("reasoning") or f"Consulta de saldo por sucursal interpretada para {identifier.display_value}"
        filters = []
        if identifier.identifier:
            filters.append({"column": "sucursal_id", "operator": "=", "value": identifier.identifier})
        elif identifier.number is not None:
            filters.append({"column": "sucursal_numero", "operator": "=", "value": identifier.number})
        elif identifier.name:
            filters.append({"column": "sucursal_nombre", "operator": "ILIKE", "value": f"%{identifier.name}%"})
        metadata = {
            "branch": identifier.to_metadata(),
            "filters": filters,
            "planner_source": "llm_branch_identifier",
            "planner_confidence": result.get("confidence"),
            "planner_reason": result.get("reasoning"),
            "planner_model": result.get("model"),
            "suggested_table": table_name,
        }
        self._logger.info(
            {
                "event": "capi_datab_llm_branch",
                "branch": identifier.to_metadata(),
                "table": table_name,
                "model": result.get("model"),
                "confidence": result.get("confidence"),
            }
        )
        return DbOperation(
            operation="select",
            sql=sql,
            parameters=params,
            output_format=format_hint,
            table=table_name,
            requires_approval=False,
            description=description,
            raw_request=instruction,
            metadata={k: v for k, v in metadata.items() if v not in (None, [], {}, "")},
        )

    def _llm_branch_identifier(self, instruction: str) -> Optional[Dict[str, Any]]:
        payload = {"instruction": instruction}
        try:
            result = self._run_sync(
                self._reasoner.reason(
                    query=json.dumps(payload, ensure_ascii=False),
                    system_prompt=_BRANCH_ANALYST_PROMPT,
                    response_format="json_object",
                )
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error({"event": "capi_datab_llm_call_failed", "error": str(exc)})
            return None

        if not result.success or not result.response:
            self._logger.warning({"event": "capi_datab_llm_unsuccessful", "error": result.error})
            return None

        try:
            parsed = json.loads(result.response)
        except json.JSONDecodeError:
            self._logger.error({"event": "capi_datab_llm_invalid_json", "response": result.response})
            return None

        task = str(parsed.get("task") or "other").lower()
        if task not in {"branch_balance", "branch"}:
            return None

        parsed.setdefault("confidence", result.confidence_score)
        parsed.setdefault("model", result.model)
        return parsed

    # ------------------------------------------------------------------
    # SQL builders
    # ------------------------------------------------------------------

    def _run_sync(self, awaitable: asyncio.Future) -> Any:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(awaitable)

        if not loop.is_running():
            return loop.run_until_complete(awaitable)

        result_box: Dict[str, Any] = {}
        error_box: Dict[str, BaseException] = {}

        def _runner() -> None:
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                result_box["value"] = new_loop.run_until_complete(awaitable)
            except BaseException as exc:  # pragma: no cover - defensive
                error_box["error"] = exc
            finally:
                new_loop.close()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_runner)
            future.result()

        if "error" in error_box:
            raise error_box["error"]
        return result_box.get("value")

    async def _run_operation(self, operation: DbOperation) -> ExecutionResult:
        database_url = self._get_database_url()
        conn: Optional[asyncpg.Connection] = None
        try:
            conn = await asyncpg.connect(database_url)
            sql_lower = operation.sql.lower()
            if operation.operation == "select":
                records = await conn.fetch(operation.sql, *operation.parameters)
                rows = [dict(record) for record in records]
                return ExecutionResult(rows=rows, rowcount=len(rows), returning=True)

            returning = " returning " in sql_lower
            if returning:
                records = await conn.fetch(operation.sql, *operation.parameters)
                rows = [dict(record) for record in records]
                return ExecutionResult(rows=rows, rowcount=len(rows), returning=True)

            status = await conn.execute(operation.sql, *operation.parameters)
            rowcount = self._parse_rowcount(status)
            return ExecutionResult(rows=None, rowcount=rowcount, status_text=status, returning=False)
        finally:
            if conn is not None:
                await conn.close()

    def _export_result(self, operation: DbOperation, execution: ExecutionResult, *, session_id: str, progress_log: Optional[List[Dict[str, Any]]] = None) -> Path:
        base_dir = self._resolve_session_export_dir(session_id)
        timestamp = datetime.now().strftime("%Y_%m_%d")
        unique_suffix = datetime.now().strftime("%H%M%S%f")[-6:]
        extension = self._extension_for(operation.output_format)
        filename = f"DataB_{timestamp}_{unique_suffix}.{extension}"
        file_path = base_dir / filename

        if operation.output_format == "json":
            payload = {
                "operation": operation.operation,
                "table": operation.table,
                "rowcount": execution.rowcount,
                "generated_at": datetime.now().isoformat(),
                "session_id": session_id,
                "sql": operation.sql,
                "parameters": operation.parameters,
                "result": execution.rows if execution.rows is not None else execution.status_text,
            }
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        elif operation.output_format == "csv":
            self._write_csv(file_path, execution)
        else:  # txt
            self._write_text(file_path, operation, execution)

        if progress_log is not None:
            self._append_progress(progress_log, label=f"Archivo exportado: {file_path.name}", scope="granular")

        self._update_session_manifest(
            session_id=session_id,
            export_path=file_path,
            operation=operation,
            execution=execution,
            progress_log=progress_log,
        )

        return file_path


    def _build_message(self, operation: DbOperation, execution: ExecutionResult, file_path: Path) -> str:
        if operation.operation == "select":
            return (
                f"Consulta completada. Se exportaron {execution.rowcount} filas a {file_path.name}."
            )
        if execution.rowcount:
            return (
                f"Operación {operation.operation.upper()} aplicada: {execution.rowcount} filas afectadas. "
                f"Evidencia guardada en {file_path.name}."
            )
        return (
            f"Operación {operation.operation.upper()} ejecutada sin filas afectadas. "
            f"Detalle disponible en {file_path.name}."
        )

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _detect_format_hint(self, text: str) -> str:
        if " csv" in text or " formato csv" in text:
            return "csv"
        if " txt" in text or " plano" in text:
            return "txt"
        if " json" in text:
            return "json"
        return "json"

    def _sanitize_identifier(self, value: str) -> str:
        if not value:
            return ""
        if not ALLOWED_IDENTIFIER.match(value):
            raise ValueError(f"Identificador SQL no válido: {value}")
        return value

    def _normalize_format(self, value: Optional[str]) -> str:
        fmt = (value or "json").lower()
        if fmt not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Formato de salida no soportado: {fmt}")
        return fmt

    def _parse_key_value_pairs(self, text: Optional[str]) -> Dict[str, Any]:
        if not text:
            return {}
        tokens = re.split(r"\s*(?:,| y | and )\s*", text.strip())
        pairs: Dict[str, Any] = {}
        for token in tokens:
            if not token:
                continue
            if '=' not in token:
                raise ValueError(f"Expresión esperada clave=valor, recibida: {token}")
            key, value = token.split('=', 1)
            sanitized_key = self._sanitize_identifier(key.strip())
            pairs[sanitized_key] = self._coerce_value(value.strip())
        return pairs

    def _coerce_value(self, value: str) -> Any:
        if value.startswith(""") and value.endswith("""):
            return value[1:-1]
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        if re.match(r"^-?\d+$", value):
            return int(value)
        if re.match(r"^-?\d+\.\d+$", value):
            return float(value)
        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        if lowered in {"null", "none"}:
            return None
        return value

    def _validate_sql(self, sql: str) -> None:
        lowered = sql.lower()
        if " drop " in lowered or lowered.startswith("drop "):
            raise ValueError("Comando DROP no permitido para Capi DataB")
        if " truncate " in lowered or lowered.startswith("truncate "):
            raise ValueError("Comando TRUNCATE no permitido para Capi DataB")
        if " alter " in lowered or lowered.startswith("alter "):
            raise ValueError("Comando ALTER no permitido para Capi DataB")

    def _requires_approval(self, operation: str) -> bool:
        return operation in {"update", "delete"}

    def _infer_operation(self, sql: str) -> str:
        tokens = sql.strip().split()
        if not tokens:
            raise ValueError("Sentencia SQL vacía")
        op = tokens[0].lower()
        if op not in {"select", "insert", "update", "delete"}:
            raise ValueError(f"Operación SQL no soportada: {op}")
        return op

    def _parse_rowcount(self, status: Optional[str]) -> int:
        if not status:
            return 0
        parts = status.split()
        for token in reversed(parts):
            if token.isdigit():
                return int(token)
        return 0

    def _extension_for(self, fmt: str) -> str:
        return {
            "json": "json",
            "csv": "csv",
            "txt": "txt",
        }.get(fmt, "json")

    def _append_progress(
        self,
        log: List[Dict[str, Any]],
        *,
        label: str,
        scope: str = "granular",
        status: str = "done",
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if log is None:
            return
        entry: Dict[str, Any] = {
            "label": label,
            "scope": scope,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }
        if extra:
            entry.update(extra)
        log.append(entry)


    def _write_csv(self, file_path: Path, execution: ExecutionResult) -> None:
        rows = execution.rows or []
        if not rows:
            with file_path.open("w", encoding="utf-8") as f:
                f.write("operation,rowcount\n")
                f.write(f"{execution.status_text or 'EXECUTE'},{execution.rowcount}\n")
            return
        import csv

        fieldnames = list(rows[0].keys())
        with file_path.open("w", encoding="utf-8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: self._stringify(v) for k, v in row.items()})


    def _resolve_session_export_dir(self, session_id: str) -> Path:
        safe_session = self._sanitize_session_id(session_id)
        workspace_root = self._get_workspace_root()
        session_dir = workspace_root / "data" / "sessions" / f"session_{safe_session}"
        export_dir = session_dir / "capi_DataB"
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir

    def _get_workspace_root(self) -> Path:
        try:
            return resolve_workspace_root()
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning(
                {
                    "event": "workspace_root_fallback",
                    "error": str(exc),
                }
            )
            default_root = Path(__file__).resolve().parents[2]
            default_root.mkdir(parents=True, exist_ok=True)
            if not (default_root / "data").exists():
                (default_root / "data").mkdir(parents=True, exist_ok=True)
            return default_root

    def _update_session_manifest(
        self,
        *,
        session_id: str,
        export_path: Path,
        operation: DbOperation,
        execution: ExecutionResult,
        progress_log: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        safe_session = self._sanitize_session_id(session_id)
        session_root = export_path.parent.parent
        manifest_path = session_root / f"session_{safe_session}.json"

        manifest: Dict[str, Any] = {
            "session_id": session_id,
            "sanitized_session_id": safe_session,
            "datab_exports": [],
        }

        if manifest_path.exists():
            try:
                loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    manifest = loaded
            except json.JSONDecodeError:
                pass

        manifest.setdefault("session_id", session_id)
        manifest.setdefault("sanitized_session_id", safe_session)
        exports = manifest.setdefault("datab_exports", [])
        if not isinstance(exports, list):
            exports = []
            manifest["datab_exports"] = exports

        export_entry = {
            "filename": export_path.name,
            "relative_path": export_path.relative_to(session_root).as_posix(),
            "absolute_path": str(export_path),
            "operation": operation.operation,
            "table": operation.table,
            "rowcount": execution.rowcount,
            "generated_at": datetime.now().isoformat(),
        }
        exports.append(export_entry)
        manifest["updated_at"] = datetime.now().isoformat()

        if progress_log:
            manifest["last_progress_steps"] = progress_log[-10:]

        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        if progress_log is not None:
            self._append_progress(progress_log, label="Manifiesto de sesión actualizado", scope="granular")

    def _sanitize_session_id(self, session_id: str) -> str:
        if not session_id:
            return "default"
        cleaned = session_id.strip()
        cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", cleaned)
        if not cleaned:
            return "default"
        return cleaned[:128]


    def _write_text(self, file_path: Path, operation: DbOperation, execution: ExecutionResult) -> None:
        lines = [
            f"Operación: {operation.operation}",
            f"Tabla: {operation.table or 'N/A'}",
            f"SQL: {operation.sql}",
            f"Parámetros: {operation.parameters}",
            f"Filas afectadas: {execution.rowcount}",
        ]
        if execution.rows:
            lines.append("Resultados:")
            for row in execution.rows:
                lines.append(json.dumps(row, ensure_ascii=False, default=str))
        elif execution.status_text:
            lines.append("")
            lines.append(f"Estado: {execution.status_text}")
        with file_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))


    def _stringify(self, value: Any) -> str:
        if isinstance(value, (int, float)):
            return str(value)
        if value is None:
            return ""
        return str(value)

    def _get_database_url(self) -> str:
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'capi_alerts')
        username = os.getenv('POSTGRES_USER', 'capi_user')
        password = os.getenv('POSTGRES_PASSWORD', 'capi_secure_2024')
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"


class SqlBuilder:
    """Utility class to build safe SQL statements with positional parameters."""

    def __init__(self, operation: str) -> None:
        self.operation = operation
        self._columns: Optional[List[str]] = None
        self._values: Optional[Dict[str, Any]] = None
        self._conditions: Optional[Dict[str, Any]] = None
        self._order_by: Optional[List[str]] = None
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._returning: Optional[List[str]] = None

    def set_columns(self, columns: Sequence[str]) -> None:
        sanitized = []
        for column in columns:
            if column == '*':
                sanitized.append('*')
            else:
                sanitized.append(self._sanitize(column))
        self._columns = sanitized

    def set_values(self, values: Optional[Dict[str, Any]]) -> None:
        if not values:
            raise ValueError("La operación requiere un objeto 'values' con datos")
        self._values = {self._sanitize(k): v for k, v in values.items()}

    def set_conditions(self, conditions: Optional[Dict[str, Any]], require: bool = False) -> None:
        if require and not conditions:
            raise ValueError("La operación requiere cláusula WHERE para evitar cambios masivos")
        if conditions:
            self._conditions = {self._sanitize(k): v for k, v in conditions.items()}

    def set_order_by(self, order_by: Optional[Sequence[str]]) -> None:
        if order_by:
            self._order_by = [self._sanitize(item) for item in order_by]

    def set_limit(self, limit: Optional[int], offset: Optional[int]) -> None:
        if limit is not None:
            self._limit = int(limit)
        if offset is not None:
            self._offset = int(offset)

    def set_returning(self, returning: Optional[Sequence[str]]) -> None:
        if returning:
            self._returning = [self._sanitize(field) for field in returning]

    def build(self, table: str) -> Tuple[str, List[Any]]:
        params: List[Any] = []
        if self.operation == 'select':
            columns = ', '.join(self._columns or ['*'])
            sql = f"SELECT {columns} FROM {table}"
            sql = self._append_conditions(sql, params)
            sql = self._append_order_limit(sql)
        elif self.operation == 'insert':
            assert self._values is not None
            columns = list(self._values.keys())
            placeholders = [self._placeholder(len(params) + idx + 1) for idx, _ in enumerate(columns)]
            params.extend(self._values.values())
            sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        elif self.operation == 'update':
            assert self._values is not None
            set_clauses = []
            for column, value in self._values.items():
                placeholder = self._placeholder(len(params) + 1)
                params.append(value)
                set_clauses.append(f"{column} = {placeholder}")
            sql = f"UPDATE {table} SET {', '.join(set_clauses)}"
            sql = self._append_conditions(sql, params, require=True)
        elif self.operation == 'delete':
            sql = f"DELETE FROM {table}"
            sql = self._append_conditions(sql, params, require=True)
        else:
            raise ValueError(f"Operación no soportada para SqlBuilder: {self.operation}")

        if self._returning:
            sql += f" RETURNING {', '.join(self._returning)}"
        return sql, params

    def _append_conditions(self, sql: str, params: List[Any], require: bool = False) -> str:
        if self._conditions:
            clauses = []
            for column, value in self._conditions.items():
                placeholder = self._placeholder(len(params) + 1)
                params.append(value)
                clauses.append(f"{column} = {placeholder}")
            sql += " WHERE " + " AND ".join(clauses)
        elif require:
            raise ValueError("La operación requiere cláusula WHERE para continuar")
        return sql

    def _append_order_limit(self, sql: str) -> str:
        if self._order_by:
            sql += " ORDER BY " + ", ".join(self._order_by)
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        if self._offset is not None:
            sql += f" OFFSET {self._offset}"
        return sql

    def _placeholder(self, idx: int) -> str:
        return f"${idx}"

    def _sanitize(self, identifier: str) -> str:
        cleaned = identifier.strip()
        if not ALLOWED_IDENTIFIER.match(cleaned) and cleaned != '*':
            raise ValueError(f"Identificador SQL no válido: {identifier}")
        return cleaned

