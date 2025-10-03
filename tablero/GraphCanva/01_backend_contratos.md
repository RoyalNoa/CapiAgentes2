# Task 01 - Normalizar contratos de grafo y catalogos (backend)

## Objetivo irrenunciable
Disenar los DTO y contratos HTTP que conectan FastAPI/LangGraph con el canvas inspirado en n8n, sin dejar ambiguedades. Cada campo debe corresponder a una fuente concreta del repositorio oficial de n8n.

## Referencias obligatorias
- Blueprint local: docs/Nuevas Funcionalidades/grafo_n8n_blueprint.md (especialmente secciones Parte I y roadmap frontend).
- Modelo persistente de n8n: 	ablero/GraphCanva/references/workflow-entity.ts (clase WorkflowEntity e interfaz ISimplifiedPinData).
- Tipos de ejecucion: 	ablero/GraphCanva/references/types-db.ts (IWorkflowDb, IExecutionResponse).
- Schema actual CAPI: Backend/src/infrastructure/langgraph/state_schema.py (GraphState, StateMutator).
- Websocket actual CAPI: Backend/src/presentation/websocket_langgraph.py (para alinear responses).
- Push API n8n: 	ablero/GraphCanva/references/push-execution.ts.

## Referencias de contrato n8n a adaptar (sin copiar literal)
- `packages/@n8n/db/src/entities/workflow-entity.ts`: tomar la estructura de `WorkflowEntity`, `nodes`, `connections`, `meta`, `pinData` para definir DTO propios en FastAPI.
- `packages/cli/src/workflows/workflows.controller.ts`: revisar el shape de las respuestas REST (`IWorkflowDb`, `IExecutionResponse`) al diseñar `GET/PATCH` locales.
- `packages/@n8n/api-types/src/push/execution.ts`: base para `AgentPushMessage` y subtipos en snake_case.
- `packages/frontend/editor-ui/src/stores/nodeTypes.store.ts`: al exponer catálogos, conservar campos (`displayName`, `group`, `properties`, `icon`) aunque el store final sea distinto.
- `packages/frontend/editor-ui/src/stores/workflows.store.ts`: usar como referencia el contenido de `meta`, `pinData`, `selectedNodes` para mantener compatibilidad con el canvas.

El objetivo es replicar contratos y semántica (nombres de campos, tipos, comportamiento) sin copiar código TypeScript, documentando cualquier divergencia.
## Entregables concretos
1. Modulo Backend/src/presentation/schemas/graph.py con:
   - AgentWorkflowDto alineado con IWorkflowDb (campos obligatorios: id, 
ame, ctive, is_archived, 
odes, connections, settings, pin_data, meta, ersion_id, 	rigger_count, 	ags, shared, permissions).
   - AgentCanvasNodeData reflejando INode (campos: id, 
ame, 	ype, 	ype_version, parameters, credentials, position, disabled, 
otes, lways_output_data, 
etry_on_fail, max_concurrency, hooks).
   - AgentCanvasConnectionMap siguiendo la forma de IConnections (mapa por connection_type -> source_index -> lista de destinos) con metainformacion opcional (last_status, last_emitted_at).
   - AgentWorkflowMeta para viewport (pan_x, pan_y, zoom), preferencias (grid_size, snap_to_grid, show_minimap), seleccion (selected_nodes, selected_edges), paneles (inspector_open, xecution_sidebar_mode) y marcas (layout_dirty, data_dirty).
   - AgentPinData clonando ISimplifiedPinData (clave por nombre de nodo -> lista de entries { json, binary?, paired_item? }).
   - Jerarquia AgentPushMessage con subtipos ExecutionStartedMessage, ExecutionFinishedMessage, NodeExecuteBeforeMessage, NodeExecuteAfterMessage, NodeExecuteAfterDataMessage, ExecutionWaitingMessage, ExecutionRecoveredMessage (payloads en snake_case y fechas en ISO8601).
   - Validadores compartidos (nsure_snake_case_keys, alidate_payload_size) para reutilizar en Task 02.
2. Ajustes en Backend/src/infrastructure/langgraph/state_schema.py:
   - Ampliar GraphState.to_frontend_format() para devolver AgentWorkflowMeta completo (viewport/seleccion) y mapear gent_results hacia pin_data cuando pin_mode este activo.
   - Alinear 
ode_positions con AgentCanvasNodeData.position (tuplas [x, y] float) y escribir comentario que cite WorkflowEntity.nodes.position.
   - Incluir helper GraphState.from_agent_workflow(dto: AgentWorkflowDto) para Task 02 (sin implementacion aun, levantar NotImplementedError).
3. Router FastAPI de solo contratos en Backend/src/api/routes/graph_workflows.py (nuevo archivo):
   - GET /agents/workflows/{workflow_id} -> retorna AgentWorkflowDto (por ahora 
aise NotImplementedError pero documentar expected response en docstring).
   - PATCH /agents/workflows/{workflow_id} -> acepta AgentWorkflowUpdateDto (solo meta, 
ode_positions, pin_data y campos permitidos) y responde AgentWorkflowDto.
   - GET /agents/graph/catalog -> responde AgentNodeCatalogDto (ver paso 7).
   - Incluir estos routers en Backend/src/api/main.py sin activar logica (solo wiring).
4. Documento docs/Nuevas Funcionalidades/graph_canvas_contracts.md con tabla de campos (campo, 	ipo, uente n8n, descripcion).

## Pasos detallados
1. **Mapear WorkflowEntity -> AgentWorkflowDto**
   - De workflow-entity.ts copiar campos 
