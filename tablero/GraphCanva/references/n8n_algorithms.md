# N8N Algorithms Relevantes para GraphCanva

> Compendio operacional de rutinas n8n (backend y frontend) que debemos reproducir o adaptar. Cada sección cita el archivo fuente descargado en `tablero/GraphCanva/references`. Usar este documento antes de permitir que la IA implemente código.

## 1. Ejecución de workflows (backend)

### 1.1 `WorkflowExecutionService.runWorkflow` (`workflow-execution.service.ts`, líneas ~47-199)
- **Entrada**: `workflowData`, `node`, `data`, `additionalData`, `mode`, `responsePromise`.
- **Algoritmo**:
  1. Construye `nodeExecutionStack` con el nodo inicial y sus datos (`data.main`).
  2. Construye `executionData: IRunExecutionData` inicial (campos `startData`, `resultData`, `runData`, `executionData.nodeExecutionStack`).
  3. Prepara `runData`, `executionId`, `workflow` (`new Workflow(workflowData.id, workflowData)`).
  4. Pide `WorkflowExecuteAdditionalData.getBase(mode, workflowData, node)` para obtener hooks (`pushExecutionStartedEvent`), acceso a credenciales, binarios, etc.
  5. Inicializa `WorkflowExecute` con workflow y data; ejecuta `runPartialWorkflow` o `run` según `mode`.
  6. Emite hooks `workflowExecuteBefore` antes de correr y `workflowExecuteAfter` al terminar.
  7. Resuelve `responsePromise` con `IExecuteResponsePromiseData` (`executionId`, `runExecutionData`) o rechaza si falla.
- **Puntos clave**: Respetar manejo de errores (genera `generateFailedExecutionFromError`), mantener `mode` (`manual`, `integrated`).

### 1.2 `WorkflowRunner.run` (`workflow-runner.ts`, líneas ~70-230)
- **Entrada**: `IWorkflowExecutionDataProcess` + flags (`loadStaticData`, `realtime`, `restartExecutionId`, `responsePromise`).
- **Algoritmo**:
  1. `executionId = activeExecutions.add(data, restartExecutionId)` (ver 1.3).
  2. Verifica permisos (`credentialsPermissionChecker.check`).
  3. Adjunta `responsePromise` a `activeExecutions` si se provee.
  4. Decide modo cola: `shouldEnqueue = executionsMode === 'queue' && data.executionMode !== 'manual'` (con feature flag `OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS`).
  5. Si en cola: llama `enqueueExecution` (envía a Bull/worker). Caso contrario ejecuta inline via `runMainProcess` (crea `WorkflowExecute`, carga static data, ejecuta). 
  6. Después de lanzar ejecución, obtiene `postExecutePromise` de `activeExecutions` y maneja errores.
- **Hooks**: Usa `getLifecycleHooksForRegularMain/ScalingMain/ScalingWorker` para notificar frontend (`workflowExecuteBefore/After`, `nodeExecuteBefore`...).

### 1.3 `ActiveExecutions` (`active-executions.ts`)
- `add(executionData, executionId?)`:
  - Si no recibe `executionId`, crea en DB (`ExecutionRepository.create`) con `status = 'new'`.
  - Inserta en `this.activeExecutions: Map<string, IExecutingWorkflowData>` con campos: `workflowData`, `executionData`, `startedAt`, `mode`, `status`.
- `attachResponsePromise(executionId, responsePromise)`: almacena promesa a resolver cuando termine.
- `addPostExecutePromise(executionId, promise)`: para operaciones after-run.
- `getPostExecutePromise`, `resolvePostExecutePromise`.
- `finalizeExecution(executionId, fullRunData?)`: marca fin, actualiza DB (`status`, `finished`, `stoppedAt`), resuelve promesas.
- `stopExecution(executionId)`: marca `stoppedAt`, dispara cancelación (`cancelled` flag) y retorna `true/false` según si existía.
- **Invariantes**: siempre actualizar DB antes de remover de `activeExecutions`; preservar `executionId` string.

### 1.4 Eventos push backend (`push-index.ts`)
- `Push.setupPushServer(restEndpoint, server, app)`: intercepta `upgrade` y asocia `WebSocketPush` si `config.backend === 'websocket'`.
- `Push.setupPushHandler`: registra middleware con auth, valida `pushRef`, origen y decide WS vs SSE.
- `Push.send(pushMsg, pushRef)`: si `shouldRelayViaPubSub` (multinodo), envía a broker; si no, `backend.sendToOne`.
- `Push.broadcast(pushMsg)`: WS/SSE a todos.
- `MAX_PAYLOAD_SIZE_BYTES = 5 MiB`: al exceder, backend recorta payload antes de enviar (debe replicarse para no romper FE).

## 2. Mapeo y utilidades de canvas (frontend)

### 2.1 Conversión de conexiones (`canvasUtils.ts`)
- `mapLegacyConnectionsToCanvasConnections(legacyConnections, nodes)`:
  1. Itera nodos origen (`legacyConnections[fromNodeName]`).
  2. Por cada tipo de conexión (`main`, `if`, `ai`, etc.), recorre puertos y destinos.
  3. Genera `sourceHandle`/`targetHandle` con `createCanvasConnectionHandleString({ mode, type, index })` → formato `${mode}/${type}/${index}`.
  4. Usa `createCanvasConnectionId` para ID estable `[source/handle][target/handle]`.
  5. Adjunta metadatos `{ source: { node, index, type }, target: { ... } }`.
