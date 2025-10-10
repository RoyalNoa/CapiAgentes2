"""Natural language planner for the Capi DataB agent."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from src.application.reasoning.llm_reasoner import LLMReasoner, LLMReasoningResult
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PlannerResponse:
    """Container with planner output and metadata."""

    success: bool
    plan: Optional[Dict[str, Any]]
    confidence: float = 0.0
    reasoning: str = ""
    provider: str = ""
    model: str = ""
    raw_response: Optional[str] = None

    @property
    def is_usable(self) -> bool:
        return self.success and self.plan is not None


class SchemaCatalog:
    """Describe allowed tables and columns for NL planning."""

    def __init__(self, tables: Dict[str, Dict[str, Iterable[str]]]) -> None:
        self._tables: Dict[str, Dict[str, List[str]]] = {}
        self._lower_table_map: Dict[str, str] = {}
        for name, spec in tables.items():
            normalized = name.strip()
            columns = [col.strip() for col in spec.get("columns", [])]
            numeric = [col.strip() for col in spec.get("numeric", [])]
            dates = [col.strip() for col in spec.get("dates", [])]
            self._tables[normalized] = {
                "columns": columns,
                "numeric": numeric,
                "dates": dates,
                "description": spec.get("description", ""),
            }
            self._lower_table_map[normalized.lower()] = normalized

    @classmethod
    def default(cls) -> "SchemaCatalog":
        return cls(
            {
                "public.saldos_sucursal": {
                    "description": "Snapshot de saldos por sucursal.",
                    "columns": [
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
                        "barrio",
                        "comuna",
                        "codigo_postal",
                        "direccion_sucursal",
                        "latitud",
                        "longitud",
                        "medido_en",
                    ],
                    "numeric": [
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
                        "latitud",
                        "longitud",
                    ],
                    "dates": ["medido_en"],
                },
                "public.saldos_actuales_sucursal_oficial": {
                    "description": "Vista con el ultimo saldo oficial por sucursal.",
                    "columns": [
                        "sucursal_id",
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
                        "direccion_sucursal",
                        "latitud",
                        "longitud",
                        "medido_en",
                        "observacion",
                    ],
                    "numeric": [
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
                        "latitud",
                        "longitud",
                    ],
                    "dates": ["medido_en"],
                },
                "public.saldos_conciliacion_sucursal": {
                    "description": "Vista que compara saldos oficiales con dispositivos.",
                    "columns": [
                        "sucursal_id",
                        "saldo_total_sucursal",
                        "saldo_total_dispositivos",
                        "desfase_oficial_vs_dispositivos",
                        "caja_teorica_sucursal",
                        "caja_teorica_dispositivos",
                        "total_tesoro",
                        "total_cajas_ventanilla",
                        "total_buzon_depositos",
                        "total_recaudacion",
                        "medido_en_oficial",
                        "medido_en_dispositivos",
                    ],
                    "numeric": [
                        "saldo_total_sucursal",
                        "saldo_total_dispositivos",
                        "desfase_oficial_vs_dispositivos",
                        "caja_teorica_sucursal",
                        "caja_teorica_dispositivos",
                        "total_tesoro",
                        "total_cajas_ventanilla",
                        "total_buzon_depositos",
                        "total_recaudacion",
                    ],
                    "dates": ["medido_en_oficial", "medido_en_dispositivos"],
                },
            }
        )

    @property
    def default_table(self) -> str:
        return "public.saldos_sucursal"

    def describe_tables(self) -> str:
        lines: List[str] = []
        for name, spec in self._tables.items():
            lines.append(f"- {name}: {spec.get('description', '').strip()}")
            columns = ", ".join(spec.get("columns", []))
            if columns:
                lines.append(f"  columnas: {columns}")
            numeric = ", ".join(spec.get("numeric", []))
            if numeric:
                lines.append(f"  numericas: {numeric}")
            dates = ", ".join(spec.get("dates", []))
            if dates:
                lines.append(f"  fechas: {dates}")
        return "\n".join(lines)

    def list_tables(self) -> List[str]:
        return list(self._tables.keys())

    def resolve_table(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        normalized = value.strip().lower()
        return self._lower_table_map.get(normalized)

    def has_table(self, value: Optional[str]) -> bool:
        return bool(self.resolve_table(value))

    def validate_column(self, table: str, column: str) -> str:
        table_name = self.resolve_table(table) or table
        spec = self._tables.get(table_name)
        if not spec:
            raise ValueError(f"Table '{table}' no permitida")
        target = column.strip()
        for allowed in spec.get("columns", []):
            if allowed.lower() == target.lower():
                return allowed
        raise ValueError(f"Column '{column}' no permitida en {table_name}")

    def is_numeric(self, table: str, column: str) -> bool:
        table_name = self.resolve_table(table) or table
        spec = self._tables.get(table_name)
        if not spec:
            return False
        target = column.strip().lower()
        return any(col.lower() == target for col in spec.get("numeric", []))

    def is_date(self, table: str, column: str) -> bool:
        table_name = self.resolve_table(table) or table
        spec = self._tables.get(table_name)
        if not spec:
            return False
        target = column.strip().lower()
        return any(col.lower() == target for col in spec.get("dates", []))


_PLANNER_PROMPT_TEMPLATE = """
Eres un planificador NL->SQL para una base de datos bancaria. Tu objetivo es
convertir una instruccion del usuario en un plan SQL seguro y parametrizado.

Tablas disponibles:
{tables}

