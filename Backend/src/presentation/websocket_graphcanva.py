from __future__ import annotations

"""WebSocket endpoint for GraphCanva overview push events."""

from fastapi import APIRouter, Depends, WebSocket
from starlette.websockets import WebSocketDisconnect

from src.graph_canva.push import GraphCanvaPushGateway, gateway


router = APIRouter()


def get_gateway() -> GraphCanvaPushGateway:
    return gateway


@router.websocket("/ws/graph-canva/{workflow_id}")
async def websocket_graph_canva(
    websocket: WebSocket,
    workflow_id: str,
    push_gateway: GraphCanvaPushGateway = Depends(get_gateway),
) -> None:
    await push_gateway.register(workflow_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await push_gateway.unregister(workflow_id, websocket)


__all__ = ["router", "get_gateway"]
