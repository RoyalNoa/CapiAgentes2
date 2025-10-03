import json
import pytest

from ia_workspace.agentes.capi_datab import handler
from ia_workspace.agentes.capi_datab.handler import CapiDataBAgent
from src.application.reasoning.llm_reasoner import LLMReasoningResult


class FakeReasoner:
    """Minimal stub that returns canned responses for planner and branch prompts."""

    def __init__(
        self,
        *,
        planner_payload: dict | None = None,
        branch_payload: dict | None = None,
        planner_confidence: float = 0.9,
    ) -> None:
        self._planner_payload = planner_payload
        self._branch_payload = branch_payload
        self._planner_confidence = planner_confidence

    async def reason(
        self,
        *,
        query: str,
        context_data=None,
        conversation_history=None,
        system_prompt: str | None = None,
        trace_id: str | None = None,
        response_format: str | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMReasoningResult:
        if system_prompt and "NL->SQL" in system_prompt:
            if self._planner_payload is None:
                return LLMReasoningResult(success=False, response=None, model="fake")
            return LLMReasoningResult(
                success=True,
                response=json.dumps(self._planner_payload),
                model="fake",
                provider="fake",
                confidence_score=self._planner_confidence,
            )
        if system_prompt == handler._BRANCH_ANALYST_PROMPT:
            if self._branch_payload is None:
                return LLMReasoningResult(success=False, response=None, model="fake")
            return LLMReasoningResult(
                success=True,
                response=json.dumps(self._branch_payload),
                model="fake",
                provider="fake",
                confidence_score=0.8,
            )
        return LLMReasoningResult(success=False, response=None, model="fake")


@pytest.fixture
def branch_agent():
    branch_payload = {
        "task": "branch_balance",
        "branch": {
            "name": "Villa Crespo",
            "raw_text": "Villa Crespo",
        },
        "table": "public.saldos_sucursal",
        "confidence": 0.9,
        "reasoning": "Sucursal identificada",
    }
    fake_reasoner = FakeReasoner(
        planner_payload=None,
        branch_payload=branch_payload,
    )
    return CapiDataBAgent(llm_reasoner=fake_reasoner)


def test_prepare_operation_builds_branch_query_from_llm(branch_agent):
    operation = branch_agent.prepare_operation(
        "Quiero el saldo total de la sucursal de Villa Crespo entre el 1 y el 31 de enero"
    )

    assert operation.operation == "select"
    assert "FROM public.saldos_sucursal" in operation.sql
    assert "ORDER BY medido_en DESC LIMIT 1" in operation.sql
    assert operation.parameters == ["%Villa Crespo%"]
    assert operation.output_format == "json"

    metadata = operation.metadata or {}
    assert metadata.get("planner_source") == "llm_branch_identifier"
    assert metadata.get("planner_confidence") == pytest.approx(0.9)
    assert metadata.get("suggested_table") == "public.saldos_sucursal"

    branch_meta = metadata.get("branch") or {}
    assert branch_meta.get("branch_name") == "Villa Crespo"

    filters = metadata.get("filters") or []
    assert filters and filters[0]["operator"] == "ILIKE"
    assert filters[0]["value"] == "%Villa Crespo%"


def test_prepare_operation_raises_when_branch_llm_fails():
    agent = CapiDataBAgent(llm_reasoner=FakeReasoner(planner_payload=None, branch_payload=None))

    with pytest.raises(ValueError, match="No se pudo interpretar la consulta de base de datos"):
        agent.prepare_operation("Necesito el saldo de Villa Crespo")
