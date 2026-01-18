from src.domain.agents.agent_models import ResponseEnvelope, ResponseType, IntentType
from src.infrastructure.langgraph.adapters.orchestrator_adapter import LangGraphOrchestratorAdapter


def make_adapter() -> LangGraphOrchestratorAdapter:
    adapter = LangGraphOrchestratorAdapter.__new__(LangGraphOrchestratorAdapter)  # type: ignore[call-arg]
    adapter._gmail_confirmations = {}
    adapter._gmail_last_responses = {}
    return adapter


def make_envelope(data: dict[str, object]) -> ResponseEnvelope:
    return ResponseEnvelope(
        trace_id="trace-id",
        response_type=ResponseType.SUCCESS,
        intent=IntentType.SUMMARY,
        message="",
        data=data,
    )


def test_extract_response_text_prefers_summary_message() -> None:
    adapter = make_adapter()
    summary = (
        "Analicé 79 sucursales contra la franja tolerable del canal Saldo Total (40%). "
        "23 muestran excedentes fuera de tolerancia y 20 registran faltantes."
    )
    envelope = make_envelope(
        {
            "summary_message": summary,
            "rows": [
                {"sucursal_nombre": "Abasto", "saldo_total_sucursal": 102000, "caja_teorica_sucursal": 100000},
                {"sucursal_nombre": "Palermo", "saldo_total_sucursal": 50000, "caja_teorica_sucursal": 60000},
            ],
        }
    )

    result = adapter._extract_response_text(envelope)

    assert result == summary


def test_friendly_fallback_skips_all_branches_scope() -> None:
    adapter = make_adapter()
    data = {
        "analysis_scope": "all_branches",
        "rows": [{"sucursal_nombre": "Abasto", "saldo_total_sucursal": 102000, "caja_teorica_sucursal": 100000}],
    }
    envelope = make_envelope(data)

    result = adapter._compose_friendly_fallback(data, envelope)

    assert result is None


def test_friendly_fallback_returns_single_branch_message() -> None:
    adapter = make_adapter()
    data = {
        "rows": [{"sucursal_nombre": "Abasto", "saldo_total_sucursal": 102000, "caja_teorica_sucursal": 100000}],
        "file_path": "DataB_2025_10_29_815152.json",
    }
    envelope = make_envelope(data)

    result = adapter._compose_friendly_fallback(data, envelope)

    assert "Abasto" in result
    assert "¿Querés que guarde este análisis en el escritorio" in result
