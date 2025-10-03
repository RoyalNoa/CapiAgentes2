"""
Professional Error Recovery System for LangGraph Orchestrator

Implements enterprise-grade error handling, retry logic, and graceful degradation
for multi-agent orchestration systems.
"""
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    ESCALATE = "escalate"
    ABORT = "abort"


@dataclass
class ErrorContext:
    """Rich error context for intelligent recovery decisions"""
    operation: str
    agent: str
    error_type: str
    error_message: str
    parameters: Dict[str, Any]
    severity: ErrorSeverity
    retry_count: int
    user_query: str
    session_id: str


@dataclass
class RecoveryAction:
    """Professional recovery action with detailed metadata"""
    strategy: RecoveryStrategy
    alternative_operation: Optional[str] = None
    modified_parameters: Optional[Dict[str, Any]] = None
    user_message: Optional[str] = None
    reasoning: Optional[str] = None


class ProfessionalErrorRecovery:
    """
    Enterprise-grade error recovery system for orchestrator optimization.

    Features:
    - Intelligent error classification
    - Context-aware recovery strategies
    - Progressive degradation
    - User-friendly error messages
    - Performance impact minimization
    """

    def __init__(self):
        self.recovery_rules = self._initialize_recovery_rules()
        self.error_patterns = self._initialize_error_patterns()

    def analyze_error(self, error: Exception, context: ErrorContext) -> RecoveryAction:
        """
        Professional error analysis with intelligent recovery decisions.

        Args:
            error: The exception that occurred
            context: Rich context about the operation and environment

        Returns:
            RecoveryAction with optimal strategy and user communication
        """
        error_classification = self._classify_error(error, context)
        recovery_strategy = self._determine_recovery_strategy(error_classification, context)

        return self._build_recovery_action(error_classification, recovery_strategy, context)

    def _classify_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Classify error with professional categorization"""
        error_type = type(error).__name__
        error_message = str(error).lower()

        # File operation specific classification
        if context.operation.startswith(("leer_", "read_")):
            if "not found" in error_message or "no encontrado" in error_message:
                return {
                    "category": "file_not_found",
                    "severity": ErrorSeverity.MEDIUM,
                    "user_friendly": True,
                    "recoverable": True
                }
            elif "permission" in error_message or "access" in error_message:
                return {
                    "category": "access_denied",
                    "severity": ErrorSeverity.HIGH,
                    "user_friendly": True,
                    "recoverable": False
                }
            elif "format" in error_message or "corrupt" in error_message:
                return {
                    "category": "file_format_error",
                    "severity": ErrorSeverity.MEDIUM,
                    "user_friendly": True,
                    "recoverable": True
                }

        # General classification fallback
        return {
            "category": "general_error",
            "severity": ErrorSeverity.MEDIUM,
            "user_friendly": False,
            "recoverable": True
        }

    def _determine_recovery_strategy(self, classification: Dict[str, Any], context: ErrorContext) -> RecoveryStrategy:
        """Determine optimal recovery strategy based on context"""
        category = classification["category"]
        severity = classification["severity"]

        # File operations recovery logic
        if category == "file_not_found":
            if context.retry_count == 0:
                return RecoveryStrategy.FALLBACK  # Try smart file search
            else:
                return RecoveryStrategy.ESCALATE  # Inform user with alternatives

        elif category == "access_denied":
            return RecoveryStrategy.ESCALATE  # Cannot recover, inform user

        elif category == "file_format_error":
            return RecoveryStrategy.FALLBACK  # Try alternative format detection

        # Default strategy based on severity
        if severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.ABORT
        elif severity == ErrorSeverity.HIGH:
            return RecoveryStrategy.ESCALATE
        else:
            return RecoveryStrategy.RETRY

    def _build_recovery_action(self, classification: Dict[str, Any], strategy: RecoveryStrategy, context: ErrorContext) -> RecoveryAction:
        """Build professional recovery action with user communication"""
        category = classification["category"]

        if category == "file_not_found" and strategy == RecoveryStrategy.FALLBACK:
            return RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK,
                alternative_operation="buscar_archivo_inteligente",
                modified_parameters={
                    **context.parameters,
                    "search_mode": "fuzzy",
                    "original_filename": context.parameters.get("filename", ""),
                    "search_locations": ["desktop", "documents", "downloads"]
                },
                user_message=f"Buscando el archivo '{context.parameters.get('filename', '')}' en ubicaciones alternativas...",
                reasoning="File not found with exact name, attempting intelligent search"
            )

        elif category == "file_not_found" and strategy == RecoveryStrategy.ESCALATE:
            return RecoveryAction(
                strategy=RecoveryStrategy.ESCALATE,
                alternative_operation="listar_archivos_similares",
                modified_parameters={
                    "pattern": f"*{context.parameters.get('filename', '')}*",
                    "suggestion_mode": True
                },
                user_message=f"No pude encontrar el archivo '{context.parameters.get('filename', '')}'. Te muestro archivos similares que encontré:",
                reasoning="Exact file not found after search, providing alternatives"
            )

        # Default escalation with informative message
        return RecoveryAction(
            strategy=RecoveryStrategy.ESCALATE,
            user_message=f"Ocurrió un problema al {context.operation}. Error: {context.error_message}",
            reasoning="Generic error escalation with user notification"
        )

    def _initialize_recovery_rules(self) -> Dict[str, Any]:
        """Initialize professional recovery rules"""
        return {
            "max_retries": 2,
            "retry_delay": 0.5,
            "fallback_timeout": 10.0,
            "user_notification_threshold": ErrorSeverity.MEDIUM
        }

    def _initialize_error_patterns(self) -> List[Dict[str, Any]]:
        """Initialize error pattern recognition"""
        return [
            {
                "pattern": r"file.*not.*found|archivo.*no.*encontrado",
                "category": "file_not_found",
                "severity": ErrorSeverity.MEDIUM
            },
            {
                "pattern": r"permission.*denied|access.*denied",
                "category": "access_denied",
                "severity": ErrorSeverity.HIGH
            },
            {
                "pattern": r"format.*error|corrupt.*file",
                "category": "file_format_error",
                "severity": ErrorSeverity.MEDIUM
            }
        ]


class EnhancedOperationExecutor:
    """
    Professional operation executor with intelligent error recovery.

    Replaces simplistic try/catch with sophisticated error handling.
    """

    def __init__(self):
        self.error_recovery = ProfessionalErrorRecovery()

    async def execute_with_recovery(self, operation: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute operation with professional error recovery.

        Returns structured result with success/failure information and user communication.
        """
        error_context = ErrorContext(
            operation=operation,
            agent=context.get("agent", "unknown"),
            error_type="",
            error_message="",
            parameters=parameters,
            severity=ErrorSeverity.LOW,
            retry_count=0,
            user_query=context.get("user_query", ""),
            session_id=context.get("session_id", "")
        )

        # Primary execution attempt
        try:
            result = await self._execute_operation(operation, parameters, context)
            return {
                "success": True,
                "result": result,
                "strategy_used": "direct_execution",
                "user_message": None
            }
        except Exception as error:
            logger.warning(f"Primary operation failed: {operation} - {error}")

            # Professional error recovery
            error_context.error_type = type(error).__name__
            error_context.error_message = str(error)

            recovery_action = self.error_recovery.analyze_error(error, error_context)

            return await self._execute_recovery(recovery_action, error_context, context)

    async def _execute_recovery(self, action: RecoveryAction, error_context: ErrorContext, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the determined recovery action"""
        if action.strategy == RecoveryStrategy.FALLBACK and action.alternative_operation:
            try:
                logger.info(f"Attempting fallback: {action.alternative_operation}")
                result = await self._execute_operation(
                    action.alternative_operation,
                    action.modified_parameters or error_context.parameters,
                    context
                )
                return {
                    "success": True,
                    "result": result,
                    "strategy_used": "fallback_recovery",
                    "user_message": action.user_message,
                    "recovery_reasoning": action.reasoning
                }
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                # Escalate after fallback failure
                action.strategy = RecoveryStrategy.ESCALATE

        if action.strategy == RecoveryStrategy.ESCALATE:
            return {
                "success": False,
                "error": error_context.error_message,
                "strategy_used": "escalation",
                "user_message": action.user_message or f"No pude completar la operación: {error_context.operation}",
                "recovery_reasoning": action.reasoning,
                "suggested_action": action.alternative_operation
            }

        # Default failure case
        return {
            "success": False,
            "error": error_context.error_message,
            "strategy_used": "abort",
            "user_message": "Ocurrió un error inesperado. Inténtalo de nuevo.",
            "recovery_reasoning": "Unrecoverable error"
        }

    async def _execute_operation(self, operation: str, parameters: Dict[str, Any], context: Dict[str, Any]):
        """Execute operation through agent - to be overridden by specific node implementations"""
        # This will be overridden by the actual node implementation
        agent = context.get("agent")
        if not agent:
            raise RuntimeError("No agent available for operation execution")

        # Create agent request
        from src.domain.agents.agent_protocol import AgentRequest
        request = AgentRequest(
            intent=operation,
            query=context.get("user_query", ""),
            parameters=parameters,
            user_id=context.get("user_id", "unknown"),
            session_id=context.get("session_id", "unknown"),
            context={"trace_id": context.get("trace_id", "unknown")}
        )

        # Execute through agent
        result = await agent.execute(request)
        return result