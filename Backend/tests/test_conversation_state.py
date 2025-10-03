"""Tests for ConversationStateManager (ORCH-A8)."""
import pytest
import time
from datetime import datetime, timedelta

from src.application.conversation.state_manager import ConversationStateManager
from src.application.conversation.state_models import ConversationState, Turn, TurnType


class TestConversationStateManager:
    """Test ConversationStateManager functionality."""
    
    @pytest.fixture
    def state_manager(self):
        """Create a ConversationStateManager instance."""
        return ConversationStateManager(max_sessions=10, session_ttl_minutes=30)
    
    def test_get_or_create_session(self, state_manager):
        """Test session creation and retrieval."""
        # Create new session
        session = state_manager.get_or_create_session("test-session", "test-user")
        
        assert session.session_id == "test-session"
        assert session.user_id == "test-user"
        assert session.active is True
        assert len(session.turns) == 0
        
        # Retrieve existing session
        same_session = state_manager.get_or_create_session("test-session", "test-user")
        assert same_session is session  # Should be the same object
    
    def test_add_user_turn(self, state_manager):
        """Test adding user turns to conversation."""
        turn = state_manager.add_user_turn(
            session_id="test-session",
            user_id="test-user",
            content="Hello, I need help",
            intent="greeting",
            metadata={"source": "web"}
        )
        
        assert turn.turn_type == TurnType.USER
        assert turn.content == "Hello, I need help"
        assert turn.intent == "greeting"
        assert turn.metadata["source"] == "web"
        assert turn.turn_id.startswith("user_")
        
        # Check session was updated
        session = state_manager._sessions["test-session"]
        assert len(session.turns) == 1
        assert session.turns[0] is turn
    
    def test_add_agent_turn(self, state_manager):
        """Test adding agent turns to conversation."""
        # Create session first
        state_manager.get_or_create_session("test-session", "test-user")
        
        response_data = {"analysis_type": "summary", "records": 100}
        turn = state_manager.add_agent_turn(
            session_id="test-session",
            content="Here's your financial summary",
            agent_name="SummaryAgent",
            response_data=response_data,
            metadata={"processing_time": 150.5}
        )
        
        assert turn.turn_type == TurnType.AGENT
        assert turn.content == "Here's your financial summary"
        assert turn.metadata["agent_name"] == "SummaryAgent"
        assert turn.metadata["response_data"] == response_data
        assert turn.metadata["processing_time"] == 150.5
        assert turn.turn_id.startswith("agent_")
    
    def test_add_agent_turn_nonexistent_session(self, state_manager):
        """Test adding agent turn to nonexistent session raises error."""
        with pytest.raises(ValueError, match="Session nonexistent not found"):
            state_manager.add_agent_turn(
                session_id="nonexistent",
                content="Test",
                agent_name="TestAgent"
            )
    
    def test_is_repeated_query_detection(self, state_manager):
        """Test repeated query detection."""
        session_id = "test-session"
        query = "Show me the financial summary"
        
        # First occurrence should not be repeated
        is_repeated_first = state_manager.is_repeated_query(session_id, query)
        assert is_repeated_first is False
        
        # Immediate repetition should be detected
        is_repeated_second = state_manager.is_repeated_query(session_id, query)
        assert is_repeated_second is True
        
        # Slightly different query should not be repeated
        is_repeated_different = state_manager.is_repeated_query(session_id, "Show me the summary")
        assert is_repeated_different is False
    
    def test_is_repeated_query_normalization(self, state_manager):
        """Test query normalization in repetition detection."""
        session_id = "test-session"
        
        # Add first query
        state_manager.is_repeated_query(session_id, "Show me the summary")
        
        # These should be detected as repetitions due to normalization
        assert state_manager.is_repeated_query(session_id, "SHOW ME THE SUMMARY") is True
        assert state_manager.is_repeated_query(session_id, "  show   me   the    summary  ") is True
    
    def test_is_summary_repeated(self, state_manager):
        """Test summary repetition detection using data hashing."""
        session_id = "test-session"
        
        summary_data = {
            "total_records": 100,
            "total_amount": 50000.0,
            "anomalies_detected": 2,
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"}
        }
        
        # First summary should not be repeated
        is_repeated_first = state_manager.is_summary_repeated(session_id, summary_data)
        assert is_repeated_first is False
        
        # Same data should be detected as repeated
        is_repeated_same = state_manager.is_summary_repeated(session_id, summary_data)
        assert is_repeated_same is True
        
        # Different data should not be repeated
        different_data = summary_data.copy()
        different_data["total_records"] = 150
        is_repeated_different = state_manager.is_summary_repeated(session_id, different_data)
        assert is_repeated_different is False
    
    def test_summary_hash_consistency(self, state_manager):
        """Test that summary hashing is consistent and order-independent."""
        data1 = {
            "total_records": 100,
            "total_amount": 1000.0,
            "anomalies_detected": 1,
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"}
        }
        
        data2 = {
            "anomalies_detected": 1,
            "total_amount": 1000.0,
            "total_records": 100,
            "date_range": {"end": "2024-12-31", "start": "2024-01-01"}
        }
        
        hash1 = state_manager._hash_summary_data(data1)
        hash2 = state_manager._hash_summary_data(data2)
        
        assert hash1 == hash2  # Should be same despite different key order
    
    def test_get_conversation_context(self, state_manager):
        """Test getting conversation context."""
        session_id = "test-session"
        
        # Add some turns
        state_manager.add_user_turn(session_id, "test-user", "Hello", "greeting")
        state_manager.add_agent_turn(session_id, "Hi there!", "GreetingAgent")
        state_manager.add_user_turn(session_id, "test-user", "Show summary", "summary_request")
        
        context = state_manager.get_conversation_context(session_id, max_turns=2)
        
        assert context["session_exists"] is True
        assert len(context["recent_turns"]) == 2
        assert context["total_turns"] == 3
        assert context["session_duration_minutes"] >= 0
        
        # Check turn data
        recent_turns = context["recent_turns"]
        assert recent_turns[0]["type"] == "agent"
        assert recent_turns[0]["content"] == "Hi there!"
        assert recent_turns[1]["type"] == "user"
        assert recent_turns[1]["content"] == "Show summary"
        assert recent_turns[1]["intent"] == "summary_request"
    
    def test_get_conversation_context_nonexistent_session(self, state_manager):
        """Test getting context for nonexistent session."""
        context = state_manager.get_conversation_context("nonexistent")
        
        assert context["session_exists"] is False
        assert context["recent_turns"] == []
    
    def test_update_session_context(self, state_manager):
        """Test updating session context."""
        session_id = "test-session"
        
        # Create session
        state_manager.get_or_create_session(session_id, "test-user")
        
        # Update context
        state_manager.update_session_context(session_id, {
            "preferred_language": "spanish",
            "analysis_depth": "detailed"
        })
        
        session = state_manager._sessions[session_id]
        assert session.context["preferred_language"] == "spanish"
        assert session.context["analysis_depth"] == "detailed"
        
        # Update with more data
        state_manager.update_session_context(session_id, {
            "preferred_language": "english",  # Should overwrite
            "time_zone": "UTC"  # Should add
        })
        
        assert session.context["preferred_language"] == "english"
        assert session.context["analysis_depth"] == "detailed"  # Should remain
        assert session.context["time_zone"] == "UTC"
    
    def test_get_session_stats(self, state_manager):
        """Test getting session statistics."""
        # Initial stats
        stats = state_manager.get_session_stats()
        assert stats["active_sessions"] == 0
        assert stats["total_turns"] == 0
        
        # Add some activity
        state_manager.add_user_turn("session1", "user1", "Hello")
        state_manager.add_agent_turn("session1", "Hi!", "Agent1")
        state_manager.add_user_turn("session2", "user2", "Summary please")
        
        stats = state_manager.get_session_stats()
        assert stats["active_sessions"] == 2
        assert stats["total_turns"] == 3
    
    def test_session_cleanup_by_ttl(self):
        """Test session cleanup based on TTL."""
        # Create manager with very short TTL
        state_manager = ConversationStateManager(max_sessions=10, session_ttl_minutes=0)
        
        # Create a session
        session = state_manager.get_or_create_session("old-session", "user1")
        
        # Manually set updated_at to past
        session.updated_at = datetime.now() - timedelta(minutes=5)
        
        # Creating new session should trigger cleanup
        state_manager.get_or_create_session("new-session", "user2")
        
        # Old session should be cleaned up
        assert "old-session" not in state_manager._sessions
        assert "new-session" in state_manager._sessions
    
    def test_session_cleanup_by_max_sessions(self):
        """Test session cleanup when max sessions exceeded."""
        # Create manager with max 2 sessions
        state_manager = ConversationStateManager(max_sessions=2, session_ttl_minutes=60)
        
        # Create 3 sessions
        state_manager.get_or_create_session("session1", "user1")
        time.sleep(0.01)  # Small delay to ensure different timestamps
        state_manager.get_or_create_session("session2", "user2")
        time.sleep(0.01)
        state_manager.get_or_create_session("session3", "user3")
        
        # Should only have 2 sessions (oldest one removed)
        assert len(state_manager._sessions) == 2
        assert "session1" not in state_manager._sessions  # Oldest removed
        assert "session2" in state_manager._sessions
        assert "session3" in state_manager._sessions
    
    def test_recent_hash_limit(self, state_manager):
        """Test that recent hashes are limited to prevent unbounded growth."""
        session_id = "test-session"
        
        # Add 15 different queries (more than the 10 hash limit)
        for i in range(15):
            state_manager.is_repeated_query(session_id, f"Query number {i}")
        
        # Should have at most 10 recent hashes
        recent_hashes = state_manager._recent_hashes.get(session_id, set())
        assert len(recent_hashes) <= 10


