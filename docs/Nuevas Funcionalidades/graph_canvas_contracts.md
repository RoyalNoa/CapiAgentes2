# Graph Canvas Contracts

Tabla de referencia para los DTO expuestos por `src/graph_canva/schemas.py`. Los orígenes provienen de los artefactos descargados en `tablero/GraphCanva/references/`.

## Workflow (GraphCanvaWorkflow)
| Campo | Tipo | Fuente n8n | Descripción |
| --- | --- | --- | --- |
| id | string | workflow-entity.ts (`WorkflowEntity.id`) | Identificador único del workflow. |
| name | string | workflow-entity.ts (`WorkflowEntity.name`) | Nombre legible del flujo. |
| active | boolean | workflow-entity.ts (`WorkflowEntity.active`) | Indica si el workflow está habilitado. |
| is_archived | boolean | workflow-entity.ts (`WorkflowEntity.isArchived`) | Marca de archivado para lectura del canvas. |
| nodes | GraphCanvaNode[] | workflow-entity.ts (`nodes: INode[]`) | Nodos con parámetros, credenciales y posición. |
| connections | GraphCanvaConnectionMap | workflow-entity.ts (`connections: IConnections`) | Conexiones agrupadas por tipo de enlace. |
| settings | dict | workflow-entity.ts (`settings?: IWorkflowSettings`) | Preferencias de ejecución globales. |
| pin_data | GraphCanvaPinData | workflow-entity.ts (`pinData?: ISimplifiedPinData`) | Datos fijados por nodo para NDV. |
| meta | GraphCanvaMeta | workflows.store.ts (`workflow.meta`) | Metadatos de UI (viewport, selección). |
| version_id | string | workflow-entity.ts (`versionId`) | Identificador de versión. |
| trigger_count | number | workflow-entity.ts (`triggerCount`) | Conteo de disparadores registrados. |
| tags | string[] | workflow-entity.ts (`tags`) | Etiquetas asociadas. |
| permissions | string[] | workflows.store.ts (`workflow.permissions`) | Permisos calculados para feature flags. |

## Node (GraphCanvaNode)
| Campo | Tipo | Fuente n8n | Descripción |
| --- | --- | --- | --- |
| id | string | workflow-interfaces.ts (`INode.id`) | Identificador del nodo. |
| name | string | workflow-interfaces.ts (`INode.name`) | Nombre visible. |
| type | string | workflow-interfaces.ts (`INode.type`) | Tipo registrado en el catálogo. |
| type_version | number | workflow-interfaces.ts (`INode.typeVersion`) | Versión del tipo. |
| parameters | dict | workflow-interfaces.ts (`INode.parameters`) | Configuración del nodo. |
| credentials | dict? | workflow-interfaces.ts (`INode.credentials`) | Credenciales asociadas. |
| position | [number, number] | workflow-entity.ts (`INode.position`) | Coordenadas en el canvas. |
| runtime_status | enum | push-execution.ts (`nodeExecuteAfter.status`) | Estado en vivo del nodo. |
| last_run_at | string? | push-execution.ts (`node.lastRun`) | Última ejecución para badges. |

## Execution (GraphCanvaExecution)
| Campo | Tipo | Fuente n8n | Descripción |
| --- | --- | --- | --- |
| execution_id | string | push-execution.ts (`executionId`) | Identificador de la ejecución. |
| workflow_id | string | push-execution.ts | Workflow asociado. |
| status | enum | execution-status.ts (`ExecutionStatus`) | Estado final de la corrida. |
| started_at | string? | push-execution.ts (`startedAt`) | Inicio ISO8601. |
| finished_at | string? | push-execution.ts (`stoppedAt`) | Fin ISO8601. |
| duration_ms | number? | workflow-execution.service.ts | Tiempo total estimado. |
| error | string? | push-execution.ts (`error`) | Mensaje de error si aplica. |
| summary | dict | workflow-execution.service.ts | Agregado de métricas y nodos completados. |

## Catálogo
| DTO | Fuente n8n | Descripción |
| --- | --- | --- |
| GraphCanvaNodeType | nodeTypes.store.ts (`INodeTypeDescription`) | Estructura para mostrar iconos, entradas, salidas. |
| GraphCanvaCredentialType | credentials metadata | Esquema de credenciales para nodos que requieren autenticación. |

## Helpers
- `ensure_snake_case_keys`: valida que los payloads respeten snake_case, inspirado en `push/index.ts`.
- `validate_payload_size`: replica el límite de 5 MiB definido en `push-index.ts` (`MAX_PAYLOAD_SIZE_BYTES`).



## Streaming de eventos
- **Endpoint**: `ws/graph-canva/{workflow_id}` (registrado en `src/presentation/websocket_graphcanva.py`).
- **Mensajes**: estructuras descritas en `GraphCanvaPushMessage` (`execution_started`, `node_execute_before`, `node_execute_after`, `node_execute_after_data`, `execution_finished`).
- **Referencia n8n**: `push-execution.ts` y `push-index.ts` (l�gica de streaming y l�mite de 5 MiB replicados con `validate_payload_size`).
