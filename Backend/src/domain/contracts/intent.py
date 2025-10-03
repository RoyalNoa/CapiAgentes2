"""Intent definitions for backward compatibility with orchestrator."""
from src.domain.agents.agent_protocol import Intent, IntentType

# Backward compatibility exports
__all__ = ["Intent", "IntentType"]