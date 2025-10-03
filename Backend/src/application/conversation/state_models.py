"""Conversation state models for tracking dialog history and context."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class TurnType(Enum):
    """Type of conversation turn."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


@dataclass
class Turn:
    """Single turn in a conversation."""
    turn_id: str
    turn_type: TurnType
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    intent: Optional[str] = None
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.turn_id.strip():
            raise ValueError("turn_id cannot be empty")
        if not self.content.strip():
            raise ValueError("content cannot be empty")


@dataclass
class ConversationState:
    """Complete state of a conversation session."""
    session_id: str
    user_id: str
    turns: List[Turn] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.session_id.strip():
            raise ValueError("session_id cannot be empty")
        if not self.user_id.strip():
            raise ValueError("user_id cannot be empty")
    
    def add_turn(self, turn: Turn) -> None:
        """Add a turn to the conversation."""
        self.turns.append(turn)
        self.updated_at = datetime.now()
    
    def get_recent_turns(self, limit: int = 5) -> List[Turn]:
        """Get the most recent turns."""
        return self.turns[-limit:] if self.turns else []
    
    def get_user_turns(self) -> List[Turn]:
        """Get all user turns."""
        return [turn for turn in self.turns if turn.turn_type == TurnType.USER]
    
    def get_agent_turns(self) -> List[Turn]:
        """Get all agent turns."""
        return [turn for turn in self.turns if turn.turn_type == TurnType.AGENT]