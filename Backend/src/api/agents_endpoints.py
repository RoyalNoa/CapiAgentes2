#!/usr/bin/env python3
"""
CAPI - Agents Management API Endpoints
=====================================
Ruta: /Backend/src/api/agents_endpoints.py
Descripción: Endpoints FastAPI para gestión y configuración de agentes del sistema.
Permite activar/desactivar agentes y consultar su estado.
Estado: ✅ EN USO ACTIVO - PantallaAgentes feature
Dependencias: FastAPI, AgentConfigService, FileAgentConfigRepository
Endpoints: GET /agents, POST /agents/toggle
Propósito: Control dinámico de agentes desde UI
"""

from __future__ import annotations

import base64
import re

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

import httpx

from src.application.services.agent_config_service import AgentConfigService
from src.shared.agent_config_repository import (
    FileAgentConfigRepository,
)

# NUEVO: Imports para registro dinámico de agentes
from src.application.services.agent_registry_service import (
    AgentRegistryService,
    FileAgentRegistryRepository,
    AgentRegistrationRequest,
    AgentManifest
)
from src.application.services.token_usage_service import TokenUsageService
from typing import Any, Dict, List, Set
from datetime import datetime
from src.infrastructure.database.postgres_client import PostgreSQLClient

# Singleton-like instances for repo/service lifetime
_repo = FileAgentConfigRepository()
_service = AgentConfigService(repo=_repo)

# NUEVO: Instancias para registro dinámico
_registry_repo = FileAgentRegistryRepository()
_registry_service = AgentRegistryService(registry_repo=_registry_repo, config_service=_service)

router = APIRouter(prefix="/api", tags=["agents"])

_token_usage_service = TokenUsageService()

@router.get("/agents")
async def list_agents():
    """Pseudocódigo:
    1. Solicitar al servicio de configuración la lista de agentes con `_service.list_status()`.
    2. Transformar cada estado en un diccionario plano con `name` y `enabled`.
    3. Entregar la colección dentro de un diccionario bajo la clave `agents` para la respuesta JSON.
    """
    statuses = _service.list_status()
    return {"agents": [{"name": s.name, "enabled": s.enabled} for s in statuses]}

@router.get("/agents/ping")
async def agents_ping():
    """Pseudocódigo:
    1. No consulta servicios auxiliares.
    2. Devuelve un diccionario fijo que indica que el router de agentes está operativo.
    """
    return {"status": "ok", "router": "agents"}


@router.post("/agents/toggle")
async def toggle_agent(payload: dict = Body(...)):
    """Pseudocódigo:
    1. Leer `name` y `enabled` del payload, asegurando que `name` no esté vacío.
    2. Invocar `_service.set_enabled` para persistir el nuevo estado del agente.
    3. Responder con el estado actualizado o con un error HTTP apropiado si los datos son inválidos.
    """
    name = str(payload.get("name", "")).strip()
    if not name:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "BAD_REQUEST", "message": "Missing 'name'"}},
        )
    enabled = bool(payload.get("enabled", True))
    config = _service.set_enabled(name=name, enabled=enabled)
    return {"status": "ok", "agents": config}

@router.get("/agents/metrics")
async def get_agents_metrics():
    """Pseudocódigo:
    1. Consultar al servicio de configuración para obtener la lista de agentes y preparar el logger.
    2. Construir una lista con nombre, bandera de habilitación y descripción real de cada agente.
    3. Calcular totales de agentes activos y totales y devolver el resumen junto con un timestamp.
    4. Si ocurre una excepción, registrar el fallo y contestar con un error 500 y su mensaje.
    """
    try:
        statuses = _service.list_status()

        # Obtener información real del sistema
        from src.core.logging import get_logger
        logger = get_logger(__name__)

        agents_with_metrics = []
        for status in statuses:
            # Solo datos reales - sin simulación
            agent_data = {
                "name": status.name,
                "enabled": status.enabled,
                "description": _get_agent_description(status.name),
                "status": "active" if status.enabled else "idle",
                # NO incluir métricas simuladas - usar solo datos reales cuando estén disponibles
            }
            agents_with_metrics.append(agent_data)

        return {
            "agents": agents_with_metrics,
            "timestamp": "real",  # Se actualizará con timestamp real
            "system_status": "operational",
            "active_agents_count": sum(1 for s in statuses if s.enabled),
            "total_agents_count": len(statuses)
        }

    except Exception as e:
        logger.error(f"Error getting agents metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "METRICS_ERROR", "message": str(e)}}
        )


def _get_agent_description(agent_name: str) -> str:
    """Pseudocódigo:
    1. Revisar el diccionario local `descriptions` con textos precargados.
    2. Devolver la descripción encontrada o, si no existe, construir una cadena genérica que incluya el nombre del agente.
    """
    descriptions = {
        "summary": "Provides financial summaries and total metrics",
        "branch": "Analyzes branch-specific performance",
        "anomaly": "Detects financial irregularities and outliers",
        "smalltalk": "Handles greetings and general conversation",
        "capi_desktop": "Capi Desktop - Manages CSV, Excel, Word files with security",
        "capi_datab": "Capi DataB - Ejecuta ABMC en PostgreSQL y exporta resultados seguros"
    }
    return descriptions.get(agent_name, f"Agent: {agent_name}")


