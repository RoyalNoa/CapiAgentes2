#!/usr/bin/env python3
"""
CAPI - Backend API Server (Main Entry Point)
==========================================
Ruta: /Backend/src/api/main.py
DescripciÃ³n: Servidor principal FastAPI con WebSocket que expone el Orquestador
LangGraph como orquestador Ãºnico para interacciÃ³n basada en chat y gestiÃ³n de agentes.
Estado: âœ… CORE ACTIVO - Servidor principal de producciÃ³n
Dependencias: FastAPI, WebSocket, LangGraph, Orchestrator
CaracterÃ­sticas: CORS, logging centralizado, gestiÃ³n agentes, chat en tiempo real
Endpoints: /api/*, /ws, /health, /status
Puerto: 8000 (configurable)
"""

from __future__ import annotations

from dataclasses import asdict

import json
import os
import locale
import sys
import asyncio
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

# Set UTF-8 encoding for Python output
if sys.platform.startswith('win'):
    # Windows-specific UTF-8 configuration
    try:
        # Set console code page to UTF-8
        os.system('chcp 65001 > nul')
        # Set locale to UTF-8
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except:
            pass
    
    # Force UTF-8 for stdout/stderr
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from ia_workspace.agentes.capi_datab.handler import CapiDataBAgent
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Cargar variables de entorno del archivo .env (normalizado UTF-8)
try:
    load_dotenv()
except UnicodeDecodeError:
    # Fallback puntual si accidentalmente se guarda con BOM u otra codificaciÃ³n
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            load_dotenv(encoding=enc)
            # Will log properly after logger is initialized
            break
        except UnicodeDecodeError:
            continue

# Agregar el directorio backend al path para imports
backend_dir = Path(__file__).parent.parent.parent  # Ir a la raÃ­z del backend
sys.path.insert(0, str(backend_dir))

# Import orchestrator through factory to maintain unidirectional dependency
from src.presentation.orchestrator_factory import OrchestratorFactory

from src.core.file_config import get_available_data_files, get_default_data_file
from src.domain.agents.agent_models import ResponseEnvelope
# from src.api.workspace_endpoints import router as workspace_router  # Commented out - depends on agents module
from src.core.logging import get_logger
from src.domain.contracts.intent import Intent
from src.core.semantics.intent_service import SemanticIntentService

# Import WebSocket event broadcaster for agent lifecycle events
from src.infrastructure.websocket import get_event_broadcaster
from src.observability.agent_metrics import record_feedback_event

from src.voice.manager import VoiceOrchestrator
from src.voice.settings import VoiceSettings
from src.voice import metrics as voice_metrics

# Logger configurado automÃ¡ticamente por sistema unificado
logger = get_logger(__name__)
logger_msg = "Using Unified LangGraph Orchestrator"

# Use LangGraph orchestrator from factory


def _sanitize_for_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(v) for v in value]
    if isinstance(value, set):
        return [_sanitize_for_json(v) for v in value]
    if isinstance(value, Decimal):
        try:
            return float(value)
        except Exception:
            return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value

app = FastAPI(title="CapiAgentes Chat Server")
app.state.start_time = datetime.now()

# Global event broadcaster instance
event_broadcaster = get_event_broadcaster()

# --- CORS middleware para permitir peticiones desde el frontend ---
# --- CORS dinÃ¡mico (incluye puertos de desarrollo adicionales) ---
_default_origins = (
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:3001,http://127.0.0.1:3001,"
    "http://localhost:3002,http://127.0.0.1:3002,"
    "http://localhost:3004,http://127.0.0.1:3004"
)

_raw_origins = os.getenv("BACKEND_CORS_ORIGINS") or "".join(_default_origins)