ame, ctive, isArchived, 
odes, connections, settings, staticData, meta, pinData, ersionId, 	riggerCount, 	ags.
   - Mantener 
odes/connections sin reestructurar; los DTO deben aceptar exactamente los arrays/diccionarios que guardamos.
   - Convertir a snake_case en FastAPI (is_archived, ersion_id, pin_data). Documentar la equivalencia en docstring para evitar errores de serializacion.
   - Incluir permissions: list[str] (para Task 04: feature flag) pero poblar vacio hasta definir roles.
   - No derivar valores en backend sin fuente explicita. Si algun campo no aplica aun, marcarlo como Optional[...] = None y documentar el TODO con referencia a blueprint.
2. **Definir AgentCanvasNodeData sin perder ningun campo de n8n**
   - Abrir 	ablero/GraphCanva/references/workflow-interfaces.ts y localizar interface INode (zona ~linea 300). Copiar campos 	ypeVersion, parameters, credentials, lwaysOutputData, xecuteOnce, 
etryOnFail, maxTries, 
otes, disabled.
   - Exponer position: tuple[float, float] tomando 
ode.position (en n8n es [number, number]). Validar con Pydantic conlist(float, min_items=2, max_items=2).
   - Agregar 
untime_status: Literal['idle','running','success','error','waiting'] y last_run_at: datetime | None para reflejar push.
   - Documentar en docstring: "No inventar campos adicionales sin actualizar blueprint".
3. **Definir AgentCanvasConnectionMap con paridad n8n**
   - En workflow-interfaces.ts buscar interface IConnections. Reproducir connections[connectionType][sourceIndex] -> list[{ node, type, index }].
   - Envolver en DTO AgentConnectionEndpoint (campos 
ode, 	ype, index, connection_id?).
   - Agregar AgentConnectionMeta (campos opcionales last_status, last_latency_ms, last_error, last_payload_sample) sin poblar aun.
4. **Meta y viewport**
   - Inspirarse en blueprint seccion "Persistencia UI" y en workflows.store.ts (funciones setWorkflowMetadata, ddToWorkflowMetadata).
   - Definir AgentWorkflowMeta con:
     - iewport: { pan_x: float; pan_y: float; zoom: float }.
     - grid: { size: int; snap: bool }.
     - panels: { inspector_open: bool; execution_sidebar_mode: Literal['hidden','summary','detail']; ndv_open_node: str | None }.
     - selection: { nodes: list[str]; edges: list[str] }.
     - nalytics: { tidy_count: int; tidy_last_at: datetime | None }.
   - Guardar meta via WorkflowEntity.meta; dejar comentario explicando que n8n usa WorkflowFEMeta y que expandimos el payload.
5. **Pin data**
   - Copiar literal la forma ISimplifiedPinData (ver final de workflow-entity.ts). Usar Field(alias="json"), Field(alias="binary") para mantener nombres.
   - Documentar que la IA no debe reordenar ni truncar arrays pinned.
6. **Contratos de push**
   - Clonar la estructura de ExecutionPushMessage (push-execution.ts). Mantener campos: xecution_id, workflow_id, mode, started_at, 
ode_name, 	ask_data, item_count_by_connection_type.
   - Implementar helper alidate_payload_size(payload: dict) que verifique el limite de 5 MiB (push-index.ts, MAX_PAYLOAD_SIZE_BYTES). Si se supera, fijar payload['data']['truncated'] = True y loggear.
   - Documentar en docstring la relacion evento->accion en frontend (apuntar a Task 03).
7. **Catalogo de nodos y credenciales**
   - Revisar 
odeTypes.store.ts para identificar campos displayName, group, description, defaults, inputs, outputs, codex.
   - Definir AgentNodeTypeDto con esos campos mas documentation_url (cuando codex?.docs?.baseUrl exista).
   - Definir AgentCredentialTypeDto (leer Backend/src/application/services/agent_registry_service.py para formato actual) y marcar TODO si faltan datos.
   - API GET /agents/graph/catalog debe devolver { "nodes": [...], "credentials": [...] }.
8. **Glue en FastAPI**
   - Crear modulorouter nuevo. Usar APIRouter(prefix="/agents", tags=["graph-workflows"]).
   - Para cada endpoint, anadir docstring con ejemplo JSON (incluir 
odes y connections reales basados en workflow-entity.ts).
   - Registrar router en Backend/src/api/main.py justo despues de la configuracion de websocket.
9. **Documentar blueprint**
   - Escribir docs/Nuevas Funcionalidades/graph_canvas_contracts.md con tablas. Cada fila debe citar la referencia (ej. workflow-entity.ts, linea 12). Usar formato Markdown simple.

## Validaciones y tests
- Crear Backend/tests/test_graph_schemas.py con pruebas:
  - Round-trip AgentWorkflowDto.model_validate -> model_dump(by_alias=True) comparando con fixture basado en n8n.
  - Verificar alidate_payload_size truncando payload de >5 MiB.
  - Probar GraphState.to_frontend_format() y asegurar que campos meta.viewport y pin_data aparezcan.

## Riesgos y mitigaciones
- Riesgo: campos faltantes respecto a n8n. Mitigacion: crear script temporal que compare llaves con IWorkflowDb (utilizar 	ypes-db.ts).
- Riesgo: snake_case inconsistente. Mitigacion: habilitar model_config = ConfigDict(populate_by_name=True) y definir alias.
- Riesgo: IA agregue logica fuera de scope. Mitigacion: dejar comentarios # Implementar en Task 02/03 donde corresponda.

## Definicion de hecho
- DTOs y router creados, tests verdes, documentacion generada y revisada.
- Ningun campo critico pendiente sin TODO referenciado.