@router.post("/agents/refresh")
async def refresh_agents():
    """Pseudocódigo:
    1. Re-inicializar el repositorio de configuración para volver a leer los archivos de agentes.
    2. Volver a pedir el estado de cada agente y sincronizar el servicio de seguimiento de tokens.
    3. Entregar la lista refrescada o reportar un error 500 si algo falla.
    """
    try:
        # Reload configuration from disk
        _repo.__init__()  # Reinitialize repository

        # Get fresh status
        statuses = _service.list_status()

        # Mantener token tracking sincronizado con los agentes configurados
        _token_usage_service.ensure_agents(status.name for status in statuses)

        return {
            "status": "refreshed",
            "agents_found": len(statuses),
            "agents": [{"name": s.name, "enabled": s.enabled} for s in statuses]
        }

    except Exception as e:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error refreshing agents: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "REFRESH_ERROR", "message": str(e)}}
        )

@router.get("/agents/token-tracking")
async def get_token_tracking(days: int = Query(30, ge=1, le=90)):
    """Devuelve resumen de consumo de tokens y lnea de tiempo."""
    default_agents = ["summary", "branch", "anomaly", "smalltalk", "capi_desktop", "capi_datab"]
    try:
        return _token_usage_service.get_summary(default_agents, days=days)
    except Exception as e:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error getting token tracking: {e}")

        response = _token_usage_service.build_empty_summary(default_agents)
        response["error"] = "Could not load token tracking data"
        return response


@router.post("/agents/token-usage")
async def record_token_usage(payload: dict = Body(...)):
    """Registra manualmente consumo de tokens para un agente."""
    try:
        agent_name = str(payload.get("agent", "")).strip()
        tokens_used = int(payload.get("tokens", 0))
        cost_usd = float(payload.get("cost_usd", 0.0))
        prompt_tokens = payload.get("prompt_tokens")
        completion_tokens = payload.get("completion_tokens")
        model = str(payload.get("model") or payload.get("llm_model") or "").strip() or None
        provider = str(payload.get("provider") or "openai").strip() or "openai"
        usage_timestamp = payload.get("timestamp") or payload.get("usage_timestamp")

        result = _token_usage_service.record_usage(
            agent_name,
            tokens_used,
            cost_usd,
            prompt_tokens=int(prompt_tokens) if prompt_tokens is not None else None,
            completion_tokens=int(completion_tokens) if completion_tokens is not None else None,
            model=model,
            provider=provider,
            usage_timestamp=str(usage_timestamp) if usage_timestamp else None,
        )
        return {"status": "ok", **result}

    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "BAD_REQUEST", "message": str(exc)}}
        )
    except Exception as exc:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error recording token usage: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "RECORDING_ERROR", "message": str(exc)}}
        )


@router.get("/agents/system-status")
async def get_system_status():
    """Pseudocódigo:
    1. Medir CPU y memoria con `psutil` y contar agentes activos según la configuración actual.
    2. Armar un diccionario con los indicadores y devolverlo junto con la marca temporal.
    3. Si la medición falla, registrar el incidente y responder con métricas básicas calculadas a partir de la configuración.
    """
    try:
        from datetime import datetime
        import psutil

        # Métricas reales del sistema
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        statuses = _service.list_status()
        active_agents = sum(1 for s in statuses if s.enabled)

        return {
            "timestamp": datetime.now().isoformat(),
            "system_operational": True,
            "cpu_percent": round(cpu_percent, 1),
            "memory_percent": round(memory.percent, 1),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "active_agents": active_agents,
            "total_agents": len(statuses),
            # Sin datos simulados como uptime falso o request counts inventados
        }

    except Exception as e:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error getting system status: {e}")

        # Fallback con datos mínimos reales
        statuses = _service.list_status()
        return {
            "timestamp": datetime.now().isoformat(),
            "system_operational": True,
            "active_agents": sum(1 for s in statuses if s.enabled),
            "total_agents": len(statuses),
            "note": "Limited system metrics available"
        }


# ==========================================
# NUEVOS ENDPOINTS: REGISTRO DINÁMICO DE AGENTES
# ==========================================

# ==========================================
# ENDPOINTS: GESTIÓN DE NIVEL DE PRIVILEGIO (BD)
# ==========================================

_ALLOWED_PRIV_LEVELS = {"restricted", "standard", "elevated", "privileged", "admin"}

