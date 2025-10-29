from decimal import Decimal

from src.infrastructure.langgraph.utils.capi_datab_formatter import compose_success_message


class _DummyOperation:
    operation = "select"

    def __init__(self) -> None:
        self.metadata = {}
        self.raw_request = ""
        self.sql = ""
        self.parameters = []

    def preview(self):
        return {}


def test_compose_success_message_excludes_timestamp_line():
    operation = _DummyOperation()
    data_payload = {
        "rows": [
            {
                "sucursal_nombre": "Palermo",
                "saldo_total_sucursal": Decimal("88000"),
                "medido_en": "2025-10-17T05:11:00Z",
            }
        ]
    }

    message = compose_success_message(
        operation=operation,
        data_payload=data_payload,
        planner_meta=None,
        export_file=None,
        fallback_message=None,
    )

    assert "Última medición" not in message
    assert "Palermo" in message
    assert "saldo total" in message.lower()
