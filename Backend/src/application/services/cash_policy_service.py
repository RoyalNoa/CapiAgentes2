"""Service layer for managing cash policies per channel."""
from __future__ import annotations

from typing import Any, Dict, List

from src.infrastructure.database.postgres_client import (
    PostgreSQLClient,
    get_postgres_client,
)


DEFAULT_CHANNELS = {
    "ATM",
    "ATS",
    "Tesoro",
    "Ventanilla",
    "Buzon",
    "Recaudacion",
    "Caja Chica",
    "Otros",
}


class CashPolicyService:
    """Encapsulates access and validation for cash management policies."""

    def __init__(self, client: PostgreSQLClient | None = None) -> None:
        self._client = client or get_postgres_client()

    async def list_policies(self) -> List[Dict[str, Any]]:
        """Retrieve configured cash policies ordered by channel."""
        return await self._client.get_cash_policies()

    async def upsert_policy(self, channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a policy for the requested channel."""
        normalized_channel = (channel or "").strip()
        if not normalized_channel:
            raise ValueError("El canal es obligatorio")
        if normalized_channel not in DEFAULT_CHANNELS:
            # Permit new channels but warn downstream callers.
            DEFAULT_CHANNELS.add(normalized_channel)
        sanitized = self._sanitize_payload(payload)
        return await self._client.upsert_cash_policy(normalized_channel, sanitized)

    def _sanitize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        cleaned: Dict[str, Any] = {}
        payload = payload or {}
        for key, value in payload.items():
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed == "":
                    cleaned[key] = None
                    continue
                if key in {"max_surplus_pct", "max_deficit_pct", "min_buffer_amount",
                           "daily_withdrawal_limit", "daily_deposit_limit",
                           "reload_lead_hours", "sla_hours",
                           "truck_fixed_cost", "truck_variable_cost_per_kg"}:
                    try:
                        cleaned[key] = float(trimmed)
                        continue
                    except ValueError as exc:
                        raise ValueError(f"Valor invalido para {key}") from exc
                cleaned[key] = trimmed
            else:
                cleaned[key] = value
        return cleaned