@router.get("/agents/privileges")
async def list_agent_privileges():
    """Pseudocódigo:
    1. Crear una conexión a Postgres mediante `PostgreSQLClient`.
    2. Ejecutar la consulta que devuelve agentes, roles y niveles de privilegio.
    3. Convertir cada fila en un diccionario serializable y enviarlo en la respuesta.
    4. Ante un fallo de base de datos, devolver un error 500 con el detalle.
    """
    try:
        db = PostgreSQLClient()
        await db.initialize()
        async with db.get_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, nombre, rol, nivel_privilegio, activo, creado_en
                FROM public.agentes
                ORDER BY nombre
                """
            )
            agentes = [
                {
                    "id": str(r[0]) if r[0] is not None else None,
                    "nombre": r[1],
                    "rol": r[2],
                    "nivel_privilegio": r[3],
                    "activo": r[4],
                    "creado_en": r[5].isoformat() if r[5] else None,
                }
                for r in rows
            ]
            return {"agents": agentes}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": {"code": "DB_ERROR", "message": str(e)}})


@router.patch("/agents/{nombre}/privilege")
async def update_agent_privilege(nombre: str, payload: dict = Body(...)):
    """Pseudocódigo:
    1. Validar que el `nivel_privilegio` solicitado esté dentro del conjunto permitido.
    2. Abrir la conexión a Postgres, verificar que el agente exista y actualizar su nivel.
    3. Leer el registro actualizado y devolverlo; si hay fallos o no existe, responder con el error adecuado.
    """
    nivel = str(payload.get("nivel_privilegio", "")).strip().lower()
    if nivel not in _ALLOWED_PRIV_LEVELS:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "BAD_REQUEST",
                    "message": f"nivel_privilegio inválido. Permitidos: {sorted(_ALLOWED_PRIV_LEVELS)}",
                }
            },
        )

    try:
        db = PostgreSQLClient()
        await db.initialize()
        async with db.get_connection() as conn:
            # Verificar existencia
            row = await conn.fetchrow(
                "SELECT id FROM public.agentes WHERE nombre = $1",
                nombre,
            )
            if not row:
                return JSONResponse(
                    status_code=404,
                    content={"error": {"code": "NOT_FOUND", "message": f"Agente '{nombre}' no existe"}},
                )

            await conn.execute(
                "UPDATE public.agentes SET nivel_privilegio = $1 WHERE nombre = $2",
                nivel,
                nombre,
            )

            # Devolver estado actualizado
            updated = await conn.fetchrow(
                "SELECT nombre, rol, nivel_privilegio, activo FROM public.agentes WHERE nombre = $1",
                nombre,
            )
            return {
                "status": "ok",
                "agent": {
                    "nombre": updated[0],
                    "rol": updated[1],
                    "nivel_privilegio": updated[2],
                    "activo": updated[3],
                },
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": {"code": "DB_ERROR", "message": str(e)}})

@router.post("/agents/register")
async def register_new_agent(payload: dict = Body(...)):
    """Pseudocódigo:
    1. Verificar que el payload incluya todos los campos obligatorios para crear un `AgentRegistrationRequest`.
    2. Construir la solicitud con los valores normalizados y registrarla a través de `_registry_service`.
    3. Si el registro es exitoso, intentar notificar al runtime para reconstruir el grafo y devolver un mensaje de éxito.
    4. Capturar y registrar errores de validación o ejecución devolviendo códigos 400 o 500 según corresponda.
    """
    try:
        from src.core.logging import get_logger
        logger = get_logger(__name__)

        # Validar campos requeridos
        required_fields = ["agent_name", "display_name", "description",
                         "agent_class_path", "node_class_path", "supported_intents"]

        for field in required_fields:
            if not payload.get(field):
                return JSONResponse(
                    status_code=400,
                    content={"error": {"code": "BAD_REQUEST", "message": f"Missing required field: {field}"}}
                )

        # Crear request de registro
        registration_request = AgentRegistrationRequest(
            agent_name=str(payload["agent_name"]).strip(),
            display_name=str(payload["display_name"]).strip(),
            description=str(payload["description"]).strip(),
            agent_class_path=str(payload["agent_class_path"]).strip(),
            node_class_path=str(payload["node_class_path"]).strip(),
            supported_intents=payload["supported_intents"],
            capabilities=payload.get("capabilities", {}),
            metadata=payload.get("metadata", {}),
            enabled=payload.get("enabled", True)
        )

        # Registrar el agente
        success = _registry_service.register_agent(registration_request)

        if success:
            logger.info(f"Agent registered successfully: {registration_request.agent_name}")

            # INTEGRACIÓN: Reconstruir grafo en el orchestrator
            try:
                from src.api.main import orchestrator
                if hasattr(orchestrator, 'runtime') and hasattr(orchestrator.runtime, 'register_agent_dynamically'):
                    success = orchestrator.runtime.register_agent_dynamically(registration_request.agent_name)
                    if not success:
                        logger.warning(f"Failed to rebuild graph for agent {registration_request.agent_name}")
            except Exception as e:
                logger.error(f"Error rebuilding graph for agent {registration_request.agent_name}: {e}")

            return {
                "status": "success",
                "message": f"Agent '{registration_request.display_name}' registered successfully",
                "agent_name": registration_request.agent_name,
                "enabled": registration_request.enabled
            }
        else:
            return JSONResponse(
                status_code=500,
                content={"error": {"code": "REGISTRATION_FAILED", "message": "Failed to register agent"}}
            )

    except ValueError as e:
        logger.error(f"Validation error registering agent: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        )
    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "REGISTRATION_ERROR", "message": str(e)}}
        )


@router.delete("/agents/{agent_name}/unregister")
async def unregister_agent(agent_name: str):
    """Pseudocódigo:
    1. Normalizar el nombre del agente y confirmar que exista en el registro.
    2. Solicitar al servicio que elimine al agente y, si lo logra, pedir al runtime que actualice el grafo.
    3. Responder con confirmación o con errores descriptivos cuando el agente no exista o falle el proceso.
    """
    try:
        from src.core.logging import get_logger
        logger = get_logger(__name__)

        agent_name = agent_name.strip()
        if not agent_name:
            return JSONResponse(
                status_code=400,
                content={"error": {"code": "BAD_REQUEST", "message": "Agent name cannot be empty"}}
            )

        # Verificar que el agente existe
        if not _registry_service.is_agent_registered(agent_name):
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "AGENT_NOT_FOUND", "message": f"Agent '{agent_name}' not found in registry"}}
            )

        # Desregistrar el agente
        success = _registry_service.unregister_agent(agent_name)

        if success:
            logger.info(f"Agent unregistered successfully: {agent_name}")

            # INTEGRACIÓN: Reconstruir grafo en el orchestrator
            try:
                from src.api.main import orchestrator
                if hasattr(orchestrator, 'runtime') and hasattr(orchestrator.runtime, 'unregister_agent_dynamically'):
                    success = orchestrator.runtime.unregister_agent_dynamically(agent_name)
                    if not success:
                        logger.warning(f"Failed to rebuild graph after unregistering agent {agent_name}")
            except Exception as e:
                logger.error(f"Error rebuilding graph after unregistering agent {agent_name}: {e}")

            return {
                "status": "success",
                "message": f"Agent '{agent_name}' unregistered successfully",
                "agent_name": agent_name
            }
        else:
            return JSONResponse(
                status_code=500,
                content={"error": {"code": "UNREGISTRATION_FAILED", "message": "Failed to unregister agent"}}
            )

    except Exception as e:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error unregistering agent {agent_name}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "UNREGISTRATION_ERROR", "message": str(e)}}
        )

@router.get("/agents/registry")
async def list_registered_agents():
    """Pseudocódigo:
    1. Recuperar todos los manifiestos almacenados en el registro dinámico.
    2. Transformar cada manifiesto en un diccionario con sus metadatos y el estado `enabled`.
    3. Devolver la lista junto con el total o reportar un error 500 si ocurre una excepción.
    """
    try:
        registered_agents = _registry_service.list_registered_agents()

        agents_data = []
        for manifest in registered_agents:
            agents_data.append({
                "agent_name": manifest.agent_name,
                "display_name": manifest.display_name,
                "version": manifest.version,
                "description": manifest.description,
                "category": manifest.category,
                "supported_intents": manifest.supported_intents,
                "capabilities": manifest.capabilities,
                "enabled": _service.is_enabled(manifest.agent_name),
                "created_at": manifest.created_at,
                "author": manifest.author
            })

        return {
            "status": "success",
            "total_registered": len(registered_agents),
            "agents": agents_data
        }

    except Exception as e:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error listing registered agents: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "LISTING_ERROR", "message": str(e)}}
        )

@router.get("/agents/{agent_name}/manifest")
async def get_agent_manifest(agent_name: str):
    """Pseudocódigo:
    1. Limpiar el nombre recibido y consultar el manifiesto en el registro.
    2. Si no existe, responder 404; de lo contrario, empaquetar los metadatos y el estado `enabled`.
    3. Registrar fallas inesperadas y responder con error 500 cuando sea necesario.
    """
    try:
        agent_name = agent_name.strip()
        manifest = _registry_service.get_agent_manifest(agent_name)

        if not manifest:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "AGENT_NOT_FOUND", "message": f"Agent '{agent_name}' not found in registry"}}
            )

        return {
            "status": "success",
            "agent_name": manifest.agent_name,
            "manifest": {
                "display_name": manifest.display_name,
                "version": manifest.version,
                "description": manifest.description,
                "category": manifest.category,
                "supported_intents": manifest.supported_intents,
                "capabilities": manifest.capabilities,
                "metadata": manifest.metadata,
                "author": manifest.author,
                "created_at": manifest.created_at
            },
            "enabled": _service.is_enabled(agent_name)
        }

    except Exception as e:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error getting agent manifest {agent_name}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "MANIFEST_ERROR", "message": str(e)}}
        )

@router.get("/agents/registry/stats")
async def get_registry_stats():
    """Pseudocódigo:
    1. Solicitar al registro dinámico sus estadísticas agregadas.
    2. Consultar la configuración actual para contar agentes habilitados y deshabilitados.
    3. Devolver ambos conjuntos de números con un timestamp o emitir error 500 ante fallas.
    """
    try:
        stats = _registry_service.get_registry_stats()

        # Agregar información de configuración
        config_statuses = _service.list_status()
        enabled_count = sum(1 for s in config_statuses if s.enabled)

        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "registry_stats": stats,
            "configuration_stats": {
                "total_configured_agents": len(config_statuses),
                "enabled_agents": enabled_count,
                "disabled_agents": len(config_statuses) - enabled_count
            }
        }

    except Exception as e:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error getting registry stats: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "STATS_ERROR", "message": str(e)}}
        )


@router.post("/agents/registry/refresh")
async def refresh_agent_registry():
    """Pseudocódigo:
    1. Ordenar al servicio de registro que vuelva a cargar la información persistida.
    2. Responder con el total de agentes detectados y la hora de actualización.
    3. Registrar cualquier excepción y devolver un error 500 si la operación falla.
    """
    try:
        agent_count = _registry_service.refresh_registry()

        return {
            "status": "success",
            "message": "Agent registry refreshed successfully",
            "total_agents": agent_count,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error refreshing agent registry: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "REFRESH_ERROR", "message": str(e)}}
        )








class GraphEndpointError(Exception):
    """Representa errores controlados al exponer el grafo de LangGraph."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _resolve_langgraph_graph(logger) -> tuple[object, str]:
    """Pseudocódigo:
    1. Extraer el runtime del orquestador y determinar si se usa grafo dinámico o estático.
    2. Obtener el grafo compilado y devolver el objeto `graph` junto con la fuente.
    3. Lanzar `GraphEndpointError` con información clara cuando falte el runtime o falle el acceso."""
    from src.api.main import orchestrator

    if not hasattr(orchestrator, "runtime"):
        raise GraphEndpointError(503, "GRAPH_UNAVAILABLE", "LangGraph runtime not initialized")

    runtime = orchestrator.runtime
    has_dynamic = getattr(runtime, "is_dynamic_system_available", None)
    graph_source = "dynamic" if callable(has_dynamic) and runtime.is_dynamic_system_available() else "static"

    compiled_graph = getattr(runtime, "graph", None)
    if compiled_graph is None:
        compiled_graph = getattr(runtime, "static_graph", None)
        graph_source = "static"

    if compiled_graph is None:
        raise GraphEndpointError(503, "GRAPH_MISSING", "No compiled LangGraph available")

    try:
        graph_obj = compiled_graph.get_graph()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error({"event": "graph_get_error", "error": str(exc)})
        raise GraphEndpointError(500, "GRAPH_ACCESS_ERROR", "Unable to access graph structure") from exc

    return graph_obj, graph_source


