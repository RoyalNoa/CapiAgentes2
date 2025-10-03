from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_BRANCH_FILTER_REGEXES = (
    re.compile(r"(?P<column>(?:\"?[\w]+\"?\.)*\"?sucursal_nombre\"?)\s*=\s*(?P<placeholder>\$\d+)", re.IGNORECASE),
    re.compile(r"(?P<column>(?:\"?[\w]+\"?\.)*\"?branch_name\"?)\s*=\s*(?P<placeholder>\$\d+)", re.IGNORECASE),
)


def extract_branch_descriptor(
    operation_preview: Optional[Dict[str, Any]],
    planner_meta: Optional[Dict[str, Any]],
    data_payload: Optional[Dict[str, Any]],
    operation_meta: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Attempt to recover a human friendly branch descriptor from multiple sources."""
    for source in filter(_is_dict, (planner_meta, operation_preview, operation_meta)):
        filters = source.get("filters") if isinstance(source.get("filters"), list) else None
        if not filters:
            continue
        for spec in filters:
            column = str(spec.get("column", ""))
            if not column:
                continue
            lowered = column.lower()
            if "sucursal" in lowered or "branch" in lowered:
                candidate = _normalize_filter_value(spec.get("value"))
                if candidate:
                    return candidate

    if isinstance(operation_meta, dict):
        candidate = _normalize_filter_value(operation_meta.get("branch"))
        if candidate:
            return candidate

    params = None
    if isinstance(data_payload, dict):
        params = data_payload.get("parameters")
    if isinstance(params, Sequence):
        for value in params:
            candidate = _normalize_filter_value(value)
            if candidate:
                return candidate
    return None


def relax_branch_filters(operation: Any, branch_hint: Optional[str]) -> None:
    """Convert strict equality filters on branch columns into ILIKE searches."""
    if not branch_hint:
        return

    sql = getattr(operation, "sql", "") or ""
    params: List[Any] = list(getattr(operation, "parameters", []) or [])
    if not sql or not params:
        return

    normalized = branch_hint.strip()
    if not normalized:
        return
    lower_hint = normalized.lower()

    replaced_any = False
    for idx, value in enumerate(params):
        if not isinstance(value, str):
            continue
        value_clean = value.strip().strip('%').lower()
        if value_clean != lower_hint:
            continue

        placeholder = f"${idx + 1}"
        updated_sql, changed = _replace_branch_condition(sql, placeholder)
        if changed:
            sql = updated_sql
            params[idx] = f"%{normalized}%"
            replaced_any = True

    if replaced_any:
        operation.sql = sql
        operation.parameters = params


def compose_success_message(
    *,
    operation: Any,
    data_payload: Dict[str, Any],
    planner_meta: Optional[Dict[str, Any]] = None,
    export_file: Optional[str] = None,
    fallback_message: Optional[str] = None,
) -> str:
    """Generate a natural language summary for DataB responses."""
    rows = _ensure_rows(data_payload)
    rowcount = data_payload.get("rowcount")
    if rowcount is None:
        rowcount = len(rows)

    operation_type = (getattr(operation, "operation", "") or "").lower()

    try:
        operation_preview = operation.preview()
    except Exception:
        operation_preview = {}

    operation_meta = getattr(operation, "metadata", None)
    branch = extract_branch_descriptor(operation_preview, planner_meta or {}, data_payload, operation_meta)
    suffix = _compose_export_suffix(export_file)

    if operation_type != "select":
        if fallback_message:
            return fallback_message + suffix
        if rowcount and rowcount > 0:
            return f"Operación completada. Se afectaron {rowcount} registros." + suffix
        return "Operación completada." + suffix

    if rowcount == 0:
        base = "No se encontraron resultados"
        if branch:
            base += f" para la sucursal '{branch}'."
        else:
            base += "."
        return base + suffix

    if rows:
        first_row = rows[0]
        if isinstance(first_row, dict) and first_row:
            if len(first_row) == 1:
                col, value = next(iter(first_row.items()))
                formatted = _format_value(value, col)
                metric_label = _prepare_metric_label(_humanize_column(col), bool(branch))
                if branch:
                    base = f"El {metric_label} de la sucursal '{branch}' es {formatted}."
                else:
                    base = f"{metric_label.capitalize()}: {formatted}."
                return base + suffix
            details = [
                f"{_prepare_metric_label(_humanize_column(col), False)}={_format_value(val, col)}"
                for col, val in first_row.items()
            ]
            if branch:
                base = f"Resultados para la sucursal '{branch}': " + ", ".join(details) + "."
            else:
                base = "Resultados: " + ", ".join(details) + "."
            if rowcount and rowcount > 1:
                base += f" Se muestra la primera de {rowcount} filas."
            return base + suffix

    if rowcount and rowcount > 0:
        if branch:
            base = f"Se obtuvieron {rowcount} registros para la sucursal '{branch}'."
        else:
            base = f"Se obtuvieron {rowcount} registros."
        return base + suffix

    if fallback_message:
        return fallback_message + suffix
    return "Consulta completada." + suffix


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _replace_branch_condition(sql: str, placeholder: str) -> Tuple[str, bool]:
    changed = False

    def _substitute(pattern: re.Pattern[str], text: str) -> str:
        nonlocal changed

        def _replacer(match: re.Match[str]) -> str:
            nonlocal changed
            changed = True
            column = match.group('column')
            return f"{column} ILIKE {placeholder}"

        return pattern.sub(_replacer, text)

    updated = sql
    for pattern in _BRANCH_FILTER_REGEXES:
        updated = _substitute(pattern, updated)
    return updated, changed


def _ensure_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = payload.get("rows")
    if isinstance(rows, list):
        return rows
    result_rows = payload.get("result")
    if isinstance(result_rows, list):
        payload.setdefault("rows", result_rows)
        return result_rows
    return []


def _normalize_filter_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        candidate = value.strip().strip('%').strip()
        return candidate.title() if candidate else None
    if isinstance(value, (list, tuple, set)):
        for item in value:
            candidate = _normalize_filter_value(item)
            if candidate:
                return candidate
    if isinstance(value, dict):
        for key in ("name", "label", "value"):
            candidate = _normalize_filter_value(value.get(key))
            if candidate:
                return candidate
    return None


def _format_value(value: Any, column: Optional[str] = None) -> str:
    if value is None:
        return "sin datos"
    column_lower = (column or "").lower()
    treat_as_currency = any(keyword in column_lower for keyword in ("saldo", "monto", "importe", "total", "amount", "balance"))
    value_str = str(value).strip()
    if treat_as_currency:
        try:
            decimal_value = Decimal(value_str.replace(',', '.'))
        except (InvalidOperation, ValueError):
            return value_str or "sin datos"
        return _format_currency(decimal_value)
    return value_str or "sin datos"


def _format_currency(amount: Decimal) -> str:
    quantized = amount.quantize(Decimal("0.01"))
    sign = "-" if quantized < 0 else ""
    abs_value = abs(quantized)
    integer_part, decimal_part = f"{abs_value:,.2f}".split('.')
    integer_part = integer_part.replace(',', '.')
    return f"{sign}${integer_part},{decimal_part}"


def _prepare_metric_label(label: str, branch_present: bool) -> str:
    cleaned = label.strip()
    if branch_present:
        tokens = [token for token in cleaned.split() if token.lower() not in ("sucursal", "branch")]
        cleaned = " ".join(tokens).strip()
    return cleaned or label or "valor"


def _humanize_column(column: str) -> str:
    return column.replace('_', ' ').strip() or "valor"


def _compose_export_suffix(export_file: Optional[str]) -> str:
    if not export_file:
        return ""
    try:
        filename = Path(export_file).name
    except Exception:
        filename = str(export_file)
    if not filename:
        return ""
    return f" Resultado exportado a {filename}."


def _is_dict(value: Optional[Dict[str, Any]]) -> bool:
    return isinstance(value, dict) and bool(value)


__all__ = [
    "compose_success_message",
    "extract_branch_descriptor",
    "relax_branch_filters",
]
