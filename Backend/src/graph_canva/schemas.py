from __future__ import annotations

"""GraphCanva contracts and helpers kept isolated from legacy graph logic."""

import copy
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, TypeAlias

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _json_default(value: Any) -> Any:
    """Serialize datetimes while dumping payload size."""
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serialisable")


def ensure_snake_case_keys(payload: Dict[str, Any]) -> None:
    """Raise ValueError when dictionary keys are not snake_case."""

    def _walk(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(key, str) and not _SNAKE_CASE_RE.match(key):
                    location = f"{path}.{key}" if path else key
                    raise ValueError(f"Key {location!r} must be snake_case")
                _walk(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                _walk(item, f"{path}[{index}]")

    _walk(payload)


def validate_payload_size(
    payload: Dict[str, Any], limit_bytes: int = 5 * 1024 * 1024
) -> Tuple[Dict[str, Any], bool]:
    """Return a deep copy of payload and flag truncation when needed."""
    clone = copy.deepcopy(payload)
    size_bytes = len(json.dumps(clone, default=_json_default).encode("utf-8"))
    if size_bytes <= limit_bytes:
        return clone, False

    data = clone.get("data")
    if isinstance(data, dict):
        data["truncated"] = True
    else:
        clone["data"] = {"truncated": True}

    meta = clone.get("meta") if isinstance(clone.get("meta"), dict) else {}
    meta.update({"size_bytes": size_bytes, "truncated_at": limit_bytes})
    clone["meta"] = meta

    return clone, True


class GraphCanvaConnectionMeta(BaseModel):
    """Optional execution metadata for a connection arc."""

    model_config = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())

    last_status: Optional[str] = Field(default=None, alias="last_status")
    last_latency_ms: Optional[float] = Field(default=None, alias="last_latency_ms")
    last_error: Optional[str] = Field(default=None, alias="last_error")
    last_payload_sample: Optional[Dict[str, Any]] = Field(default=None, alias="last_payload_sample")


class GraphCanvaConnectionEndpoint(BaseModel):
    """Connection endpoint that maps to n8n IConnection."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    node: str
    type: str
    index: int = 0
    connection_id: Optional[str] = Field(default=None, alias="connection_id")
    meta: Optional[GraphCanvaConnectionMeta] = None


GraphCanvaConnectionMap: TypeAlias = Dict[str, Dict[str, List[GraphCanvaConnectionEndpoint]]]


class GraphCanvaViewport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pan_x: float = Field(default=0.0, alias="pan_x")
    pan_y: float = Field(default=0.0, alias="pan_y")
    zoom: float = Field(default=1.0)


class GraphCanvaGrid(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    size: int = Field(default=20)
    snap: bool = Field(default=True, alias="snap")


class GraphCanvaPanels(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    inspector_open: bool = Field(default=False, alias="inspector_open")
    execution_sidebar_mode: Literal["hidden", "summary", "detail"] = Field(
        "hidden", alias="execution_sidebar_mode"
    )
    ndv_open_node: Optional[str] = Field(default=None, alias="ndv_open_node")


class GraphCanvaSelection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nodes: List[str] = Field(default_factory=list)
    edges: List[str] = Field(default_factory=list)


class GraphCanvaAnalytics(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tidy_count: int = Field(default=0, alias="tidy_count")
    tidy_last_at: Optional[datetime] = Field(default=None, alias="tidy_last_at")


class GraphCanvaMeta(BaseModel):
    """Frontend view preferences mirrored from n8n meta."""

    model_config = ConfigDict(populate_by_name=True)

    viewport: GraphCanvaViewport = Field(default_factory=GraphCanvaViewport)
    grid: GraphCanvaGrid = Field(default_factory=GraphCanvaGrid)
    panels: GraphCanvaPanels = Field(default_factory=GraphCanvaPanels)
    selection: GraphCanvaSelection = Field(default_factory=GraphCanvaSelection)
    analytics: GraphCanvaAnalytics = Field(default_factory=GraphCanvaAnalytics)
    layout_dirty: bool = Field(default=False, alias="layout_dirty")
    data_dirty: bool = Field(default=False, alias="data_dirty")


class GraphCanvaPinItem(BaseModel):
    """Pinned execution data for a node."""

    model_config = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())

    json: Dict[str, Any] = Field(default_factory=dict)
    binary: Optional[Dict[str, Any]] = None
    paired_item: Optional[Any] = Field(default=None, alias="paired_item")


GraphCanvaPinData: TypeAlias = Dict[str, List[GraphCanvaPinItem]]


class GraphCanvaNode(BaseModel):
    """Node contract aligned with n8n INode."""

    model_config = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())

    id: str
    name: str
    type: str
    type_version: int = Field(alias="type_version")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    credentials: Optional[Dict[str, Any]] = None
    position: List[float] = Field(default_factory=lambda: [0.0, 0.0])
    disabled: bool = False
    notes: Optional[str] = None
    always_output_data: Optional[bool] = Field(default=None, alias="always_output_data")
    retry_on_fail: Optional[bool] = Field(default=None, alias="retry_on_fail")
    max_concurrency: Optional[int] = Field(default=None, alias="max_concurrency")
    hooks: Optional[Dict[str, Any]] = None
    runtime_status: Literal["idle", "running", "success", "error", "waiting"] = Field(
        "idle", alias="runtime_status"
    )
    last_run_at: Optional[datetime] = Field(default=None, alias="last_run_at")

    @field_validator("position")
    @classmethod
    def _ensure_position(cls, value: List[float]) -> List[float]:
        if len(value) != 2:
            raise ValueError("position must be [x, y]")
        return [float(value[0]), float(value[1])]


class GraphCanvaWorkflow(BaseModel):
    """Workflow payload consumed by the overview canvas."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    active: bool = False
    is_archived: bool = Field(default=False, alias="is_archived")
    nodes: List[GraphCanvaNode] = Field(default_factory=list)
    connections: GraphCanvaConnectionMap = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)
    pin_data: Optional[GraphCanvaPinData] = Field(default=None, alias="pin_data")
    meta: GraphCanvaMeta = Field(default_factory=GraphCanvaMeta)
    version_id: Optional[str] = Field(default=None, alias="version_id")
    trigger_count: int = Field(default=0, alias="trigger_count")
    tags: List[str] = Field(default_factory=list)
    shared: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="created_at")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updated_at")