async def _render_mermaid_png_with_fallback(
    graph_obj, *, logger
) -> tuple[bytes | None, str | None]:
    """Genera el PNG del grafo priorizando renderizado local y registrando errores."""

    # Nota: mantenemos el mismo orden que sugiere la documentacion de LangGraph.
    # 1) draw_mermaid_png (API LangGraph) para replicar display(Image(...)).
    # 2) Render local con Pyppeteer para no depender de servicios externos.
    # 3) mermaid.ink como ultimo recurso, siempre registrando la falla previa.

    errors: list[str] = []
    mermaid_diagram: str | None = None

    try:
        from langchain_core.runnables.graph import MermaidDrawMethod
    except Exception as import_exc:  # pragma: no cover - dependencia opcional
        MermaidDrawMethod = None
        logger.debug({
            "event": "graph_png_mermaid_method_unavailable",
            "error": str(import_exc),
        })

    attempt_specs: list[tuple[str, dict[str, object]]] = []
    if MermaidDrawMethod is not None:
        attempt_specs.append(
            (
                "mermaid_api",
                {
                    "draw_method": MermaidDrawMethod.API,
                    "max_retries": 3,
                    "retry_delay": 2.0,
                },
            )
        )
    attempt_specs.append(("default_draw", {}))

    for label, call_kwargs in attempt_specs:
        try:
            png_bytes = graph_obj.draw_mermaid_png(**call_kwargs)
            if png_bytes:
                return png_bytes, None
        except Exception as exc:  # pragma: no cover - defensivo
            logger.warning(
                {
                    "event": "graph_png_attempt_failed",
                    "method": label,
                    "error": str(exc),
                }
            )
            errors.append(f"{label}: {exc}")

    def _ensure_mermaid_diagram() -> str | None:
        nonlocal mermaid_diagram
        if mermaid_diagram is not None:
            return mermaid_diagram
        try:
            mermaid_diagram = graph_obj.draw_mermaid()
            return mermaid_diagram
        except Exception as exc:  # pragma: no cover - defensivo
            logger.error({
                "event": "graph_png_mermaid_source_error",
                "error": str(exc),
            })
            errors.append(f"mermaid_text: {exc}")
            return None

    diagram = _ensure_mermaid_diagram()
    if not diagram:
        summarized_errors = "; ".join(errors) if errors else "Unable to render Mermaid PNG"
        return None, summarized_errors

    custom_png, pyppeteer_error = await _render_mermaid_png_via_pyppeteer(
        diagram,
        logger=logger,
    )
    if custom_png:
        return custom_png, None
    if pyppeteer_error:
        errors.append(f"pyppeteer: {pyppeteer_error}")

    fallback_bytes = _fetch_mermaid_png_via_service(diagram, logger=logger)
    if fallback_bytes is not None:
        return fallback_bytes, None

    errors.append("mermaid_ink: remote renderer unavailable")
    summarized_errors = "; ".join(errors) if errors else "Unable to render Mermaid PNG"
    return None, summarized_errors


