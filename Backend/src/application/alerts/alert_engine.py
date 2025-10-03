"""
Alert Engine - Sistema de alertas inteligentes
Detecta anomalías y genera alertas basadas en análisis financiero
"""
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Niveles de severidad de alertas"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    URGENT = "urgent"


class AlertCategory(Enum):
    """Categorías de alertas financieras"""
    RISK_MANAGEMENT = "risk_management"
    PERFORMANCE_ANOMALY = "performance_anomaly"
    VOLUME_SPIKE = "volume_spike"
    THRESHOLD_BREACH = "threshold_breach"
    PATTERN_DETECTION = "pattern_detection"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"


@dataclass
class AlertCondition:
    """Condición para disparar una alerta"""
    name: str
    condition_type: str  # "threshold", "pattern", "anomaly", "trend"
    parameters: Dict[str, Any]
    enabled: bool = True
    
    def evaluate(self, data: Dict[str, Any]) -> bool:
        """Evalúa si la condición se cumple"""
        if not self.enabled:
            return False
            
        try:
            if self.condition_type == "threshold":
                return self._evaluate_threshold(data)
            elif self.condition_type == "pattern":
                return self._evaluate_pattern(data)
            elif self.condition_type == "anomaly":
                return self._evaluate_anomaly(data)
            elif self.condition_type == "trend":
                return self._evaluate_trend(data)
            else:
                logger.warning(f"Unknown condition type: {self.condition_type}")
                return False
        except Exception as e:
            logger.error(f"Error evaluating condition {self.name}: {e}")
            return False
    
    def _evaluate_threshold(self, data: Dict[str, Any]) -> bool:
        """Evalúa condiciones de umbral"""
        metric = self.parameters.get("metric")
        threshold = self.parameters.get("threshold")
        operator = self.parameters.get("operator", "greater_than")
        
        if not metric or threshold is None:
            return False
            
        value = self._extract_metric_value(data, metric)
        if value is None:
            return False
            
        if operator == "greater_than":
            return value > threshold
        elif operator == "less_than":
            return value < threshold
        elif operator == "equal":
            return abs(value - threshold) < 0.001
        elif operator == "not_equal":
            return abs(value - threshold) >= 0.001
        else:
            return False
    
    def _evaluate_pattern(self, data: Dict[str, Any]) -> bool:
        """Evalúa patrones en los datos"""
        pattern_type = self.parameters.get("pattern_type")
        
        if pattern_type == "consecutive_increases":
            return self._check_consecutive_increases(data)
        elif pattern_type == "volatility_spike":
            return self._check_volatility_spike(data)
        elif pattern_type == "unusual_distribution":
            return self._check_unusual_distribution(data)
        else:
            return False
    
    def _evaluate_anomaly(self, data: Dict[str, Any]) -> bool:
        """Evalúa anomalías estadísticas"""
        metric = self.parameters.get("metric")
        threshold_std = self.parameters.get("threshold_std", 2.0)
        
        if not metric:
            return False
            
        values = self._extract_time_series(data, metric)
        if len(values) < 10:  # Necesita suficientes datos
            return False
            
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        current_value = values[-1]
        z_score = abs(current_value - mean_val) / max(std_dev, 0.001)
        
        return z_score > threshold_std
    
    def _evaluate_trend(self, data: Dict[str, Any]) -> bool:
        """Evalúa tendencias en los datos"""
        metric = self.parameters.get("metric")
        trend_type = self.parameters.get("trend_type", "increasing")
        min_periods = self.parameters.get("min_periods", 5)
        
        if not metric:
            return False
            
        values = self._extract_time_series(data, metric)
        if len(values) < min_periods:
            return False
            
        # Simple trend detection usando regresión lineal básica
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return False
            
        slope = numerator / denominator
        
        if trend_type == "increasing":
            return slope > self.parameters.get("threshold", 0.01)
        elif trend_type == "decreasing":
            return slope < -self.parameters.get("threshold", 0.01)
        else:
            return False
    
    def _extract_metric_value(self, data: Dict[str, Any], metric: str) -> Optional[float]:
        """Extrae valor de métrica de los datos"""
        try:
            # Soporte para paths anidados como "metrics.total_volume"
            keys = metric.split(".")
            value = data
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None
    
    def _extract_time_series(self, data: Dict[str, Any], metric: str) -> List[float]:
        """Extrae serie temporal de métrica"""
        # Implementación simplificada - busca arrays de valores
        values = []
        metric_value = self._extract_metric_value(data, metric)
        
        if metric_value is not None:
            values.append(metric_value)
            
        # Busca datos históricos si están disponibles
        if "historical_data" in data:
            historical = data["historical_data"]
            if isinstance(historical, list):
                for entry in historical:
                    val = self._extract_metric_value(entry, metric)
                    if val is not None:
                        values.append(val)
        
        return values
    
    def _check_consecutive_increases(self, data: Dict[str, Any]) -> bool:
        """Verifica aumentos consecutivos"""
        metric = self.parameters.get("metric")
        min_consecutive = self.parameters.get("min_consecutive", 3)
        
        values = self._extract_time_series(data, metric)
        if len(values) < min_consecutive + 1:
            return False
            
        consecutive_count = 0
        for i in range(1, len(values)):
            if values[i] > values[i-1]:
                consecutive_count += 1
                if consecutive_count >= min_consecutive:
                    return True
            else:
                consecutive_count = 0
                
        return False
    
    def _check_volatility_spike(self, data: Dict[str, Any]) -> bool:
        """Verifica picos de volatilidad"""
        metric = self.parameters.get("metric")
        volatility_threshold = self.parameters.get("volatility_threshold", 0.1)
        
        values = self._extract_time_series(data, metric)
        if len(values) < 5:
            return False
            
        # Calcular volatilidad como desviación estándar de cambios porcentuales
        changes = []
        for i in range(1, len(values)):
            if values[i-1] != 0:
                change = (values[i] - values[i-1]) / values[i-1]
                changes.append(change)
        
        if len(changes) < 3:
            return False
            
        mean_change = sum(changes) / len(changes)
        variance = sum((c - mean_change) ** 2 for c in changes) / len(changes)
        volatility = variance ** 0.5
        
        return volatility > volatility_threshold
    
    def _check_unusual_distribution(self, data: Dict[str, Any]) -> bool:
        """Verifica distribuciones inusuales"""
        # Implementación simplificada
        return False


