from __future__ import annotations

"""Service layer for the GraphCanva overview graph."""

import asyncio
from typing import List, Optional

from .push import (
    GraphCanvaPushGateway,
    build_execution_finished,
    build_execution_started,
    build_node_after,
    build_node_after_data,
    build_node_before,
    gateway,
)
from .repository import GraphCanvaRepository, repository
from .schemas import (
    GraphCanvaCatalog,
    GraphCanvaExecution,
    GraphCanvaExecutionRequest,
    GraphCanvaNode,
    GraphCanvaWorkflow,
    GraphCanvaWorkflowUpdate,
)


class GraphCanvaError(RuntimeError):
    """Base error for the GraphCanva subsystem."""


class GraphCanvaNotFound(GraphCanvaError):
    """Raised when a requested resource is missing."""


class GraphCanvaService:
    """Coordinates repository access and WebSocket friendly workflow simulation."""

    def __init__(
        self,
        repo: GraphCanvaRepository = repository,
        push_gateway: GraphCanvaPushGateway = gateway,
    ) -> None:
        self._repo = repo
        self._push = push_gateway

    def get_workflow(self, workflow_id: str) -> GraphCanvaWorkflow:
        try:
            return self._repo.get_workflow(workflow_id)
        except KeyError as exc:
            raise GraphCanvaNotFound(f"Workflow {workflow_id!r} not found") from exc

    def update_workflow(
        self, workflow_id: str, update: GraphCanvaWorkflowUpdate
    ) -> GraphCanvaWorkflow:
        try:
            return self._repo.patch_workflow(workflow_id, update)
        except KeyError as exc:
            raise GraphCanvaNotFound(f"Workflow {workflow_id!r} not found") from exc

    def list_workflows(self) -> List[GraphCanvaWorkflow]:
        return self._repo.list_workflows()

    def get_catalog(self) -> GraphCanvaCatalog:
        return self._repo.get_catalog()

    async def run_workflow(
        self, workflow_id: str, request: GraphCanvaExecutionRequest
    ) -> GraphCanvaExecution:
        try:
            workflow = self._repo.get_workflow(workflow_id)
            execution = self._repo.create_execution(workflow_id, request)
        except KeyError as exc:
            raise GraphCanvaNotFound(f"Workflow {workflow_id!r} not found") from exc

        await self._push.emit(
            workflow_id,
            build_execution_started(
                execution_id=execution.execution_id,
                workflow_id=workflow_id,
                mode=request.mode or "manual",
            ),
        )

        # Simulate sequential node lifecycle events.
        for index, node in enumerate(workflow.nodes):
            await self._emit_node_sequence(workflow_id, execution.execution_id, node, index)

        summary = {
            "started_at": execution.started_at,
            "completed_nodes": [node.id for node in workflow.nodes],
            "metrics": {"duration_ms": 420},
        }
        execution = self._repo.finalize_execution(
            execution.execution_id,
            status="success",
            summary={**execution.summary, **summary},
        )

        await self._push.emit(
            workflow_id,
            build_execution_finished(
                execution_id=execution.execution_id,
                workflow_id=workflow_id,
                status=execution.status,
                data=summary,
            ),
        )
        return execution

    async def _emit_node_sequence(
        self,
        workflow_id: str,
        execution_id: str,
        node: GraphCanvaNode,
        index: int,
    ) -> None:
        await self._push.emit(
            workflow_id,
            build_node_before(
                execution_id=execution_id,
                workflow_id=workflow_id,
                node_name=node.name,
            ),
        )
        await asyncio.sleep(0)
        await self._push.emit(
            workflow_id,
            build_node_after(
                execution_id=execution_id,
                workflow_id=workflow_id,
                node_name=node.name,
                status="success",
            ),
        )
        await self._push.emit(
            workflow_id,
            build_node_after_data(
                execution_id=execution_id,
                workflow_id=workflow_id,
                node_name=node.name,
                data={
                    "items": index + 1,
                    "preview": node.parameters,
                },
            ),
        )

    def get_execution(self, execution_id: str) -> GraphCanvaExecution:
        try:
            return self._repo.get_execution(execution_id)
        except KeyError as exc:
            raise GraphCanvaNotFound(f"Execution {execution_id!r} not found") from exc

    def list_executions(self, workflow_id: Optional[str] = None) -> List[GraphCanvaExecution]:
        return self._repo.list_executions(workflow_id)


service = GraphCanvaService()