def _fetch_mermaid_png_via_service(mermaid_diagram: str, *, logger) -> bytes | None:
    """Envía el diagrama Mermaid al servicio mermaid.ink para obtener un PNG."""
    if not mermaid_diagram or not mermaid_diagram.strip():
        return None

    try:
        encoded = base64.urlsafe_b64encode(mermaid_diagram.encode("utf-8")).decode("ascii")
        url = f"https://mermaid.ink/img/{encoded}"
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content
    except httpx.HTTPError as exc:  # pragma: no cover - depende del servicio externo
        logger.warning({"event": "graph_png_http_error", "error": str(exc)})
    except Exception as exc:  # pragma: no cover - defensivo
        logger.error({"event": "graph_png_fallback_exception", "error": str(exc)})
    return None


MERMAID_JS_URL = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"
_MERMAID_JS_CACHE: dict[str, str] = {}


def _load_mermaid_js_bundle(*, logger) -> str | None:
    """Descarga y cachea Mermaid.js para renderizar sin depender del CDN desde el navegador."""

    cached = _MERMAID_JS_CACHE.get("content")
    if cached:
        return cached

    try:
        response = httpx.get(MERMAID_JS_URL, timeout=15.0)
        response.raise_for_status()
        _MERMAID_JS_CACHE["content"] = response.text
        return _MERMAID_JS_CACHE["content"]
    except httpx.HTTPError as exc:  # pragma: no cover - depende del CDN
        logger.warning(
            {
                "event": "graph_mermaid_js_http_error",
                "error": str(exc),
                "url": MERMAID_JS_URL,
            }
        )
    except Exception as exc:  # pragma: no cover - defensivo
        logger.error({"event": "graph_mermaid_js_unexpected", "error": str(exc)})
    return None


