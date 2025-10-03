from typing import Any, Dict

from fastapi.testclient import TestClient

from src.api.cash_policies_endpoints import get_cash_policy_service
from src.api.main import app


_DEFAULT_POLICY = {
    "channel": "ATM",
    "max_surplus_pct": 0.10,
    "max_deficit_pct": 0.05,
    "min_buffer_amount": None,
    "daily_withdrawal_limit": None,
    "daily_deposit_limit": None,
    "reload_lead_hours": None,
    "sla_hours": None,
    "truck_fixed_cost": None,
    "truck_variable_cost_per_kg": None,
    "notes": None,
    "updated_at": "2025-09-24T12:00:00",
}


class StubCashPolicyService:
    def __init__(self) -> None:
        self.policies = [_DEFAULT_POLICY]
        self.last_upsert: Dict[str, Any] | None = None
        self.raise_on_upsert: Exception | None = None

    async def list_policies(self):
        return self.policies

    async def upsert_policy(self, channel: str, payload: Dict[str, Any]):
        if self.raise_on_upsert:
            raise self.raise_on_upsert
        sanitized = {**_DEFAULT_POLICY, **payload, "channel": channel, "updated_at": "2025-09-24T12:30:00"}
        self.last_upsert = {"channel": channel, "payload": payload}
        return sanitized


def override_dependency(service: StubCashPolicyService):
    app.dependency_overrides[get_cash_policy_service] = lambda: service

def clear_override():
    app.dependency_overrides.pop(get_cash_policy_service, None)


def test_list_cash_policies_endpoint():
    service = StubCashPolicyService()
    override_dependency(service)
    try:
        with TestClient(app) as client:
            response = client.get("/api/cash-policies")
            assert response.status_code == 200
            assert response.json() == service.policies
    finally:
        clear_override()


def test_upsert_cash_policy_endpoint_success():
    service = StubCashPolicyService()
    override_dependency(service)
    try:
        with TestClient(app) as client:
            response = client.put(
                "/api/cash-policies/ATM",
                json={
                    "max_surplus_pct": 0.15,
                    "truck_fixed_cost": 25000,
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["channel"] == "ATM"
            assert payload["max_surplus_pct"] == 0.15
            assert payload["truck_fixed_cost"] == 25000
            assert service.last_upsert == {
                "channel": "ATM",
                "payload": {
                    "max_surplus_pct": 0.15,
                    "truck_fixed_cost": 25000,
                },
            }
    finally:
        clear_override()


def test_upsert_cash_policy_endpoint_validation_error():
    service = StubCashPolicyService()
    service.raise_on_upsert = ValueError("Dato inválido")
    override_dependency(service)
    try:
        with TestClient(app) as client:
            response = client.put(
                "/api/cash-policies/ATM",
                json={"max_surplus_pct": 0.2},
            )
            assert response.status_code == 400
            assert response.json()["detail"] == "Dato inválido"
    finally:
        clear_override()