class TestConversationStateManagerIntegration:
    """Integration tests for ConversationStateManager."""
    
    def test_full_conversation_flow(self):
        """Test complete conversation flow with state tracking."""
        state_manager = ConversationStateManager()
        session_id = "integration-test"
        user_id = "test-user"
        
        # User starts conversation
        user_turn1 = state_manager.add_user_turn(
            session_id, user_id, "Hello, I need financial analysis", "greeting"
        )
        
        # Agent responds
        agent_turn1 = state_manager.add_agent_turn(
            session_id, "Hi! I can help with financial analysis. What would you like to know?",
            "GreetingAgent"
        )
        
        # User asks for summary
        user_turn2 = state_manager.add_user_turn(
            session_id, user_id, "Give me a financial summary", "summary_request"
        )
        
        # Check if it's a repeated query (should be false for first check after adding turn)
        is_repeated = state_manager.is_repeated_query(session_id, "Give me a financial summary")
        assert is_repeated is False  # False because is_repeated_query was not called before adding the turn
        
        # Now it should be repeated if we ask again
        is_repeated_second = state_manager.is_repeated_query(session_id, "Give me a financial summary")
        assert is_repeated_second is True  # True because we just checked it above
        
        # Agent provides summary
        summary_data = {
            "total_records": 1000,
            "total_amount": 500000.0,
            "anomalies_detected": 5
        }
        agent_turn2 = state_manager.add_agent_turn(
            session_id, "Here's your financial summary", "SummaryAgent", summary_data
        )
        
        # Check if summary is repeated (should be false for first time)
        is_summary_repeated = state_manager.is_summary_repeated(session_id, summary_data)
        assert is_summary_repeated is False  # First time generating this summary
        
        # Same summary again should be detected as repeated
        is_summary_repeated_again = state_manager.is_summary_repeated(session_id, summary_data)
        assert is_summary_repeated_again is True
        
        # Get conversation context
        context = state_manager.get_conversation_context(session_id)
        
        assert context["session_exists"] is True
        assert context["total_turns"] == 4
        assert len(context["recent_turns"]) == 4
        
        # Verify turn sequence
        turns = context["recent_turns"]
        assert turns[0]["type"] == "user"
        assert turns[0]["content"] == "Hello, I need financial analysis"
        assert turns[1]["type"] == "agent"
        assert turns[2]["type"] == "user"
        assert turns[2]["content"] == "Give me a financial summary"
        assert turns[3]["type"] == "agent"
        assert turns[3]["content"] == "Here's your financial summary"