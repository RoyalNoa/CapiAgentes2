"""Agent protocol definitions for the LangGraph orchestrator."""
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .agent_models import AgentTask, AgentResult, IntentType

# Alias for backward compatibility
Intent = IntentType


@runtime_checkable
class Agent(Protocol):
    """Protocol that all agents must implement."""
    
    @abstractmethod
    async def process(self, task: AgentTask) -> AgentResult:
        """Process a task and return a result."""
        pass
    
    @property
    @abstractmethod
    def supported_intents(self) -> list[IntentType]:
        """Return list of intents this agent can handle."""
        pass
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return the name of this agent."""
        pass


class BaseAgent(ABC):
    """Base class for agents with common functionality."""

    def __init__(self, name: str = None):
        self._name = name or getattr(self, 'AGENT_NAME', 'unnamed_agent')

    @property
    def agent_name(self) -> str:
        return self._name

    @abstractmethod
    async def process(self, task: AgentTask) -> AgentResult:
        """Process a task and return a result."""
        pass

    @property
    @abstractmethod
    def supported_intents(self) -> list[IntentType]:
        """Return list of intents this agent can handle."""
        pass

    def can_handle_intent(self, intent: IntentType) -> bool:
        """Check if this agent can handle the given intent."""
        return intent in self.supported_intents


# New request/result classes compatible with current agent system
@dataclass
class AgentRequest:
    """Request for agent processing - compatible format"""
    intent: str
    query: str = ""
    parameters: Optional[Dict[str, Any]] = None
    user_id: str = "system"
    session_id: str = "default"
    context: Dict[str, Any] = field(default_factory=dict)

    def to_task(self) -> AgentTask:
        """Convert to AgentTask for compatibility"""
        return AgentTask(
            task_id=f"{self.session_id}_{datetime.now().timestamp()}",
            intent=self.intent,
            query=self.query,
            user_id=self.user_id,
            session_id=self.session_id,
            context=self.context,
            metadata=self.parameters or {}
        )


@dataclass
class AgentResponse:
    """Response from agent - simplified format"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'success': self.success,
            'data': self.data,
            'message': self.message,
            'metadata': self.metadata
        }


__all__ = [
    "Agent",
    "BaseAgent",
    "AgentRequest",
    "AgentResponse",
    "Intent",  # Backward compatibility alias
    "IntentType",
]