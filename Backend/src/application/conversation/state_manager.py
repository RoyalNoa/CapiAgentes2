"""Conversation state manager with anti-repetition logic."""
import hashlib
import json
import time
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import asdict

from .state_models import ConversationState, Turn, TurnType

logger = logging.getLogger(__name__)


class ConversationStateManager:
    """
    Manages conversation state and implements anti-repetition logic.
    
    Features:
    - Track conversation history per session
    - Detect repeated queries using content hashing
    - Prevent redundant summary generation
    - Context-aware response deduplication
    """
    
    def __init__(self, max_sessions: int = 100, session_ttl_minutes: int = 60):
        """
        Initialize conversation state manager.
        
        Args:
            max_sessions: Maximum number of sessions to keep in memory
            session_ttl_minutes: Session time-to-live in minutes
        """
        self._sessions: Dict[str, ConversationState] = {}
        self._summary_hashes: Dict[str, str] = {}  # session_id -> last_summary_hash
        self._recent_hashes: Dict[str, Set[str]] = {}  # session_id -> set of recent query hashes
        self._max_sessions = max_sessions
        self._session_ttl = timedelta(minutes=session_ttl_minutes)
    
    def get_or_create_session(self, session_id: str, user_id: str) -> ConversationState:
        """
        Get existing session or create new one.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            
        Returns:
            ConversationState for the session
        """
        if session_id not in self._sessions:
            # Clean up old sessions before creating new one
            self._cleanup_expired_sessions()
            logger.info(f"Creating new conversation session: {session_id} for user: {user_id}")
            
            # Create new session
            self._sessions[session_id] = ConversationState(
                session_id=session_id,
                user_id=user_id
            )
            self._recent_hashes[session_id] = set()
        
        return self._sessions[session_id]
    
    def add_user_turn(self, session_id: str, user_id: str, content: str, 
                     intent: Optional[str] = None, metadata: Optional[Dict] = None) -> Turn:
        """
        Add a user turn to the conversation.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            content: User message content
            intent: Detected intent (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Created Turn object
        """
        session = self.get_or_create_session(session_id, user_id)
        
        turn = Turn(
            turn_id=f"user_{len(session.turns) + 1}_{int(time.time() * 1000)}",
            turn_type=TurnType.USER,
            content=content,
            intent=intent,
            metadata=metadata or {}
        )
        
        session.add_turn(turn)
        return turn
    
    def add_agent_turn(self, session_id: str, content: str, agent_name: str,
                      response_data: Optional[Dict] = None, metadata: Optional[Dict] = None) -> Turn:
        """
        Add an agent response turn to the conversation.
        
        Args:
            session_id: Session identifier
            content: Agent response content
            agent_name: Name of responding agent
            response_data: Response data from agent
            metadata: Additional metadata
            
        Returns:
            Created Turn object
        """
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self._sessions[session_id]
        
        turn_metadata = {"agent_name": agent_name}
        if response_data:
            turn_metadata["response_data"] = response_data
        if metadata:
            turn_metadata.update(metadata)
        
        turn = Turn(
            turn_id=f"agent_{len(session.turns) + 1}_{int(time.time() * 1000)}",
            turn_type=TurnType.AGENT,
            content=content,
            metadata=turn_metadata
        )
        
        session.add_turn(turn)
        return turn
    
    def is_repeated_query(self, session_id: str, query: str, 
                         time_window_minutes: int = 5) -> bool:
        """
        Check if query is a recent repetition.
        
        Args:
            session_id: Session identifier
            query: User query to check
            time_window_minutes: Time window for repetition detection
            
        Returns:
            True if query is a recent repetition
        """
        # Create session if doesn't exist for hash tracking
        if session_id not in self._recent_hashes:
            self._recent_hashes[session_id] = set()
        
        query_hash = self._hash_query(query)
        
        # Check if query hash exists in recent hashes
        is_repeated = query_hash in self._recent_hashes[session_id]
        
        # Add current hash to recent hashes (with cleanup) regardless of repetition
        self._add_recent_hash(session_id, query_hash)
        
        return is_repeated
    
    def is_summary_repeated(self, session_id: str, summary_data: Dict) -> bool:
        """
        Check if summary data is essentially the same as the last generated summary.
        
        Uses SHA256 hash of ordered metrics to detect repetition.
        
        Args:
            session_id: Session identifier
            summary_data: Summary data to check
            
        Returns:
            True if summary is essentially repeated
        """
        summary_hash = self._hash_summary_data(summary_data)
        
        if session_id in self._summary_hashes:
            if self._summary_hashes[session_id] == summary_hash:
                return True
        
        # Update hash for this session
        self._summary_hashes[session_id] = summary_hash
        return False
    
    def get_conversation_context(self, session_id: str, max_turns: int = 5) -> Dict:
        """
        Get conversation context for the session.
        
        Args:
            session_id: Session identifier
            max_turns: Maximum number of recent turns to include
            
        Returns:
            Dictionary with conversation context
        """
        if session_id not in self._sessions:
            return {"recent_turns": [], "session_exists": False}
        
        session = self._sessions[session_id]
        recent_turns = session.get_recent_turns(max_turns)
        
        return {
            "recent_turns": [
                {
                    "type": turn.turn_type.value,
                    "content": turn.content,
                    "intent": turn.intent,
                    "timestamp": turn.timestamp.isoformat()
                }
                for turn in recent_turns
            ],
            "session_exists": True,
            "total_turns": len(session.turns),
            "session_duration_minutes": (datetime.now() - session.created_at).total_seconds() / 60,
            "context": session.context
        }
    
    def update_session_context(self, session_id: str, context_updates: Dict) -> None:
        """
        Update session context with new information.
        
        Args:
            session_id: Session identifier
            context_updates: Context updates to merge
        """
        if session_id in self._sessions:
            self._sessions[session_id].context.update(context_updates)
    
    def get_session_stats(self) -> Dict:
        """
        Get statistics about managed sessions.
        
        Returns:
            Dictionary with session statistics
        """
        active_sessions = len(self._sessions)
        total_turns = sum(len(session.turns) for session in self._sessions.values())
        
        return {
            "active_sessions": active_sessions,
            "total_turns": total_turns,
            "summary_hashes_cached": len(self._summary_hashes),
            "recent_hashes_cached": sum(len(hashes) for hashes in self._recent_hashes.values())
        }
    
    def _hash_query(self, query: str) -> str:
        """
        Generate hash for query content.
        
        Args:
            query: Query string to hash
            
        Returns:
            SHA256 hash of normalized query
        """
        # Normalize query: lowercase, strip whitespace, remove extra spaces
        normalized = " ".join(query.lower().strip().split())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]  # First 16 chars
    
    def _hash_summary_data(self, summary_data: Dict) -> str:
        """
        Generate hash for summary data using ordered metrics.
        
        Args:
            summary_data: Summary data dictionary
            
        Returns:
            SHA256 hash of ordered summary metrics
        """
        # Extract key metrics in consistent order
        date_range = summary_data.get("date_range") or {}
        metrics = {
            "total_records": summary_data.get("total_records", 0),
            "total_amount": summary_data.get("total_amount", 0),
            "anomalies_detected": summary_data.get("anomalies_detected", 0),
            "date_range_start": date_range.get("start") if isinstance(date_range, dict) else None,
            "date_range_end": date_range.get("end") if isinstance(date_range, dict) else None
        }
        
        # Create stable JSON representation
        metrics_json = json.dumps(metrics, sort_keys=True, default=str)
        return hashlib.sha256(metrics_json.encode('utf-8')).hexdigest()[:16]
    
    def _add_recent_hash(self, session_id: str, query_hash: str) -> None:
        """
        Add query hash to recent hashes with cleanup.
        
        Args:
            session_id: Session identifier
            query_hash: Query hash to add
        """
        if session_id not in self._recent_hashes:
            self._recent_hashes[session_id] = set()
        
        self._recent_hashes[session_id].add(query_hash)
        
        # Keep only last 10 hashes per session to prevent unbounded growth
        if len(self._recent_hashes[session_id]) > 10:
            # Remove oldest hash (this is simple; in production might want FIFO queue)
            self._recent_hashes[session_id].pop()
    
    def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions to prevent memory leaks."""
        current_time = datetime.now()
        expired_sessions = []
        
        # Always check for expired sessions regardless of count
        for session_id, session in self._sessions.items():
            if current_time - session.updated_at > self._session_ttl:
                expired_sessions.append(session_id)
        
        # Remove expired sessions
        for session_id in expired_sessions:
            del self._sessions[session_id]
            if session_id in self._summary_hashes:
                del self._summary_hashes[session_id]
            if session_id in self._recent_hashes:
                del self._recent_hashes[session_id]
        
        # If still too many sessions after cleanup, remove oldest ones
        while len(self._sessions) >= self._max_sessions:
            oldest_session_id = min(
                self._sessions.keys(),
                key=lambda sid: self._sessions[sid].updated_at
            )
            del self._sessions[oldest_session_id]
            if oldest_session_id in self._summary_hashes:
                del self._summary_hashes[oldest_session_id]
            if oldest_session_id in self._recent_hashes:
                del self._recent_hashes[oldest_session_id]