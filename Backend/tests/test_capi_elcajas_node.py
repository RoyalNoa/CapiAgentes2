import pytest

from src.domain.agents.agent_models import AgentResult, TaskStatus
from src.infrastructure.langgraph.nodes.capi_elcajas_node import CapiElCajasNode
from src.infrastructure.langgraph.state_schema import GraphState

EL_CAJAS_AGENT_ID = "b37d1f90-6b35-4fb3-866e-2f88c9b29850"


@pytest.fixture
def el_cajas_node(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.langgraph.nodes.capi_elcajas_node.AGENT_AVAILABLE",
        False,
    )
    node = CapiElCajasNode()
    node.agent = object()  # ensure availability check passes
    return node


def _state_with_rows(**overrides):
    base = {
        "session_id": "session-1",
        "trace_id": "trace-1",
        "user_id": "user-1",
        "original_query": "saldo palermo",
        "response_message": "DataB: saldo disponible 1.000 ARS",
        "response_metadata": {},
        "response_data": {},
        "shared_artifacts": {"capi_datab": {"rows": [{"sucursal_id": "001"}]}}
    }
    base.update(overrides)
    return GraphState(**base)


def test_el_cajas_enriches_state(monkeypatch, el_cajas_node):
    data_payload = {
        "analysis": [{"status": "warning", "branch_id": "001"}],
        "alerts_created": 2,
        "alerts_to_persist": [{
            "priority": "critical",
            "prioridad": "critica",
            "estado": "abierta",
            "problema": "Alerta de prueba",
            "datos_clave": ["Desvio de prueba"],
            "acciones": "Evaluar caja",
            "agente_id": EL_CAJAS_AGENT_ID,
        }],
        "alert_operations": [{
            "values": {
                "prioridad": "critica",
                "estado": "abierta",
                "problema": "Alerta de prueba",
                "agente_id": EL_CAJAS_AGENT_ID,
            },
            "persisted": False,
        }],
        "recommendation_files": [{
            "path": "/tmp/recommendation.json",
            "filename": "recomendacion_boedo.xlsx",
            "summary": "Desvío relevante en Boedo",
            "hypothesis": "Cajas con déficit",
            "impact": "-20000 ARS",
            "branch_name": "Boedo",
            "suggested_actions": [{
                "channel": "Tesoro",
                "action": "Reforzar efectivo",
                "amount": 20000,
                "reason": "Déficit del 20%",
                "urgency": "alta"
            }]
        }],
    }
    agent_result = AgentResult(
        task_id="task-1",
        agent_name="capi_elcajas",
        status=TaskStatus.COMPLETED,
        data=data_payload,
        message="Desvio detectado en sucursal",
    )
    monkeypatch.setattr(el_cajas_node, "_run_agent", lambda task: agent_result)

    initial_state = _state_with_rows()
    updated = el_cajas_node.run(initial_state)

    assert "El Cajas: Desvio detectado en sucursal" in (updated.response_message or "")
    assert updated.response_metadata.get("el_cajas_status") == "warning"
    assert updated.response_metadata.get("el_cajas_alerts") == 2
    meta = updated.response_metadata or {}
    assert meta.get('el_cajas_pending') is True
    assert meta.get('requires_human_approval') is True
    actions = meta.get('actions') or []
    assert any(action.get('id') == 'save_recommendation' for action in actions)
    assert meta.get('pending_desktop_instruction')
    assert updated.response_data.get("el_cajas") == data_payload
    assert updated.shared_artifacts.get("capi_elcajas") == data_payload
    assert "capi_elcajas" in updated.completed_nodes
    assert updated.routing_decision == "human_gate"


def test_el_cajas_handles_agent_failure(monkeypatch, el_cajas_node):
    def boom(_task):
        raise RuntimeError("boom")

    monkeypatch.setattr(el_cajas_node, "_run_agent", boom)
    initial_state = _state_with_rows()

    updated = el_cajas_node.run(initial_state)

    assert updated.response_metadata.get("el_cajas_status") == "error"
    assert any(err["error_type"] == "el_cajas_error" for err in updated.errors)
    assert "El Cajas:" in (updated.response_message or "")


def test_el_cajas_no_rows_skips_agent(monkeypatch, el_cajas_node):
    called = False

    def marker(_task):  # pragma: no cover - should not execute
        nonlocal called
        called = True

    monkeypatch.setattr(el_cajas_node, "_run_agent", marker)
    state = _state_with_rows(shared_artifacts={"capi_datab": {"rows": []}})

    updated = el_cajas_node.run(state)

    assert called is False
    assert updated.response_metadata.get("el_cajas_status") == "no_data"
    assert "El Cajas" in (updated.response_message or "")
    assert "capi_elcajas" in updated.completed_nodes
