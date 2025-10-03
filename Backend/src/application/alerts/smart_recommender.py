"""
Smart Recommender - Sistema de recomendaciones inteligentes
Genera recomendaciones basadas en análisis financiero y LLM
"""
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Tipos de recomendaciones"""
    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    OPERATIONAL = "operational"
    RISK_MITIGATION = "risk_mitigation"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    COMPLIANCE = "compliance"
    PROCESS_IMPROVEMENT = "process_improvement"


class RecommendationPriority(Enum):
    """Prioridades de recomendaciones"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RecommendationStatus(Enum):
    """Estados de recomendaciones"""
    ACTIVE = "active"
    IMPLEMENTED = "implemented"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


@dataclass
class ActionItem:
    """Item de acción específico dentro de una recomendación"""
    description: str
    estimated_effort: str  # "low", "medium", "high"
    estimated_timeframe: str  # "immediate", "short_term", "medium_term", "long_term"
    responsible_party: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    completed: bool = False


@dataclass
class Recommendation:
    """Recomendación generada por el sistema"""
    id: str
    title: str
    description: str
    type: RecommendationType
    priority: RecommendationPriority
    status: RecommendationStatus
    confidence_score: float
    created_at: datetime
    context_data: Dict[str, Any]
    rationale: str
    action_items: List[ActionItem] = field(default_factory=list)
    expected_impact: Dict[str, Any] = field(default_factory=dict)
    success_metrics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    implemented_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte recomendación a diccionario"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat(),
            "context_data": self.context_data,
            "rationale": self.rationale,
            "action_items": [
                {
                    "description": item.description,
                    "estimated_effort": item.estimated_effort,
                    "estimated_timeframe": item.estimated_timeframe,
                    "responsible_party": item.responsible_party,
                    "dependencies": item.dependencies,
                    "completed": item.completed
                } for item in self.action_items
            ],
            "expected_impact": self.expected_impact,
            "success_metrics": self.success_metrics,
            "metadata": self.metadata,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "implemented_at": self.implemented_at.isoformat() if self.implemented_at else None
        }


