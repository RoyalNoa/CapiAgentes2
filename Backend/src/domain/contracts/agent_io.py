"""Agent IO definitions for backward compatibility with orchestrator."""
from src.domain.agents.agent_models import AgentTask, AgentResult, TaskStatus

# Backward compatibility exports  
__all__ = ["AgentTask", "AgentResult", "TaskStatus"]