@dataclass
class Alert:
    """Alerta generada por el sistema"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    category: AlertCategory
    triggered_by: str  # Nombre de la condición que disparó la alerta
    triggered_at: datetime
    data_context: Dict[str, Any]
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte alerta a diccionario"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "triggered_by": self.triggered_by,
            "triggered_at": self.triggered_at.isoformat(),
            "data_context": self.data_context,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


class AlertEngine:
    """
    Motor de alertas inteligentes para análisis financiero
    Monitorea condiciones y genera alertas automáticas
    """
    
    def __init__(self):
        """Inicializa el motor de alertas"""
        self.conditions: List[AlertCondition] = []
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        self.metrics = {
            "total_evaluations": 0,
            "alerts_triggered": 0,
            "alerts_resolved": 0,
            "conditions_checked": 0,
            "avg_evaluation_time": 0.0
        }
        
        # Cargar condiciones predeterminadas
        self._load_default_conditions()
        
        logger.info("AlertEngine inicializado con {} condiciones".format(len(self.conditions)))
    
    def _load_default_conditions(self):
        """Carga condiciones de alerta predeterminadas para análisis financiero"""
        default_conditions = [
            # Alertas de riesgo
            AlertCondition(
                name="high_risk_score",
                condition_type="threshold",
                parameters={
                    "metric": "metrics.risk_score",
                    "threshold": 0.7,
                    "operator": "greater_than"
                }
            ),
            
            AlertCondition(
                name="low_liquidity",
                condition_type="threshold",
                parameters={
                    "metric": "metrics.liquidity_ratio",
                    "threshold": 0.2,
                    "operator": "less_than"
                }
            ),
            
            # Alertas de rendimiento
            AlertCondition(
                name="performance_decline",
                condition_type="trend",
                parameters={
                    "metric": "metrics.performance_score",
                    "trend_type": "decreasing",
                    "threshold": 0.05,
                    "min_periods": 3
                }
            ),
            
            # Alertas de volumen
            AlertCondition(
                name="volume_spike",
                condition_type="anomaly",
                parameters={
                    "metric": "metrics.total_volume",
                    "threshold_std": 2.5
                }
            ),
            
            AlertCondition(
                name="unusual_transaction_pattern",
                condition_type="pattern",
                parameters={
                    "pattern_type": "volatility_spike",
                    "metric": "metrics.avg_amount",
                    "volatility_threshold": 0.15
                }
            ),
            
            # Alertas operacionales
            AlertCondition(
                name="high_processing_time",
                condition_type="threshold",
                parameters={
                    "metric": "processing_time",
                    "threshold": 10.0,
                    "operator": "greater_than"
                }
            ),
            
            AlertCondition(
                name="error_rate_high",
                condition_type="threshold",
                parameters={
                    "metric": "metrics.error_rate",
                    "threshold": 0.05,
                    "operator": "greater_than"
                }
            )
        ]
        
        self.conditions.extend(default_conditions)
    
    def add_condition(self, condition: AlertCondition):
        """Agrega nueva condición de alerta"""
        self.conditions.append(condition)
        logger.info(f"Condición de alerta agregada: {condition.name}")
    
    def remove_condition(self, condition_name: str) -> bool:
        """Remueve condición de alerta por nombre"""
        initial_count = len(self.conditions)
        self.conditions = [c for c in self.conditions if c.name != condition_name]
        
        removed = len(self.conditions) < initial_count
        if removed:
            logger.info(f"Condición de alerta removida: {condition_name}")
        
        return removed
    
    def evaluate_data(self, data: Dict[str, Any], trace_id: Optional[str] = None) -> List[Alert]:
        """
        Evalúa datos contra todas las condiciones y genera alertas
        
        Args:
            data: Datos a evaluar
            trace_id: ID de trazabilidad
            
        Returns:
            Lista de alertas generadas
        """
        if not trace_id:
            trace_id = str(uuid4())
        
        start_time = time.time()
        new_alerts = []
        self.metrics["total_evaluations"] += 1
        
        logger.info(f"[{trace_id}] Evaluando {len(self.conditions)} condiciones de alerta")
        
        for condition in self.conditions:
            try:
                self.metrics["conditions_checked"] += 1
                
                if condition.evaluate(data):
                    alert = self._create_alert(condition, data, trace_id)
                    new_alerts.append(alert)
                    self.active_alerts.append(alert)
                    self.alert_history.append(alert)
                    self.metrics["alerts_triggered"] += 1
                    
                    logger.warning(f"[{trace_id}] ALERTA DISPARADA: {alert.title} ({alert.severity.value})")
                    
            except Exception as e:
                logger.error(f"[{trace_id}] Error evaluando condición {condition.name}: {e}")
        
        # Actualizar métricas de tiempo
        evaluation_time = time.time() - start_time
        self._update_avg_evaluation_time(evaluation_time)
        
        logger.info(f"[{trace_id}] Evaluación completada: {len(new_alerts)} nuevas alertas en {evaluation_time:.3f}s")
        
        return new_alerts
    
    def _create_alert(self, condition: AlertCondition, data: Dict[str, Any], trace_id: str) -> Alert:
        """Crea alerta basada en condición disparada"""
        alert_id = f"alert_{int(time.time())}_{condition.name}"
        
        # Determinar severidad y categoría basado en la condición
        severity, category = self._determine_alert_properties(condition, data)
        
        # Generar título y descripción
        title, description = self._generate_alert_content(condition, data)
        
        # Generar recomendaciones
        recommendations = self._generate_recommendations(condition, data)
        
        alert = Alert(
            id=alert_id,
            title=title,
            description=description,
            severity=severity,
            category=category,
            triggered_by=condition.name,
            triggered_at=datetime.now(timezone.utc),
            data_context=data.copy(),
            recommendations=recommendations,
            metadata={
                "trace_id": trace_id,
                "condition_type": condition.condition_type,
                "condition_parameters": condition.parameters
            }
        )
        
        return alert
    
    def _determine_alert_properties(self, condition: AlertCondition, data: Dict[str, Any]) -> Tuple[AlertSeverity, AlertCategory]:
        """Determina severidad y categoría de la alerta"""
        # Mapeo de condiciones a propiedades de alerta
        severity_map = {
            "high_risk_score": AlertSeverity.CRITICAL,
            "low_liquidity": AlertSeverity.URGENT,
            "performance_decline": AlertSeverity.WARNING,
            "volume_spike": AlertSeverity.WARNING,
            "unusual_transaction_pattern": AlertSeverity.INFO,
            "high_processing_time": AlertSeverity.WARNING,
            "error_rate_high": AlertSeverity.CRITICAL
        }
        
        category_map = {
            "high_risk_score": AlertCategory.RISK_MANAGEMENT,
            "low_liquidity": AlertCategory.RISK_MANAGEMENT,
            "performance_decline": AlertCategory.PERFORMANCE_ANOMALY,
            "volume_spike": AlertCategory.VOLUME_SPIKE,
            "unusual_transaction_pattern": AlertCategory.PATTERN_DETECTION,
            "high_processing_time": AlertCategory.OPERATIONAL,
            "error_rate_high": AlertCategory.OPERATIONAL
        }
        
        severity = severity_map.get(condition.name, AlertSeverity.INFO)
        category = category_map.get(condition.name, AlertCategory.OPERATIONAL)
        
        return severity, category
    
    def _generate_alert_content(self, condition: AlertCondition, data: Dict[str, Any]) -> Tuple[str, str]:
        """Genera título y descripción de la alerta"""
        content_templates = {
            "high_risk_score": {
                "title": "Nivel de Riesgo Elevado",
                "description": "El score de riesgo ha superado el umbral crítico de {threshold}. Valor actual: {current_value:.3f}"
            },
            "low_liquidity": {
                "title": "Liquidez Baja Crítica",
                "description": "La ratio de liquidez ha caído por debajo del mínimo seguro de {threshold}. Valor actual: {current_value:.3f}"
            },
            "performance_decline": {
                "title": "Declive en Performance",
                "description": "Se detectó tendencia decreciente en el score de performance durante {min_periods} períodos consecutivos"
            },
            "volume_spike": {
                "title": "Anomalía en Volumen de Transacciones",
                "description": "El volumen de transacciones muestra comportamiento anómalo ({threshold_std} desviaciones estándar)"
            },
            "unusual_transaction_pattern": {
                "title": "Patrón de Transacciones Inusual",
                "description": "Se detectó volatilidad inusual en el monto promedio de transacciones"
            },
            "high_processing_time": {
                "title": "Tiempo de Procesamiento Elevado",
                "description": "El tiempo de procesamiento excede el umbral de {threshold}s. Tiempo actual: {current_value:.2f}s"
            },
            "error_rate_high": {
                "title": "Tasa de Errores Crítica",
                "description": "La tasa de errores supera el umbral crítico de {threshold}. Valor actual: {current_value:.3f}"
            }
        }
        
        template = content_templates.get(condition.name, {
            "title": f"Alerta: {condition.name}",
            "description": f"Condición {condition.name} disparada"
        })
        
        # Reemplazar placeholders con valores reales
        current_value = None
        if condition.condition_type == "threshold":
            metric = condition.parameters.get("metric")
            current_value = condition._extract_metric_value(data, metric) if metric else None
        
        format_data = {
            "threshold": condition.parameters.get("threshold", "N/A"),
            "current_value": current_value if current_value is not None else "N/A",
            "min_periods": condition.parameters.get("min_periods", "N/A"),
            "threshold_std": condition.parameters.get("threshold_std", "N/A")
        }
        
        try:
            title = template["title"].format(**format_data)
            description = template["description"].format(**format_data)
        except KeyError:
            title = template["title"]
            description = template["description"]
        
        return title, description
    
    def _generate_recommendations(self, condition: AlertCondition, data: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones basadas en la condición disparada"""
        recommendations_map = {
            "high_risk_score": [
                "Revisar distribución de activos y considerar diversificación",
                "Implementar estrategias de mitigación de riesgo inmediatas",
                "Analizar exposición a sectores volátiles",
                "Considerar reducir posiciones de alto riesgo"
            ],
            "low_liquidity": [
                "Mejorar gestión de cash flow y reservas líquidas",
                "Revisar términos de crédito y facilidades de liquidez",
                "Acelerar cobros y optimizar ciclo de conversión",
                "Evaluar venta de activos no críticos"
            ],
            "performance_decline": [
                "Analizar factores causantes del declive",
                "Revisar estrategia de inversión y allocation",
                "Considerar rebalanceo de portafolio",
                "Evaluar cambios en condiciones de mercado"
            ],
            "volume_spike": [
                "Investigar origen del incremento de volumen",
                "Verificar capacidad operacional para manejar volumen",
                "Monitorear liquidez y exposición al riesgo",
                "Analizar impacto en spreads y costos"
            ],
            "unusual_transaction_pattern": [
                "Investigar patrones de transacciones anómalas",
                "Revisar controles de riesgo operacional",
                "Verificar sistemas de detección de fraude",
                "Analizar comportamiento de clientes"
            ],
            "high_processing_time": [
                "Optimizar procesos y workflows",
                "Revisar capacidad de infraestructura",
                "Identificar cuellos de botella en el sistema",
                "Considerar escalamiento de recursos"
            ],
            "error_rate_high": [
                "Investigar causas raíz de errores",
                "Revisar procesos de validación de datos",
                "Fortalecer controles de calidad",
                "Implementar monitoreo adicional"
            ]
        }
        
        return recommendations_map.get(condition.name, ["Revisar condición y tomar acción apropiada"])
    
    def resolve_alert(self, alert_id: str, resolution_note: Optional[str] = None) -> bool:
        """Marca alerta como resuelta"""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc)
                if resolution_note:
                    alert.metadata["resolution_note"] = resolution_note
                
                # Remover de alertas activas
                self.active_alerts.remove(alert)
                self.metrics["alerts_resolved"] += 1
                
                logger.info(f"Alerta resuelta: {alert_id}")
                return True
        
        logger.warning(f"Alerta no encontrada para resolver: {alert_id}")
        return False
    
    def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None,
                         category_filter: Optional[AlertCategory] = None) -> List[Alert]:
        """Obtiene alertas activas con filtros opcionales"""
        filtered_alerts = self.active_alerts.copy()
        
        if severity_filter:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity_filter]
            
        if category_filter:
            filtered_alerts = [a for a in filtered_alerts if a.category == category_filter]
        
        return filtered_alerts
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del estado de alertas"""
        active_by_severity = {}
        for severity in AlertSeverity:
            active_by_severity[severity.value] = len([a for a in self.active_alerts if a.severity == severity])
        
        active_by_category = {}
        for category in AlertCategory:
            active_by_category[category.value] = len([a for a in self.active_alerts if a.category == category])
        
        return {
            "total_active_alerts": len(self.active_alerts),
            "total_conditions": len(self.conditions),
            "alerts_by_severity": active_by_severity,
            "alerts_by_category": active_by_category,
            "system_metrics": self.metrics.copy()
        }
    
    def _update_avg_evaluation_time(self, evaluation_time: float):
        """Actualiza tiempo promedio de evaluación"""
        current_avg = self.metrics["avg_evaluation_time"]
        total_evaluations = self.metrics["total_evaluations"]
        
        if total_evaluations == 1:
            self.metrics["avg_evaluation_time"] = evaluation_time
        else:
            self.metrics["avg_evaluation_time"] = (
                (current_avg * (total_evaluations - 1) + evaluation_time) / total_evaluations
            )
    
    def clear_resolved_alerts(self, older_than_hours: int = 24):
        """Limpia alertas resueltas más antiguas que X horas"""
        cutoff_time = datetime.now(timezone.utc)
        cutoff_timestamp = cutoff_time.timestamp() - (older_than_hours * 3600)
        
        initial_count = len(self.alert_history)
        self.alert_history = [
            a for a in self.alert_history 
            if not a.resolved or a.resolved_at.timestamp() > cutoff_timestamp
        ]
        
        cleaned = initial_count - len(self.alert_history)
        if cleaned > 0:
            logger.info(f"Limpiadas {cleaned} alertas resueltas de más de {older_than_hours}h")