"""
API Routes for Semantic NLP Metrics and Monitoring

Production endpoints for:
- System health monitoring
- A/B testing metrics
- Feature flag management
- Real-time alerts
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import json

from src.core.monitoring import get_semantic_metrics
from src.core.feature_flags import get_feature_flag_manager, FeatureFlagStatus
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics", "monitoring"])


@router.get("/health")
async def get_system_health():
    """Get current system health metrics"""
    try:
        metrics = get_semantic_metrics()
        health = metrics.get_system_health()

        return {
            "status": "healthy",
            "metrics": {
                "avg_response_time_ms": health.avg_response_time,
                "requests_per_minute": health.requests_per_minute,
                "error_rate_percent": health.error_rate,
                "semantic_system_usage_percent": health.semantic_system_usage,
                "legacy_system_usage_percent": health.legacy_system_usage,
                "confidence_distribution": health.confidence_distribution,
                "intent_distribution": health.intent_distribution,
                "timestamp": health.timestamp.isoformat()
            }
        }
    except Exception as e:
        logger.error({"event": "health_metrics_error", "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to retrieve health metrics")


@router.get("/accuracy")
async def get_accuracy_metrics(time_window_minutes: int = 60):
    """Get accuracy metrics for specified time window"""
    try:
        metrics = get_semantic_metrics()
        accuracy = metrics.get_accuracy_metrics(time_window_minutes)

        return {
            "status": "success",
            "accuracy_metrics": accuracy
        }
    except Exception as e:
        logger.error({"event": "accuracy_metrics_error", "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to retrieve accuracy metrics")


@router.get("/ab-testing")
async def get_ab_testing_metrics():
    """Get A/B testing comparison metrics"""
    try:
        metrics = get_semantic_metrics()
        ab_testing = metrics.get_a_b_testing_metrics()

        return {
            "status": "success",
            "ab_testing_metrics": ab_testing
        }
    except Exception as e:
        logger.error({"event": "ab_testing_metrics_error", "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to retrieve A/B testing metrics")


@router.get("/export")
async def export_all_metrics(format: str = "json"):
    """Export all metrics for external monitoring systems"""
    try:
        metrics = get_semantic_metrics()
        exported_data = metrics.export_metrics(format)

        if format == "json":
            return json.loads(exported_data)
        else:
            return {"status": "success", "data": exported_data}
    except Exception as e:
        logger.error({"event": "export_metrics_error", "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to export metrics")


@router.get("/feature-flags")
async def get_feature_flags():
    """Get current feature flag status"""
    try:
        flag_manager = get_feature_flag_manager()
        flags = flag_manager.get_all_flags()

        return {
            "status": "success",
            "feature_flags": flags
        }
    except Exception as e:
        logger.error({"event": "feature_flags_error", "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to retrieve feature flags")


@router.post("/feature-flags/{flag_name}/update")
async def update_feature_flag(
    flag_name: str,
    status: str,
    rollout_percentage: Optional[int] = None
):
    """Update feature flag status (admin operation)"""
    try:
        # Validate status
        try:
            flag_status = FeatureFlagStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid values: {[s.value for s in FeatureFlagStatus]}"
            )

        flag_manager = get_feature_flag_manager()
        success = flag_manager.update_flag(flag_name, flag_status, rollout_percentage)

        if not success:
            raise HTTPException(status_code=404, detail=f"Feature flag '{flag_name}' not found")

        return {
            "status": "success",
            "message": f"Feature flag '{flag_name}' updated to '{status}'",
            "rollout_percentage": rollout_percentage
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error({"event": "update_feature_flag_error", "flag": flag_name, "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to update feature flag")


@router.post("/feature-flags/{flag_name}/emergency-disable")
async def emergency_disable_flag(flag_name: str, reason: str):
    """Emergency disable feature flag with audit trail"""
    try:
        flag_manager = get_feature_flag_manager()
        success = flag_manager.emergency_disable(flag_name, reason)

        if not success:
            raise HTTPException(status_code=404, detail=f"Feature flag '{flag_name}' not found")

        return {
            "status": "success",
            "message": f"Feature flag '{flag_name}' emergency disabled",
            "reason": reason
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error({"event": "emergency_disable_error", "flag": flag_name, "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to emergency disable feature flag")


@router.get("/alerts")
async def get_current_alerts():
    """Get current system alerts and warnings"""
    try:
        metrics = get_semantic_metrics()
        health = metrics.get_system_health()

        alerts = []

        # Check for high error rate
        if health.error_rate > 5.0:
            alerts.append({
                "type": "error_rate",
                "severity": "high",
                "message": f"Error rate is {health.error_rate:.1f}%, exceeding 5% threshold",
                "value": health.error_rate
            })

        # Check for slow response times
        if health.avg_response_time > 500:
            alerts.append({
                "type": "slow_response",
                "severity": "medium",
                "message": f"Average response time is {health.avg_response_time:.1f}ms, exceeding 500ms threshold",
                "value": health.avg_response_time
            })

        # Check for low semantic system usage (might indicate issues)
        if health.semantic_system_usage < 10 and health.requests_per_minute > 0:
            alerts.append({
                "type": "low_semantic_usage",
                "severity": "low",
                "message": f"Semantic system usage is only {health.semantic_system_usage:.1f}%",
                "value": health.semantic_system_usage
            })

        return {
            "status": "success",
            "alerts": alerts,
            "alert_count": len(alerts)
        }
    except Exception as e:
        logger.error({"event": "alerts_error", "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@router.get("/dashboard")
async def get_dashboard_data():
    """Get comprehensive dashboard data"""
    try:
        metrics = get_semantic_metrics()
        flag_manager = get_feature_flag_manager()

        health = metrics.get_system_health()
        accuracy = metrics.get_accuracy_metrics(60)
        ab_testing = metrics.get_a_b_testing_metrics()
        flags = flag_manager.get_all_flags()

        return {
            "status": "success",
            "dashboard": {
                "system_health": {
                    "avg_response_time_ms": health.avg_response_time,
                    "requests_per_minute": health.requests_per_minute,
                    "error_rate_percent": health.error_rate,
                    "semantic_usage_percent": health.semantic_system_usage
                },
                "accuracy": accuracy,
                "ab_testing": ab_testing,
                "feature_flags": flags,
                "timestamp": health.timestamp.isoformat()
            }
        }
    except Exception as e:
        logger.error({"event": "dashboard_error", "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")