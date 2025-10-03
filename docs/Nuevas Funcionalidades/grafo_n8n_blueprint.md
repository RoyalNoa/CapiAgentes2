# Blueprint de grafo de agentes estilo n8n

## Objetivo y alcance
- Describir con precisión cómo n8n estructura su canvas interactivo para que podamos replicar la experiencia en CAPI.
- Identificar los módulos backend que suministran datos, eventos en vivo y contratos de seguridad para el grafo.
- Documentar los componentes frontend, stores y utilidades que materializan la UI (layout, interacciones, animaciones, estados de ejecución).
- Servir como guía para desarrolladores o agentes que deban implementar o extender un grafo de agentes en nuestra plataforma.

**Fuentes clave consultadas (repo n8n-io/n8n):**
- `packages/@n8n/db/src/entities/workflow-entity.ts`
- `packages/cli/src/workflows/workflow.service.ts`, `workflow-execution.service.ts`, `workflow-runner.ts`, `active-workflow-manager.ts`
- `packages/cli/src/push/*.ts` y `packages/@n8n/api-types/src/push/*.ts`
- `packages/workflow/src/workflow.ts` y utilidades en `packages/workflow/src/common`
- `packages/frontend/editor-ui/src/components/canvas/*`
- `packages/frontend/editor-ui/src/composables/*` (en particular `useCanvas*`, `useCanvasMapping`, `useKeybindings`, `useContextMenu`)
- Stores de Pinia en `packages/frontend/editor-ui/src/stores/workflows.store.ts` y `nodeTypes.store.ts`

---

## Parte I — Backend (orquestación y contratos de datos)

### 1. Modelo persistente y contratos
- **Entidad principal**: `WorkflowEntity` (TypeORM) almacena el grafo completo (`nodes`, `connections`, `settings`, `meta`, `pinData`, `versionId`).
  - `nodes`: arreglo de `INode` (definido en `@n8n/workflow`). Cada nodo persiste `id`, `name`, `type`, `typeVersion`, `parameters`, credenciales asociadas y `position: [x, y]` que determina su ubicación en el canvas.
  - `connections`: estructura `IConnections` por tipo de conexión (`main`, `ai`, `if`, etc.), utilizada para reconstruir edges.
  - `pinData`: resultados manuales por nodo para ejecutar sin volver a llamar al agente (se muestra en la UI como estado "pinned").
  - `meta` (`WorkflowFEMeta`): metadatos de la UI (zoom inicial, pan, dimensiones de sticky notes, hints de layout). Es opcional, pero evita recalcular layout en el cliente.
  - `settings`: preferencias globales del workflow (ej. ejecución automática, tiempos de espera).
- **Normalización en @n8n/workflow**: la librería expone tipos (`Workflow`, `NodeHelpers`, `NodeConnectionTypes`) y funciones (`getConnectedNodes`, `mapConnectionsByDestination`) que garantizan que un `WorkflowEntity` pueda convertirse en un grafo navegable.
- **Compatibilidad multiusuario**: campos `shared`, `tags`, `folder` y `versionId` soportan permisos, versionado y agrupación.

### 2. Servicios y repositorios
- `WorkflowService` (`packages/cli/src/workflows/workflow.service.ts`):
  - CRUD completo (incluye duplicado, archivado) y orquestación de permisos via `OwnershipService`, `RoleService` y `WorkflowSharingService`.
  - Dispara hooks (`ExternalHooks`) para extensiones y publica eventos para auditoría.
- `WorkflowRepository` / `SharedWorkflowRepository` (`@n8n/db`): centralizan acceso a DB con filtros por proyectos, carpetas, etiquetas.
- `WorkflowExecutionService` & `WorkflowRunner`: coordinan ejecuciones manuales o planificadas, convierten `WorkflowEntity` en una instancia `Workflow` (librería core) y delegan en `ActiveWorkflowManager` para activar webhooks o triggers.
- `ActiveWorkflowManager`: mantiene workflows activos en memoria, gestiona start/stop de tareas recurrentes y enlaza con `ActiveExecutions` (cola de ejecuciones en curso).
- `BinaryDataService`: almacena outputs pesados y simplifica la respuesta para push events.