async def _render_mermaid_png_via_pyppeteer(
    mermaid_diagram: str,
    *,
    logger,
    background_color: str = "#ffffff",
    padding: int = 24,
) -> tuple[bytes | None, str | None]:
    """Genera un PNG usando Pyppeteer en caso de que draw_mermaid_png falle."""

    try:
        from pyppeteer import launch
    except ImportError as exc:  # pragma: no cover - dependencia opcional
        return None, f"pyppeteer_missing: {exc}"

    script_content = _load_mermaid_js_bundle(logger=logger)
    if not script_content:
        return None, "mermaid_js_unavailable"

    browser = await launch(
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )

    try:
        page = await browser.newPage()
        html_template = (
            "<html><head><style>body{margin:0;padding:0;background:%s;}"
            "#mermaid-host{display:inline-block;padding:0;margin:0;}</style></head>"
            "<body><div id='mermaid-host'></div></body></html>"
        ) % background_color
        await page.setContent(html_template)
        await page.addScriptTag({"content": script_content})

        await page.waitForFunction("window.mermaid && window.mermaid.mermaidAPI", timeout=5000)

        await page.evaluate(
            """(graph) => {
                window.mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });
                const host = document.getElementById('mermaid-host');
                const renderResult = window.mermaid.mermaidAPI.render('capi_graph', graph);
                host.innerHTML = renderResult.svg;
            }""",
            mermaid_diagram,
        )

        dimensions = await page.evaluate(
            """(padding) => {
                const svg = document.querySelector('#mermaid-host svg');
                if (!svg) {
                    throw new Error('SVG render failed');
                }
                const bbox = svg.getBBox();
                const width = Math.ceil(bbox.width + padding);
                const height = Math.ceil(bbox.height + padding);
                return { width, height };
            }""",
            padding,
        )

        width = max(int(dimensions["width"]), 64)
        height = max(int(dimensions["height"]), 64)

        await page.setViewport(
            {
                "width": width,
                "height": height,
                "deviceScaleFactor": 2,
                "isLandscape": width >= height,
            }
        )

        await page.evaluate(
            """(background) => {
                const svg = document.querySelector('#mermaid-host svg');
                if (svg) {
                    svg.style.background = background;
                    svg.style.margin = '0';
                }
            }""",
            background_color,
        )

        img_bytes = await page.screenshot({"fullPage": False})
        return img_bytes, None
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning({"event": "graph_pyppeteer_render_failed", "error": str(exc)})
        return None, str(exc)
    finally:
        try:
            await browser.close()
        except Exception:  # pragma: no cover - mejor esfuerzo
            pass


_MERMAID_NODE_PATTERN = re.compile(r'^([A-Za-z0-9_]+)\(')


def _extract_mermaid_nodes(mermaid_diagram: str) -> Set[str]:
    """Obtiene el conjunto de nodos definidos en un diagrama Mermaid."""

    nodes: Set[str] = set()
    for raw_line in mermaid_diagram.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("classDef") or line.startswith("%%"):
            continue
        if "-->" in line or "-.->" in line or line.endswith(";"):
            continue
        match = _MERMAID_NODE_PATTERN.match(line)
        if match:
            nodes.add(match.group(1))
    return nodes


def _build_conceptual_mermaid_diagram(graph_obj, *, logger) -> str:
    """Arma un diagrama conceptual con recursos reales (DB/desktop) y Capi Alertas."""

    base_diagram = graph_obj.draw_mermaid()
    observed_nodes = _extract_mermaid_nodes(base_diagram)

    required_core = {
        "__start__",
        "start",
        "intent",
        "react",
        "reasoning",
        "supervisor",
        "router",
        "human_gate",
        "assemble",
        "finalize",
        "__end__",
    }

    missing = required_core - observed_nodes
    if missing:
        logger.warning(
            {
                "event": "conceptual_core_missing",
                "missing_nodes": sorted(missing),
            }
        )

    lines: list[str] = [
        "---",
        "config:",
        "  flowchart:",
        "    curve: linear",
        "---",
        "graph TD;",
        "    classDef control fill:#1b2233,stroke:#7df9ff,color:#e6f1ff,line-height:1.2;",
        "    classDef agent fill:#f2f0ff,stroke:#4540a0,color:#1c1858,line-height:1.2;",
        "    classDef resource fill:#e0f7ff,stroke:#0284c7,color:#064e64;",
        "    classDef integration fill:#efe9ff,stroke:#7c3aed,color:#2f1f6b;",
        "",
        "    __start__([<p>__start__</p>]):::control",
        "    start(start):::control",
        "    intent(intent):::control",
        "    react(react):::control",
        "    reasoning(reasoning):::control",
        "    supervisor(supervisor):::control",
        "    loop_controller(loop_controller):::control",
        "    router(router):::control",
        "    smalltalk(smalltalk):::agent",
        "    summary(summary):::agent",
        "    branch(branch):::agent",
        "    anomaly(anomaly):::agent",
        "    capi_noticias(capi_noticias):::agent",
        "    capi_desktop(capi_desktop):::agent",
        "    capi_datab(capi_datab):::agent",
        "    capi_alertas(capi_alertas):::agent",
        "    human_gate(human_gate):::control",
        "    assemble(assemble):::control",
        "    finalize(finalize):::control",
        "    __end__([<p>__end__</p>]):::control",
        "    datastore[(PostgreSQL capi_alerts)]:::resource",
        "    user_desktop[[User Desktop Files]]:::resource",
        "",
        "    subgraph Recursos__Persistencia",
        "        datastore",
        "    end",
        "    subgraph Recursos__Externos",
        "        user_desktop",
        "    end",
        "",
        "    __start__ --> start;",
        "    start --> intent;",
        "    intent --> react;",
        "    react --> reasoning;",
        "    reasoning --> supervisor;",
        "    supervisor --> loop_controller;",
        "    loop_controller --> router;",
        "    loop_controller --> assemble;",
        "    router -.-> smalltalk;",
        "    router -.-> summary;",
        "    router -.-> branch;",
        "    router -.-> anomaly;",
        "    router -.-> capi_noticias;",
        "    router -.-> capi_desktop;",
        "    router -.-> capi_datab;",
        "    capi_datab -->|alertas| capi_alertas;",
        "    capi_datab -->|exporta evidencia| capi_desktop;",
        "    smalltalk --> assemble;",
        "    summary --> assemble;",
        "    branch --> assemble;",
        "    anomaly --> assemble;",
        "    capi_desktop --> assemble;",
        "    capi_datab --> assemble;",
        "    capi_alertas -->|aprobado| capi_desktop;",
        "    capi_alertas -->|rechazado| assemble;",
        "    capi_desktop --> user_desktop;",
        "    human_gate --> assemble;",
        "    assemble --> finalize;",
        "    finalize --> __end__;",
    ]

    return "\n".join(lines) + "\n"
