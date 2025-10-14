"""
Test LangGraph orchestrator integration - verifies complete workflow
"""
import pytest
import tempfile
from pathlib import Path
from src.presentation.orchestrator_factory import OrchestratorFactory


@pytest.fixture(autouse=True)
def reset_agent_config():
    config_path = Path(tempfile.gettempdir()) / "capi_agents" / "agents_config.json"
    if config_path.exists():
        config_path.unlink()
    yield

from src.domain.agents.agent_models import ResponseEnvelope


@pytest.mark.asyncio
async def test_langgraph_orchestrator_greeting():
    """Test LangGraph orchestrator handles greeting intent"""
    # Create LangGraph orchestrator
    orchestrator = OrchestratorFactory.create_orchestrator()

    # Process greeting query
    result = await orchestrator.process_query(
        query="Hola, Ã‚Â¿cÃƒÂ³mo estÃƒÂ¡s?",
        user_id="test_user",
        session_id="test_session_1"
    )

    # Verify response envelope
    assert isinstance(result, ResponseEnvelope)
    assert result.message is not None
    assert len(result.message) > 0
    message_lower = result.message.lower()
    assert any(greeting in message_lower for greeting in ["hola", "saludos", "buen"]) or "resumen" in message_lower

    # Verify metadata contains LangGraph execution details
    assert result.meta is not None
    assert "completed_nodes" in result.meta


@pytest.mark.asyncio
async def test_langgraph_orchestrator_summary():
    """Test LangGraph orchestrator handles summary request"""
    # Create LangGraph orchestrator
    orchestrator = OrchestratorFactory.create_orchestrator()

    # Process summary query
    result = await orchestrator.process_query(
        query="Dame un resumen de los datos financieros",
        user_id="test_user",
        session_id="test_session_2"
    )

    # Verify response envelope
    assert isinstance(result, ResponseEnvelope)
    assert result.message is not None
    assert len(result.message) > 0

    # Should contain financial summary keywords
    message_lower = result.message.lower()
    assert any(word in message_lower for word in ["resumen", "registros", "total", "datos"])

    # Verify metadata
    assert result.meta is not None
    assert "completed_nodes" in result.meta
    assert "capi_gus" in str(result.meta.get("completed_nodes", []))
    reasoning_plan = result.data.get("reasoning_plan") if isinstance(result.data, dict) else None
    assert reasoning_plan is not None
    assert reasoning_plan.get("recommended_agent") in {"capi_gus", "capi_desktop", "capi_datab", "summary"}
    meta_summary = result.meta.get("reasoning_summary")
    assert meta_summary is not None
    assert meta_summary.get("progress_percent") is not None
    assert meta_summary.get("remaining_steps") >= 0
    assert result.meta.get("reasoning_plan") is not None


@pytest.mark.asyncio
async def test_langgraph_orchestrator_unknown_intent():
    """Test LangGraph orchestrator handles unknown/fallback intent"""
    # Create LangGraph orchestrator
    orchestrator = OrchestratorFactory.create_orchestrator()

    # Process unknown query
    result = await orchestrator.process_query(
        query="Ã‚Â¿CÃƒÂ³mo cocinar pasta?",
        user_id="test_user",
        session_id="test_session_3"
    )

    # Verify response envelope
    assert isinstance(result, ResponseEnvelope)
    assert result.message is not None
    assert len(result.message) > 0

    # Should provide helpful fallback response - LangGraph generates appropriate fallback
    # Just verify it's a reasonable fallback message
    assert len(result.message) > 10  # Has substantial content
    assert result.message is not None

    # Verify metadata
    assert result.meta is not None
    assert "completed_nodes" in result.meta


def test_langgraph_orchestrator_creation():
    """Test LangGraph orchestrator can be created successfully"""
    orchestrator = OrchestratorFactory.create_orchestrator()

    # Verify orchestrator has expected attributes
    assert hasattr(orchestrator, 'process_query')
    assert hasattr(orchestrator, 'agent_name')
    assert orchestrator.agent_name == "langgraph_orchestrator"


def test_orchestrator_factory_selects_langgraph():
    """Test factory always selects LangGraph as orchestrator type"""
    # Test with default parameter
    orchestrator1 = OrchestratorFactory.create_orchestrator()
    assert orchestrator1.agent_name == "langgraph_orchestrator"

    # Test with explicit langgraph type
    orchestrator2 = OrchestratorFactory.create_orchestrator(orchestrator_type="langgraph")
    assert orchestrator2.agent_name == "langgraph_orchestrator"

    # Test with legacy type (should still use LangGraph)
    orchestrator3 = OrchestratorFactory.create_orchestrator(orchestrator_type="default")
    assert orchestrator3.agent_name == "langgraph_orchestrator"
