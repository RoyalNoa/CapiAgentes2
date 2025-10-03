"""Unified agent models and contracts for CapiAgentes.

This module consolidates all agent-related data structures, eliminating
duplications between contracts.py and models.py.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(Enum):
    """Status of agent task processing."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorSeverity(Enum):
    """Severity levels for agent errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IntentType(str, Enum):
    """Intent classification types."""
    SUMMARY = "summary"
    SUMMARY_REQUEST = "summary_request"  # Alias para compatibilidad con intent classifier
    ANOMALY = "anomaly"
    ANOMALY_QUERY = "anomaly_query"  # Alias para intent classifier
    BRANCH = "branch"
    BRANCH_QUERY = "branch_query"  # Alias para intent classifier
    FILE_OPERATION = "file_operation"  # Nuevo intent para operaciones de archivo
    DB_OPERATION = "db_operation"  # Operaciones sobre bases de datos
    QUERY = "query"
    SMALL_TALK = "small_talk"
    GREETING = "greeting"
    NEWS_MONITORING = "news_monitoring"
    FALLBACK = "fallback"
    UNKNOWN = "unknown"


class ResponseType(str, Enum):
    """Types of responses the system can generate."""
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"
    FALLBACK = "fallback"
    SYSTEM = "system"
    NOTICE = "notice"
    SMALL_TALK = "small_talk"


@dataclass
class AgentTask:
    """Task to be processed by an agent."""
    task_id: str
    intent: str
    query: str
    user_id: str
    session_id: str
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.task_id.strip():
            raise ValueError("task_id cannot be empty")
        if not self.query.strip():
            raise ValueError("query cannot be empty")
        if not self.user_id.strip():
            raise ValueError("user_id cannot be empty")


@dataclass
class AgentResult:
    """Result from agent task processing."""
    task_id: str
    agent_name: str
    status: TaskStatus
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error: Optional['AgentError'] = None
    processing_time: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.task_id.strip():
            raise ValueError("task_id cannot be empty")
        if not self.agent_name.strip():
            raise ValueError("agent_name cannot be empty")
            
    def is_success(self) -> bool:
        """Check if the result indicates success."""
        return self.status == TaskStatus.COMPLETED and self.error is None


@dataclass 
class AgentError:
    """Error information from agent processing."""
    error_code: str
    error_message: str
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.error_code.strip():
            raise ValueError("error_code cannot be empty")
        if not self.error_message.strip():
            raise ValueError("error_message cannot be empty")


@dataclass
class SuggestedAction:
    """Suggested action for user interaction."""
    action_type: str
    label: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.action_type.strip():
            raise ValueError("action_type cannot be empty")
        if not self.label.strip():
            raise ValueError("label cannot be empty")


@dataclass
class IntentDetection:
    """Result of intent classification."""
    intent: IntentType
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass
class ResponseEnvelope:
    """Response envelope for unified agent communication."""
    trace_id: str
    response_type: ResponseType
    intent: IntentType
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    suggested_actions: List[SuggestedAction] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_error(self, msg: str) -> None:
        """Add an error message and update response type."""
        self.errors.append(msg)
        if self.response_type == ResponseType.SUCCESS:
            self.response_type = ResponseType.ERROR

    def add_suggested_action(self, action: SuggestedAction) -> None:
        """Add a suggested action to the response."""
        self.suggested_actions.append(action)
    
    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return self.response_type == ResponseType.SUCCESS


__all__ = [
    "TaskStatus",
    "ErrorSeverity", 
    "IntentType",
    "ResponseType",
    "AgentTask",
    "AgentResult",
    "AgentError",
    "SuggestedAction",
    "IntentDetection",
    "ResponseEnvelope",
]

