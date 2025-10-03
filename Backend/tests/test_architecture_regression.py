"""Architecture regression tests to prevent duplicity re-introduction.

These tests ensure that:
1. Legacy conversation state modules don't reappear
2. Agent contracts remain unified
3. Import paths stay consistent
"""
import os
import pytest
from pathlib import Path


class TestArchitecturalConsistency:
    """Test suite to prevent architectural regression."""
    
    def test_no_legacy_conversation_state(self):
        """Ensure legacy conversation state module is not reintroduced."""
        legacy_path = Path(__file__).parent.parent / "src" / "core" / "conversation" / "state.py"
        assert not legacy_path.exists(), f"Legacy conversation state found at {legacy_path}"
    
    def test_no_duplicate_agent_models(self):
        """Ensure agent models are not duplicated."""
        models_path = Path(__file__).parent.parent / "src" / "domain" / "agents" / "models.py"
        contracts_path = Path(__file__).parent.parent / "src" / "domain" / "agents" / "contracts.py"
        
        assert not models_path.exists(), f"Duplicate models.py found at {models_path}"
        assert not contracts_path.exists(), f"Duplicate contracts.py found at {contracts_path}"
    
    def test_unified_agent_models_exists(self):
        """Ensure unified agent models file exists."""
        unified_path = Path(__file__).parent.parent / "src" / "domain" / "agents" / "agent_models.py"
        assert unified_path.exists(), f"Unified agent_models.py missing at {unified_path}"
    
    def test_no_legacy_src_agents(self):
        """Ensure legacy src/agents directory doesn't exist."""
        legacy_agents = Path(__file__).parent.parent / "src" / "agents"
        assert not legacy_agents.exists(), f"Legacy src/agents directory found at {legacy_agents}"
    
    def test_conversation_state_manager_import(self):
        """Test that ConversationStateManager imports from unified location."""
        try:
            from src.application.conversation.state_manager import ConversationStateManager
            assert ConversationStateManager is not None
        except ImportError as e:
            pytest.fail(f"ConversationStateManager import failed: {e}")
    
    def test_agent_models_import(self):
        """Test that agent models import from unified location."""
        try:
            from src.domain.agents.agent_models import (
                AgentTask, AgentResult, AgentError, 
                TaskStatus, ErrorSeverity, SuggestedAction
            )
            assert all([
                AgentTask is not None,
                AgentResult is not None,
                AgentError is not None,
                TaskStatus is not None,
                ErrorSeverity is not None,
                SuggestedAction is not None
            ])
        except ImportError as e:
            pytest.fail(f"Agent models import failed: {e}")
    
    def test_agent_protocol_import(self):
        """Test that agent protocol imports correctly."""
        try:
            from src.domain.agents.agent_protocol import Agent, BaseAgent, Intent, IntentType
            assert all([
                Agent is not None,
                BaseAgent is not None,
                Intent is not None,
                IntentType is not None
            ])
        except ImportError as e:
            pytest.fail(f"Agent protocol import failed: {e}")
    
    def test_backward_compatibility_alias(self):
        """Test that Intent alias works for backward compatibility."""
        from src.domain.agents.agent_protocol import Intent, IntentType
        assert Intent is IntentType, "Intent alias should point to IntentType"
    
    def test_no_circular_imports(self):
        """Test that there are no circular import issues."""
        try:
            # Import all major modules together
            from src.domain.agents.agent_models import AgentTask
            from src.domain.agents.agent_protocol import Agent
            from src.application.conversation.state_manager import ConversationStateManager
            
            # If we get here without ImportError, no circular dependencies
            assert True
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")


class TestCleanupValidation:
    """Validate that cleanup was successful."""
    
    def test_no_orphaned_imports(self):
        """Check that no files import from deleted modules."""
        backend_root = Path(__file__).parent.parent
        
        # Files that should not exist anymore
        forbidden_imports = [
            "from src.core.conversation.state",
            "from src.domain.agents.models",
            "from src.domain.agents.contracts",
            "from src.agents.base"
        ]
        
        # Scan all Python files
        for py_file in backend_root.rglob("*.py"):
            if py_file.name.startswith("test_architecture_regression"):
                continue  # Skip this test file
                
            try:
                content = py_file.read_text(encoding='utf-8')
                for forbidden in forbidden_imports:
                    assert forbidden not in content, \
                        f"Forbidden import '{forbidden}' found in {py_file}"
            except UnicodeDecodeError:
                # Skip binary or non-UTF8 files
                continue


@pytest.mark.integration
class TestIntegrationConsistency:
    """Test that the consolidated architecture works in integration."""
    
    def test_agent_task_creation(self):
        """Test creating an agent task with unified models."""
        from src.domain.agents.agent_models import AgentTask, TaskStatus
        
        task = AgentTask(
            task_id="test-123",
            intent="summary",
            query="Test query",
            user_id="test-user",
            session_id="test-session"
        )
        
        assert task.task_id == "test-123"
        assert task.intent == "summary"
        assert task.query == "Test query"
    
    def test_conversation_state_creation(self):
        """Test creating conversation state with unified manager."""
        from src.application.conversation.state_manager import ConversationStateManager
        
        manager = ConversationStateManager()
        session = manager.get_or_create_session("test-session", "test-user")
        
        assert session.session_id == "test-session"
        assert session.user_id == "test-user"
    
    def test_response_envelope_with_unified_models(self):
        """Test response envelope with unified agent models."""
        from src.domain.agents.agent_models import ResponseType, IntentType, ResponseEnvelope
        
        envelope = ResponseEnvelope(
            trace_id="trace-123",
            response_type=ResponseType.SUCCESS,
            intent=IntentType.SUMMARY,
            message="Test response"
        )
        
        assert envelope.trace_id == "trace-123"
        assert envelope.response_type == ResponseType.SUCCESS
        assert envelope.intent == IntentType.SUMMARY