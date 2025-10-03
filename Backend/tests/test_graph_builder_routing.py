
import os
from contextlib import contextmanager

import pytest
from unittest.mock import patch, MagicMock

from src.infrastructure.langgraph.graph_builder import GraphBuilder
from src.infrastructure.langgraph.state_schema import GraphState
from src.infrastructure.langgraph.nodes.router_node import RouterNode
from src.domain.contracts.intent import Intent


@contextmanager
def patched_env():
    values = {
        "SECRET_KEY": "x" * 32,
        "API_KEY_BACKEND": "y" * 32,
        "OPENAI_API_KEY": "sk-test-1234567890abcdef1234567890abcdef",
    }
    original = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, old_value in original.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def _build_graph_builder():
    with patched_env():
        builder = GraphBuilder()
        builder.build_minimal()
        return builder


def _make_state(metadata):
    return GraphState(
        session_id="test-session",
        trace_id="trace-123",
        user_id="tester",
        original_query="consulta",
        response_metadata=metadata,
    )


def test_capi_datab_routes_to_el_cajas_when_pending():
    builder = _build_graph_builder()
    conditional = builder._conditional_edges.get("capi_datab")
    assert conditional is not None

    state = _make_state({"el_cajas_pending": True})
    assert conditional.resolver(state) == "capi_elcajas"


def test_capi_datab_routes_to_desktop_when_ready():
    builder = _build_graph_builder()
    conditional = builder._conditional_edges.get("capi_datab")
    assert conditional is not None

    state = _make_state({"datab_desktop_ready": True})
    assert conditional.resolver(state) == "capi_desktop"


def test_capi_datab_routes_to_human_gate_by_default():
    builder = _build_graph_builder()
    conditional = builder._conditional_edges.get("capi_datab")
    assert conditional is not None

    state = _make_state({})
    assert conditional.resolver(state) == "human_gate"


def test_router_short_circuits_to_el_cajas_after_datab():
    with patched_env(),             patch('src.infrastructure.langgraph.nodes.router_node.SemanticIntentService') as semantic_mock,             patch('src.infrastructure.langgraph.nodes.router_node.get_global_context_manager'),             patch('src.infrastructure.langgraph.nodes.router_node.get_semantic_metrics'):

        semantic_instance = semantic_mock.return_value
        semantic_instance.classify_intent.return_value = MagicMock(
            target_agent='summary',
            intent=Intent.SUMMARY_REQUEST,
            confidence=0.5,
            requires_clarification=False,
            entities={},
            reasoning='',
            provider='test-provider',
            model='test-model',
        )

        state = GraphState(
            session_id='test-session',
            trace_id='trace-001',
            user_id='tester',
            original_query='saldo palermo',
            detected_intent=Intent.DB_OPERATION,
            intent_confidence=0.9,
            completed_nodes=['start', 'capi_datab'],
            response_metadata={'el_cajas_pending': True},
        )

        router = RouterNode()
        updated = router.run(state)

        assert updated.routing_decision == 'capi_elcajas'
        semantic_instance.classify_intent.assert_not_called()