_allowed_origins = [o.strip() for o in _raw_origins.split(',') if o.strip()]
logger.info(f"[CORS] OrÃ­genes permitidos ({len(_allowed_origins)} configurados): {', '.join(_allowed_origins[:3])}{'...' if len(_allowed_origins) > 3 else ''}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include workspace router
# app.include_router(workspace_router)  # Commented out - workspace router not available

# Agents management router for PantallaAgentes
try:
    from src.api.agents_endpoints import router as agents_router
    app.include_router(agents_router)
    logger.info("Agents management router loaded successfully")
except ImportError as e:
    logger.warning(f"Agents router not available: {e}")

# Google integrations router
try:
    from src.api.google_endpoints import router as google_router
    app.include_router(google_router)
    logger.info("Google integrations router loaded successfully")
except ImportError as e:
    logger.warning(f"Google router not available: {e}")

# Historical Alerts Router
try:
    from src.api.alerts_endpoints import router as alerts_router
    app.include_router(alerts_router)
    logger.info("Historical alerts router loaded successfully")
except ImportError as e:
    logger.warning(f"Historical alerts router not available: {e}")

# Cash Policies Router
try:
    from src.api.cash_policies_endpoints import router as cash_policies_router
    app.include_router(cash_policies_router)
    logger.info("Cash policies router loaded successfully")
except ImportError as e:
    logger.warning(f"Cash policies router not available: {e}")

# Session files inspector router
try:
    from src.api.session_files_endpoints import router as session_files_router
    app.include_router(session_files_router)
    logger.info("Session files router loaded successfully")
except ImportError as e:
    logger.warning(f"Session files router not available: {e}")

# Maps Router for geo data feeds
try:
    from src.api.maps_endpoints import router as maps_router
    app.include_router(maps_router)
    logger.info("Maps router loaded successfully")
except ImportError as e:
    logger.warning(f"Maps router not available: {e}")

# Demo Interface Router for Technical Competition
try:
    from src.presentation.demo_interface import router as demo_router
    app.include_router(demo_router)
    logger.info("Demo interface router loaded successfully")
except ImportError as e:
    logger.warning(f"Demo interface not available: {e}")

# Saldos router
try:
    from src.api.saldos_endpoints import router as saldos_router
    app.include_router(saldos_router)
    logger.info("Saldos router loaded successfully")
except ImportError as e:
    logger.warning(f"Saldos router not available: {e}")

# Voice streaming router
try:
    from src.api.voice_endpoints import router as voice_router
    app.include_router(voice_router)
    logger.info("Voice router loaded successfully")
except ImportError as e:
    logger.warning(f"Voice router not available: {e}")

# GraphCanva overview router
try:
    from src.graph_canva.router import router as graph_canva_router
    app.include_router(graph_canva_router)
    logger.info("GraphCanva overview router loaded successfully")
except ImportError as e:
    logger.warning(f"GraphCanva router not available: {e}")

# GraphCanva websocket router
try:
    from src.presentation.websocket_graphcanva import router as graphcanva_ws_router
    app.include_router(graphcanva_ws_router)
    logger.info("GraphCanva websocket router loaded successfully")
except ImportError as e:
    logger.warning(f"GraphCanva websocket not available: {e}")

# Crear orquestrador DESPUÃ‰S de cargar variables de entorno
logger.info(f"Inicializando orquestrador: {logger_msg}")
api_key_available = bool(os.getenv("OPENAI_API_KEY"))
logger.info(f"OPENAI_API_KEY configurada: {'Si' if api_key_available else 'No'}")

# Initialize LangGraph orchestrator
enable_narrative = os.getenv("LANGGRAPH_ENABLE_NARRATIVE", "false").lower() == "true"
confidence_threshold = float(os.getenv("LANGGRAPH_CONFIDENCE_THRESHOLD", "0.6"))

orchestrator = OrchestratorFactory.create_orchestrator(
    memory_window=20,
    memory_ttl_minutes=120,
    enable_narrative=enable_narrative,
    confidence_threshold=confidence_threshold,
    api_port=os.getenv('PORT', '8000')
)
voice_settings = VoiceSettings()
try:
    app.state.voice_orchestrator = VoiceOrchestrator(orchestrator=orchestrator, settings=voice_settings)
    logger.info({"event": "voice_orchestrator_ready", "language": voice_settings.google_speech_language})
except Exception as exc:
    logger.warning({"event": "voice_orchestrator_init_failed", "error": str(exc)})

logger.info(f"Unified LangGraph Orchestrator inicializado (narrative={enable_narrative}, threshold={confidence_threshold})")
semantic_service = SemanticIntentService()
datab_agent = CapiDataBAgent()

async def _handle_direct_datab(instruction: str, session_id: str, user_id: str) -> Dict[str, Any]:
    def _execute():
        operation = datab_agent.prepare_operation(instruction)
        task_id = f"direct_{session_id}_{uuid.uuid4().hex[:8]}"
        return datab_agent.execute_operation(
            operation,
            task_id=task_id,
            user_id=user_id,
            session_id=session_id,
        )

    agent_result = await asyncio.to_thread(_execute)
    payload = agent_result.data.copy() if agent_result.data else {}
    return {
        "success": agent_result.is_success(),
        "message": agent_result.message or "Operacion completada",
        "agent": agent_result.agent_name,
        "data": payload,
    }


logger.info("=== CapiAgentes Application Starting ===")
logger.info("Orquestador unificado inicializado")

# Inicializar datos al arrancar el servidor
state: Dict[str, Any] = {
    "data": None
    # conversations now handled by orchestrator
}


class HumanApprovalRequest(BaseModel):
    """Payload para registrar la decision humana sobre un bloqueo del grafo."""

    session_id: str = Field(..., description="Identificador unico de la sesion LangGraph")
    approved: bool = Field(..., description="Define si la ejecucion puede continuar")
    interrupt_id: Optional[str] = Field(
        default=None,
        description="Identificador de la interrupcion devuelto por LangGraph (opcional)",
    )
    message: Optional[str] = Field(default=None, description="Mensaje visible para el usuario final")
    reason: Optional[str] = Field(default=None, description="Motivo interno que respalda la decision")
    approved_by: Optional[str] = Field(default=None, description="Operador que registro la decision")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos adicionales asociados a la decision")


def _serialize_response_envelope(envelope: ResponseEnvelope) -> Dict[str, Any]:
    """Convierte un ResponseEnvelope a un diccionario JSON serializable."""

    payload: Dict[str, Any] = {
        "trace_id": envelope.trace_id,
        "response_type": getattr(envelope.response_type, "value", str(envelope.response_type)),
        "intent": getattr(envelope.intent, "value", str(envelope.intent)),
        "message": envelope.message,
        "data": envelope.data,
        "meta": envelope.meta,
        "errors": envelope.errors,
        "created_at": envelope.created_at.isoformat() if hasattr(envelope.created_at, "isoformat") else envelope.created_at,
    }
    if getattr(envelope, "suggested_actions", None):
        payload["suggested_actions"] = [
            asdict(action) if hasattr(action, "__dataclass_fields__") else action
            for action in envelope.suggested_actions
        ]
    return payload


def initialize_data():
    """Carga automÃ¡ticamente los datos al inicio del servidor.

    Usa el orchestrator activo si expone un mÃ©todo de carga; de lo contrario omite.
    """
    import asyncio
    
    async def load_data_async():
        try:
            default_file = get_default_data_file()
            if not default_file:
                logger.warning("No hay archivo de datos por defecto disponible")
                return
            if not hasattr(orchestrator, "load_data_use_case"):
                logger.info("Orchestrator no expone load_data_use_case todavÃ­a; omitiendo carga inicial")
                return
            # CAMBIO: Cargar TODOS los archivos en lugar de uno solo
            if hasattr(orchestrator, "load_all_data_files"):
                logger.info("Cargando TODOS los archivos de datos desde Backend/ia_workspace/data/")
                result = await orchestrator.load_all_data_files()
            else:
                logger.info(f"Cargando datos desde: {default_file}")
                # LangGraph orchestrator - load_data_use_case es una funciÃ³n async
                if asyncio.iscoroutinefunction(orchestrator.load_data_use_case):
                    result = await orchestrator.load_data_use_case(default_file)
                else:
                    # Si no es async, llamar directamente
                    result = orchestrator.load_data_use_case(default_file)
            
            # Procesar resultado
            if isinstance(result, dict) and result.get('success'):
                state["data"] = {
                    "json": result.get('data', {}).get("json_data", []),
                    "anomalies": result.get('data', {}).get("anomalies", []),
                    "summary": result.get('data', {}).get("summary", {}),
                    "dashboard": result.get('data', {}).get("dashboard", {})
                }
                # Manejar tanto carga individual como masiva
                data = result.get('data', {})
                if 'total_records' in data:  # Carga masiva
                    logger.info(f"Carga masiva completada - {data['total_records']} registros de {data.get('total_files', 0)} archivos")
                else:  # Carga individual
                    records = data.get('records_count', 0)
                    logger.info(f"Datos cargados correctamente ({records} registros)")
            elif hasattr(result, 'success'):
                # Objeto con atributo success
                if result.success:
                    state["data"] = {
                        "json": result.data.get("json_data", []),
                        "anomalies": result.data.get("anomalies", []),
                        "summary": result.data.get("summary", {}),
                        "dashboard": result.data.get("dashboard", {})
                    }
                    logger.info(f"Datos cargados correctamente ({result.data.get('records_count', 0)} registros)")
                else:
                    logger.error(f"FallÃ³ la carga de datos: {getattr(result, 'message', 'Error desconocido')}")
            else:
                logger.warning(f"Formato de resultado no reconocido: {type(result)}")
                
        except Exception:
            logger.exception('Error al cargar datos automÃ¡ticamente durante la inicializaciÃ³n')
    
    # Ejecutar la carga de datos
    try:
        # Intentar obtener el loop existente
        loop = asyncio.get_running_loop()
        # Si hay un loop, crear una tarea
        asyncio.create_task(load_data_async())
    except RuntimeError:
        # No hay loop, crear uno nuevo
        asyncio.run(load_data_async())

# Cargar datos al inicializar el servidor
logger.info("Iniciando carga de datos...")
initialize_data()
logger.info(f"Sistema de datos inicializado - state['data'] is None: {state['data'] is None}")
if state.get("data"):
    logger.info(f"Datos cargados: {len(state['data'].get('json', []))} registros JSON")
else:
    logger.warning("No se pudieron cargar datos - state['data'] es None")


@app.websocket("/ws/agents")
async def websocket_agents_endpoint(ws: WebSocket) -> None:
    """WebSocket endpoint for agent lifecycle events.

    Dedicated endpoint for PantallaAgentes real-time visualization.
    Clients connect here to receive agent_start, agent_end, and node_transition events.
    """
    await ws.accept()

    # Add connection to event broadcaster
    await event_broadcaster.add_connection(ws)

    try:
        # Keep connection alive and handle ping/pong
        while True:
            try:
                # Wait for messages from client (ping/pong or commands)
                message = await ws.receive_text()
                data = json.loads(message) if message else {}

                # Handle client commands
                if data.get("type") == "ping":
                    await ws.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                elif data.get("type") == "get_history":
                    history = event_broadcaster.get_event_history(limit=data.get("limit", 20))
                    await ws.send_json({"type": "history", "events": history})

            except json.JSONDecodeError:
                # Ignore malformed messages
                pass
    except WebSocketDisconnect:
        pass
    finally:
        # Remove connection from broadcaster
        await event_broadcaster.remove_connection(ws)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Simple WebSocket endpoint to process instructions via chat.

    The client should send a JSON message containing at least the field
    ``instruction`` with a free-form command. Optionally ``file_path`` and
    ``client_id`` can be provided when the instruction involves data ingesti
    on.
    """

    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"instruction": raw}
            instruction = payload.get("instruction", "")
            file_path = payload.get("file_path")
            client_id = payload.get("client_id", "default")
            
            # Conversation memory is handled by the orchestrator itself

            # Si no hay datos, responder con error
            if state.get("data") is None:
                await ws.send_json(
                    {
                        "error": "No hay datos disponibles. Verifica que existan archivos CSV en la carpeta data/",
                    }
                )
                continue

            # *** ROUTING TO ORCHESTRATOR ***
            session_extra = {'session_id': client_id, 'client_id': client_id}
            logger.info('[WEBSOCKET DEBUG] Processing instruction', extra=dict(session_extra, log_context=f'instruction={instruction[:80]}'))
            logger.info('[WEBSOCKET DEBUG] Using LangGraph orchestrator', extra=session_extra)

            try:
                # Broadcast node transition: input → intent
                await event_broadcaster.broadcast_node_transition(
                    from_node="input",
                    to_node="intent",
                    session_id=client_id,
                    action="intent",
                    meta={"query": instruction[:100]}  # Truncate long queries
                )

                # LangGraph orchestrator returns ResponseEnvelope
                import asyncio
                import time
                start_time = time.time()

                result_obj = await orchestrator.process_query(
                    query=instruction,
                    user_id=client_id,
                    session_id=client_id,
                    channel="websocket"
                )

                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                # Convert ResponseEnvelope to dict format
                result = {
                    "success": result_obj.is_success(),
                    "message": result_obj.message,
                    "agent": result_obj.meta.get("agent", "orchestrator"),
                    "data": {
                        **result_obj.data,
                        "response_type": result_obj.response_type.value if hasattr(result_obj.response_type, 'value') else str(result_obj.response_type),
                        "processing_time_ms": result_obj.meta.get("pipeline_ms", 0),
                        "request_id": result_obj.trace_id
                    }
                }
                
                if result.get("success", False):
                    # Enhanced orchestrator format with proper agent names
                    response_content = result["message"]
                    agent_name = result.get("agent", "CapiOrchestrator")
                    response_type = result["data"].get("response_type", "success")

                    # Broadcast agent events if an agent was used
                    if agent_name and agent_name != "CapiOrchestrator":
                        # Broadcast agent start and end events
                        await event_broadcaster.broadcast_agent_start(
                            agent_name=agent_name,
                            session_id=client_id,
                            meta={"intent": result_obj.intent.value if hasattr(result_obj, 'intent') else "unknown"}
                        )

                        await event_broadcaster.broadcast_agent_end(
                            agent_name=agent_name,
                            session_id=client_id,
                            success=True,
                            duration_ms=execution_time,
                            meta={"response_type": response_type}
                        )

                    # Broadcast node transition: agent → response
                    await event_broadcaster.broadcast_node_transition(
                        from_node="execution",
                        to_node="response",
                        session_id=client_id,
                        action="response",
                        meta={"agent": agent_name, "success": True}
                    )

                    # Conversation memory is handled by the orchestrator itself

                    response_payload = {
                        "respuesta": response_content,
                        "tipo": response_type.upper(),
                        "confidence": "high",
                        "processing_time": result["data"].get("processing_time_ms", 0),
                        "request_id": result["data"].get("request_id"),
                    }

                    data_payload = result.get("data")
                    if isinstance(data_payload, dict):
                        safe_data = _sanitize_for_json(data_payload)
                        response_payload["data"] = safe_data
                        shared_artifacts = safe_data.get("shared_artifacts")
                        if shared_artifacts:
                            response_payload.setdefault("shared_artifacts", shared_artifacts)

                    meta_payload = result_obj.meta if isinstance(result_obj.meta, dict) else {}
                    if meta_payload:
                        response_payload["metadata"] = meta_payload
                        response_metadata = meta_payload.get("response_metadata")
                        if isinstance(response_metadata, dict):
                            response_payload["response_metadata"] = response_metadata

                    await ws.send_json({
                        "agent": agent_name,
                        "response": response_payload,
                    })
                else:
                    await ws.send_json({
                        "agent": "error",
                        "response": {
                            "respuesta": f"Error procesando consulta: {result.get('message') if isinstance(result, dict) else getattr(result, 'message', str(result))}",
                            "tipo": "error"
                        }
                    })
            except Exception as e:  # pragma: no cover - resiliencia
                session_extra = {'session_id': client_id, 'client_id': client_id}
                logger.exception('Unhandled exception in websocket_endpoint', extra=session_extra)
                # Respuesta genÃ©rica de fallback
                fallback_response = f"Lo siento, hubo un error procesando tu consulta: '{instruction}'. Por favor intenta reformular tu pregunta."
                # Conversation memory is handled by the orchestrator itself
                
                await ws.send_json({
                    "agent": "error", 
                    "response": {
                        "respuesta": fallback_response,
                        "tipo": "error"
                    }
                })
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/graph")
async def websocket_graph_endpoint(ws: WebSocket) -> None:
    """WebSocket endpoint for LangGraph real-time updates.

    Provides real-time graph execution updates and visualization data.
    """
    from src.presentation.websocket_langgraph import langgraph_ws_endpoint

    # Generate session ID
    import uuid
    session_id = str(uuid.uuid4())

    try:
        await langgraph_ws_endpoint.handle_websocket(ws, session_id)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception('Unhandled exception in websocket_graph_endpoint', extra={'session_id': session_id})


# --- REST API endpoints para fallback HTTP ---
from fastapi import Body

@app.api_route("/api/command", methods=["POST", "GET", "OPTIONS"])
async def api_command(request: Request):
    request_id = request.headers.get('x-request-id') or str(uuid.uuid4())
    logger.info(
        '/api/command request received',
        extra={'request_id': request_id, 'log_context': f"method={request.method}"}
    )

    if request.method != 'POST':
        return {'info': "Endpoint operativo. Usa POST con JSON {instruction, client_id}"}

    try:
        raw_body = await request.body()
        raw_length = len(raw_body) if raw_body else 0
        raw_preview = ''
        if raw_body:
            raw_preview = raw_body[:300].decode('utf-8', errors='ignore').replace('\r', ' ').replace('\n', ' ')
        logger.info(
            '/api/command payload received',
            extra={'request_id': request_id, 'log_context': f"bytes={raw_length} preview={raw_preview}"}
        )

        try:
            data = json.loads(raw_body.decode('utf-8') or '{}') if raw_body else {}
        except json.JSONDecodeError as exc:
            logger.warning(
                'JSON invÃ¡lido en /api/command',
                extra={'request_id': request_id, 'log_context': f'error={exc}'}
            )
            return JSONResponse(
                status_code=400,
                content={'error': {'code': 'BAD_JSON', 'message': 'JSON invÃ¡lido'}}
            )

        instruction = data.get('instruction', '')
        file_path = data.get('file_path')
        client_id = data.get('client_id', 'default')

        if not isinstance(instruction, str):
            return JSONResponse(status_code=400, content={'error': {'code': 'INVALID_TYPE', 'message': "'instruction' debe ser string"}})
        if not instruction.strip():
            return JSONResponse(status_code=400, content={'error': {'code': 'MISSING_INSTRUCTION', 'message': "Falta 'instruction' en el cuerpo JSON"}})

        base_extra = {'request_id': request_id, 'client_id': client_id, 'session_id': client_id}
        logger.info(
            '[EMAIL_TRACE] backend.api_command',
            extra=dict(base_extra, log_context=f"instruction_raw={instruction}")
        )
        logger.info(
            'Command payload validated',
            extra=dict(base_extra, log_context=f"instruction={instruction[:80]} file={file_path or '<none>'}")
        )
        logger.info(
            'Data availability assessed',
            extra=dict(base_extra, log_context=f"data_loaded={bool(state.get('data'))}")
        )
        llm_ready = bool(getattr(orchestrator, 'llm_reasoner', None))
        logger.info(
            'LLM availability status',
            extra=dict(base_extra, log_context=f"llm_ready={llm_ready}")
        )

        classification = await asyncio.to_thread(
            semantic_service.classify_intent,
            instruction,
            {'session_id': client_id, 'trace_id': request_id},
        )
        intent_value = getattr(classification.intent, 'value', str(classification.intent))
        target_agent = classification.target_agent or 'unknown'
        classification_info = {
            'intent': intent_value,
            'confidence': float(classification.confidence or 0.0),
            'provider': classification.provider,
            'target_agent': target_agent,
        }
        logger.info(
            'Semantic classification result',
            extra=dict(
                base_extra,
                log_context=f"intent={intent_value} target={target_agent} confidence={classification_info['confidence']:.2f}",
            ),
        )

        if state.get('data') is None:
            logger.warning('No hay datos en estado, intentando cargar automÃ¡ticamente...', extra=base_extra)
            initialize_data()
            if state.get('data') is None:
                logger.info('Usando LangGraph orchestrador, omitiendo verificaciÃ³n de datos pre-procesamiento', extra=base_extra)

        logger.info('Routing instruction to orchestrator', extra=base_extra)
        orchestrator_extra = dict(base_extra)

        try:
            result_obj = await orchestrator.process_query(
                query=instruction,
                user_id=client_id,
                session_id=client_id,
                channel="http_api"
            )
            orchestrator_extra['trace_id'] = result_obj.trace_id
            result = {
                'success': result_obj.is_success(),
                'message': result_obj.message,
                'agent': result_obj.meta.get('agent', 'orchestrator'),
                'data': {
                    **result_obj.data,
                    'response_type': result_obj.response_type.value if hasattr(result_obj.response_type, 'value') else str(result_obj.response_type),
                    'processing_time_ms': result_obj.meta.get('pipeline_ms', 0),
                    'request_id': result_obj.trace_id
                }
            }

            if result.get('success', False):
                response_content = result['message']
                agent_name = result.get('agent', 'CapiOrchestrator')
                response_type = result['data'].get('response_type', 'success')
                processing_time = result['data'].get('processing_time_ms', 0.0)
                orchestrator_extra['agent_name'] = agent_name

                logger.info(
                    'Orchestrator response ready',
                    extra=dict(
                        orchestrator_extra,
                        log_context=f"response_type={response_type} processing_time_ms={processing_time}"
                    )
                )

                safe_response_content = response_content.encode('utf-8', errors='ignore').decode('utf-8')

                response_data = {
                    'agent': agent_name,
                    'response': {
                        'respuesta': safe_response_content,
                        'tipo': response_type.upper(),
                        'confidence': 'high',
                        'processing_time': processing_time,
                        'request_id': result['data'].get('request_id'),
                        'agent_name': agent_name
                    },
                    'diagnostics': classification_info
                }

                safe_data = _sanitize_for_json(result.get('data', {}))
                response_data['response']['data'] = safe_data
                shared_artifacts = safe_data.get('shared_artifacts') if isinstance(safe_data, dict) else None
                if shared_artifacts:
                    response_data['response'].setdefault('shared_artifacts', shared_artifacts)

                meta_payload = result_obj.meta if isinstance(result_obj.meta, dict) else {}
                if meta_payload:
                    response_data['response']['metadata'] = meta_payload
                    response_metadata = meta_payload.get('response_metadata')
                    if isinstance(response_metadata, dict):
                        response_data['response']['response_metadata'] = response_metadata

                return JSONResponse(
                    status_code=200,
                    content=response_data,
                    headers={'Content-Type': 'application/json; charset=utf-8'}
                )

            error_message = result.get('message') if isinstance(result, dict) else getattr(result, 'message', str(result))
            safe_message = str(error_message).encode('utf-8', errors='ignore').decode('utf-8')
            logger.error('Fallo en LangGraph orchestrator', extra=dict(orchestrator_extra, log_context=f'message={safe_message}'))
            return JSONResponse(
                status_code=500,
                content={'error': {'code': 'PROCESSING_ERROR', 'message': safe_message}},
                headers={'Content-Type': 'application/json; charset=utf-8'}
            )
        except Exception as exc:  # pragma: no cover
            logger.exception('Unhandled exception in api_command process_query block', extra=orchestrator_extra)
            fallback_response = f"Lo siento, hubo un error procesando tu consulta: '{instruction}'. Por favor intenta reformular tu pregunta."
            safe_error_message = str(exc).encode('utf-8', errors='ignore').decode('utf-8')
            return JSONResponse(
                status_code=500,
                content={'error': {'code': 'PROCESSING_ERROR', 'message': safe_error_message}},
                headers={'Content-Type': 'application/json; charset=utf-8'}
            )

    except Exception as exc:
        logger.exception('Unhandled exception in api_command root handler', extra={'request_id': request_id})
        safe_final_error = str(exc).encode('utf-8', errors='ignore').decode('utf-8')
        return JSONResponse(
            status_code=500,
            content={'error': {'code': 'INTERNAL_ERROR', 'message': safe_final_error}},
            headers={'Content-Type': 'application/json; charset=utf-8'}
        )



# Deprecated /api/ingest endpoint removed - data auto-loads on startup

@app.get("/api/files")
async def list_files():
    """Lista archivos disponibles usando configuraciÃ³n centralizada."""
    files = get_available_data_files()
    # Convertir datetime a timestamp para JSON
    for file_info in files:
        if "modified" in file_info:
            file_info["modified"] = file_info["modified_timestamp"]
    return {"files": files}


# --- Health & readiness (para compatibilidad con frontend) ---
@app.get("/api/health")
async def api_health():
    return {"status": "ok", "service": "chat_server"}

# Alias root para healthcheck de Docker (docker-compose usa /health)
@app.get("/health", include_in_schema=False)
async def root_health():  # pragma: no cover - simple alias
    return {"status": "ok", "service": "chat_server"}

@app.get("/api/orchestrator/info")
async def orchestrator_info():
    """Retorna informaciÃ³n detallada del orquestador activo."""
    try:
        info = {
            "type": orchestrator.__class__.__name__,
            "module": orchestrator.__class__.__module__,
            "langgraph_enabled": True,
            "version": "2.0.0",
            "capabilities": {
                "process_query": hasattr(orchestrator, 'process_query'),
                "load_data": hasattr(orchestrator, 'load_data_use_case'),
                "metrics": hasattr(orchestrator, 'get_metrics'),
                "memory": hasattr(orchestrator, 'get_session_history')
            }
        }
        
        # Obtener configuraciÃ³n de LangGraph
        if hasattr(orchestrator, 'config'):
            info["configuration"] = {
                "memory_window": getattr(orchestrator.config, 'memory_window_size', None),
                "memory_ttl": getattr(orchestrator.config, 'memory_ttl_minutes', None),
                "narrative_enabled": getattr(orchestrator.config, 'pipeline_enable_narrative', False),
                "confidence_threshold": getattr(orchestrator.config, 'intent_confidence_threshold', 0.6)
            }
        
        return info
        
    except Exception as e:
        logger.error(f"Error obteniendo info del orchestrador: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INFO_ERROR", "message": str(e)}}
        )

@app.get("/api/metrics")
async def get_metrics():
    """Obtiene mÃ©tricas del sistema y del orquestador."""
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - app.state.start_time).total_seconds(),
            "orchestrator_type": orchestrator.__class__.__name__,
            "langgraph_enabled": True
        }
        
        # Obtener mÃ©tricas del orquestador LangGraph
        if hasattr(orchestrator, 'get_metrics'):
            orchestrator_metrics = orchestrator.get_metrics()
            metrics["orchestrator"] = orchestrator_metrics
        
        # MÃ©tricas de memoria de conversaciÃ³n (now handled by orchestrator)
        if hasattr(orchestrator, 'get_active_sessions'):
            active_sessions = orchestrator.get_active_sessions()
            metrics["conversations"] = {
                "active_sessions": len(active_sessions),
                "note": "Conversation memory managed by orchestrator"
            }
        else:
            metrics["conversations"] = {
                "active_sessions": 0,
                "note": "Conversation memory managed by orchestrator"
            }
        
        # MÃ©tricas de datos
        if state.get("data"):
            data = state["data"]
            metrics["data"] = {
                "loaded": True,
                "records": len(data.get("json", [])),
                "anomalies": len(data.get("anomalies", [])),
                "has_summary": bool(data.get("summary")),
                "has_dashboard": bool(data.get("dashboard"))
            }
        else:
            metrics["data"] = {"loaded": False}
        
        voice_snapshot = {
            "active_streams": 0.0,
            "stream_bytes_total": 0.0,
            "stream_warnings": {},
            "turns": {},
            "turn_latency_ms": {"count": 0.0, "sum": 0.0},
            "stream_duration_seconds": {"count": 0.0, "sum": 0.0},
        }
        try:
            def _collect_sample(metric, suffix=None):
                for family in metric.collect():
                    for sample in family.samples:
                        if suffix and not sample.name.endswith(suffix):
                            continue
                        return sample.value
                return 0.0

            def _collect_by_label(metric, suffix):
                data = {}
                for family in metric.collect():
                    for sample in family.samples:
                        if not sample.name.endswith(suffix):
                            continue
                        label = next(iter(sample.labels.values()), "total") if sample.labels else "total"
                        data[label] = sample.value
                return data

            voice_snapshot = {
                "active_streams": _collect_sample(voice_metrics.VOICE_ACTIVE_STREAMS),
                "stream_bytes_total": _collect_sample(voice_metrics.VOICE_STREAM_BYTES, "_total"),
                "stream_warnings": _collect_by_label(voice_metrics.VOICE_STREAM_WARNINGS, "_total"),
                "turns": _collect_by_label(voice_metrics.VOICE_TURNS, "_total"),
                "turn_latency_ms": {
                    "count": _collect_sample(voice_metrics.VOICE_TURN_LATENCY, "_count"),
                    "sum": _collect_sample(voice_metrics.VOICE_TURN_LATENCY, "_sum"),
                },
                "stream_duration_seconds": {
                    "count": _collect_sample(voice_metrics.VOICE_STREAM_DURATION, "_count"),
                    "sum": _collect_sample(voice_metrics.VOICE_STREAM_DURATION, "_sum"),
                },
            }
        except Exception as voice_error:  # pragma: no cover - metrics collection should not break API
            logger.warning({"event": "voice_metrics_collect_failed", "error": str(voice_error)})

        metrics["voice"] = voice_snapshot

        return metrics
        
    except Exception as e:
        logger.error(f"Error obteniendo mÃ©tricas: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "METRICS_ERROR", "message": str(e)}}
        )

@app.post("/api/orchestrator/reload")
async def reload_orchestrator():
    """Recarga el orquestador con la configuraciÃ³n actual."""
    global orchestrator
    
    try:
        # Unified orchestrator factory handles instantiation
        
        # Recargar con configuraciÃ³n actualizada
        enable_narrative = os.getenv("LANGGRAPH_ENABLE_NARRATIVE", "false").lower() == "true"
        confidence_threshold = float(os.getenv("LANGGRAPH_CONFIDENCE_THRESHOLD", "0.6"))
        
        orchestrator = OrchestratorFactory.create_orchestrator(
            memory_window=20,
            memory_ttl_minutes=120,
            enable_narrative=enable_narrative,
            confidence_threshold=confidence_threshold,
            api_port=os.getenv('PORT', '8000')
        )
        
        message = f"LangGraph Orchestrator recargado (narrative={enable_narrative}, threshold={confidence_threshold})"
        
        logger.info(message)
        
        return {
            "status": "success",
            "message": message,
            "orchestrator_type": orchestrator.__class__.__name__
        }

    except Exception as e:
        logger.error(f"Error recargando orchestrador: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "RELOAD_ERROR", "message": str(e)}}
        )


@app.post("/api/orchestrator/human/decision")
async def submit_human_decision(payload: HumanApprovalRequest):
    """Registra la decision humana y reanuda el grafo si procede."""
    if not hasattr(orchestrator, "resume_human_gate"):
        raise HTTPException(
            status_code=501,
            detail="El orquestador activo no soporta aprobaciones humanas",
        )

    resume_payload: Dict[str, Any] = {
        "approved": payload.approved,
        "message": payload.message,
        "reason": payload.reason,
        "approved_by": payload.approved_by,
        "metadata": payload.metadata,
        "node": "human_gate",
        "resumed_at": datetime.utcnow().isoformat(),
    }
    resume_payload = {key: value for key, value in resume_payload.items() if value is not None}
    if not resume_payload.get("metadata"):
        resume_payload.pop("metadata", None)

    if payload.interrupt_id:
        command_payload: Dict[str, Any] = {payload.interrupt_id: resume_payload}
    else:
        command_payload = dict(resume_payload)

    try:
        envelope = await orchestrator.resume_human_gate(
            session_id=payload.session_id,
            decision=command_payload,
        )
    except AttributeError as exc:
        logger.exception("Orchestrator resume_human_gate missing", extra={"session_id": payload.session_id})
        raise HTTPException(
            status_code=501,
            detail="El orquestador activo no implementa la reanudacion de human_gate",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Error reanudando flujo human_gate",
            extra={
                "session_id": payload.session_id,
                "interrupt_id": payload.interrupt_id,
                "approved": payload.approved,
            },
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    response_payload = _serialize_response_envelope(envelope)

    logger.info(
        {
            "event": "human_gate_resumed",
            "session_id": payload.session_id,
            "interrupt_id": payload.interrupt_id,
            "approved": payload.approved,
        }
    )

    return {
        "success": True,
        "session_id": payload.session_id,
        "interrupt_id": payload.interrupt_id,
        "decision": resume_payload,
        "resume_payload": command_payload,
        "response": response_payload,
    }


@app.get("/api/ready")
async def api_ready():
    # Listo si el objeto orchestrator existe; opcionalmente podrÃ­amos validar modelos
    return {"ready": True, "has_data": state.get("data") is not None}

# /api/test endpoint removed to avoid production interference
# Basic functionality testing now available through /api/health and /api/status

@app.post("/api/start")
async def api_start_backend(request: Request):
    """Endpoint para 'iniciar' backend - principalmente reinicia la carga de datos"""
    try:
        data = await request.json()
        action = data.get("action", "start")
        
        if action == "start":
            # Reinicializar datos
            initialize_data()
            
            return {
                "status": "success",
                "message": "Backend iniciado correctamente",
                "data_loaded": state.get("data") is not None,
                "timestamp": Path(__file__).stat().st_mtime
            }
        else:
            return JSONResponse(
                status_code=400, 
                content={"error": {"code": "INVALID_ACTION", "message": "AcciÃ³n no vÃ¡lida"}}
            )
            
    except Exception as e:
        logger.exception('Unhandled exception in api_start_backend')
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "START_ERROR", "message": str(e)}}
        )

@app.post("/api/stop")
async def api_stop_backend(request: Request):
    """Endpoint para 'detener' backend - limpia datos cargados"""
    try:
        data = await request.json()
        action = data.get("action", "stop")
        
        if action == "stop":
            # Limpiar datos cargados (simula detener el backend)
            state["data"] = None
            
            return {
                "status": "success",
                "message": "Backend detenido correctamente",
                "data_cleared": True
            }
        else:
            return JSONResponse(
                status_code=400,
                content={"error": {"code": "INVALID_ACTION", "message": "AcciÃ³n no vÃ¡lida"}}
            )
            
    except Exception as e:
        logger.exception('Unhandled exception in api_stop_backend')
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "STOP_ERROR", "message": str(e)}}
        )

@app.get("/api/status")
async def api_backend_status():
    """Endpoint para obtener estado detallado del backend"""
    try:
        default_file = get_default_data_file()
        available_files = get_available_data_files()
        
        # Obtener informaciÃ³n adicional del orquestador
        orchestrator_info = {
            "type": orchestrator.__class__.__name__,
            "module": orchestrator.__class__.__module__,
            "has_load_data": hasattr(orchestrator, 'load_data_use_case'),
            "has_metrics": hasattr(orchestrator, 'get_metrics')
        }
        
        return {
            "status": "online",
            "service": "chat_server",
            "orchestrator_type": "LangGraphOrchestratorAdapter",
            "langgraph_enabled": True,
            "orchestrator_info": orchestrator_info,
            "data_loaded": state.get("data") is not None,
            "default_file": default_file,
            "available_files": len(available_files),
            "active_conversations": "managed_by_orchestrator",
            "uptime": "active",  # En una implementaciÃ³n real, calcularÃ­as el uptime
            "last_activity": Path(__file__).stat().st_mtime if Path(__file__).exists() else None
        }
    except Exception as e:
        logger.exception('Unhandled exception in api_backend_status')
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "service": "chat_server",
                "error": str(e),
                "data_loaded": False
            }
        )

# --- Endpoints para manejo de conversaciÃ³n ---
@app.get("/api/conversation/{client_id}")
async def get_conversation_history(client_id: str):
    """Obtiene el historial de conversaciÃ³n de un cliente."""
    try:
        # Conversation history is now handled by the orchestrator
        if hasattr(orchestrator, 'get_session_history'):
            history = orchestrator.get_session_history(client_id)
            return {
                "client_id": client_id,
                "message_count": len(history) if history else 0,
                "history": history or []
            }
        else:
            return {
                "client_id": client_id,
                "message_count": 0,
                "history": [],
                "note": "Conversation history managed by orchestrator"
            }
    except Exception as e:
        logger.exception('Unhandled exception in get_conversation_history')
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "HISTORY_ERROR", "message": str(e)}}
        )

@app.delete("/api/conversation/{client_id}")
async def clear_conversation_history(client_id: str):
    """Limpia el historial de conversaciÃ³n de un cliente."""
    try:
        # Conversation history is now handled by the orchestrator
        if hasattr(orchestrator, 'clear_session_history'):
            orchestrator.clear_session_history(client_id)
        elif hasattr(orchestrator, 'conversation_state_manager'):
            orchestrator.conversation_state_manager.clear_session(client_id)
        
        return {
            "status": "success",
            "message": f"Historial de conversaciÃ³n limpiado para {client_id}",
            "client_id": client_id
        }
    except Exception as e:
        logger.exception('Unhandled exception in clear_conversation_history')
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "CLEAR_ERROR", "message": str(e)}}
        )

@app.get("/api/conversations")
async def list_active_conversations():
    """Lista todas las conversaciones activas."""
    try:
        # Conversations are now handled by the orchestrator
        if hasattr(orchestrator, 'get_active_sessions'):
            active_sessions = orchestrator.get_active_sessions()
            summary = [{
                "client_id": session_id,
                "message_count": "managed_by_orchestrator",
                "last_activity": "managed_by_orchestrator",
                "last_message_preview": "managed_by_orchestrator"
            } for session_id in active_sessions]
            
            return {
                "active_conversations": len(summary),
                "conversations": summary,
                "note": "Conversation details managed by orchestrator"
            }
        else:
            return {
                "active_conversations": 0,
                "conversations": [],
                "note": "Conversation management delegated to orchestrator"
            }
    except Exception as e:
        logger.exception('Unhandled exception in list_active_conversations')
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "LIST_ERROR", "message": str(e)}}
        )

# --- Endpoints para sistema de aprendizaje ---
@app.post("/api/feedback")
async def submit_feedback(request: Request):
    """Recibe feedback del usuario para mejorar las respuestas."""
    try:
        data = await request.json()
        
        user_id = data.get("user_id", "default")
        session_id = str(data.get("session_id") or data.get("client_id") or user_id or "feedback")
        turn_id_raw = data.get("turn_id")
        try:
            turn_id = int(turn_id_raw)
        except (TypeError, ValueError):
            turn_id = int(datetime.utcnow().timestamp() * 1000) % 1_000_000_000
        query = data.get("query", "")
        response = data.get("response", "")
        feedback_type = data.get("feedback_type", "neutral")  # positive, neutral, helpful, unclear, etc.
        rating = data.get("rating")  # 1-5 optional
        comments = data.get("comments", "")
        channel = data.get("channel") or "http_api"
        trace_id = data.get("trace_id")
        intent = data.get("intent")
        agent_name = data.get("agent_name") or "unknown"

        feedback_score = None
        if rating is not None:
            try:
                feedback_score = float(rating)
            except (TypeError, ValueError):
                feedback_score = None

        metadata = {
            "feedback_type": feedback_type,
            "query_preview": query[:120] if isinstance(query, str) and query else None,
            "response_preview": response[:120] if isinstance(response, str) and response else None,
            "comments": comments[:500] if isinstance(comments, str) and comments else None,
        }
        metadata = {key: value for key, value in metadata.items() if value}

        record_feedback_event(
            agent_name=agent_name,
            session_id=session_id,
            turn_id=turn_id,
            feedback_score=feedback_score,
            feedback_text=comments if comments else None,
            user_id=user_id,
            channel=channel,
            trace_id=trace_id,
            intent=intent,
            metadata=metadata or None,
        )

        learning_available = False  # Simplified for now

        logger.info(
            "Feedback received",
            extra={
                "user_id": user_id,
                "session_id": session_id,
                "turn_id": turn_id,
                "feedback_type": feedback_type,
                "rating": feedback_score,
            },
        )
        message = "Feedback recibido (sistema de aprendizaje en transicion)"

        return {
            "status": "success",
            "message": message,
            "user_id": user_id,
            "feedback_type": feedback_type,
            "learning_system_available": learning_available
        }

    except Exception as e:
        logger.exception('Unhandled exception in submit_feedback')
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "FEEDBACK_ERROR", "message": str(e)}}
        )

@app.get("/api/learning/insights")
async def get_learning_insights():
    """Obtiene insights del sistema de aprendizaje."""
    try:
        if not hasattr(orch, 'learning_system'):
            return {"error": "Sistema de aprendizaje no inicializado"}
        
        insights = orch.learning_system.analyze_learning_insights()
        return {
            "status": "success",
            "insights": insights
        }
        
    except Exception as e:
        logger.exception('Unhandled exception in get_learning_insights')
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INSIGHTS_ERROR", "message": str(e)}}
        )

@app.get("/api/suggestions/{client_id}")
async def get_suggested_questions(client_id: str):
    """Obtiene preguntas sugeridas para un usuario basadas en su historial."""
    try:
        if not hasattr(orch, 'learning_system'):
            return {"suggestions": []}
        
        # Usar contexto actual bÃ¡sico
        current_context = "dashboard_general"
        
        suggestions = orch.learning_system.get_suggested_questions(client_id, current_context)
        
        return {
            "status": "success",
            "client_id": client_id,
            "suggestions": suggestions,
            "context": current_context
        }
        
    except Exception as e:
        logger.exception('Unhandled exception in get_suggested_questions')
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "SUGGESTIONS_ERROR", "message": str(e)}}
        )

@app.get("/api/architecture")
async def get_architecture_info():
    """Obtiene informaciÃ³n sobre la arquitectura del orchestrator activo."""
    try:
        orchestrator_name = "LangGraphOrchestrator"
        
        # Get basic orchestrator information
        architecture_info = {
            "type": "LangGraph Architecture", 
            "agents": "Registry-based multi-agent system",
            "location": "ia_workspace/orchestrator/"
        }
        
        use_cases = ["summary", "branch_analysis", "anomaly_detection", "greeting", "small_talk"]
        
        return {
            "status": "success",
            "active_orchestrator": orchestrator_name,
            "architecture": architecture_info,
            "available_use_cases": use_cases,
            "message": f"Arquitectura {orchestrator_name} completamente implementada"
        }
        
    except Exception as e:
        logger.exception('Unhandled exception in get_architecture_info')
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "ARCHITECTURE_ERROR", "message": str(e)}}
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    logger.info(f"ðŸš€ CapiAgentes Backend Server starting on port {port}...")
    logger.info("ðŸ“Š Observable Intelligence Pipelineâ„¢ - Ready for Demo")
    logger.info("Sistema inicializado con arquitectura unificada y logging centralizado")
    uvicorn.run(app, host="0.0.0.0", port=port)

# Production-only diagnostic endpoint - logs all version requests for security monitoring
@app.get("/__version", include_in_schema=False)
async def version_info():
    """Production version info endpoint with security logging"""
    try:
        import hashlib
        from datetime import datetime
        path = Path(__file__)
        content = path.read_bytes()
        sha = hashlib.sha256(content).hexdigest()[:12]

        # Log version requests for production security monitoring
        logger.info({
            "event": "version_info_request",
            "timestamp": datetime.now().isoformat(),
            "file_hash": sha,
            "environment": os.getenv("ENVIRONMENT", "production")
        })

        return {"file": str(path), "sha256": sha, "size": len(content)}
    except Exception as e:
        logger.error({
            "event": "version_info_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
        return {"error": str(e)}


