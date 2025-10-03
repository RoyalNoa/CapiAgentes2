import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
IA_WORKSPACE = BACKEND_ROOT / "ia_workspace"
if str(IA_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(IA_WORKSPACE))

import json
from typing import Any, Dict

import pytest

from src.application.reasoning.llm_reasoner import LLMReasoningResult
from src.domain.utils.branch_identifier import BranchIdentifier
from agentes.capi_datab.handler import CapiDataBAgent, DbOperation, ExecutionResult


class FakeReasoner:
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload

    async def reason(self, **_: Any) -> LLMReasoningResult:  # pragma: no cover - simple stub
        return LLMReasoningResult(
            success=True,
            response=json.dumps(self.payload),
            model="fake-llm",
            confidence_score=0.9,
        )


@pytest.mark.parametrize(
    "branch_payload,expected_param",
    [
        ({"task": "branch_balance", "branch": {"number": 45}}, [45]),
        ({"task": "branch_balance", "branch": {"name": "Palermo"}}, ["%Palermo%"]),
    ],
)
def test_llm_branch_balance(branch_payload, expected_param):
    agent = CapiDataBAgent(llm_reasoner=FakeReasoner(branch_payload))
    operation = agent.prepare_operation("cuánto dinero hay en la sucursal solicitada?")

    assert operation.operation == "select"
    assert "FROM public.saldos_sucursal" in operation.sql
    assert operation.parameters == expected_param
    assert BranchIdentifier.from_payload(branch_payload.get("branch")) is not None


def test_llm_branch_balance_returns_none_when_llm_says_other():
    agent = CapiDataBAgent(llm_reasoner=FakeReasoner({"task": "other"}))
    operation = agent.prepare_operation("consulta poco clara")

    assert operation.operation == "select"
    assert "sucursal" not in operation.sql.lower()


def test_datab_exports_land_in_workspace(tmp_path, monkeypatch):
    # Provide env path pointing to the agentes subfolder to verify normalization
    workspace_root = tmp_path / "custom_root"
    monkeypatch.setenv("CAPI_IA_WORKSPACE", str(workspace_root / "agentes"))

    agent = CapiDataBAgent(llm_reasoner=FakeReasoner({"task": "other"}))
    operation = DbOperation(
        operation="select",
        sql="SELECT 1",
        parameters=[],
        output_format="json",
        table="public.demo",
        requires_approval=False,
        description="test",
        raw_request="SELECT 1",
    )
    execution = ExecutionResult(rows=[{"value": 1}], rowcount=1, returning=True)

    session_id = "chat-123 demo"
    export_path = agent._export_result(operation, execution, session_id=session_id)

    sanitized = agent._sanitize_session_id(session_id)
    expected_session_dir = workspace_root / "data" / "sessions" / f"session_{sanitized}"

    assert export_path.parent == expected_session_dir / "capi_DataB"
    assert export_path.exists()

    manifest_path = expected_session_dir / f"session_{sanitized}.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["session_id"] == session_id
    assert manifest["datab_exports"], "Expected manifest to track DataB exports"
    first_export = manifest["datab_exports"][0]
    assert first_export["filename"] == export_path.name
    assert first_export["relative_path"].startswith("capi_DataB/")
    assert Path(first_export["absolute_path"]).resolve() == export_path.resolve()

