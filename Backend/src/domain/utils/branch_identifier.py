from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

_ALLOWED_TABLES = {
    "public.saldos_sucursal",
    "public.saldos_actuales_sucursal_oficial",
    "public.saldos_conciliacion_sucursal",
}


@dataclass
class BranchIdentifier:
    """Structured representation of a branch reference detected upstream."""

    raw_text: str
    number: Optional[int] = None
    name: Optional[str] = None
    identifier: Optional[str] = None

    def has_number(self) -> bool:
        return self.number is not None

    def has_name(self) -> bool:
        return bool(self.name)

    def has_identifier(self) -> bool:
        return bool(self.identifier)

    def build_condition(self, param_index_start: int = 1) -> Tuple[str, List[Any]]:
        """Build a safe SQL condition and parameters for the detected branch."""
        if self.identifier:
            return f"sucursal_id = ${param_index_start}", [self.identifier]
        if self.number is not None:
            return f"sucursal_numero = ${param_index_start}", [self.number]
        if self.name:
            return f"sucursal_nombre ILIKE ${param_index_start}", [f"%{self.name}%"]
        raise ValueError("Branch identifier is incomplete; cannot build condition")

    @property
    def display_value(self) -> str:
        if self.identifier:
            return self.identifier
        if self.number is not None:
            return f"#{self.number}"
        if self.name:
            return self.name
        return self.raw_text

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "branch_number": self.number,
            "branch_name": self.name,
            "branch_id": self.identifier,
        }

    @classmethod
    def from_payload(cls, payload: Dict[str, Any], fallback_text: str = "") -> Optional["BranchIdentifier"]:
        """Create an identifier from LLM payload data."""
        if not payload:
            return None
        number = payload.get("number")
        identifier = payload.get("id") or payload.get("identifier")
        name = payload.get("name") or payload.get("branch_name")
        raw = payload.get("raw_text") or fallback_text or name or identifier or str(number or "")
        if not any([number, identifier, name]):
            return None
        try:
            parsed_number = int(number) if number is not None else None
        except (TypeError, ValueError):
            parsed_number = None
        identifier = str(identifier).strip() if identifier else None
        name = str(name).strip() if name else None
        return cls(raw_text=raw or fallback_text, number=parsed_number, name=name, identifier=identifier)


def validate_table(table_name: str) -> str:
    """Ensure the suggested table is one of the allowed views."""
    normalized = table_name.strip()
    if normalized.lower() in {t.lower() for t in _ALLOWED_TABLES}:
        # Preserve canonical casing from allowlist
        for allowed in _ALLOWED_TABLES:
            if allowed.lower() == normalized.lower():
                return allowed
    # Default to safest view when LLM is unsure
    return "public.saldos_sucursal"


__all__ = ["BranchIdentifier", "validate_table"]
