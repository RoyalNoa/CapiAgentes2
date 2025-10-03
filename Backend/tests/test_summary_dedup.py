"""Tests for summary deduplication functionality (ORCH-A8)."""
import pytest

from src.application.conversation.state_manager import ConversationStateManager


class TestSummaryDeduplication:
    """Test summary deduplication using SHA256 hash of ordered metrics."""
    
    @pytest.fixture
    def state_manager(self):
        """Create a ConversationStateManager instance."""
        return ConversationStateManager()
    
    def test_hash_summary_data_ordered_metrics(self, state_manager):
        """Test that summary hashing uses ordered metrics consistently."""
        # Core financial metrics in different orders
        summary1 = {
            "total_records": 1000,
            "total_amount": 50000.0,
            "anomalies_detected": 3,
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "extra_field": "ignored"  # Should be ignored in hash
        }
        
        summary2 = {
            "anomalies_detected": 3,
            "date_range": {"end": "2024-12-31", "start": "2024-01-01"},
            "total_amount": 50000.0,
            "total_records": 1000,
            "another_extra": "also ignored"  # Should be ignored
        }
        
        hash1 = state_manager._hash_summary_data(summary1)
        hash2 = state_manager._hash_summary_data(summary2)
        
        assert hash1 == hash2  # Should be identical
        assert len(hash1) == 16  # Should be truncated SHA256 (first 16 chars)
    
    def test_hash_summary_data_different_values(self, state_manager):
        """Test that different metric values produce different hashes."""
        base_summary = {
            "total_records": 1000,
            "total_amount": 50000.0,
            "anomalies_detected": 3,
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"}
        }
        
        # Test different total_records
        diff_records = base_summary.copy()
        diff_records["total_records"] = 2000
        
        # Test different total_amount
        diff_amount = base_summary.copy()
        diff_amount["total_amount"] = 75000.0
        
        # Test different anomalies
        diff_anomalies = base_summary.copy()
        diff_anomalies["anomalies_detected"] = 5
        
        # Test different date range
        diff_dates = base_summary.copy()
        diff_dates["date_range"] = {"start": "2024-01-01", "end": "2024-06-30"}
        
        base_hash = state_manager._hash_summary_data(base_summary)
        records_hash = state_manager._hash_summary_data(diff_records)
        amount_hash = state_manager._hash_summary_data(diff_amount)
        anomalies_hash = state_manager._hash_summary_data(diff_anomalies)
        dates_hash = state_manager._hash_summary_data(diff_dates)
        
        # All should be different
        hashes = [base_hash, records_hash, amount_hash, anomalies_hash, dates_hash]
        assert len(set(hashes)) == 5  # All unique
    
    def test_hash_summary_data_missing_fields(self, state_manager):
        """Test that missing fields are handled gracefully."""
        incomplete_summary = {
            "total_records": 500,
            # Missing total_amount, anomalies_detected, date_range
        }
        
        complete_summary = {
            "total_records": 500,
            "total_amount": 0,
            "anomalies_detected": 0,
            "date_range": {"start": None, "end": None}
        }
        
        incomplete_hash = state_manager._hash_summary_data(incomplete_summary)
        complete_hash = state_manager._hash_summary_data(complete_summary)
        
        # Should be the same (missing fields default to 0/None)
        assert incomplete_hash == complete_hash
    
    def test_summary_deduplication_realistic_scenario(self, state_manager):
        """Test realistic summary deduplication scenario."""
        session_id = "financial_session"
        
        # First summary request
        summary_v1 = {
            "total_records": 2500,
            "total_amount": 1250000.0,
            "anomalies_detected": 7,
            "date_range": {"start": "2024-01-01", "end": "2024-09-09"},
            "processing_time": 150.5,  # This should be ignored in hash
            "timestamp": "2024-09-09T10:30:00"  # This should be ignored in hash
        }
        
        is_repeated = state_manager.is_summary_repeated(session_id, summary_v1)
        assert is_repeated is False  # First time
        
        # Same core data, different metadata (should be considered repeated)
        summary_v2 = {
            "total_records": 2500,
            "total_amount": 1250000.0,
            "anomalies_detected": 7,
            "date_range": {"start": "2024-01-01", "end": "2024-09-09"},
            "processing_time": 275.8,  # Different processing time
            "timestamp": "2024-09-09T10:35:00",  # Different timestamp
            "agent_name": "SummaryAgent"  # Extra field
        }
        
        is_repeated_v2 = state_manager.is_summary_repeated(session_id, summary_v2)
        assert is_repeated_v2 is True  # Should be detected as repeated
        
        # Updated data (new records processed) should not be repeated
        summary_v3 = {
            "total_records": 2750,  # More records
            "total_amount": 1375000.0,  # More amount
            "anomalies_detected": 8,  # More anomalies
            "date_range": {"start": "2024-01-01", "end": "2024-09-09"}  # Same date range
        }
        
        is_repeated_v3 = state_manager.is_summary_repeated(session_id, summary_v3)
        assert is_repeated_v3 is False  # New data, not repeated
        
        # Going back to v1 data should not be repeated because we moved to v3 (only tracks last hash)
        is_repeated_v1_again = state_manager.is_summary_repeated(session_id, summary_v1)
        assert is_repeated_v1_again is False  # Not repeated because we moved to v3
        
        # But v1 again should now be repeated since we just checked it
        is_repeated_v1_again_2 = state_manager.is_summary_repeated(session_id, summary_v1)
        assert is_repeated_v1_again_2 is True
    
    def test_summary_deduplication_multiple_sessions(self, state_manager):
        """Test that summary deduplication is per-session."""
        session1 = "user_session_1"
        session2 = "user_session_2"
        
        summary = {
            "total_records": 1000,
            "total_amount": 50000.0,
            "anomalies_detected": 2
        }
        
        # First time in session1
        is_repeated_s1_first = state_manager.is_summary_repeated(session1, summary)
        assert is_repeated_s1_first is False
        
        # First time in session2 (should not be repeated even though same data)
        is_repeated_s2_first = state_manager.is_summary_repeated(session2, summary)
        assert is_repeated_s2_first is False
        
        # Second time in session1 (should be repeated)
        is_repeated_s1_second = state_manager.is_summary_repeated(session1, summary)
        assert is_repeated_s1_second is True
        
        # Second time in session2 (should be repeated)
        is_repeated_s2_second = state_manager.is_summary_repeated(session2, summary)
        assert is_repeated_s2_second is True
    
    def test_summary_hash_edge_cases(self, state_manager):
        """Test edge cases in summary hashing."""
        # Empty summary
        empty_summary = {}
        empty_hash = state_manager._hash_summary_data(empty_summary)
        assert len(empty_hash) == 16
        
        # Summary with null values
        null_summary = {
            "total_records": None,
            "total_amount": None,
            "anomalies_detected": None,
            "date_range": None
        }
        null_hash = state_manager._hash_summary_data(null_summary)
        assert len(null_hash) == 16
        
        # Summary with zero values
        zero_summary = {
            "total_records": 0,
            "total_amount": 0.0,
            "anomalies_detected": 0,
            "date_range": {"start": None, "end": None}
        }
        zero_hash = state_manager._hash_summary_data(zero_summary)
        assert len(zero_hash) == 16
        
        # Null and zero should both be valid hashes but may be different
        # Both should be valid 16-character hashes
        assert null_hash != zero_hash  # They're actually different in our implementation
        assert all(len(h) == 16 for h in [empty_hash, null_hash, zero_hash])
    
    def test_summary_deduplication_performance(self, state_manager):
        """Test that summary deduplication doesn't cause performance issues."""
        session_id = "performance_test"
        
        # Generate many slightly different summaries
        for i in range(100):
            summary = {
                "total_records": 1000 + i,
                "total_amount": 50000.0 + (i * 100),
                "anomalies_detected": i % 10,
                "date_range": {"start": "2024-01-01", "end": f"2024-01-{i+1:02d}"}
            }
            
            # Each should be unique (not repeated)
            is_repeated = state_manager.is_summary_repeated(session_id, summary)
            assert is_repeated is False
        
        # Test that we can still detect repetition of the last summary
        last_summary = {
            "total_records": 1099,
            "total_amount": 59900.0,
            "anomalies_detected": 9,
            "date_range": {"start": "2024-01-01", "end": "2024-01-100"}
        }
        
        is_repeated_last = state_manager.is_summary_repeated(session_id, last_summary)
        assert is_repeated_last is True  # Should match the last one generated
    
    def test_integration_with_conversation_state(self, state_manager):
        """Test integration of summary deduplication with conversation state."""
        session_id = "integration_session"
        user_id = "test_user"
        
        # Start conversation
        state_manager.add_user_turn(
            session_id, user_id, "Give me a summary", "summary_request"
        )
        
        # Generate first summary
        summary_data = {
            "total_records": 500,
            "total_amount": 25000.0,
            "anomalies_detected": 1
        }
        
        is_repeated_first = state_manager.is_summary_repeated(session_id, summary_data)
        assert is_repeated_first is False
        
        # Add agent response with summary
        state_manager.add_agent_turn(
            session_id, "Here's your financial summary", "SummaryAgent", summary_data
        )
        
        # User asks for the same summary again
        state_manager.add_user_turn(
            session_id, user_id, "Show me that summary again", "summary_request"
        )
        
        # Should be detected as repeated
        is_repeated_second = state_manager.is_summary_repeated(session_id, summary_data)
        assert is_repeated_second is True
        
        # Check conversation context includes both turns
        context = state_manager.get_conversation_context(session_id)
        assert context["total_turns"] == 3
        assert context["session_exists"] is True
        
        # Check that we still track session state correctly
        assert len(state_manager._summary_hashes) >= 1
        assert session_id in state_manager._summary_hashes