@router.get("/agents/graph/mermaid_svg")
async def get_agents_graph_mermaid_svg():
    """Pseudocódigo:
    1. Resolver el grafo de LangGraph mediante `_resolve_langgraph_graph`.
    2. Renderizar la salida Mermaid (texto) con `draw_mermaid()` y devolverla con metadatos básicos.
    3. Capturar errores controlados y retornarlos como JSON con el código HTTP correspondiente."""
    from src.core.logging import get_logger
    logger = get_logger(__name__)

    try:
        graph_obj, graph_source = _resolve_langgraph_graph(logger)

        try:
            mermaid_diagram = graph_obj.draw_mermaid()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error({"event": "graph_draw_error", "error": str(exc)})
            raise GraphEndpointError(500, "GRAPH_RENDER_ERROR", "Failed to render Mermaid diagram") from exc

        # Nota: esta respuesta solo transporta Mermaid SVG en texto; el PNG se maneja en el endpoint hermano.
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "source": graph_source,
            "diagram": mermaid_diagram,
        }

    except GraphEndpointError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )




@router.get("/agents/graph/mermaid_png")
async def get_agents_graph_mermaid_png():
    """Pseudocódigo:
    1. Resolver el grafo mediante `_resolve_langgraph_graph`.
    2. Probar `draw_mermaid_png` (API) y un render local con Pyppeteer usando el mismo Mermaid dinámico.
    3. Si todo falla, acudir a mermaid.ink; finalmente codificar en Base64 el PNG (equivalente a `display(Image(graph.get_graph().draw_mermaid_png()))`)."""
    from src.core.logging import get_logger
    logger = get_logger(__name__)

    try:
        graph_obj, graph_source = _resolve_langgraph_graph(logger)

        png_bytes = None
        png_error: str | None = None

        if hasattr(graph_obj, "draw_mermaid_png"):
            png_bytes, png_error = await _render_mermaid_png_with_fallback(graph_obj, logger=logger)
        else:
            png_error = "Mermaid PNG rendering not supported by current graph object"

        if png_bytes:
            encoded_png = base64.b64encode(png_bytes).decode("ascii")
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "source": graph_source,
                "diagram_png": encoded_png,
                "diagram_png_mime": "image/png",
            }

        # Nota: esta ruta solo traslada la vista PNG; el frontend mantiene el toggle SVG/PNG.
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "source": graph_source,
            "diagram_png_error": png_error or "Unable to render Mermaid PNG",
        }

    except GraphEndpointError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )


@router.get("/agents/graph/mermaid_conceptual")
async def get_agents_graph_mermaid_conceptual():
    """Pseudocódigo:
    1. Resolver el grafo real de LangGraph y tomar como referencia su Mermaid base.
    2. Construir un diagrama conceptual agregando recursos reales (PostgreSQL, Desktop) y el módulo Capi Alertas.
    3. Devolver la cadena Mermaid resultante indicando que se trata de la vista conceptual."""

    from src.core.logging import get_logger

    logger = get_logger(__name__)

    try:
        graph_obj, graph_source = _resolve_langgraph_graph(logger)
        conceptual_diagram = _build_conceptual_mermaid_diagram(graph_obj, logger=logger)

        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "source": graph_source,
            "view": "conceptual",
            "diagram": conceptual_diagram,
        }

    except GraphEndpointError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