- `mapCanvasConnectionToLegacyConnection(sourceNode, targetNode, connection)` hace la inversa usando `parseCanvasConnectionHandleString`.
- `mapLegacyEndpointsToCanvasConnectionPort(endpoints, endpointNames)` construye puertos con label ordenado, inyecta espaciadores (`insertSpacersBetweenEndpoints`) cuando hay entradas opcionales.
- `checkOverlap(node1, node2)`: detección axis-aligned bounding boxes para evitar superposiciones.

### 2.2 Mapper completo (`useCanvasMapping.ts`)
- **Render types**: funciones `createStickyNoteRenderType`, `createAddNodesRenderType`, `createDefaultNodeRenderType` (aplica iconos, tooltips, labels usando `nodeTypesStore`).
- **Computed caches**:
  - `nodeTypeDescriptionByNodeId`, `isTriggerNodeById`, `nodeSubtitleById`, `nodeInputsById`, `nodeOutputsById`.
  - Usa `mapLegacyEndpointsToCanvasConnectionPort` para convertir definiciones de inputs/outputs.
- **Ejecutions overlay**:
  - `nodeExecutionRunDataById` y `nodeExecutionRunDataOutputMapById` (via `throttledWatch`) agregan iteraciones → `ExecutionOutputMap` (conteo de items por conexión y puerto).
  - `updateNodeExecutionData(node, runData)` actualiza estado (`options.tooltip`, badges), alimenta NDV.
- **Uso recomendado**: replicar la estructura con hooks React (memo + Zustand), conservando throttling (evita repintar con spam de eventos push).

### 2.3 Auto-layout (`useCanvasLayout.ts`)
- Basado en `dagre`:
  1. `getTargetData(target)` decide si layout se aplica a selección o a todo.
  2. Filtra sticky notes (`node.data.type !== STICKY_NODE_TYPE`).
  3. `createDagreGraph({ nodes, edges })`: crea grafo principal, ordena nodos (`sortNodesByPosition`) y aristas (`sortEdgesByPosition`).
  4. Divide en componentes (`dagre.graphlib.alg.components`). Para cada subgrafo:
     - Detecta nodos AI config (padres y configuraciones) y crea subgrafo top-bottom (`createDagreVerticalGraph`).
     - Usa constantes `NODE_X_SPACING`, `NODE_Y_SPACING`, `AI_X_SPACING`, `AI_Y_SPACING` para espaciar.
     - Alinea sticky notes con padding `STICKY_BOTTOM_PADDING`.
  5. Ejecuta `dagre.layout(graph)` y obtiene nuevas coordenadas.
  6. Aplica `roundToGrid` (implícito en `calculateNodeSize`/grid) y devuelve `CanvasLayoutResult { boundingBox, nodes: [{ id, x, y, width, height }] }`.
- **Uso**: replicar con React Flow usando `@dagrejs/dagre`, mantener constantes de espaciado para consistencia visual.

## 3. Manejo de eventos en vivo (frontend)

### 3.1 Conexión push (`usePushConnection.ts`)
- Instancia `createEventQueue<PushMessage>(processEvent)` para serializar eventos → evita race conditions.
- `processEvent` despacha a handlers especializados (`nodeExecuteBefore`, `nodeExecuteAfterData`, etc.) ubicados en `usePushConnection/handlers/*`.
- Handlers actualizan stores (`useWorkflowsStore`, `useUIStore`), abren NDV, marcan estados de nodos (`executingNode` store).
- **Claves**: mantener same event names (camelCase). Utilizar colas y `await` en handlers para procesar en orden.

### 3.2 Store `useWorkflowsStore` (`workflows.store.ts`)
- Node metadata management: `setWorkflowMetadata`, `addToWorkflowMetadata`, `pinData`, `setNodeExecutionData`, `setWorkflowExecutionData`.
- Execution overlay: `workflowExecutionStartedData`, `workflowExecutionResultDataLastUpdate`, `workflowExecutionPairedItemMappings`.
- Methods `isNodeDirty`, `markNodeDirty`, `resetNodeExecutionData` replican estados de configuración.
- **Uso**: cuando backend emita `AgentPushMessage`, frontend debe llamar funciones equivalentes para reflejar estado.

## 4. Complementos útiles

- `createEventQueue` (`@n8n/utils/event-queue`): genera cola FIFO asíncrona con `enqueue` y `flush`, evitando overlap.
- `throttledWatch` (`@vueuse/core`): en n8n se usa con 250 ms para agrupar actualizaciones de ejecuciones; replicar con `lodash/throttle` o similar.
- `insertSpacersBetweenEndpoints`: asegura que puertos opcionales mantengan separación visual (representar como `null` intercalados en arrays).
- `calculateNodeSize` (`nodeViewUtils`) y `DEFAULT_NODE_SIZE`: derivan ancho/alto según número de puertos y si NDV está embebido.
- `getAllConnectedAiConfigNodes` (`useCanvasLayout.ts`): BFS del subgrafo AI configurables para agrupar paneles.

## 5. Cómo aplicar en CAPI

1. **Backend**: replicar secuencia `WorkflowRunner -> ActiveExecutions -> Push` respetando hooks y mensajes. Cualquier diferencia debe documentarse y mantener contractos de Task 01.
2. **Frontend**: usar las funciones de mapeo/layout tal como se describen, adaptadas a React Flow pero con la misma estructura de datos (handles, IDs, layout, badges).
3. **Eventos**: mantener `executionStarted`, `nodeExecuteBefore`, `nodeExecuteAfter`, `nodeExecuteAfterData`, `executionFinished`. Procesarlos en el mismo orden y con colas para evitar estados inconsistentes.
4. **Validación**: comparar la salida de nuestros algoritmos con los JSON generados por n8n (fixtures) antes de liberar.