### 3. API HTTP relevante
- `workflows.controller.ts` expone endpoints REST `GET/POST/PATCH/DELETE /rest/workflows` que devuelven/aceptan objetos `IWorkflowDb` con nodos, conexiones y `meta`.
- `POST /rest/workflows/run` lanza ejecuciones manuales y responde con `executionId` (clave para escuchar actualizaciones por push).
- `GET /rest/executions` y `GET /rest/executions/:id` permiten consultar históricos, incluyendo `data` serializada por nodo.
- `GET /rest/node-types` y `GET /rest/credential-types` entregan el catálogo de componentes disponibles (usado por el canvas para pintar iconos, entradas/salidas y validaciones).
- Operaciones adicionales: pinning (`POST /rest/workflows/:id/pin-data`), compartir recursos (`POST /rest/workflows/:id/share`), mover entre proyectos/carpetas.

### 4. Ejecución y streaming de estado (push)
- `packages/cli/src/push/index.ts` habilita SSE y WebSocket según configuración (`N8N_PUSH_BACKEND=sse|websocket`). Administra sesiones autenticadas, valida origen y reenvía mensajes del broker (`Publisher`).
- Tipos de mensajes definidos en `packages/@n8n/api-types/src/push/execution.ts`:
  - `executionStarted`, `executionWaiting`, `executionFinished`, `executionRecovered`.
  - Eventos de nodo: `nodeExecuteBefore`, `nodeExecuteAfter`, `nodeExecuteAfterData`, `nodeExecuteError`, `nodeExecuteRetry`, `nodeExecuteUpdated`.
  - `executionProgress` y `broadcastExecutionFinished` para informar progreso global y finalización a múltiples clientes.
- El payload incluye `executionId`, `workflowId`, `nodeName`, estado (`running`, `success`, `error`, `waiting`) y, cuando aplica, conteos de items por salida (`itemCountByConnectionType`). La UI usa esta granularidad para animar nodos y aristas específicas.
- Para cargas grandes, los datos completos se envían en un evento separado (`nodeExecuteAfterData`) o se reemplazan por placeholders que luego se resuelven vía REST (`execution.data`), minimizando saturación del canal push.

### 5. Layout y metadatos de UI guardados en backend
- `WorkflowFEMeta` (campo `meta`) suele contener:
  - `canvasDimensions`, `viewport` (posición/zoom inicial al abrir).
  - Última selección de nodos, historial de tidy-up automático, preferencias de minimapa o paneles auxiliares.
- `pinData` y `settings` complementan la experiencia visual (nodos pinneados muestran badges, settings definen si el grafo arranca activo o en modo sólo lectura).
- Para replicar la UX hay que persistir, al menos, `nodes[].position`, `pinData`, `meta.viewport` y un `versionId` para invalidar caches.

### 6. Seguridad y multitenencia
- `WorkflowSharingService` y `ProjectService` comparten recursos por proyecto/rol (`workflow:owner`, `workflow:editor`, `workflow:viewer`).
- `OwnershipService` aplica reglas de negocio antes de ejecutar acciones destructivas o de activación.
- Los endpoints checan scopes vía `hasSharing` y `addUserScopes`; el push revalida tokens antes de subscribir clientes.
- Para CAPI: replicar capas de autorización antes de exponer el grafo y filtrar nodos visibles según permisos.

### 7. Recomendaciones para adaptar a CAPI backend
1. **Definir entidad** `AgentWorkflow` con campos equivalentes (`nodes`, `connections`, `meta`, `pinData`, `versionId`). Incluir `agentWorkspaceId` y `visibility` si aplica.
2. **Catalogar componentes** (agentes, control nodes) en un módulo equivalente a `@n8n/workflow` con tipos y helpers de puertos (entrada/salida, cardinalidad, etiquetas).
3. **Servicios**: crear `AgentWorkflowService` (CRUD, versionado, activación), `AgentExecutionService` (planificación y seguimiento) y `ActiveAgentManager` (manejo en memoria de flujos vivos).
4. **Canal en vivo**: elegir SSE/WebSocket, definir mensajes inspirados en `PushMessage` (start, progress, node running, node success/error, finalize). Incorporar throttling y payload diferido para outputs grandes.
5. **Persistir metadatos**: guardar `canvasViewport`, `tidyLayoutSignature`, `panelState` para rehidratar UI sin recalcular.
6. **Permisos**: integrar con el sistema actual (roles, proyectos, workspaces) para aislar grafos por cliente.

---

## Parte II — Frontend (experiencia Canvas)

