# Task 02 - Orquestacion, ejecucion y streaming de estado (backend)

## Objetivo irrenunciable
Replicar en FastAPI/LangGraph la tuberia de ejecucion manual similar a n8n: orquestar workflows, gestionar colas, emitir eventos push con la misma granularidad (`executionStarted`, `nodeExecuteAfter`, etc.) y persistir historicos.

## Referencias obligatorias
- Gestion de ejecuciones n8n: `tablero/GraphCanva/references/workflow-execution.service.ts`, `workflow-runner.ts`, `active-workflow-manager.ts`, `active-executions.ts`.
- Push backend n8n: `tablero/GraphCanva/references/push-index.ts` y `tablero/GraphCanva/references/push-execution.ts`.
- Endpoints actuales CAPI: `Backend/src/presentation/websocket_langgraph.py`, `Backend/src/api/agents_endpoints.py` (metodos `/agents/graph/status`, `/agents/graph/refresh`).
- DTOs definidos en Task 01 (`Backend/src/presentation/schemas/graph.py`).
- Estado LangGraph actual: `Backend/src/infrastructure/langgraph/state_schema.py`, `Backend/src/infrastructure/langgraph/` (nodos y runtime).

## Entregables concretos
1. Servicio `Backend/src/application/services/execution_service.py` con responsabilidades:
   - `queue_manual_execution(workflow_id, session_id, agent_payload)` -> crea ejecucion alineada con `WorkflowRunner.run`.
   - `get_execution(execution_id)` -> retorna DTO `AgentExecutionDto` (similar a `IExecutionResponse`).
   - `list_executions(workflow_id, limit, offset)` -> historial resumido.
   - `cancel_execution(execution_id)` -> equivalente a `ActiveExecutions.stopExecution()`.
2. Gestor runtime `Backend/src/infrastructure/langgraph/runtime/execution_manager.py` que encapsule:
   - Transformacion `AgentWorkflowDto` -> instancia LangGraph.
   - Registro en cola asincrona (`asyncio.Queue`) y workers dedicados.
   - Conexion con `GraphState` para actualizar estado y recuperar `agent_results`.
3. Integracion push:
   - Extender `LangGraphWebSocketEndpoint` para suscribirse a eventos de `ExecutionService`.
   - Implementar `PushGateway` (wrapper) que reproduzca metodos `send`, `broadcast`, `has_push_ref` inspirados en `Push` de n8n (ver `push-index.ts`).
   - Hookear cada transicion (inicio, antes/despues de nodo, fin) para emitir `AgentPushMessage` definido en Task 01.
4. Persistencia minima:
   - Repositorio en memoria `ExecutionRepository` (dict) con metodos `save`, `get`, `list`, `update_status`. Dejar TODO para mover a DB.
   - Serializar `GraphState` y `AgentWorkflowDto` (solo campos necesarios) para consulta posterior (`execution.summary`).
5. Endpoints reales en router `graph_workflows.py`:
   - `POST /agents/workflows/{id}/run` -> dispara `queue_manual_execution`, devuelve `{ "execution_id": ..., "status_url": ..., "push_ref": ... }`.
   - `GET /agents/executions/{execution_id}` -> `AgentExecutionDto`.
   - `GET /agents/workflows/{id}/executions` -> lista paginada.
   - `POST /agents/executions/{execution_id}/cancel`.
6. Suite de pruebas en `Backend/tests/test_execution_service.py` con mocks de LangGraph y del gateway push.

## Algoritmos n8n a adaptar (sin copiar literal)
- `packages/cli/src/workflows/workflow-execution.service.ts`: replicar la orquestación de `runWorkflow`, hooks y construcción de `IRunExecutionData`, ajustándolo a FastAPI/LangGraph.
- `packages/cli/src/workflow-runner.ts`: usar como guía la colaboración entre `WorkflowRunner`, `ActiveExecutions`, colas y hooks lifecycle.
- `packages/cli/src/active-executions.ts`: adaptar la gestión de ejecuciones activas (add/finish/cancel) manteniendo estados y persistencia.
- `packages/cli/src/push/index.ts`: implementar validaciones de payload, multiplexado y control `pushRef` respetando el límite de 5 MiB y orden de eventos.
- `packages/@n8n/api-types/src/push/execution.ts`: asegurar paridad de mensajes `executionStarted`, `nodeExecuteAfter`, `executionFinished`, etc.
- `packages/cli/src/push/websocket.push.ts` y `sse.push.ts`: tomar como referencia patrones de reconexión y limpieza de sesiones aunque se use solo WebSocket en CAPI.

Adaptar las ideas a nuestra arquitectura (FastAPI + websockets propios), evitando copiar código literal pero conservando el comportamiento observable (orden de eventos, campos, validación de errores).
## Pasos detallados
1. **Diseno de ExecutionService (mirroring n8n)**
   - Revisar `workflow-execution.service.ts` para entender `runExecutionData`, `createExecutionData`, `pushExecutionStartedEvent`.
   - Implementar metodos equivalentes:
     - `build_execution_context` produce `ExecutionContext` (workflow dto, graph state inicial, metadata, push_ref).
     - `enqueue_execution` mete contexto en `ExecutionManager` y devuelve `execution_id`.
     - `await_result` (opcional) usara `asyncio.create_task` para observar finalizacion.
   - Registrar tiempos `started_at`, `stopped_at`, `status` (`running`, `success`, `error`, `cancelled`).