Devuelve exclusivamente un JSON con estas claves:
{{
  "operation": "select",
  "table": "...",
  "columns": ["columna", ...],
  "aggregations": [{{"column": "col", "func": "sum", "alias": "total"}}],
  "filters": [{{"column": "col", "op": "=", "value": "valor"}}],
  "group_by": ["columna"],
  "order_by": [{{"column": "campo", "direction": "desc"}}],
  "limit": 10,
  "offset": 0,
  "branch": {{"name": "", "number": null, "id": null, "raw_text": null}},
  "needs_branch_lookup": false,
  "output_format": "json",
  "confidence": 0.0,
  "reasoning": "explicacion breve"
}}

Reglas:
- Usa operation "select". Nunca generes DDL ni DML destructivo.
- Limita las columnas y tablas a la lista proporcionada.
- Cuando el usuario mencione una sucursal, llena el objeto branch y marca
  needs_branch_lookup=true si falta informacion estructurada.
- Convierte filtros a comparaciones simples (", >, <, >=, <=, ilike, between, in).
- Siempre incluye un limite razonable (maximo 100) y ordena si corresponde.
- output_format debe ser "json", "csv" o "txt".
- confidence debe ser un numero entre 0 y 1 que indique tu seguridad.
- El JSON no debe contener comentarios ni texto adicional.
""".strip()


class NLQueryPlanner:
    """LLM-backed planner that generates structured plans for SQL execution."""

    def __init__(
        self,
        *,
        reasoner: Optional[LLMReasoner] = None,
        catalog: Optional[SchemaCatalog] = None,
        min_confidence: float = 0.55,
    ) -> None:
        if reasoner is not None:
            self._reasoner = reasoner
        else:
            try:
                self._reasoner = LLMReasoner(model="gpt-4.1", temperature=0.1, max_tokens=350)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning({"event": "capi_datab_planner_reasoner_fallback", "error": str(exc)})
                self._reasoner = LLMReasoner(model="gpt-4o", temperature=0.1, max_tokens=350)
        self.catalog = catalog or SchemaCatalog.default()
        self.min_confidence = min_confidence
        self._system_prompt = _PLANNER_PROMPT_TEMPLATE.format(
            tables=self.catalog.describe_tables()
        )

    def plan(
        self,
        instruction: str,
        *,
        format_hint: Optional[str] = None,
        run_sync=None,
    ) -> PlannerResponse:
        """Generate a plan synchronously using the provided execution helper."""

        coro = self._request_plan(instruction, format_hint=format_hint)
        if run_sync is not None:
            result = run_sync(coro)
        else:
            result = asyncio.run(coro)
        if not result.is_usable:
            return result
        if result.confidence < self.min_confidence:
            logger.info(
                {
                    "event": "nl_planner_below_threshold",
                    "confidence": result.confidence,
                    "threshold": self.min_confidence,
                }
            )
            return PlannerResponse(
                success=False,
                plan=None,
                confidence=result.confidence,
                reasoning=result.reasoning,
                provider=result.provider,
                model=result.model,
                raw_response=result.raw_response,
            )
        return result

    async def _request_plan(
        self,
        instruction: str,
        *,
        format_hint: Optional[str],
    ) -> PlannerResponse:
        payload = {
            "instruction": instruction,
            "format_hint": (format_hint or "json").lower(),
            "allowed_tables": self.catalog.list_tables(),
        }
        result = await self._reasoner.reason(
            query=json.dumps(payload, ensure_ascii=False),
            system_prompt=self._system_prompt,
            response_format="json_object",
        )
        return self._build_response(result)

    def _build_response(self, result: LLMReasoningResult) -> PlannerResponse:
        if not result.success or not result.response:
            logger.warning(
                {
                    "event": "nl_planner_reasoner_failed",
                    "error": result.error,
                    "provider": result.provider,
                }
            )
            return PlannerResponse(success=False, plan=None, raw_response=result.response)

        try:
            parsed = json.loads(result.response)
        except json.JSONDecodeError:
            logger.error(
                {
                    "event": "nl_planner_invalid_json",
                    "response": result.response,
                }
            )
            return PlannerResponse(
                success=False,
                plan=None,
                raw_response=result.response,
            )

        if not isinstance(parsed, dict):
            logger.error({"event": "nl_planner_unexpected_payload", "payload": parsed})
            return PlannerResponse(success=False, plan=None, raw_response=result.response)

        confidence = self._extract_confidence(parsed, default=result.confidence_score)
        reasoning = str(parsed.get("reasoning") or "").strip()
        parsed.setdefault("operation", "select")
        parsed.setdefault("columns", [])
        parsed.setdefault("aggregations", [])
        parsed.setdefault("filters", [])
        parsed.setdefault("group_by", [])
        parsed.setdefault("order_by", [])
        parsed.setdefault("limit", None)
        parsed.setdefault("offset", 0)
        parsed.setdefault("branch", None)
        parsed.setdefault("needs_branch_lookup", False)
        parsed.setdefault("output_format", "json")
        parsed.setdefault("confidence", confidence)
        parsed.setdefault("reasoning", reasoning)

        return PlannerResponse(
            success=True,
            plan=parsed,
            confidence=confidence,
            reasoning=reasoning,
            provider=result.provider,
            model=result.model,
            raw_response=result.response,
        )

    @staticmethod
    def _extract_confidence(payload: Dict[str, Any], default: float = 0.0) -> float:
        value = payload.get("confidence", default)
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = float(default or 0.0)
        return max(0.0, min(confidence, 1.0))


__all__ = ["NLQueryPlanner", "PlannerResponse", "SchemaCatalog"]



