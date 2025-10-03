"""
CapiAgentes Historical Alerts API Endpoints
Professional REST API for Historical Alerts Management
Author: Claude Code Expert
"""

from typing import List, Optional, Dict, Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ..infrastructure.database.postgres_client import (
    get_postgres_client,
    PostgreSQLClient,
    AlertPriority,
    AlertStatus
)
from ..core.exceptions import DatabaseError

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/alerts", tags=["Historical Alerts"])

# Pydantic models

class AlertBranchInfo(BaseModel):
    sucursal_id: str
    nombre: Optional[str] = None
    saldo_total: Optional[float] = None
    caja_teorica: Optional[float] = None
    saldo_cobertura_pct: Optional[float] = Field(None, description="Cobertura porcentual respecto a la caja teorica")


class AlertDeviceInfo(BaseModel):
    dispositivo_id: str
    tipo: Optional[str] = None
    saldo_total: Optional[float] = None
    caja_teorica: Optional[float] = None
    saldo_cobertura_pct: Optional[float] = Field(None, description="Cobertura porcentual respecto a la capacidad del dispositivo")
    latitud: Optional[float] = None
    longitud: Optional[float] = None


class AlertSummaryResponse(BaseModel):
    id: str
    alert_code: str
    timestamp: datetime
    title: str
    priority: str
    status: str
    financial_impact: Optional[float] = None
    currency: str = "USD"
    confidence_score: Optional[float] = None
    pending_tasks: int = 0
    affected_entities: List[Dict[str, Any]] = []
    sucursal: Optional[AlertBranchInfo] = None
    dispositivo: Optional[AlertDeviceInfo] = None

class AlertDetailResponse(BaseModel):
    id: str
    alert_code: str
    timestamp: datetime
    alert_type: str
    priority: str
    agent_source: str
    title: str
    description: Optional[str] = None
    financial_impact: Optional[float] = None
    currency: str = "USD"
    confidence_score: Optional[float] = None
    status: str
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # AI Analysis data
    root_cause: Optional[str] = None
    probability_fraud: Optional[float] = None
    probability_system_error: Optional[float] = None
    similar_incidents_count: Optional[int] = None
    trend_analysis: Optional[str] = None
    risk_assessment: Optional[str] = None
    confidence_level: Optional[float] = None
    model_version: Optional[str] = None

    # Related data
    affected_entities: List[Dict[str, Any]] = []
    sucursal: Optional[AlertBranchInfo] = None
    dispositivo: Optional[AlertDeviceInfo] = None
    human_tasks: List[Dict[str, Any]] = []

class TeamWorkloadResponse(BaseModel):
    team_name: str
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    avg_progress: float

class CriticalAlertsSummaryResponse(BaseModel):
    total_critical: int
    total_financial_impact: float
    avg_confidence: float
    high_fraud_risk: int

class TaskProgressUpdate(BaseModel):
    progress_percentage: int = Field(..., ge=0, le=100)
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|blocked)$")
    completion_notes: Optional[str] = None

class AlertStatusUpdateRequest(BaseModel):
    status: Literal['pending', 'accepted', 'rejected'] = Field(..., description="Human gate decision for this alert")
    reason: Optional[str] = Field(None, description="Optional explanation for auditing")
    actor: Optional[str] = Field(None, description="Operator responsible for the decision")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata related to the decision")

UI_STATUS_TO_DB_STATUS: Dict[str, str] = {
    'pending': 'abierta',
    'accepted': 'resuelta',
    'rejected': 'silenciada',
}
class SearchResponse(BaseModel):
    id: str
    alert_code: str
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    timestamp: datetime
    financial_impact: Optional[float] = None
    relevance_score: float

# Dependency injection
async def get_db_client() -> PostgreSQLClient:
    """Get database client dependency"""
    return get_postgres_client()

# API Endpoints

