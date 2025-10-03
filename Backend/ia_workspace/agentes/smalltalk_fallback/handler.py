"""SmallTalk and Fallback agent for handling casual conversation and unknown intents."""
import time
from typing import List, Dict, Any
import random

from ...domain.agents.agent_protocol import BaseAgent
from ...domain.contracts.intent import Intent
from ...domain.contracts.agent_io import AgentTask, AgentResult, TaskStatus
from ...core.logging.tracing import get_traced_logger

logger = get_traced_logger(__name__)


class SmallTalkFallbackAgent(BaseAgent):
    """
    Agent responsible for handling small talk, greetings, and fallback responses.
    
    Handles:
    - GREETING: Welcome messages and initial greetings
    - SMALL_TALK: Casual conversation and off-topic queries
    - UNKNOWN: Queries that couldn't be classified properly
    """
    
    def __init__(self):
        """Initialize the SmallTalk and Fallback agent."""
        super().__init__(name="SmallTalkFallbackAgent")
        
        # Greeting responses in Spanish and English
        self.greeting_responses = [
            "¡Hola! Soy tu asistente financiero de CapiAgentes. ¿En qué puedo ayudarte hoy?",
            "¡Buenos días! Estoy aquí para ayudarte con análisis financieros. ¿Qué necesitas?",
            "¡Hola! Puedo ayudarte con resúmenes, análisis de sucursales y detección de anomalías. ¿Por dónde empezamos?",
            "Hello! I'm your financial assistant from CapiAgentes. How can I help you today?",
            "Hi there! I'm here to help with financial analysis. What do you need?",
        ]
        
        # Small talk responses
        self.smalltalk_responses = [
            "Me gusta conversar, pero me especializo en análisis financiero. ¿Te puedo ayudar con algún resumen o análisis de datos?",
            "Eso suena interesante, aunque mi fuerte son los números y análisis financieros. ¿Necesitas ayuda con algún reporte?",
            "Entiendo tu consulta, pero soy mejor analizando datos financieros. ¿Te gustaría ver un resumen de tus datos?",
            "That's interesting! Though I specialize in financial analysis. Can I help you with any financial data?",
            "I appreciate the conversation, but I'm best at analyzing financial information. Need any reports?"
        ]
        
        # Fallback responses for unknown intents
        self.fallback_responses = [
            "No estoy seguro de cómo ayudarte con eso. Puedo generar resúmenes financieros, analizar sucursales o detectar anomalías. ¿Qué prefieres?",
            "Disculpa, no entendí completamente tu consulta. ¿Podrías reformularla? Puedo ayudarte con análisis financieros.",
            "No logré entender exactamente qué necesitas. Mis especialidades son: resúmenes financieros, análisis por sucursal y detección de anomalías.",
            "I'm not sure how to help with that. I can generate financial summaries, analyze branches, or detect anomalies. What would you prefer?",
            "Sorry, I didn't quite understand your query. Could you rephrase it? I can help with financial analysis."
        ]
        
        # Suggested actions for each intent type
        self.suggested_actions = {
            Intent.GREETING: [
                {"action_type": "summary", "label": "Ver Resumen", "description": "Generar resumen financiero"},
                {"action_type": "branches", "label": "Analizar Sucursales", "description": "Análisis por sucursal"},
                {"action_type": "anomalies", "label": "Detectar Anomalías", "description": "Buscar irregularidades"}
            ],
            Intent.SMALL_TALK: [
                {"action_type": "summary", "label": "Resumen Financiero", "description": "Cambiar a análisis financiero"},
                {"action_type": "help", "label": "Ver Ayuda", "description": "Conocer mis capacidades"}
            ],
            Intent.UNKNOWN: [
                {"action_type": "help", "label": "Ayuda", "description": "Ver qué puedo hacer"},
                {"action_type": "examples", "label": "Ejemplos", "description": "Ver consultas de ejemplo"},
                {"action_type": "rephrase", "label": "Reformular", "description": "Intentar con otras palabras"}
            ]
        }
    
    @property
    def supported_intents(self) -> List[Intent]:
        """Return intents this agent can handle."""
        return [Intent.GREETING, Intent.SMALL_TALK, Intent.UNKNOWN]
    
    async def process(self, task: AgentTask) -> AgentResult:
        """
        Process a small talk, greeting, or unknown intent task.
        
        Args:
            task: Task to process
            
        Returns:
            AgentResult with appropriate response
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing {task.intent} task: {task.task_id}")

            # Validate intent (already an Intent enum)
            intent = task.intent
            if intent not in self.supported_intents:
                return AgentResult(
                    task_id=task.task_id,
                    agent_name=self.agent_name,
                    status=TaskStatus.FAILED,
                    message=f"Invalid intent '{task.intent}' for SmallTalkFallbackAgent",
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            # Generate appropriate response based on intent
            response_data = self._generate_response(intent, task.query, task.context)
            
            processing_time = (time.time() - start_time) * 1000
            
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.agent_name,
                status=TaskStatus.COMPLETED,
                data=response_data,
                message=response_data["response_message"],
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error processing smalltalk/fallback task {task.task_id}: {str(e)}")
            processing_time = (time.time() - start_time) * 1000
            
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.agent_name,
                status=TaskStatus.FAILED,
                message=f"Error procesando consulta: {str(e)}",
                processing_time_ms=processing_time
            )
    
    def _generate_response(self, intent: Intent, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate appropriate response based on intent type.
        
        Args:
            intent: Classified intent
            query: Original user query
            context: Task context
            
        Returns:
            Dictionary with response data
        """
        if intent == Intent.GREETING:
            return self._handle_greeting(query, context)
        elif intent == Intent.SMALL_TALK:
            return self._handle_small_talk(query, context)
        else:  # UNKNOWN
            return self._handle_unknown(query, context)
    
    def _handle_greeting(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle greeting intent."""
        response_message = random.choice(self.greeting_responses)
        
        return {
            "response_type": "greeting",
            "response_message": response_message,
            "intent_handled": Intent.GREETING.value,
            "conversation_starter": True,
            "suggested_actions": self.suggested_actions[Intent.GREETING],
            "capabilities": [
                "Generar resúmenes financieros completos",
                "Analizar rendimiento por sucursal", 
                "Detectar anomalías en transacciones",
                "Responder consultas sobre datos financieros"
            ],
            "examples": [
                "Dame un resumen financiero",
                "Analizar datos por sucursal",
                "Detectar anomalías en los datos"
            ]
        }
    
    def _handle_small_talk(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle small talk intent."""
        response_message = random.choice(self.smalltalk_responses)
        
        # Try to detect language preference
        is_spanish = self._is_spanish_query(query)
        
        return {
            "response_type": "small_talk",
            "response_message": response_message,
            "intent_handled": Intent.SMALL_TALK.value,
            "redirect_to_business": True,
            "language_detected": "spanish" if is_spanish else "english",
            "suggested_actions": self.suggested_actions[Intent.SMALL_TALK],
            "original_query": query,
            "business_alternatives": [
                "¿Te gustaría ver un resumen de tus datos financieros?",
                "¿Necesitas análisis de alguna sucursal específica?",
                "¿Quieres que detecte anomalías en las transacciones?"
            ]
        }
    
    def _handle_unknown(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown intent."""
        response_message = random.choice(self.fallback_responses)
        
        # Analyze query for potential keywords that might help
        keywords_found = self._extract_potential_keywords(query)
        
        return {
            "response_type": "fallback", 
            "response_message": response_message,
            "intent_handled": Intent.UNKNOWN.value,
            "needs_clarification": True,
            "original_query": query,
            "keywords_detected": keywords_found,
            "suggested_actions": self.suggested_actions[Intent.UNKNOWN],
            "help_message": "Intenta con consultas como: 'resumen financiero', 'datos por sucursal', 'detectar anomalías'",
            "available_commands": [
                "resumen / summary - Generar resumen financiero",
                "sucursal / branch - Análisis por sucursal",
                "anomalías / anomalies - Detectar irregularidades"
            ]
        }
    
    def _is_spanish_query(self, query: str) -> bool:
        """
        Detect if query is likely in Spanish.
        
        Args:
            query: Query text to analyze
            
        Returns:
            True if query seems to be in Spanish
        """
        spanish_indicators = [
            'que', 'como', 'donde', 'cuando', 'por', 'para', 'con', 'sin', 'sobre',
            'hola', 'gracias', 'por favor', 'disculpa', 'perdón', 'ayuda',
            'necesito', 'quiero', 'puedes', 'puedo', 'está', 'estoy', 'es', 'son'
        ]
        
        query_lower = query.lower()
        spanish_count = sum(1 for indicator in spanish_indicators if indicator in query_lower)
        
        # Simple heuristic: if query has Spanish indicators, likely Spanish
        return spanish_count > 0
    
    def _extract_potential_keywords(self, query: str) -> List[str]:
        """
        Extract potential keywords from query that might indicate intent.
        
        Args:
            query: Query text to analyze
            
        Returns:
            List of potential keywords found
        """
        # Keywords that might indicate specific intents
        financial_keywords = {
            'summary': ['resumen', 'summary', 'total', 'general', 'overview'],
            'branch': ['sucursal', 'branch', 'office', 'oficina', 'location'],
            'anomaly': ['anomalia', 'anomaly', 'anomalies', 'error', 'problema', 'irregular', 'extraño']
        }
        
        query_lower = query.lower()
        found_keywords = []
        
        for category, keywords in financial_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    found_keywords.append(f"{keyword} ({category})")
        
        return found_keywords