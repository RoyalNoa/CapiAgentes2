from __future__ import annotations

"""In-memory repository for GraphCanva workflows and executions."""

import secrets
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from .schemas import (
    GraphCanvaCatalog,
    GraphCanvaCredentialType,
    GraphCanvaExecution,
    GraphCanvaExecutionRequest,
    GraphCanvaNode,
    GraphCanvaNodeType,
    GraphCanvaPinData,
    GraphCanvaWorkflow,
    GraphCanvaWorkflowUpdate,
)
DEFAULT_WORKFLOW_ID = "graph-canva-demo"


def _build_sample_workflow() -> GraphCanvaWorkflow:
    timestamp = datetime.utcnow()
    nodes = [
        {
            "id": "start",
            "name": "Start",
            "type": "capi.start",
            "type_version": 1,
            "parameters": {"trigger": "manual"},
            "position": [-280.0, 0.0],
            "always_output_data": True,
            "runtime_status": "idle",
        },
        {
            "id": "ingest",
            "name": "Collect Signals",
            "type": "capi.workspace.fetch",
            "type_version": 2,
            "parameters": {"source": "workspace", "limit": 20},
            "position": [-40.0, -40.0],
            "runtime_status": "idle",
        },
        {
            "id": "analyze",
            "name": "Analyze Impact",
            "type": "capi.llm.analyze",
            "type_version": 1,
            "parameters": {"model": "gpt-4o-mini", "prompt": "Summarize revenue impact"},
            "position": [220.0, -20.0],
            "runtime_status": "idle",
        },
        {
            "id": "report",
            "name": "Prepare Briefing",
            "type": "capi.output.briefing",
            "type_version": 1,
            "parameters": {"channel": "slack"},
            "position": [460.0, 60.0],
            "runtime_status": "idle",
        },
    ]
    connections = {
        "main": {
            "start": [
                {"node": "ingest", "type": "main", "index": 0},
            ],
            "ingest": [
                {"node": "analyze", "type": "main", "index": 0},
            ],
            "analyze": [
                {"node": "report", "type": "main", "index": 0},
            ],
        }
    }
    meta = {
        "viewport": {"pan_x": -120.0, "pan_y": -40.0, "zoom": 0.9},
        "grid": {"size": 24, "snap": True},
        "panels": {"inspector_open": True, "execution_sidebar_mode": "summary", "ndv_open_node": None},
        "selection": {"nodes": [], "edges": []},
        "analytics": {"tidy_count": 3, "tidy_last_at": timestamp},
        "layout_dirty": False,
        "data_dirty": False,
    }
    return GraphCanvaWorkflow.model_validate(
        {
            "id": DEFAULT_WORKFLOW_ID,
            "name": "Revenue Insights Overview",
            "active": True,
            "nodes": nodes,
            "connections": connections,
            "settings": {"execution_order": "sequential"},
            "meta": meta,
            "version_id": "v1.0.0",
            "trigger_count": 12,
            "tags": ["overview", "demo"],
            "permissions": [],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )


def _build_catalog() -> GraphCanvaCatalog:
    return GraphCanvaCatalog(
        nodes=[
            GraphCanvaNodeType(
                name="capi.start",
                display_name="Start",
                group="system",
                description="Manual trigger to kickoff a workflow run.",
                icon="play",
                inputs=[],
                outputs=["main"],
                defaults={"name": "Start"},
            ),
            GraphCanvaNodeType(
                name="capi.workspace.fetch",
                display_name="Collect Signals",
                group="workspace",
                description="Reads workspace documents and aggregates signals.",
                icon="database",
                inputs=["main"],
                outputs=["main"],
                defaults={"name": "Collect Signals"},
                properties=[],
            ),
            GraphCanvaNodeType(
                name="capi.llm.analyze",
                display_name="Analyze Impact",
                group="ai",
                description="LLM agent that transforms data into insights.",
                icon="sparkles",
                inputs=["main"],
                outputs=["main"],
                defaults={"name": "Analyze Impact"},
            ),
            GraphCanvaNodeType(
                name="capi.output.briefing",
                display_name="Prepare Briefing",
                group="output",
                description="Publishes the executive briefing to the selected channel.",
                icon="presentation-chart",
                inputs=["main"],
                outputs=[],
                defaults={"name": "Prepare Briefing"},
            ),
        ],
        credentials=[
            GraphCanvaCredentialType(
                name="slackApi",
                display_name="Slack API Token",
                properties={"fields": ["token"]},
                icon="slack",
            )
        ],
    )


class GraphCanvaRepository:
    """Simple in-memory backing store for the overview graph."""

    def __init__(self) -> None:
        self._workflows: Dict[str, GraphCanvaWorkflow] = {}
        self._executions: Dict[str, GraphCanvaExecution] = {}
        self._catalog: GraphCanvaCatalog = _build_catalog()
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        workflow = _build_sample_workflow()
        self._workflows[workflow.id] = workflow

    def list_workflows(self) -> List[GraphCanvaWorkflow]:
        return list(self._workflows.values())

    def get_workflow(self, workflow_id: str) -> GraphCanvaWorkflow:
        if workflow_id not in self._workflows:
            raise KeyError(workflow_id)
        return self._workflows[workflow_id]

    def save_workflow(self, workflow: GraphCanvaWorkflow) -> GraphCanvaWorkflow:
        workflow = workflow.model_copy(update={"updated_at": datetime.utcnow()})
        self._workflows[workflow.id] = workflow
        return workflow

    def patch_workflow(self, workflow_id: str, update: GraphCanvaWorkflowUpdate) -> GraphCanvaWorkflow:
        workflow = self.get_workflow(workflow_id)
        updates: Dict[str, Any] = {}
        if update.meta is not None:
            updates["meta"] = update.meta
        if update.pin_data is not None:
            updates["pin_data"] = update.pin_data
        if update.node_positions:
            updated_nodes: List[GraphCanvaNode] = []
            for node in workflow.nodes:
                if node.id in update.node_positions:
                    updated_nodes.append(node.model_copy(update={"position": update.node_positions[node.id]}))
                else:
                    updated_nodes.append(node)
            updates["nodes"] = updated_nodes
        if updates:
            updates["updated_at"] = datetime.utcnow()
            workflow = workflow.model_copy(update=updates)
            self._workflows[workflow_id] = workflow
        return workflow

    def upsert_pin_data(self, workflow_id: str, pin_data: GraphCanvaPinData) -> GraphCanvaWorkflow:
        workflow = self.get_workflow(workflow_id)
        workflow = workflow.model_copy(
            update={"pin_data": pin_data, "updated_at": datetime.utcnow()}
        )
        self._workflows[workflow_id] = workflow
        return workflow

    def create_execution(
        self, workflow_id: str, request: GraphCanvaExecutionRequest
    ) -> GraphCanvaExecution:
        if workflow_id not in self._workflows:
            raise KeyError(workflow_id)
        execution_id = secrets.token_hex(8)
        now = datetime.utcnow()
        execution = GraphCanvaExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status="running",
            started_at=now,
            summary={
                "mode": request.mode,
                "session_id": request.session_id,
                "input_payload": request.payload,
            },
        )
        self._executions[execution_id] = execution
        return execution

    def finalize_execution(
        self,
        execution_id: str,
        *,
        status: Literal["success", "error", "cancelled"] = "success",
        error: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
    ) -> GraphCanvaExecution:
        if execution_id not in self._executions:
            raise KeyError(execution_id)
        execution = self._executions[execution_id]
        finished_at = datetime.utcnow()
        duration_ms = (
            int((finished_at - execution.started_at).total_seconds() * 1000)
            if execution.started_at
            else None
        )
        execution = execution.model_copy(
            update={
                "status": status,
                "error": error,
                "finished_at": finished_at,
                "duration_ms": duration_ms,
                "summary": summary or execution.summary,
            }
        )
        self._executions[execution_id] = execution
        return execution

    def get_execution(self, execution_id: str) -> GraphCanvaExecution:
        if execution_id not in self._executions:
            raise KeyError(execution_id)
        return self._executions[execution_id]

    def list_executions(self, workflow_id: Optional[str] = None) -> List[GraphCanvaExecution]:
        executions = list(self._executions.values())
        if workflow_id:
            executions = [item for item in executions if item.workflow_id == workflow_id]
        return sorted(executions, key=lambda item: item.started_at or datetime.min, reverse=True)

    def get_catalog(self) -> GraphCanvaCatalog:
        return self._catalog


repository = GraphCanvaRepository()