### 1. Stack y cimientos
- Basado en **Vue 3 + Vite + Pinia** y el motor de grafos **@vue-flow/core** (equivalente Vue de React Flow).
- Componentes principales en `packages/frontend/editor-ui/src/components/canvas` y `components/Graph`.
- El estado global se reparte entre `useWorkflowsStore`, `useNodeTypesStore`, `useUIStore`, mientras que la comunicación con backend usa composables `useWorkflowHelpers`, `usePushConnection`, `useExternalHooks`.

### 2. Mapeo de datos (`useCanvasMapping`)
- Recibe `workflow.nodes` y `workflow.connections` (`Ref<INodeUi[]>`, `Ref<IConnections>`).
- Genera `CanvasNode[]` y `CanvasConnection[]` para VueFlow:
  - Calcula tipo de render (`Default`, `StickyNote`, `AddNodes`, `AIPrompt`).
  - Define puertos (`CanvasConnectionPort`) con etiquetas, `maxConnections` y marcadores de obligatoriedad (`required`).
  - Fusiona información de ejecución (`nodeExecutionRunData`, `nodePinnedData`, `issues`) para pintar badges y estados (`idle`, `running`, `error`, `success`, `pinned`).
  - Para edges, deriva `status` (`running`, `success`, `error`, `pinned`) y `itemCountByConnectionType` para tooltips.
- Emplea utilidades de `canvasUtils.ts` para transformar conexiones legacy (`mapLegacyConnectionsToCanvasConnections`, `parseCanvasConnectionHandleString`).

### 3. Componente central `Canvas.vue`
- Envuelve `VueFlow` y provee `CanvasKey` a través de `provide/inject`.
- Propiedades destacadas:
  - `nodes`, `connections` (ya en formato VueFlow) con throttling cuando `executing` es `true`.
  - `eventBus` (creado con `@n8n/utils/event-bus`) para coordinar acciones desde paneles externos (fitView, tidy-up, selección programática).
  - Flags: `readOnly`, `executing`, `suppressInteraction`, `keyBindings`.
- Interacciones gestionadas:
  - `useKeybindings` define atajos (`⌘A`, `Delete`, `⌘C/⌘V`, `Shift+Arrow` para nudge, `⌘⇧L` para tidy up).
  - `useContextMenu` abre menús sobre nodos, pane o conexiones (`duplicate`, `disable`, `add sticky`, `tidy selection`).
  - `useCanvasNodeHover` calcula nodos “cercanos” para mostrar triggers contextuales.
  - `useCanvasTraversal` facilita navegación a padres/hijos/hermanos vía teclado.
  - `useCanvasLayout` (Dagre) implementa `tidy-up` con spacing configurable y soporte para subgrafos AI.
  - `useViewportAutoAdjust` realiza `fitView` automático tras cambios significativos.
- UI complementaria: `MiniMap`, `CanvasControlButtons` (zoom, tidy, reset), `CanvasBackground` (grid animada), `CanvasArrowHeadMarker` para flechas.

### 4. Nodos (`CanvasNode.vue` + renderers)
- Contiene toolbar contextual (`run`, `stop`, `toggle enable`, `open context menu`, `focus`), badges de estado, y `CanvasHandleRenderer` para cada puerto.
- Usa clases dinámicas (`hovered`, `selected`, `showToolbar`) y animaciones CSS (`pulse`, `breathe`) según `status` y `enabled`.
- `CanvasNodeRenderer` delega el contenido dependiendo del `render.type` (por ejemplo, sticky notes renderizan contenido HTML, prompts AI muestran plantilla específica).
- `CanvasNodeTrigger` se dibuja para nodos disparadores (start nodes) con área de interacción extendida.

### 5. Aristas (`CanvasEdge.vue`)
- Se apoya en `BaseEdge` de VueFlow y en `EdgeLabelRenderer` para overlays.
- Estilos según estado (`success` color verde, `error` rojo, `pinned` morado, `running` cyan). Conexiones no-main usan línea punteada (`strokeDasharray`).
- Toolbar contextual permite insertar nodos en medio de la conexión, eliminarla o abrir detalles.
- Calcula `labelPosition` y segmentos curvos vs rectos (`getEdgeRenderData`) para mejorar legibilidad.