2. **ExecutionManager y workers**
   - Basarse en `workflow-runner.ts` (`run`) y `active-executions.ts` (`add`, `finish`, `stopExecution`).
   - Implementar clase `ExecutionManager` con atributos:
     - `self.queue: asyncio.Queue[ExecutionContext]`.
     - `self.active: dict[str, ActiveExecutionState]` (`started_at`, `status`, `cancel_event`, `push_ref`).
     - `self.worker_task = asyncio.create_task(self._worker_loop())` lanzado al inicializar.
   - `_worker_loop` debe:
     - sacar contextos de la cola,
     - emitir `execution_started` via push,
     - ejecutar `LangGraphOrchestrator` (inyeccion en Task 02) capturando eventos de nodo,
     - manejar errores y actualizar `status`.
   - Permitir multiples workers configurables (ver `ActiveWorkflowManager` para inspiracion). Por defecto 1 worker.
3. **Eventos de nodo**
   - Instrumentar nodos LangGraph para emitir callbacks. Si no existe hook, envolver `GraphNode.execute` y usar `try/finally` para enviar `node_execute_after` y `node_execute_after_data`.
   - Estructura de eventos:
     1. `AgentPushMessage(type='execution_started')` antes de ejecutar primer nodo.
     2. Para cada nodo: `node_execute_before`, `node_execute_after`, `node_execute_after_data`.
     3. Final: `execution_finished` (status segun resultado) o `execution_waiting` si se pausa.
   - Adjuntar `item_count_by_connection_type` usando longitud de outputs (ver `push-execution.ts`).
4. **PushGateway**
   - Crear `Backend/src/presentation/push/push_gateway.py` con metodos:
     - `register(push_ref: str, websocket: WebSocket)`.
     - `deregister(push_ref: str)`.
     - `send(push_ref: str, message: AgentPushMessage)` -> usa helper `validate_payload_size` (Task 01).
     - `broadcast(message)`.
     - `has(push_ref)`.
   - Integrar en `LangGraphWebSocketEndpoint`: al `accept()` registrar el websocket, manejar mensajes entrantes (`ping`, `cancel_execution`, `subscribe_execution`).
   - En `finally`, deregistrar para evitar fugas.
5. **Persistencia y consultas**
   - Definir `AgentExecutionDto` (campos: `execution_id`, `workflow_id`, `mode`, `status`, `started_at`, `stopped_at`, `duration_ms`, `error`, `summary`, `run_data_meta`).
   - `ExecutionRepository` puede usar `asyncio.Lock` para proteger el dict compartido.
   - `list` debe soportar filtros por `workflow_id` y `status`.
6. **Endpoints reales**
   - Completar handlers en `graph_workflows.py` usando `ExecutionService`.
   - `POST /run`: validar que workflow exista (usar `AgentWorkflowDto` de Task 01). Responder `202` con cuerpo que incluya `polling_url`, `push_ref`, `execution_id`.
   - `GET /executions/{id}`: si ejecucion finalizo, incluir `summary` con totales (nodos completados, fallidos, duracion) y `links` (ej. `logs_url`).
   - `POST /executions/{id}/cancel`: si ejecucion ya termino, devolver `409` con error JSON; de lo contrario marcar `cancel_event.set()` y responder `202`.
7. **Integracion con GraphState**
   - Ampliar `GraphState` con metodos auxiliares: `mark_node_started`, `mark_node_finished`, `mark_error` actualizando `completed_nodes`, `errors`.
   - Cada vez que se emita evento push, llamar `GraphState.to_frontend_format()` y adjuntarlo como `data.graph_state` para que el frontend tenga foto actual.
8. **Pruebas**
   - Tests asincronicos con `pytest.mark.asyncio`.
   - Mockear LangGraph para devolver resultados deterministas y forzar errores.
   - Simular WebSocket usando `fastapi.testclient` (`client.websocket_connect`). Verificar que se emiten mensajes en orden exacto.
   - Probar cancelacion forzada (enviar `cancel_execution` a websocket y comprobar status `cancelled`).

## Riesgos y mitigaciones
- Riesgo: fuga de tasks asincronas. Mitigacion: exponer `shutdown()` en `ExecutionManager` y llamarlo en `FastAPI lifespan` (similar a `Push.onShutdown`).
- Riesgo: eventos en desorden. Mitigacion: ordenar `emit_event` y tests que comparen secuencia.
- Riesgo: payload gigante. Mitigacion: helper Task 01.
- Riesgo: IA agregue implementacion de DB permanente sin diseno. Mitigacion: documentar TODO antes y mantener memoria en Task 02.

## Definicion de hecho
- WS entrega eventos segun contrato Task 01.
- Endpoints funcionales con tests.
- Documentacion actualizada describiendo como consumir `POST /run` y mensajes push.