@router.patch(
    "/{alert_id}/status",
    summary="Update Alert Status",
    description="Persist a human gate decision for an alert"
)
async def update_alert_status_endpoint(
    alert_id: str = Path(..., description="The identifier of the alert"),
    payload: AlertStatusUpdateRequest = ...,
    db: PostgreSQLClient = Depends(get_db_client)
) -> Dict[str, Any]:
    """Update alert status in persistence layer."""

    target_status = UI_STATUS_TO_DB_STATUS.get(payload.status)
    if not target_status:
        raise HTTPException(status_code=400, detail="Unsupported status value")

    try:
        updated = await db.update_alert_status(
            alert_id=alert_id,
            new_status=target_status,
            actor=payload.actor,
            reason=payload.reason,
            metadata=payload.metadata
        )
    except DatabaseError as e:
        logger.error(
            f"Database error updating alert {alert_id} status: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(
            f"Unexpected error updating alert {alert_id} status: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    if not updated:
        raise HTTPException(status_code=404, detail="Alert not found")

    logger.info(
        "Alert status updated via API",
        extra={
            "alert_id": alert_id,
            "status": payload.status,
            "stored_status": target_status,
            "actor": payload.actor,
        }
    )

    return {
        "alert_id": alert_id,
        "status": payload.status,
        "stored_status": target_status,
        "reason": payload.reason,
    }

@router.get(
    "/",
    response_model=List[AlertSummaryResponse],
    summary="Get Historical Alerts",
    description="Retrieve historical alerts with filtering and pagination"
)
async def get_historical_alerts(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of alerts to return"),
    offset: int = Query(0, ge=0, description="Number of alerts to skip"),
    status: Optional[str] = Query(None, description="Filter by status (active, in_progress, resolved)"),
    priority: Optional[str] = Query(None, description="Filter by priority (low, medium, high, critical)"),
    agent: Optional[str] = Query(None, description="Filter by agent source"),
    db: PostgreSQLClient = Depends(get_db_client)
) -> List[AlertSummaryResponse]:
    """Get historical alerts with optional filters"""
    try:
        alerts = await db.get_historical_alerts(
            limit=limit,
            offset=offset,
            status_filter=status,
            priority_filter=priority,
            agent_filter=agent
        )

        return [AlertSummaryResponse(**alert) for alert in alerts]

    except DatabaseError as e:
        logger.error(f"Database error retrieving alerts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error retrieving alerts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "/{alert_id}",
    response_model=AlertDetailResponse,
    summary="Get Alert Details",
    description="Retrieve detailed information for a specific alert including AI analysis and tasks"
)
async def get_alert_details(
    alert_id: str = Path(..., description="The identifier of the alert"),
    db: PostgreSQLClient = Depends(get_db_client)
) -> AlertDetailResponse:
    """Get detailed information for a specific alert"""
    try:
        alert = await db.get_alert_by_id(alert_id)

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        return AlertDetailResponse(**alert)

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Database error retrieving alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error retrieving alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "/search",
    response_model=List[SearchResponse],
    summary="Search Alerts",
    description="Full-text search across alert titles and descriptions"
)
async def search_alerts(
    q: str = Query(..., min_length=3, description="Search query (minimum 3 characters)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: PostgreSQLClient = Depends(get_db_client)
) -> List[SearchResponse]:
    """Search alerts using full-text search"""
    try:
        results = await db.search_alerts(search_term=q, limit=limit)

        return [SearchResponse(**result) for result in results]

    except DatabaseError as e:
        logger.error(f"Database error searching alerts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error searching alerts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "/summary/critical",
    response_model=CriticalAlertsSummaryResponse,
    summary="Critical Alerts Summary",
    description="Get summary statistics for critical active alerts"
)
async def get_critical_alerts_summary(
    db: PostgreSQLClient = Depends(get_db_client)
) -> CriticalAlertsSummaryResponse:
    """Get summary of critical alerts"""
    try:
        summary = await db.get_critical_alerts_summary()

        return CriticalAlertsSummaryResponse(**summary)

    except DatabaseError as e:
        logger.error(f"Database error retrieving critical alerts summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error retrieving critical alerts summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "/teams/workload",
    response_model=List[TeamWorkloadResponse],
    summary="Team Workload",
    description="Get current workload distribution across teams"
)
async def get_team_workload(
    db: PostgreSQLClient = Depends(get_db_client)
) -> List[TeamWorkloadResponse]:
    """Get team workload statistics"""
    try:
        workload = await db.get_team_workload()

        return [TeamWorkloadResponse(**team) for team in workload]

    except DatabaseError as e:
        logger.error(f"Database error retrieving team workload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error retrieving team workload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put(
    "/tasks/{task_id}/progress",
    summary="Update Task Progress",
    description="Update progress and status of a specific task"
)
async def update_task_progress(
    task_id: str = Path(..., description="The UUID of the task"),
    progress_update: TaskProgressUpdate = ...,
    db: PostgreSQLClient = Depends(get_db_client)
) -> Dict[str, Any]:
    """Update task progress"""
    try:
        success = await db.update_task_progress(
            task_id=task_id,
            progress_percentage=progress_update.progress_percentage,
            status=progress_update.status,
            completion_notes=progress_update.completion_notes
        )

        if not success:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "message": "Task progress updated successfully",
            "task_id": task_id,
            "progress": progress_update.progress_percentage
        }

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Database error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "/health",
    summary="Database Health Check",
    description="Check database connectivity and performance"
)
async def database_health_check(
    db: PostgreSQLClient = Depends(get_db_client)
) -> Dict[str, Any]:
    """Check database health"""
    try:
        # Simple health check query
        async with db.get_connection() as conn:
            result = await conn.fetchval('SELECT COUNT(*) FROM alerts.historical_alerts')

        return {
            "status": "healthy",
            "database": "postgresql",
            "total_alerts": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")

# Context sharing endpoint for AI integration
@router.get(
    "/{alert_id}/ai-context",
    summary="Get AI Context",
    description="Get formatted context for AI analysis and chat integration"
)
async def get_alert_ai_context(
    alert_id: str = Path(..., description="The identifier of the alert"),
    db: PostgreSQLClient = Depends(get_db_client)
) -> Dict[str, Any]:
    """Get AI-optimized context for an alert"""
    try:
        alert = await db.get_alert_by_id(alert_id)

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Format context for AI consumption
        ai_context = {
            "alert_summary": {
                "code": alert.get("alert_code"),
                "title": alert.get("title"),
                "priority": alert.get("priority"),
                "financial_impact": alert.get("financial_impact"),
                "confidence": alert.get("confidence_score")
            },
            "ai_analysis": {
                "root_cause": alert.get("root_cause"),
                "fraud_probability": alert.get("probability_fraud"),
                "trend_analysis": alert.get("trend_analysis"),
                "risk_assessment": alert.get("risk_assessment")
            },
            "operational_context": {
                "affected_entities": alert.get("affected_entities", []),
                "pending_tasks": len([t for t in alert.get("human_tasks", []) if t.get("status") == "pending"]),
                "status": alert.get("status"),
                "datos_clave": alert.get("datos_clave", [])
            },
            "recommended_actions": [
                {
                    "title": task.get("task_title"),
                    "description": task.get("task_description"),
                    "priority": task.get("priority"),
                    "team": task.get("assigned_to_team"),
                    "status": task.get("status"),
                    "progress": task.get("progress_percentage", 0)
                }
                for task in alert.get("human_tasks", [])
            ]
        }

        return ai_context

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Database error retrieving AI context for alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error retrieving AI context for alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

