from __future__ import annotations

import re
from datetime import datetime, timezone
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
            narrative = _compose_branch_narrative(first_row, branch)
            if narrative:
                return narrative + suffix
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
    treat_as_currency = any(
        keyword in column_lower
        for keyword in ("saldo", "monto", "importe", "total", "amount", "balance", "caja")
    )
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
    return f" Si precisas revisar el detalle puedo compartirte el archivo {filename}."


def _compose_branch_narrative(row: Dict[str, Any], branch: Optional[str]) -> Optional[str]:
    branch_name = branch or row.get("sucursal_nombre") or row.get("branch_name")
    branch_name = str(branch_name).strip() if branch_name else None

    primary_fields: Tuple[str, ...] = (
        "saldo_total_sucursal",
        "saldo_total",
        "total_saldo",
        "saldo",
        "balance_total",
    )
    primary_value_text = None
    primary_label = None
    primary_field = None
    primary_raw_value: Any = None
    for candidate in primary_fields:
        if candidate in row and row.get(candidate) is not None:
            primary_field = candidate
            primary_raw_value = row.get(candidate)
            primary_value_text = _format_value(primary_raw_value, candidate)
            primary_label = _humanize_column(candidate)
            break

    if not primary_value_text:
        return None

    sentences: List[str] = []
    if branch_name:
        sentences.append(f"El saldo total de la sucursal '{branch_name}' es {primary_value_text}.")
    else:
        sentences.append(f"El {primary_label} es {primary_value_text}.")

    theoretical_fields: Tuple[str, ...] = (
        "caja_teorica_sucursal",
        "saldo_teorico",
        "teorico_total",
    )
    theoretic_raw_value: Any = None
    theoretic_field = None
    for candidate in theoretical_fields:
        if candidate in row and row.get(candidate) is not None:
            theoretic_raw_value = row.get(candidate)
            theoretic_field = candidate
            formatted = _format_value(theoretic_raw_value, candidate)
            theoretical_sentence = f"La caja teórica registrada asciende a {formatted}."
            delta = _delta_values(theoretic_raw_value, primary_raw_value)
            if delta is not None and delta != 0:
                diff_text = _format_value(abs(delta), "delta_saldo")
                if delta > 0:
                    theoretical_sentence += f" Existe una brecha de {diff_text} respecto del saldo operativo."
                else:
                    theoretical_sentence += f" El saldo operativo supera a la caja teórica por {diff_text}."
            sentences.append(theoretical_sentence)
            break

    distribution_map = [
        ("total_atm", "ATM"),
        ("total_ats", "ATS"),
        ("total_tesoro", "Tesoro"),
        ("total_cajas_ventanilla", "cajas ventanilla"),
        ("total_buzon_depositos", "buzón de depósitos"),
        ("total_recaudacion", "recaudación"),
        ("total_caja_chica", "caja chica"),
        ("total_otros", "otros"),
    ]
    distribution_parts = []
    for field, label in distribution_map:
        if field in row and row.get(field) is not None:
            distribution_parts.append(f"{label} { _format_value(row[field], field) }")

    if distribution_parts:
        sentences.append("Distribución actual: " + ", ".join(distribution_parts) + ".")

    measured_at = row.get("medido_en") or row.get("fecha")
    timestamp_text = _format_timestamp(measured_at)
    if timestamp_text:
        sentences.append(f"Última medición: {timestamp_text}.")

    return " ".join(_strip_sentence(sentence) for sentence in sentences if sentence)


def _is_dict(value: Optional[Dict[str, Any]]) -> bool:
    return isinstance(value, dict) and bool(value)


def _delta_values(reference: Any, comparable: Any) -> Optional[Decimal]:
    ref = _as_decimal(reference)
    target = _as_decimal(comparable)
    if ref is None or target is None:
        return None
    return ref - target


def _as_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def _format_timestamp(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        cleaned = cleaned.replace("Z", "+00:00") if cleaned.endswith("Z") else cleaned
        try:
            dt = datetime.fromisoformat(cleaned)
        except ValueError:
            return cleaned
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%d/%m/%Y %H:%M UTC")


def _strip_sentence(sentence: str) -> str:
    return sentence.strip().replace("  ", " ")


__all__ = [
    "compose_success_message",
    "extract_branch_descriptor",
    "relax_branch_filters",
]