class SmartRecommender:
    """
    Sistema de recomendaciones inteligentes para análisis financiero
    Combina reglas de negocio con LLM reasoning para generar recomendaciones
    """
    
    def __init__(self, llm_reasoner=None):
        """
        Inicializa el sistema de recomendaciones
        
        Args:
            llm_reasoner: Instancia de LLMReasoner para recomendaciones inteligentes
        """
        self.llm_reasoner = llm_reasoner
        self.active_recommendations: List[Recommendation] = []
        self.recommendation_history: List[Recommendation] = []
        self.metrics = {
            "total_recommendations": 0,
            "recommendations_by_type": {},
            "recommendations_by_priority": {},
            "implementation_rate": 0.0,
            "avg_confidence_score": 0.0,
            "avg_generation_time": 0.0
        }
        
        # Templates para diferentes tipos de recomendaciones
        self._init_recommendation_templates()
        
        logger.info("SmartRecommender inicializado")
    
    def _init_recommendation_templates(self):
        """Inicializa templates para recomendaciones"""
        self.templates = {
            "high_risk": {
                "type": RecommendationType.RISK_MITIGATION,
                "priority": RecommendationPriority.URGENT,
                "title_template": "Mitigación de Riesgo Elevado: {risk_type}",
                "actions": [
                    "Evaluar exposición actual al riesgo",
                    "Implementar controles adicionales",
                    "Diversificar posiciones de alto riesgo",
                    "Establecer límites más estrictos"
                ]
            },
            "performance_decline": {
                "type": RecommendationType.PERFORMANCE_OPTIMIZATION,
                "priority": RecommendationPriority.HIGH,
                "title_template": "Optimización de Performance: {decline_area}",
                "actions": [
                    "Analizar factores de declive",
                    "Revisar estrategia de allocation",
                    "Optimizar procesos críticos",
                    "Implementar monitoreo continuo"
                ]
            },
            "volume_anomaly": {
                "type": RecommendationType.OPERATIONAL,
                "priority": RecommendationPriority.MEDIUM,
                "title_template": "Gestión de Anomalía de Volumen",
                "actions": [
                    "Investigar causa de la anomalía",
                    "Verificar capacidad operacional",
                    "Ajustar controles de riesgo",
                    "Comunicar a stakeholders relevantes"
                ]
            },
            "liquidity_optimization": {
                "type": RecommendationType.STRATEGIC,
                "priority": RecommendationPriority.HIGH,
                "title_template": "Optimización de Liquidez",
                "actions": [
                    "Revisar flujo de caja proyectado",
                    "Optimizar timing de cobros y pagos",
                    "Evaluar líneas de crédito disponibles",
                    "Implementar mejores prácticas de gestión de liquidez"
                ]
            }
        }
    
    async def generate_recommendations(self, 
                                     analysis_data: Dict[str, Any],
                                     alert_context: Optional[List] = None,
                                     trace_id: Optional[str] = None) -> List[Recommendation]:
        """
        Genera recomendaciones basadas en datos de análisis
        
        Args:
            analysis_data: Datos del análisis financiero
            alert_context: Contexto de alertas activas
            trace_id: ID de trazabilidad
            
        Returns:
            Lista de recomendaciones generadas
        """
        if not trace_id:
            trace_id = str(uuid4())
        
        start_time = time.time()
        recommendations = []
        
        logger.info(f"[{trace_id}] Generando recomendaciones inteligentes")
        
        try:
            # Generar recomendaciones basadas en reglas
            rule_based = self._generate_rule_based_recommendations(analysis_data, alert_context, trace_id)
            recommendations.extend(rule_based)
            
            # Generar recomendaciones usando LLM si está disponible
            if self.llm_reasoner:
                llm_based = await self._generate_llm_recommendations(analysis_data, alert_context, trace_id)
                recommendations.extend(llm_based)
            
            # Post-procesar y filtrar recomendaciones
            recommendations = self._post_process_recommendations(recommendations, trace_id)
            
            # Actualizar métricas
            generation_time = time.time() - start_time
            self._update_metrics(recommendations, generation_time)
            
            # Almacenar recomendaciones
            for rec in recommendations:
                self.active_recommendations.append(rec)
                self.recommendation_history.append(rec)
            
            logger.info(f"[{trace_id}] Generadas {len(recommendations)} recomendaciones en {generation_time:.2f}s")
            
        except Exception as e:
            logger.error(f"[{trace_id}] Error generando recomendaciones: {e}")
            
        return recommendations
    
    def _generate_rule_based_recommendations(self, 
                                           data: Dict[str, Any], 
                                           alerts: Optional[List],
                                           trace_id: str) -> List[Recommendation]:
        """Genera recomendaciones basadas en reglas de negocio"""
        recommendations = []
        
        # Extraer métricas clave
        metrics = data.get("metrics", {})
        risk_score = metrics.get("risk_score", 0.0)
        performance_score = metrics.get("performance_score", 0.0)
        liquidity_ratio = metrics.get("liquidity_ratio", 1.0)
        total_volume = metrics.get("total_volume", 0.0)
        variance = metrics.get("variance", 0.0)
        
        # Recomendación por alto riesgo
        if risk_score > 0.7:
            rec = self._create_recommendation_from_template(
                template_key="high_risk",
                data=data,
                specific_data={"risk_score": risk_score, "risk_type": "Score elevado"},
                trace_id=trace_id,
                confidence=0.9
            )
            recommendations.append(rec)
        
        # Recomendación por declive de performance
        if performance_score < 0.3:
            rec = self._create_recommendation_from_template(
                template_key="performance_decline",
                data=data,
                specific_data={"performance_score": performance_score, "decline_area": "Score general"},
                trace_id=trace_id,
                confidence=0.8
            )
            recommendations.append(rec)
        
        # Recomendación por liquidez baja
        if liquidity_ratio < 0.3:
            rec = self._create_recommendation_from_template(
                template_key="liquidity_optimization",
                data=data,
                specific_data={"liquidity_ratio": liquidity_ratio},
                trace_id=trace_id,
                confidence=0.85
            )
            recommendations.append(rec)
        
        # Recomendación por alta varianza
        if variance > 0.2:
            rec = self._create_recommendation_from_template(
                template_key="volume_anomaly",
                data=data,
                specific_data={"variance": variance},
                trace_id=trace_id,
                confidence=0.7
            )
            recommendations.append(rec)
        
        # Recomendaciones basadas en alertas activas
        if alerts:
            for alert in alerts:
                if hasattr(alert, 'category') and hasattr(alert, 'severity'):
                    rec = self._create_alert_based_recommendation(alert, data, trace_id)
                    if rec:
                        recommendations.append(rec)
        
        return recommendations
    
    async def _generate_llm_recommendations(self, 
                                          data: Dict[str, Any], 
                                          alerts: Optional[List],
                                          trace_id: str) -> List[Recommendation]:
        """Genera recomendaciones usando LLM reasoning"""
        recommendations = []
        
        try:
            # Construir contexto para LLM
            context_data = {
                "financial_data": data,
                "active_alerts": [alert.to_dict() if hasattr(alert, 'to_dict') else str(alert) for alert in (alerts or [])],
                "analysis_focus": "strategic_recommendations",
                "domain": "financial_risk_management"
            }
            
            # Construir prompt para recomendaciones
            prompt = self._build_recommendation_prompt(data, alerts)
            
            # Llamar al LLM
            llm_result = await self.llm_reasoner.reason(
                query=prompt,
                context_data=context_data,
                trace_id=trace_id
            )
            
            if llm_result.success:
                # Parsear respuesta y crear recomendaciones
                llm_recommendations = self._parse_llm_recommendations(llm_result, data, trace_id)
                recommendations.extend(llm_recommendations)
            else:
                logger.warning(f"[{trace_id}] LLM reasoning falló: {llm_result.error}")
                
        except Exception as e:
            logger.error(f"[{trace_id}] Error en LLM recommendations: {e}")
        
        return recommendations
    
    def _build_recommendation_prompt(self, data: Dict[str, Any], alerts: Optional[List]) -> str:
        """Construye prompt para recomendaciones LLM"""
        metrics = data.get("metrics", {})
        
        prompt = f"""
        Analiza la siguiente situación financiera y genera recomendaciones estratégicas específicas:

        MÉTRICAS ACTUALES:
        - Risk Score: {metrics.get('risk_score', 'N/A')}
        - Performance Score: {metrics.get('performance_score', 'N/A')}
        - Liquidity Ratio: {metrics.get('liquidity_ratio', 'N/A')}
        - Total Volume: {metrics.get('total_volume', 'N/A')}
        - Varianza: {metrics.get('variance', 'N/A')}
        - Total Records: {metrics.get('total_records', 'N/A')}

        CONTEXTO ADICIONAL:
        {data.get('analysis', 'No hay análisis adicional disponible')}

        ALERTAS ACTIVAS: {len(alerts) if alerts else 0}

        INSTRUCCIONES:
        1. Genera 2-4 recomendaciones estratégicas específicas
        2. Para cada recomendación incluye:
           - Título claro y accionable
           - Descripción detallada (2-3 párrafos)
           - Justificación basada en las métricas
           - Prioridad (LOW, MEDIUM, HIGH, URGENT)
           - Tipo (STRATEGIC, TACTICAL, OPERATIONAL, RISK_MITIGATION, PERFORMANCE_OPTIMIZATION)
           - 3-5 pasos de implementación específicos
           - Métricas de éxito esperadas

        FORMATO DE RESPUESTA:
        Estructura cada recomendación claramente separada con delimitadores.
        
        Genera las recomendaciones:
        """
        
        return prompt
    
    def _parse_llm_recommendations(self, llm_result, data: Dict[str, Any], trace_id: str) -> List[Recommendation]:
        """Parsea respuesta LLM y crea objetos Recommendation"""
        recommendations = []
        
        try:
            response_text = llm_result.response
            
            # Implementación simplificada de parsing
            # En una implementación completa, usaríamos parsing más sofisticado
            
            # Crear una recomendación base desde la respuesta LLM
            rec_id = f"llm_rec_{int(time.time())}"
            
            recommendation = Recommendation(
                id=rec_id,
                title="Recomendación Estratégica LLM",
                description=response_text[:500] + "..." if len(response_text) > 500 else response_text,
                type=RecommendationType.STRATEGIC,
                priority=RecommendationPriority.HIGH,
                status=RecommendationStatus.ACTIVE,
                confidence_score=llm_result.confidence_score,
                created_at=datetime.now(timezone.utc),
                context_data=data.copy(),
                rationale=f"Generado por LLM con confidence {llm_result.confidence_score:.2f}",
                action_items=[
                    ActionItem(
                        description="Revisar recomendación completa del LLM",
                        estimated_effort="medium",
                        estimated_timeframe="short_term"
                    )
                ],
                expected_impact={
                    "risk_reduction": "potential",
                    "performance_improvement": "potential"
                },
                success_metrics=[
                    "Mejora en métricas de riesgo",
                    "Incremento en performance score",
                    "Optimización de procesos"
                ],
                metadata={
                    "trace_id": trace_id,
                    "generation_method": "llm",
                    "llm_processing_time": llm_result.processing_time,
                    "token_usage": llm_result.token_usage
                }
            )
            
            recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"[{trace_id}] Error parseando recomendaciones LLM: {e}")
        
        return recommendations
    
    def _create_recommendation_from_template(self, 
                                           template_key: str, 
                                           data: Dict[str, Any],
                                           specific_data: Dict[str, Any],
                                           trace_id: str,
                                           confidence: float) -> Recommendation:
        """Crea recomendación usando template predefinido"""
        template = self.templates.get(template_key, {})
        rec_id = f"rule_{template_key}_{int(time.time())}"
        
        # Generar título dinámico
        title_template = template.get("title_template", f"Recomendación: {template_key}")
        try:
            title = title_template.format(**specific_data)
        except KeyError:
            title = title_template
        
        # Generar descripción
        description = self._generate_template_description(template_key, data, specific_data)
        
        # Crear action items
        action_items = []
        for action_desc in template.get("actions", []):
            action_items.append(ActionItem(
                description=action_desc,
                estimated_effort="medium",
                estimated_timeframe="short_term"
            ))
        
        # Generar métricas de impacto esperado
        expected_impact = self._calculate_expected_impact(template_key, specific_data)
        
        recommendation = Recommendation(
            id=rec_id,
            title=title,
            description=description,
            type=template.get("type", RecommendationType.OPERATIONAL),
            priority=template.get("priority", RecommendationPriority.MEDIUM),
            status=RecommendationStatus.ACTIVE,
            confidence_score=confidence,
            created_at=datetime.now(timezone.utc),
            context_data=data.copy(),
            rationale=self._generate_rationale(template_key, specific_data),
            action_items=action_items,
            expected_impact=expected_impact,
            success_metrics=self._generate_success_metrics(template_key),
            metadata={
                "trace_id": trace_id,
                "generation_method": "rule_based",
                "template_used": template_key
            }
        )
        
        return recommendation
    
    def _create_alert_based_recommendation(self, alert, data: Dict[str, Any], trace_id: str) -> Optional[Recommendation]:
        """Crea recomendación basada en alerta activa"""
        try:
            rec_id = f"alert_{alert.id}_{int(time.time())}"
            
            recommendation = Recommendation(
                id=rec_id,
                title=f"Acción Requerida: {alert.title}",
                description=f"Recomendación generada por alerta: {alert.description}",
                type=RecommendationType.TACTICAL,
                priority=self._map_alert_severity_to_priority(alert.severity),
                status=RecommendationStatus.ACTIVE,
                confidence_score=0.8,
                created_at=datetime.now(timezone.utc),
                context_data=data.copy(),
                rationale=f"Generado automáticamente por alerta {alert.category.value}",
                action_items=[
                    ActionItem(
                        description=rec,
                        estimated_effort="medium",
                        estimated_timeframe="immediate"
                    ) for rec in alert.recommendations[:3]  # Tomar primeras 3 recomendaciones
                ],
                expected_impact={
                    "alert_resolution": True,
                    "risk_mitigation": True
                },
                success_metrics=[
                    "Resolución de alerta",
                    "Mejora en métricas relacionadas"
                ],
                metadata={
                    "trace_id": trace_id,
                    "generation_method": "alert_based",
                    "source_alert_id": alert.id
                }
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error creando recomendación desde alerta: {e}")
            return None
    
    def _generate_template_description(self, template_key: str, data: Dict[str, Any], specific_data: Dict[str, Any]) -> str:
        """Genera descripción detallada para template"""
        # Helper function para formatear valores seguros
        def safe_format(value, decimals=3):
            if isinstance(value, (int, float)):
                return f"{value:.{decimals}f}"
            return str(value)
        
        risk_score = safe_format(specific_data.get('risk_score', 'N/A'))
        performance_score = safe_format(specific_data.get('performance_score', 'N/A'))
        liquidity_ratio = safe_format(specific_data.get('liquidity_ratio', 'N/A'))
        variance = safe_format(specific_data.get('variance', 'N/A'))
        
        descriptions = {
            "high_risk": f"""
            Se ha detectado un nivel de riesgo elevado ({risk_score}) que requiere atención inmediata. 
            Esta situación puede impactar negativamente el desempeño del portafolio y aumentar la exposición a pérdidas potenciales.
            
            Es crucial implementar medidas de mitigación para reducir la exposición al riesgo y proteger los activos gestionados.
            Las acciones recomendadas se enfocan en diversificación, controles adicionales y revisión de límites de exposición.
            """,
            "performance_decline": f"""
            Se ha identificado un declive en el performance score ({performance_score}) que indica 
            deterioro en la eficiencia de las operaciones financieras.
            
            Este declive puede ser resultado de condiciones de mercado adversas, estrategias subóptimas, o factores operacionales.
            Es importante analizar las causas raíz e implementar mejoras para recuperar niveles de performance óptimos.
            """,
            "liquidity_optimization": f"""
            El ratio de liquidez actual ({liquidity_ratio}) indica oportunidades de optimización 
            en la gestión de liquidez y flujo de caja.
            
            Una gestión eficiente de liquidez es fundamental para mantener operaciones fluidas y aprovechar oportunidades de inversión.
            Las mejoras en este área pueden reducir costos financieros y mejorar flexibilidad operacional.
            """,
            "volume_anomaly": f"""
            Se ha detectado una anomalía en el patrón de volumen (varianza: {variance}) 
            que requiere investigación y posible ajuste de controles.
            
            Las anomalías de volumen pueden indicar cambios en comportamiento de mercado, problemas operacionales,
            o oportunidades no identificadas que requieren análisis detallado.
            """
        }
        
        return descriptions.get(template_key, "Recomendación generada automáticamente por el sistema de análisis.")
    
    def _generate_rationale(self, template_key: str, specific_data: Dict[str, Any]) -> str:
        """Genera justificación para la recomendación"""
        risk_score = specific_data.get('risk_score', 'N/A')
        performance_score = specific_data.get('performance_score', 'N/A')
        liquidity_ratio = specific_data.get('liquidity_ratio', 'N/A')
        variance = specific_data.get('variance', 'N/A')
        
        rationales = {
            "high_risk": f"Risk score de {risk_score} supera umbral crítico de 0.7",
            "performance_decline": f"Performance score de {performance_score} por debajo de mínimo aceptable",
            "liquidity_optimization": f"Liquidity ratio de {liquidity_ratio} indica oportunidad de mejora",
            "volume_anomaly": f"Varianza de {variance} indica patrón anómalo"
        }
        
        return rationales.get(template_key, "Basado en análisis de métricas del sistema")
    
    def _calculate_expected_impact(self, template_key: str, specific_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula impacto esperado de la recomendación"""
        impacts = {
            "high_risk": {
                "risk_reduction": "15-25%",
                "portfolio_stability": "high",
                "timeframe": "1-2 months"
            },
            "performance_decline": {
                "performance_improvement": "10-20%",
                "operational_efficiency": "medium",
                "timeframe": "2-3 months"
            },
            "liquidity_optimization": {
                "cost_reduction": "5-15%",
                "operational_flexibility": "high",
                "timeframe": "1 month"
            },
            "volume_anomaly": {
                "risk_mitigation": "medium",
                "operational_control": "high",
                "timeframe": "2-4 weeks"
            }
        }
        
        return impacts.get(template_key, {"impact": "positive", "timeframe": "medium_term"})
    
    def _generate_success_metrics(self, template_key: str) -> List[str]:
        """Genera métricas de éxito para la recomendación"""
        metrics = {
            "high_risk": [
                "Reducción de risk score por debajo de 0.6",
                "Mejora en diversificación del portafolio",
                "Disminución de volatilidad"
            ],
            "performance_decline": [
                "Incremento de performance score sobre 0.4",
                "Mejora en ROI de operaciones",
                "Optimización de procesos clave"
            ],
            "liquidity_optimization": [
                "Mejora en liquidity ratio sobre 0.4",
                "Reducción en costos de financiamiento",
                "Optimización de flujo de caja"
            ],
            "volume_anomaly": [
                "Normalización de patrones de volumen",
                "Reducción de varianza por debajo de 0.15",
                "Mejora en controles operacionales"
            ]
        }
        
        return metrics.get(template_key, ["Mejora en métricas relacionadas"])
    
    def _map_alert_severity_to_priority(self, severity) -> RecommendationPriority:
        """Mapea severidad de alerta a prioridad de recomendación"""
        mapping = {
            "info": RecommendationPriority.LOW,
            "warning": RecommendationPriority.MEDIUM,
            "critical": RecommendationPriority.HIGH,
            "urgent": RecommendationPriority.URGENT
        }
        
        severity_str = severity.value if hasattr(severity, 'value') else str(severity)
        return mapping.get(severity_str, RecommendationPriority.MEDIUM)
    
    def _post_process_recommendations(self, recommendations: List[Recommendation], trace_id: str) -> List[Recommendation]:
        """Post-procesa recomendaciones para evitar duplicados y mejorar calidad"""
        # Filtrar duplicados por título similar
        unique_recommendations = []
        seen_titles = set()
        
        for rec in recommendations:
            title_key = rec.title.lower().replace(" ", "")
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_recommendations.append(rec)
            else:
                logger.debug(f"[{trace_id}] Recomendación duplicada filtrada: {rec.title}")
        
        # Ordenar por prioridad y confidence
        priority_order = {
            RecommendationPriority.URGENT: 4,
            RecommendationPriority.HIGH: 3,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 1
        }
        
        unique_recommendations.sort(
            key=lambda r: (priority_order.get(r.priority, 0), r.confidence_score),
            reverse=True
        )
        
        # Limitar a máximo 8 recomendaciones activas
        return unique_recommendations[:8]
    
    def _update_metrics(self, recommendations: List[Recommendation], generation_time: float):
        """Actualiza métricas del sistema"""
        self.metrics["total_recommendations"] += len(recommendations)
        
        # Actualizar conteos por tipo
        for rec in recommendations:
            type_key = rec.type.value
            self.metrics["recommendations_by_type"][type_key] = (
                self.metrics["recommendations_by_type"].get(type_key, 0) + 1
            )
            
            priority_key = rec.priority.value
            self.metrics["recommendations_by_priority"][priority_key] = (
                self.metrics["recommendations_by_priority"].get(priority_key, 0) + 1
            )
        
        # Actualizar confidence score promedio
        if recommendations:
            total_confidence = sum(r.confidence_score for r in recommendations)
            current_avg = self.metrics["avg_confidence_score"]
            total_recs = self.metrics["total_recommendations"]
            
            if total_recs == len(recommendations):
                self.metrics["avg_confidence_score"] = total_confidence / len(recommendations)
            else:
                previous_total = (current_avg * (total_recs - len(recommendations)))
                self.metrics["avg_confidence_score"] = (previous_total + total_confidence) / total_recs
        
        # Actualizar tiempo promedio de generación
        current_avg_time = self.metrics["avg_generation_time"]
        total_generations = len(self.recommendation_history)  # Proxy para total de generaciones
        
        if total_generations == 1:
            self.metrics["avg_generation_time"] = generation_time
        else:
            self.metrics["avg_generation_time"] = (
                (current_avg_time * (total_generations - 1) + generation_time) / total_generations
            )
    
    def implement_recommendation(self, recommendation_id: str, implementation_note: Optional[str] = None) -> bool:
        """Marca recomendación como implementada"""
        for rec in self.active_recommendations:
            if rec.id == recommendation_id:
                rec.status = RecommendationStatus.IMPLEMENTED
                rec.implemented_at = datetime.now(timezone.utc)
                if implementation_note:
                    rec.metadata["implementation_note"] = implementation_note
                
                # Remover de activas
                self.active_recommendations.remove(rec)
                
                # Actualizar tasa de implementación
                total_completed = sum(1 for r in self.recommendation_history if r.status == RecommendationStatus.IMPLEMENTED)
                self.metrics["implementation_rate"] = total_completed / max(1, len(self.recommendation_history))
                
                logger.info(f"Recomendación implementada: {recommendation_id}")
                return True
        
        logger.warning(f"Recomendación no encontrada: {recommendation_id}")
        return False
    
    def dismiss_recommendation(self, recommendation_id: str, dismissal_reason: Optional[str] = None) -> bool:
        """Descarta recomendación"""
        for rec in self.active_recommendations:
            if rec.id == recommendation_id:
                rec.status = RecommendationStatus.DISMISSED
                if dismissal_reason:
                    rec.metadata["dismissal_reason"] = dismissal_reason
                
                self.active_recommendations.remove(rec)
                logger.info(f"Recomendación descartada: {recommendation_id}")
                return True
        
        return False
    
    def get_active_recommendations(self, 
                                 priority_filter: Optional[RecommendationPriority] = None,
                                 type_filter: Optional[RecommendationType] = None) -> List[Recommendation]:
        """Obtiene recomendaciones activas con filtros"""
        filtered = self.active_recommendations.copy()
        
        if priority_filter:
            filtered = [r for r in filtered if r.priority == priority_filter]
            
        if type_filter:
            filtered = [r for r in filtered if r.type == type_filter]
        
        return filtered
    
    def get_recommendation_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del sistema de recomendaciones"""
        active_by_priority = {}
        for priority in RecommendationPriority:
            active_by_priority[priority.value] = len([r for r in self.active_recommendations if r.priority == priority])
        
        active_by_type = {}
        for rec_type in RecommendationType:
            active_by_type[rec_type.value] = len([r for r in self.active_recommendations if r.type == rec_type])
        
        return {
            "total_active_recommendations": len(self.active_recommendations),
            "total_historical_recommendations": len(self.recommendation_history),
            "recommendations_by_priority": active_by_priority,
            "recommendations_by_type": active_by_type,
            "system_metrics": self.metrics.copy()
        }