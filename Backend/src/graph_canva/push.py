from __future__ import annotations

"""WebSocket push gateway for GraphCanva overview events."""

import asyncio
from collections import defaultdict
from typing import Dict, List

from starlette.websockets import WebSocket, WebSocketDisconnect

from .schemas import (
    GraphCanvaExecutionFinished,
    GraphCanvaExecutionStarted,
    GraphCanvaNodeExecuteAfter,
    GraphCanvaNodeExecuteAfterData,
    GraphCanvaNodeExecuteBefore,
    GraphCanvaPushMessage,
    validate_payload_size,
)


class GraphCanvaPushGateway:
    """Broadcasts GraphCanva push messages to subscribed clients."""

    def __init__(self) -> None:
        self._connections: Dict[str, List[WebSocket]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def register(self, workflow_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[workflow_id].append(websocket)

    async def unregister(self, workflow_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if workflow_id in self._connections and websocket in self._connections[workflow_id]:
                self._connections[workflow_id].remove(websocket)
            if workflow_id in self._connections and not self._connections[workflow_id]:
                del self._connections[workflow_id]

    async def emit(self, workflow_id: str, message: GraphCanvaPushMessage) -> None:
        payload, truncated = validate_payload_size(message.model_dump(by_alias=True))
        payload.setdefault("meta", {})
        payload["meta"]["truncated"] = truncated
        async with self._lock:
            targets = list(self._connections.get(workflow_id, []))
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except WebSocketDisconnect:
                await self.unregister(workflow_id, websocket)


def build_execution_started(**kwargs) -> GraphCanvaExecutionStarted:
    return GraphCanvaExecutionStarted(**kwargs)


def build_execution_finished(**kwargs) -> GraphCanvaExecutionFinished:
    return GraphCanvaExecutionFinished(**kwargs)


def build_node_before(**kwargs) -> GraphCanvaNodeExecuteBefore:
    return GraphCanvaNodeExecuteBefore(**kwargs)


def build_node_after(**kwargs) -> GraphCanvaNodeExecuteAfter:
    return GraphCanvaNodeExecuteAfter(**kwargs)


def build_node_after_data(**kwargs) -> GraphCanvaNodeExecuteAfterData:
    return GraphCanvaNodeExecuteAfterData(**kwargs)


gateway = GraphCanvaPushGateway()

__all__ = [
    "GraphCanvaPushGateway",
    "gateway",
    "build_execution_started",
    "build_execution_finished",
    "build_node_before",
    "build_node_after",
    "build_node_after_data",
]
