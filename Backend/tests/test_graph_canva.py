import warnings

import pytest

from src.graph_canva.repository import DEFAULT_WORKFLOW_ID, GraphCanvaRepository
from src.graph_canva.schemas import (
    GraphCanvaExecutionRequest,
    GraphCanvaWorkflow,
    GraphCanvaWorkflowUpdate,
    validate_payload_size,
)
from src.graph_canva.service import GraphCanvaService

warnings.filterwarnings("ignore", message='Field name "json" in "GraphCanvaPinItem" shadows')


class StubPushGateway:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    async def emit(self, workflow_id: str, message) -> None:  # type: ignore[override]
        self.messages.append({"workflow_id": workflow_id, "type": message.type})


def test_workflow_schema_roundtrip() -> None:
    repo = GraphCanvaRepository()
    workflow = repo.get_workflow(DEFAULT_WORKFLOW_ID)
    payload = workflow.model_dump(by_alias=True)
    clone = GraphCanvaWorkflow.model_validate(payload)
    assert clone == workflow


def test_validate_payload_size_truncates() -> None:
    payload = {"data": {"blob": "x" * 32}}
    clone, truncated = validate_payload_size(payload, limit_bytes=16)
    assert truncated is True
    assert clone["data"]["truncated"] is True
    assert payload is not clone


@pytest.mark.asyncio
async def test_service_run_workflow_finishes_successfully() -> None:
    repo = GraphCanvaRepository()
    push = StubPushGateway()
    svc = GraphCanvaService(repo, push)  # type: ignore[arg-type]
    execution = await svc.run_workflow(DEFAULT_WORKFLOW_ID, GraphCanvaExecutionRequest())

    assert execution.status == "success"
    assert execution.finished_at is not None
    assert execution.summary["metrics"]["duration_ms"] == 420

    event_types = [message["type"] for message in push.messages]
    assert event_types[0] == "execution_started"
    assert event_types[-1] == "execution_finished"


def test_patch_workflow_updates_node_position() -> None:
    repo = GraphCanvaRepository()
    svc = GraphCanvaService(repo)
    workflow = svc.get_workflow(DEFAULT_WORKFLOW_ID)
    node_id = workflow.nodes[0].id
    update = GraphCanvaWorkflowUpdate(node_positions={node_id: [10.0, 20.0]})
    updated = svc.update_workflow(DEFAULT_WORKFLOW_ID, update)
    new_position = next(node.position for node in updated.nodes if node.id == node_id)
    assert new_position == [10.0, 20.0]
