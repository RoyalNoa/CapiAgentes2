import json
from pathlib import Path

import pytest

from src.domain.agents.agent_models import IntentType
from src.infrastructure.langgraph.state_schema import GraphState, WorkflowStatus
from src.infrastructure.workspace.session_storage import SessionStorage


@pytest.fixture
def sample_state() -> GraphState:
    return GraphState(
        session_id="demo-session",
        trace_id="trace-001",
        user_id="user-123",
        original_query="¿Cuál es el saldo de la sucursal 12?",
        workflow_mode="chat",
        external_payload={},
        status=WorkflowStatus.COMPLETED,
        current_node="finalize",
        completed_nodes=["start", "finalize"],
        detected_intent=IntentType.QUERY,
        intent_confidence=0.92,
        routing_decision="summary",
        active_agent="summary",
        conversation_history=[
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "¡Hola!"},
        ],
        memory_window=[{"role": "user", "content": "Hola"}],
    )


def _manifest_path(storage: SessionStorage, session_id: str) -> Path:
    sanitized = storage.sanitize_session_id(session_id)
    return (
        storage._session_dir(sanitized)  # pylint: disable=protected-access
        / f"session_{sanitized}.json"
    )


def test_session_storage_persists_manifest(tmp_path, monkeypatch, sample_state: GraphState):
    workspace_root = tmp_path / "ia_workspace_root"
    monkeypatch.setenv("CAPI_IA_WORKSPACE", str(workspace_root))

    storage = SessionStorage()
    storage.update_from_state(sample_state)

    manifest_path = _manifest_path(storage, sample_state.session_id)
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["session_id"] == sample_state.session_id
    assert manifest["conversation_history"] == sample_state.conversation_history
    assert manifest["datab_exports"] == []
    assert sample_state.session_id in storage.list_sessions()


def test_session_storage_preserves_existing_exports(tmp_path, monkeypatch, sample_state: GraphState):
    workspace_root = tmp_path / "ia_workspace_root"
    monkeypatch.setenv("CAPI_IA_WORKSPACE", str(workspace_root))

    storage = SessionStorage()
    manifest_path = _manifest_path(storage, sample_state.session_id)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "session_id": sample_state.session_id,
                "sanitized_session_id": storage.sanitize_session_id(sample_state.session_id),
                "datab_exports": [{"filename": "DataB_file.json"}],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    storage.update_from_state(sample_state)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["datab_exports"] == [{"filename": "DataB_file.json"}]
    assert manifest["last_query"] == sample_state.original_query
    assert manifest["conversation_history"]