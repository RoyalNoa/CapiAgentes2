# Task 02 - Orquestacion, ejecucion y streaming de estado

## Objetivo
Implementar la tuberia de ejecucion y eventos en vivo inspirada en el stack de n8n (`WorkflowRunner`, `ActiveWorkflowManager`, `push`).

## Alcance
- Reforzar la fabrica de orquestadores para montar `LangGraph` con capacidades de ejecucion granular.
- Implementar un servicio de ejecuciones (`ExecutionService`) que transforme `AgentWorkflowDto` en instancias ejecutables.
- Habilitar un backend de push (SSE/WebSocket) con tipado basado en los mensajes de n8n.

## Pasos sugeridos
1. Crear modulo `Backend/src/application/services/execution_service.py` que acepte `workflow_id/session_id`, valide permisos y dispare la ejecucion.
2. Integrar con el runtime actual (`langgraph_ws_endpoint`) para que los eventos se envien via `websocket.send_json` con la forma acordada en Task 01.
3. Anadir un adaptador de persistencia para almacenar ejecuciones recientes (`GET /agents/workflows/{id}/executions`).
4. Reutilizar/crear colas o mecanismos async para soportar reintentos, pausa/continuacion y cancelaciones.
5. Asegurar trazabilidad (`trace_id`, metricas) y logging estructurado.

## Criterios de aceptacion
- Pruebas de integracion basicas (pueden mockear LangGraph) verificando que los eventos push se emiten en orden y con payload valido.
- Endpoint `POST /agents/workflows/run` retornando `execution_id` y permitiendo consultar estado por `GET /agents/executions/{execution_id}`.
- Manejo de errores y desconexiones documentado.