### 6. Controles, accesibilidad y usabilidad
- `viewToggleGroup` alterna entre modos (Overview vs Canvas). Para nuestra adaptación se añadirá Mermaid como tercer modo.
- Selección por rango, arrastre de múltiples nodos, focus management (toolbar con `tabindex` y eventos `focus/blur`).
- `useShortKeyPress` previene atajos repetidos; `useDeviceSupport` adapta interacciones a touch/desktop.
- `isOutsideSelected` permite cerrar paneles cuando se clica fuera del canvas.

### 7. Live execution overlay
- `usePushConnection` mantiene una conexión SSE/WebSocket y alimenta `useWorkflowsStore` con eventos `PushMessage`.
- `useCanvasMapping` responde a cambios en run data: marca `node.data.execution.status` y `CanvasConnectionData.status`, activa animaciones y actualiza badges con conteo de items.
- Los eventos `nodeExecuteAfterData` se fusionan en el store para permitir abrir la NDV (Node Detail View) con resultados completos.

### 8. Estado global y caches
- `useWorkflowsStore` guarda el workflow actual, historial de ejecuciones, nodos seleccionados, paneles visibles y metadatos (`state.workflow.meta.viewport`).
- `useNodeTypesStore` aporta metainformación (iconos, categorías, heurísticas de configuración) para renderizar nodos.
- `useUIStore` controla flags globales (modo oscuro, paneles abiertos, experimentos NDV).
- Se usa `throttledRef` (`@vueuse/core`) para reducir renders cuando llegan eventos de ejecución intensivos.

### 9. Estilos y tematización
- SCSS modules (`Canvas.vue`, `CanvasNode.vue`, `CanvasEdge.vue`) con tokens CSS (`--color-primary`, `--canvas-zoom-compensation-factor`).
- Fondo `GridBackground` combina patrones de líneas + puntos y gradientes radiales para dar profundidad tipo HUD.
- Animaciones suaves (`transition: opacity`, `transform: scale`) refuerzan la retroalimentación (hover, running, minimap).

### 10. Roadmap de adopción en CAPI (Frontend)
1. **Seleccionar motor**: React Flow o mantener nuestra capa D3. Si se busca paridad con n8n, React Flow ofrece API equivalente a VueFlow.
2. **Normalizar contrato de datos**: replicar `CanvasNodeData`/`CanvasConnectionData` (status, puertos, métricas) en TypeScript compartido con backend.
3. **Crear mapper** (equivalente a `useCanvasMapping`) que consuma `AgentWorkflow` y produzca nodos/edges aptos para el motor elegido.
4. **Diseñar componente `AgentCanvas`**:
   - Propiedades: `workflow`, `executionState`, `readOnly`, callbacks `onRunNode`, `onToggleNode`, `onOpenContextMenu`.
   - Inyectar servicios (stores o context) para keybindings, selección, tidy-up, push events.
5. **Interacciones clave**: drag & drop, conexión condicional, shortcuts (duplicar, deshabilitar, tidy), context menus.
6. **Estados de ejecución**: aplicar clases/animaciones cuando `push` informa `running/success/error`, con indicadores en edges (p.ej. glow animado).
7. **Persistencia UI**: guardar `viewport`, `selectedNodes`, `panelState` en `meta` al salir y restaurar al entrar.
8. **Testing**: replicar el enfoque de n8n (tests de componentes + snapshot + e2e) para validar interacciones complejas.

---

## Próximos pasos sugeridos
1. **Definir contrato compartido** (`AgentWorkflowDto`, `AgentCanvasNodeData`, `AgentPushMessage`) inspirado en los tipos de n8n.
2. **Levantar endpoints** mínimos (fetch workflow, guardar layout, ejecutar, escuchar ejecución) reutilizando la infraestructura actual de agentes.
3. **Implementar prototipo frontend** con el mapper y el canvas personalizado, empezando por la lectura visual (sin push) y sumando luego eventos en vivo.
4. **Migrar configuraciones existentes** al nuevo formato (`meta`, `pinData`, `settings`) para conservar UX previa.
5. **Documentar guía de desarrollo** (librerías UI, estándares de estilo, pruebas) para que futuros agentes/colaboradores puedan extender el grafo sin fricción.

Este blueprint sirve como referencia auditada: cualquier desviación en la implementación debe comprobarse contra los puntos anteriores para mantener la coherencia con la experiencia n8n y con las expectativas de CAPI.
