"""
Core Semantic NLP Module

Módulo central para procesamiento semántico de lenguaje natural.
Reemplaza todos los sistemas de patterns hardcodeados del proyecto.
"""

from .intent_service import SemanticIntentService, IntentResult
from .context_manager import GlobalConversationContext, ConversationState, get_global_context_manager
from .entity_extractor import EntityExtractor
from .semantic_similarity import SemanticSimilarity

__all__ = [
    'SemanticIntentService',
    'IntentResult',
    'GlobalConversationContext',
    'ConversationState',
    'get_global_context_manager',
    'EntityExtractor',
    'SemanticSimilarity'
]