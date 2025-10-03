import pytest

from src.application.services import cash_policy_service as module
from src.application.services.cash_policy_service import CashPolicyService


class StubPostgresClient:
    def __init__(self):
        self.list_payload = [
            {
                "channel": "ATM",
                "max_surplus_pct": 0.1,
                "max_deficit_pct": 0.05,
                "updated_at": "2025-09-24T12:00:00",
            }
        ]
        self.last_upsert_channel = None
        self.last_upsert_payload = None

    async def get_cash_policies(self):
        return self.list_payload

    async def upsert_cash_policy(self, channel, payload):
        self.last_upsert_channel = channel
        self.last_upsert_payload = payload
        return {"channel": channel, **payload}


@pytest.mark.asyncio
async def test_list_policies_delegates_to_client():
    client = StubPostgresClient()
    service = CashPolicyService(client=client)

    policies = await service.list_policies()

    assert policies == client.list_payload


@pytest.mark.asyncio
async def test_upsert_policy_sanitizes_numeric_strings(monkeypatch):
    monkeypatch.setattr(module, "DEFAULT_CHANNELS", {"ATM", "Tesoro"})
    client = StubPostgresClient()
    service = CashPolicyService(client=client)

    result = await service.upsert_policy(
        " ATM ",
        {
            "max_surplus_pct": " 0.25 ",
            "min_buffer_amount": "1000",
            "notes": "   revisar semanal   ",
        },
    )

    assert client.last_upsert_channel == "ATM"
    assert client.last_upsert_payload["max_surplus_pct"] == pytest.approx(0.25)
    assert client.last_upsert_payload["min_buffer_amount"] == pytest.approx(1000.0)
    assert client.last_upsert_payload["notes"] == "revisar semanal"
    assert result["channel"] == "ATM"
    assert result["max_surplus_pct"] == pytest.approx(0.25)


@pytest.mark.asyncio
async def test_upsert_policy_accepts_new_channels(monkeypatch):
    monkeypatch.setattr(module, "DEFAULT_CHANNELS", {"ATM"})
    client = StubPostgresClient()
    service = CashPolicyService(client=client)

    await service.upsert_policy("Caja Auxiliar", {})

    assert client.last_upsert_channel == "Caja Auxiliar"
    assert "Caja Auxiliar" in module.DEFAULT_CHANNELS


@pytest.mark.asyncio
async def test_upsert_policy_rejects_blank_channel(monkeypatch):
    monkeypatch.setattr(module, "DEFAULT_CHANNELS", {"ATM"})
    client = StubPostgresClient()
    service = CashPolicyService(client=client)

    with pytest.raises(ValueError):
        await service.upsert_policy("   ", {})

    assert client.last_upsert_channel is None


@pytest.mark.asyncio
async def test_upsert_policy_validates_numeric_fields(monkeypatch):
    monkeypatch.setattr(module, "DEFAULT_CHANNELS", {"ATM"})
    client = StubPostgresClient()
    service = CashPolicyService(client=client)

    with pytest.raises(ValueError):
        await service.upsert_policy("ATM", {"max_surplus_pct": "not-a-number"})

    assert client.last_upsert_channel is None
