from __future__ import annotations

"""FastAPI router exposing the isolated GraphCanva overview APIs."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .service import GraphCanvaNotFound, GraphCanvaService, service
from .schemas import (
    GraphCanvaCatalog,
    GraphCanvaExecution,
    GraphCanvaExecutionRequest,
    GraphCanvaWorkflow,
    GraphCanvaWorkflowUpdate,
)


def get_service() -> GraphCanvaService:
    """Dependency returning the shared GraphCanvaService instance."""

    return service


router = APIRouter(prefix="/api/graph-canva", tags=["graph-canva"])


@router.get(
    "/workflows/{workflow_id}",
    response_model=GraphCanvaWorkflow,
    summary="Retrieve a GraphCanva workflow",
)
async def get_workflow(workflow_id: str, svc: GraphCanvaService = Depends(get_service)) -> GraphCanvaWorkflow:
    """Return the workflow DTO consumed by the overview canvas."""

    try:
        return svc.get_workflow(workflow_id)
    except GraphCanvaNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/workflows",
    response_model=list[GraphCanvaWorkflow],
    summary="List available GraphCanva workflows",
)
async def list_workflows(svc: GraphCanvaService = Depends(get_service)) -> list[GraphCanvaWorkflow]:
    return svc.list_workflows()


@router.patch(
    "/workflows/{workflow_id}",
    response_model=GraphCanvaWorkflow,
    summary="Persist layout/meta changes for a workflow",
)
async def patch_workflow(
    workflow_id: str,
    patch: GraphCanvaWorkflowUpdate,
    svc: GraphCanvaService = Depends(get_service),
) -> GraphCanvaWorkflow:
    """Update workflow metadata, pinned data or node positions."""

    try:
        return svc.update_workflow(workflow_id, patch)
    except GraphCanvaNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/workflows/{workflow_id}/run",
    response_model=GraphCanvaExecution,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a simulated workflow run",
)
async def run_workflow(
    workflow_id: str,
    request: GraphCanvaExecutionRequest,
    svc: GraphCanvaService = Depends(get_service),
) -> GraphCanvaExecution:
    """Queue an execution and immediately simulate its completion for the overview canvas."""

    try:
        return await svc.run_workflow(workflow_id, request)
    except GraphCanvaNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/executions/{execution_id}",
    response_model=GraphCanvaExecution,
    summary="Inspect a simulated execution",
)
async def get_execution(
    execution_id: str,
    svc: GraphCanvaService = Depends(get_service),
) -> GraphCanvaExecution:
    try:
        return svc.get_execution(execution_id)
    except GraphCanvaNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/workflows/{workflow_id}/executions",
    response_model=list[GraphCanvaExecution],
    summary="List executions for a workflow",
)
async def list_executions(
    workflow_id: str,
    limit: Optional[int] = Query(default=10, ge=1, le=100),
    svc: GraphCanvaService = Depends(get_service),
) -> list[GraphCanvaExecution]:
    executions = svc.list_executions(workflow_id)
    return executions[: limit or len(executions)]


@router.get(
    "/catalog",
    response_model=GraphCanvaCatalog,
    summary="Retrieve the node and credential catalog",
)
async def get_catalog(svc: GraphCanvaService = Depends(get_service)) -> GraphCanvaCatalog:
    return svc.get_catalog()


__all__ = ["router", "get_service"]
