"""
WebSocket endpoint for LangGraph integration

Provides real-time graph execution updates via WebSocket.
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Optional
import json
import uuid

# Use factory to avoid direct imports
from .orchestrator_factory import OrchestratorFactory
from src.core.logging import get_logger


logger = get_logger(__name__)


class LangGraphWebSocketEndpoint:
    """WebSocket endpoint for LangGraph real-time updates"""

    def __init__(self):
        """Initialize the WebSocket endpoint"""
        # Create LangGraph orchestrator via factory
        self.orchestrator = OrchestratorFactory.create_orchestrator(
            orchestrator_type="langgraph"
        )

    async def handle_websocket(self, websocket: WebSocket, session_id: Optional[str] = None):
        """
        Handle WebSocket connection for graph updates

        Args:
            websocket: FastAPI WebSocket connection
            session_id: Optional session ID
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        await websocket.accept()

        try:
            # Get WebSocket handler from LangGraph if available
            # NOTE: orquestador structure not implemented yet, using fallback
            # if hasattr(self.orchestrator, 'langgraph_orchestrator'):
            #     langgraph = self.orchestrator.langgraph_orchestrator
            #     if hasattr(langgraph, 'enable_websocket') and langgraph.enable_websocket:
            #         # Delegate to LangGraph WebSocket handler
            #         from ia_workspace.orquestador.langgraph.websocket.graph_websocket import graph_ws_handler
            #         await graph_ws_handler.handle_connection(websocket, session_id)
            #         return

            # Fallback: Basic WebSocket handling
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Process message
                if message.get("type") == "query":
                    query = message.get("query", "")
                    response = await self.orchestrator.process_command(
                        query=query,
                        session_id=session_id
                    )

                    # Send response
                    if hasattr(response, "model_dump"):
                        payload = response.model_dump()
                    elif hasattr(response, "dict"):
                        payload = response.dict()
                    else:
                        payload = str(response)

                    await websocket.send_json({
                        "type": "response",
                        "data": payload
                    })

                elif message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            logger.info('LangGraph websocket disconnected', extra={'session_id': session_id})
        except Exception:
            logger.exception('Unhandled error in LangGraph websocket session', extra={'session_id': session_id})
            await websocket.close()


# Global instance
langgraph_ws_endpoint = LangGraphWebSocketEndpoint()