@router.get("/agents/graph/status")
async def get_dynamic_graph_status():
    """Pseudocódigo:
    1. Confirmar que el runtime exponga `get_dynamic_graph_status`.
    2. Si existe, devolver el estado del grafo junto con la bandera de disponibilidad; si no, responder con un estado mínimo.
    3. Capturar excepciones, registrarlas y contestar con error 500 cuando corresponda.
    """
    try:
        from src.api.main import orchestrator

        # Verificar si el sistema dinámico está disponible
        if hasattr(orchestrator, 'runtime') and hasattr(orchestrator.runtime, 'get_dynamic_graph_status'):
            graph_status = orchestrator.runtime.get_dynamic_graph_status()
            is_dynamic = orchestrator.runtime.is_dynamic_system_available()

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "dynamic_system_available": is_dynamic,
                "graph_status": graph_status
            }
        else:
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "dynamic_system_available": False,
                "message": "Dynamic graph system not available in current orchestrator"
            }

    except Exception as e:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error getting dynamic graph status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "GRAPH_STATUS_ERROR", "message": str(e)}}
        )


@router.post("/agents/graph/refresh")
async def refresh_dynamic_graph():
    """Pseudocódigo:
    1. Verificar que el runtime provea `refresh_dynamic_graph`.
    2. Ejecutar la actualización y responder éxito, fallo controlado o sistema no disponible según el resultado.
    3. Registrar y devolver error 500 si ocurre una excepción.
    """
    try:
        from src.api.main import orchestrator

        if hasattr(orchestrator, 'runtime') and hasattr(orchestrator.runtime, 'refresh_dynamic_graph'):
            success = orchestrator.runtime.refresh_dynamic_graph()

            if success:
                return {
                    "status": "success",
                    "message": "Dynamic graph refreshed successfully",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return JSONResponse(
                    status_code=500,
                    content={"error": {"code": "REFRESH_FAILED", "message": "Failed to refresh dynamic graph"}}
                )
        else:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "SYSTEM_NOT_AVAILABLE", "message": "Dynamic graph system not available"}}
            )

    except Exception as e:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error refreshing dynamic graph: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "GRAPH_REFRESH_ERROR", "message": str(e)}}
        )



@router.get("/agents/capi_noticias/status")
async def get_capi_noticias_status():
    """Pseudocódigo:
    1. Consultar al programador `_news_scheduler` por su estado actual.
    2. Devolver los datos envueltos en una respuesta con timestamp.
    3. Registrar excepciones y responder con HTTP 500 si la consulta falla.
    """
    try:
        status = _news_scheduler.get_status()
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": status
        }
    except Exception as e:
        from src.core.logging import get_logger
        get_logger(__name__).error(f"Error getting Capi Noticias status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "CAPI_NOTICIAS_STATUS_ERROR", "message": str(e)}}
        )


@router.post("/agents/capi_noticias/config")
async def update_capi_noticias_config(payload: Dict[str, Any] = Body(...)):
    """Pseudocódigo:
    1. Leer los parámetros opcionales del payload y pasarlos a `_news_scheduler.update_configuration`.
    2. Devolver la configuración resultante y la marca temporal.
    3. Registrar excepciones y contestar con error 500 si ocurriera algún problema.
    """
    try:
        config = _news_scheduler.update_configuration(
            interval_minutes=payload.get("interval_minutes"),
            source_urls=payload.get("source_urls"),
            max_articles_per_source=payload.get("max_articles_per_source"),
            enabled=payload.get("enabled"),
            segments=payload.get("segments") or payload.get("segment_thresholds"),
        )
        return {
            "status": "success",
            "message": "Configuración actualizada",
            "config": config,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        from src.core.logging import get_logger
        get_logger(__name__).error(f"Error updating Capi Noticias config: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "CAPI_NOTICIAS_CONFIG_ERROR", "message": str(e)}}
        )


@router.post("/agents/capi_noticias/start")
async def start_capi_noticias():
    """Pseudocódigo:
    1. Invocar `_news_scheduler.start()` para poner en marcha el scheduler.
    2. Confirmar la operación o devolver un error 500 si se produce una excepción.
    """
    try:
        _news_scheduler.start()
        return {"status": "success", "message": "Capi Noticias scheduler started"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "CAPI_NOTICIAS_START_ERROR", "message": str(e)}}
        )


@router.post("/agents/capi_noticias/stop")
async def stop_capi_noticias():
    """Pseudocódigo:
    1. Llamar a `_news_scheduler.stop()` para detener el scheduler.
    2. Responder con confirmación o con un error 500 si la parada falla.
    """
    try:
        _news_scheduler.stop()
        return {"status": "success", "message": "Capi Noticias scheduler stopped"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "CAPI_NOTICIAS_STOP_ERROR", "message": str(e)}}
        )


@router.post("/agents/capi_noticias/run")
async def run_capi_noticias(payload: Dict[str, Any] | None = Body(None)):
    """Pseudocódigo:
    1. Asegurar que el payload sea un diccionario y extraer parámetros opcionales para la ejecución manual.
    2. Disparar `_news_scheduler.trigger_run` registrando que la ejecución proviene de la API.
    3. Devolver el resultado con su resumen o, ante un fallo, registrar y responder con error 500.
    """
    payload = payload or {}
    try:
        result = _news_scheduler.trigger_run(
            trigger="manual_api",
            source_urls=payload.get("source_urls"),
            max_articles_per_source=payload.get("max_articles_per_source"),
        )
        return {
            "status": "success",
            "message": result.get("summary", {}).get("headline", "Ejecución completada"),
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        from src.core.logging import get_logger
        get_logger(__name__).error(f"Error executing Capi Noticias run: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "CAPI_NOTICIAS_RUN_ERROR", "message": str(e)}}
        )