class GraphCanvaWorkflowUpdate(BaseModel):
    """Patch payload accepted by the workflow endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    meta: Optional[GraphCanvaMeta] = None
    node_positions: Optional[Dict[str, List[float]]] = Field(default=None, alias="node_positions")
    pin_data: Optional[GraphCanvaPinData] = Field(default=None, alias="pin_data")

    @field_validator("node_positions")
    @classmethod
    def _ensure_node_positions(
        cls, value: Optional[Dict[str, List[float]]]
    ) -> Optional[Dict[str, List[float]]]:
        if value is None:
            return value
        for node_id, coords in value.items():
            if len(coords) != 2:
                raise ValueError(f"node {node_id!r} position must be [x, y]")
        return {node_id: [float(coords[0]), float(coords[1])] for node_id, coords in value.items()}


class GraphCanvaNodeProperty(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    display_name: Optional[str] = Field(default=None, alias="display_name")
    type: str = "string"
    description: Optional[str] = None


class GraphCanvaNodeType(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    display_name: str = Field(alias="display_name")
    group: str
    description: Optional[str] = None
    icon: Optional[str] = None
    defaults: Dict[str, Any] = Field(default_factory=dict)
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    properties: List[GraphCanvaNodeProperty] = Field(default_factory=list)
    documentation_url: Optional[str] = Field(default=None, alias="documentation_url")


class GraphCanvaCredentialType(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    display_name: str = Field(alias="display_name")
    properties: Dict[str, Any] = Field(default_factory=dict)
    icon: Optional[str] = None
    documentation_url: Optional[str] = Field(default=None, alias="documentation_url")


class GraphCanvaCatalog(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nodes: List[GraphCanvaNodeType] = Field(default_factory=list)
    credentials: List[GraphCanvaCredentialType] = Field(default_factory=list)


GraphCanvaExecutionStatus = Literal["queued", "running", "success", "error", "cancelled"]


class GraphCanvaExecution(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    execution_id: str = Field(alias="execution_id")
    workflow_id: str = Field(alias="workflow_id")
    status: GraphCanvaExecutionStatus = Field(default="queued")
    started_at: Optional[datetime] = Field(default=None, alias="started_at")
    finished_at: Optional[datetime] = Field(default=None, alias="finished_at")
    duration_ms: Optional[int] = Field(default=None, alias="duration_ms")
    error: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)


class GraphCanvaExecutionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal["manual", "scheduled", "webhook"] = Field(default="manual")
    session_id: Optional[str] = Field(default=None, alias="session_id")
    payload: Dict[str, Any] = Field(default_factory=dict)


class GraphCanvaPushMessage(BaseModel):
    """Base push envelope for the overview canvas stream."""

    model_config = ConfigDict(populate_by_name=True)

    type: str
    execution_id: str = Field(alias="execution_id")
    workflow_id: str = Field(alias="workflow_id")
    emitted_at: datetime = Field(default_factory=datetime.utcnow, alias="emitted_at")
    data: Dict[str, Any] = Field(default_factory=dict)


class GraphCanvaExecutionStarted(GraphCanvaPushMessage):
    type: Literal["execution_started"] = Field(default="execution_started")
    mode: Literal["manual", "scheduled", "webhook"] = Field(default="manual")


class GraphCanvaExecutionFinished(GraphCanvaPushMessage):
    type: Literal["execution_finished"] = Field(default="execution_finished")
    status: GraphCanvaExecutionStatus = Field(default="success")
    error: Optional[str] = None


class GraphCanvaNodeExecuteBefore(GraphCanvaPushMessage):
    type: Literal["node_execute_before"] = Field(default="node_execute_before")
    node_name: str = Field(alias="node_name")


class GraphCanvaNodeExecuteAfter(GraphCanvaPushMessage):
    type: Literal["node_execute_after"] = Field(default="node_execute_after")
    node_name: str = Field(alias="node_name")
    status: GraphCanvaExecutionStatus = Field(default="success")


class GraphCanvaNodeExecuteAfterData(GraphCanvaPushMessage):
    type: Literal["node_execute_after_data"] = Field(default="node_execute_after_data")
    node_name: str = Field(alias="node_name")


__all__ = [
    "ensure_snake_case_keys",
    "validate_payload_size",
    "GraphCanvaConnectionMeta",
    "GraphCanvaConnectionEndpoint",
    "GraphCanvaConnectionMap",
    "GraphCanvaViewport",
    "GraphCanvaGrid",
    "GraphCanvaPanels",
    "GraphCanvaSelection",
    "GraphCanvaAnalytics",
    "GraphCanvaMeta",
    "GraphCanvaPinItem",
    "GraphCanvaPinData",
    "GraphCanvaNode",
    "GraphCanvaWorkflow",
    "GraphCanvaWorkflowUpdate",
    "GraphCanvaNodeType",
    "GraphCanvaCredentialType",
    "GraphCanvaCatalog",
    "GraphCanvaExecution",
    "GraphCanvaExecutionRequest",
    "GraphCanvaPushMessage",
    "GraphCanvaExecutionStarted",
    "GraphCanvaExecutionFinished",
    "GraphCanvaNodeExecuteBefore",
    "GraphCanvaNodeExecuteAfter",
    "GraphCanvaNodeExecuteAfterData",
]


