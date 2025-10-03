"""
Production Monitoring and Metrics for Semantic NLP System

Enterprise-grade monitoring with:
- Performance metrics
- Accuracy tracking
- Error rate monitoring
- A/B testing metrics
- Alert thresholds
"""

import time
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

from src.core.logging import get_logger
from src.domain.contracts.intent import Intent

logger = get_logger(__name__)


@dataclass
class MetricEntry:
    """Single metric measurement"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentClassificationMetric:
    """Metrics for intent classification accuracy"""
    session_id: str
    query: str
    predicted_intent: str
    confidence: float
    actual_intent: Optional[str] = None
    processing_time_ms: float = 0.0
    system_used: str = "semantic"  # "semantic" or "legacy"
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SystemHealthMetric:
    """System health and performance metrics"""
    avg_response_time: float
    requests_per_minute: int
    error_rate: float
    semantic_system_usage: float
    legacy_system_usage: float
    confidence_distribution: Dict[str, int]
    intent_distribution: Dict[str, int]
    timestamp: datetime = field(default_factory=datetime.now)


class SemanticNLPMetrics:
    """
    Production metrics collector for semantic NLP system

    Tracks:
    - Classification accuracy
    - Response times
    - Error rates
    - A/B testing results
    - System health
    """

    def __init__(self, buffer_size: int = 10000, alert_thresholds: Optional[Dict] = None):
        self.buffer_size = buffer_size
        self.alert_thresholds = alert_thresholds or self._default_alert_thresholds()

        # Thread-safe metrics storage
        self._lock = threading.RLock()
        self._metrics_buffer: deque = deque(maxlen=buffer_size)
        self._intent_metrics: deque = deque(maxlen=buffer_size)

        # Real-time counters
        self._counters = defaultdict(int)
        self._timings = defaultdict(list)
        self._errors = defaultdict(int)

        # Health monitoring
        self._last_health_check = datetime.now()
        self._health_metrics = []

        logger.info({"event": "semantic_metrics_initialized",
                    "buffer_size": buffer_size,
                    "alert_thresholds": self.alert_thresholds})

    def track_intent_classification(self, session_id: str, query: str,
                                   predicted_intent: Intent, confidence: float,
                                   processing_time_ms: float, system_used: str = "semantic",
                                   actual_intent: Optional[Intent] = None):
        """Track intent classification metrics"""
        metric = IntentClassificationMetric(
            session_id=session_id,
            query=query,
            predicted_intent=predicted_intent.value if predicted_intent else "none",
            confidence=confidence,
            actual_intent=actual_intent.value if actual_intent else None,
            processing_time_ms=processing_time_ms,
            system_used=system_used
        )

        with self._lock:
            self._intent_metrics.append(metric)

            # Update real-time counters
            self._counters[f"intent_{predicted_intent.value if predicted_intent else 'none'}"] += 1
            self._counters[f"system_{system_used}"] += 1
            self._timings["classification_time"].append(processing_time_ms)

            # Keep only recent timings (last 1000)
            if len(self._timings["classification_time"]) > 1000:
                self._timings["classification_time"] = self._timings["classification_time"][-1000:]

        logger.debug({"event": "intent_classification_tracked",
                     "intent": predicted_intent.value if predicted_intent else "none",
                     "confidence": confidence,
                     "system": system_used,
                     "processing_time": processing_time_ms})

        # Check for alerts
        self._check_alert_thresholds(metric)

    def track_error(self, error_type: str, error_details: str, session_id: str = "unknown"):
        """Track errors for monitoring"""
        with self._lock:
            self._errors[error_type] += 1

        error_metric = MetricEntry(
            timestamp=datetime.now(),
            metric_name="error",
            value=1.0,
            tags={"error_type": error_type, "session_id": session_id},
            metadata={"error_details": error_details}
        )

        with self._lock:
            self._metrics_buffer.append(error_metric)

        logger.error({"event": "semantic_nlp_error",
                     "error_type": error_type,
                     "session_id": session_id,
                     "details": error_details})

    def get_system_health(self) -> SystemHealthMetric:
        """Get current system health metrics"""
        with self._lock:
            now = datetime.now()
            recent_metrics = [m for m in self._intent_metrics
                            if now - m.timestamp < timedelta(minutes=5)]

            if not recent_metrics:
                return SystemHealthMetric(
                    avg_response_time=0.0,
                    requests_per_minute=0,
                    error_rate=0.0,
                    semantic_system_usage=0.0,
                    legacy_system_usage=0.0,
                    confidence_distribution={},
                    intent_distribution={}
                )

            # Calculate metrics
            avg_response_time = sum(m.processing_time_ms for m in recent_metrics) / len(recent_metrics)
            requests_per_minute = len(recent_metrics)

            # System usage
            semantic_count = sum(1 for m in recent_metrics if m.system_used == "semantic")
            legacy_count = len(recent_metrics) - semantic_count
            total_requests = len(recent_metrics)

            semantic_usage = (semantic_count / total_requests * 100) if total_requests > 0 else 0
            legacy_usage = (legacy_count / total_requests * 100) if total_requests > 0 else 0

            # Confidence distribution
            confidence_ranges = {"low": 0, "medium": 0, "high": 0, "very_high": 0}
            for metric in recent_metrics:
                if metric.confidence < 0.5:
                    confidence_ranges["low"] += 1
                elif metric.confidence < 0.7:
                    confidence_ranges["medium"] += 1
                elif metric.confidence < 0.9:
                    confidence_ranges["high"] += 1
                else:
                    confidence_ranges["very_high"] += 1

            # Intent distribution
            intent_counts = defaultdict(int)
            for metric in recent_metrics:
                intent_counts[metric.predicted_intent] += 1

            # Error rate calculation
            total_errors = sum(self._errors.values())
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

            return SystemHealthMetric(
                avg_response_time=avg_response_time,
                requests_per_minute=requests_per_minute,
                error_rate=error_rate,
                semantic_system_usage=semantic_usage,
                legacy_system_usage=legacy_usage,
                confidence_distribution=confidence_ranges,
                intent_distribution=dict(intent_counts)
            )

    def get_accuracy_metrics(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Calculate accuracy metrics for time window"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            recent_metrics = [m for m in self._intent_metrics
                            if m.timestamp > cutoff_time and m.actual_intent is not None]

            if not recent_metrics:
                return {"accuracy": 0.0, "total_labeled": 0, "by_intent": {}}

            # Calculate overall accuracy
            correct_predictions = sum(1 for m in recent_metrics
                                    if m.predicted_intent == m.actual_intent)
            accuracy = (correct_predictions / len(recent_metrics)) * 100

            # Accuracy by intent
            intent_accuracy = {}
            for intent in set(m.actual_intent for m in recent_metrics):
                intent_metrics = [m for m in recent_metrics if m.actual_intent == intent]
                intent_correct = sum(1 for m in intent_metrics if m.predicted_intent == m.actual_intent)
                intent_accuracy[intent] = (intent_correct / len(intent_metrics)) * 100

            return {
                "accuracy": accuracy,
                "total_labeled": len(recent_metrics),
                "by_intent": intent_accuracy,
                "time_window_minutes": time_window_minutes
            }

    def get_a_b_testing_metrics(self) -> Dict[str, Any]:
        """Get A/B testing comparison metrics"""
        with self._lock:
            recent_metrics = [m for m in self._intent_metrics
                            if datetime.now() - m.timestamp < timedelta(hours=1)]

            semantic_metrics = [m for m in recent_metrics if m.system_used == "semantic"]
            legacy_metrics = [m for m in recent_metrics if m.system_used == "legacy"]

            def calculate_stats(metrics_list):
                if not metrics_list:
                    return {"count": 0, "avg_confidence": 0, "avg_response_time": 0}

                return {
                    "count": len(metrics_list),
                    "avg_confidence": sum(m.confidence for m in metrics_list) / len(metrics_list),
                    "avg_response_time": sum(m.processing_time_ms for m in metrics_list) / len(metrics_list)
                }

            return {
                "semantic_system": calculate_stats(semantic_metrics),
                "legacy_system": calculate_stats(legacy_metrics),
                "total_requests": len(recent_metrics),
                "semantic_percentage": (len(semantic_metrics) / len(recent_metrics) * 100) if recent_metrics else 0
            }

    def _check_alert_thresholds(self, metric: IntentClassificationMetric):
        """Check if metric triggers any alerts"""
        # Low confidence alert
        if metric.confidence < self.alert_thresholds["min_confidence"]:
            logger.warning({"event": "low_confidence_alert",
                          "session_id": metric.session_id,
                          "query": metric.query,
                          "confidence": metric.confidence,
                          "threshold": self.alert_thresholds["min_confidence"]})

        # Slow response alert
        if metric.processing_time_ms > self.alert_thresholds["max_response_time_ms"]:
            logger.warning({"event": "slow_response_alert",
                          "session_id": metric.session_id,
                          "processing_time": metric.processing_time_ms,
                          "threshold": self.alert_thresholds["max_response_time_ms"]})

    def _default_alert_thresholds(self) -> Dict[str, float]:
        """Default alert thresholds"""
        return {
            "min_confidence": 0.3,
            "max_response_time_ms": 500.0,
            "max_error_rate": 5.0,
            "min_accuracy": 80.0
        }

    def export_metrics(self, format: str = "json") -> str:
        """Export metrics for external monitoring systems"""
        health = self.get_system_health()
        accuracy = self.get_accuracy_metrics()
        ab_testing = self.get_a_b_testing_metrics()

        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "system_health": {
                "avg_response_time": health.avg_response_time,
                "requests_per_minute": health.requests_per_minute,
                "error_rate": health.error_rate,
                "semantic_usage": health.semantic_system_usage,
                "legacy_usage": health.legacy_system_usage
            },
            "accuracy": accuracy,
            "ab_testing": ab_testing
        }

        if format == "json":
            return json.dumps(metrics_data, indent=2)
        else:
            return str(metrics_data)


# Global singleton
_semantic_metrics: Optional[SemanticNLPMetrics] = None


def get_semantic_metrics() -> SemanticNLPMetrics:
    """Get global semantic metrics instance"""
    global _semantic_metrics
    if _semantic_metrics is None:
        _semantic_metrics = SemanticNLPMetrics()
    return _semantic_metrics