# Task 03 - Canvas interactivo estilo n8n en Next.js (frontend)

## Objetivo irrenunciable
Entregar un canvas React que replique las capacidades del editor n8n (drag & drop, conexiones, estado en vivo, paneles) pero integrado a la UI de CAPI. Todo comportamiento debe estar documentado y referenciar las fuentes de n8n para evitar interpretaciones libres.

## Referencias obligatorias
- Componentes n8n Canvas V2: `tablero/GraphCanva/references/Canvas.vue`, `CanvasNode.vue`, `CanvasEdge.vue`, `CanvasConnectionLine.vue`.
- Composables Vue n8n: `tablero/GraphCanva/references/useCanvasMapping.ts`, `usePushConnection.ts`, `workflows.store.ts`, `nodeTypes.store.ts`.
- Contratos backend definidos en Task 01 (`AgentWorkflowDto`, `AgentPushMessage`).
- Eventos push definidos en Task 02.
- UI actual CAPI: `Frontend/src/app/workspace/page.tsx`, `WorkspaceTab.tsx` para integracion visual.

## Entregables concretos
1. Modulo `Frontend/src/app/workspace/canvas/` con estructura:
   - `AgentCanvas.tsx`: componente principal (envuelve React Flow).
   - `AgentCanvasNode.tsx`, `AgentCanvasEdge.tsx`, `AgentCanvasMiniMap.tsx`, `AgentCanvasToolbar.tsx`, `AgentCanvasPanel.tsx`.
   - `index.ts` exportando API publica.
2. Hooks y stores:
   - `useAgentCanvasStore.ts` (Zustand) gestionando workflow actual, seleccion, viewport, paneles.
   - `useAgentCanvasMapping.ts` (React) traduciendo `AgentWorkflowDto` -> nodos/edges React Flow (mirar `useCanvasMapping.ts`).
   - `useAgentPushConnection.ts` manejando WebSocket y aplicando `AgentPushMessage` (basarse en `usePushConnection.ts`).
   - `useAgentCanvasShortcuts.ts` replicando atajos clave (`ctrl/cmd + c/v`, `delete`, `shift + drag`) inspirados en `useCanvasOperations.ts` y `useKeybindings`.
3. Servicios API:
   - `Frontend/src/services/graphWorkflows.ts` con funciones `fetchWorkflow`, `saveWorkflowMeta`, `runWorkflow`, `listExecutions`, `cancelExecution`, `fetchCatalog` (usar `fetch` con base en Next). Deben consumir endpoints Task 01/02.
4. UI de panel lateral y NDV (Node Detail View) basadas en blueprint:
   - Panel derecho (propiedades) y panel inferior (ejecucion) modulados en `AgentCanvasPanel.tsx`.
   - Modal NDV `AgentNodeDetail.tsx` que se abre al hacer doble click o desde eventos push (inspirarse en `nodeViewUtils` de n8n).
5. Tests:
   - Pruebas unitarias con Jest/RTL (`__tests__/AgentCanvasMapping.test.tsx`, `__tests__/AgentCanvasPush.test.tsx`).
   - Pruebas de Playwright opcionales (documentar TODO si no se implementan).
6. Documentacion en `docs/frontend/graph_canvas_frontend.md` (capturas + flujo de datos).

## Algoritmos n8n a adaptar (sin copiar literal)
- `packages/frontend/editor-ui/src/composables/useCanvasMapping.ts`: traducir el mapper de nodos, puertos, tooltips, badges y runtime status a hooks React, conservando throttling (`throttledWatch`) y cálculo de métricas por conexión.
- `packages/frontend/editor-ui/src/utils/canvasUtils.ts`: usar la misma lógica de handles (`createCanvasConnectionHandleString`), IDs de conexión y detección de solapamientos al portar a React Flow.
- `packages/frontend/editor-ui/src/composables/useCanvasLayout.ts`: replicar el auto-layout con dagre (componentes, subgrafos AI, spacing) ajustado a nuestra estructura de datos.
- `packages/frontend/editor-ui/src/composables/usePushConnection/*`: guiarse por la cola `createEventQueue` y handlers para procesar mensajes push en orden.
- `packages/frontend/editor-ui/src/stores/workflows.store.ts` y `nodeTypes.store.ts`: adaptar la gestión de metadata, pinData, NDV y catálogo de nodos al stack React/Zustand.
- `packages/frontend/editor-ui/src/composables/useCanvasOperations.ts`, `useCanvasTraversal.ts`, `useContextMenu.ts`: inspirarse para duplicar atajos y UX del canvas sin copiar estilos exactos.

Objetivo: emular el comportamiento y UX del editor n8n con nuestra estética y stack (React Flow + Tailwind), evitando copy/paste literal pero asegurando que todas las capacidades estén presentes.
## Pasos detallados
1. **Setup de React Flow**
   - Instalar React Flow (si no esta) en `Frontend/package.json`. Configurar `ReactFlowProvider` dentro de `AgentCanvas`.
   - Configurar `defaultEdgeOptions`, `snapToGrid`, `fitView` basados en `Canvas.vue` (`reactFlowOptions`).
   - Reproducir configuracion de fondo (`GridBackground`), minimapa y viewport (consultar blueprint seccion estilos y `Canvas.vue`).
2. **Mapper AgentWorkflowDto -> ReactFlow**
   - Replicar logica de `useCanvasMapping.ts`:
     - Calcular `renderType` por nodo (default, sticky, AI prompt). En React usar `nodeTypes` registrando componentes personalizados.
     - Mapear `inputs` y `outputs` segun `NodeHelpers.getNodeInputs` (Task 01 debe exponer helper en backend; mientras tanto replicar logica con datos disponibles).
     - Calcular `nodeSubtitle`, `tooltips`, `badges` segun `nodeTypesStore` (consumir catalogo HTTP). Guardar en store para memoizacion.
     - Convertir `connections` a edges React Flow (usar `id = f"{sourceNode}-{sourceHandle}->{targetNode}-{targetHandle}"`).
     - Incluir `data.runtimeStatus`, `data.pinStatus`, `data.metrics` para overlay.
3. **Estado global (Zustand)**
   - Inspirarse en `workflows.store.ts` para definir slices:
     - `workflow`: `AgentWorkflowDto` actual.
     - `viewport`: `ViewportState { x, y, zoom }`.
     - `selection`: `{ nodes: string[], edges: string[] }`.
     - `ndv`: `{ open: boolean, nodeId?: string }`.
     - `execution`: `AgentExecutionState` (status, logs, metrics).
   - Implementar acciones `loadWorkflow`, `setViewport`, `selectNodes`, `applyPushEvent`, `persistMeta`.
   - Guardar `meta` usando `debounce` (500ms) antes de llamar `saveWorkflowMeta`.
4. **Integracion push**
   - `useAgentPushConnection` debe:
     - Abrir WS `ws(s)://backend/ws/graph?session_id=...&push_ref=...`.
     - Escuchar `AgentPushMessage` y actualizar store (`applyPushEvent`).
     - Reproducir logica de `usePushConnection.ts`: reconexion exponencial, heartbeats `ping/pong`, manejo de `broadcastExecutionFinished`.
   - En `applyPushEvent`, mapear tipos:
     - `execution_started` -> marcar `execution.status='running'`, `workflow.meta.executionSidebarMode='detail'`.
     - `node_execute_before` -> resaltar nodo (set `runtimeStatus='running'`).
     - `node_execute_after` -> actualizar `runtimeStatus` segun `status` e insertar resumen en panel.
     - `node_execute_after_data` -> guardar payload para NDV (limitar size, truncar si `truncated` flag).
     - `execution_finished` -> actualizar badges, limpiar highlight.
5. **Interacciones de canvas**
   - Drag & drop: habilitar `onNodeDragStop` -> persistir `node_positions` (Task 01 meta). Solo enviar `PATCH` cuando el usuario suelta nodo.
   - Conectar nodos: usar `onConnect` -> actualizar edges en store y enviar `PATCH` (en Task 03 solo actualizar estado local; persistencia real se define en Task futuro, dejar TODO).
   - Seleccion multiple: replicar lasso (`CanvasSelection` en n8n) usando `reactflow` builtin selection pero custom overlay.
   - Context menu: implementar `AgentCanvasContextMenu` inspirado en `useContextMenu.ts` (opciones: ejecutar nodo, duplicar, eliminar, disable/enable, tidy).
   - Atajos: `delete` -> elimina seleccion, `ctrl+d` -> duplicar (copiar nodo con offset 40,40), `shift+?` -> tidy (dejar TODO si no se implementa aun).
6. **Paneles y NDV**
   - Panel derecho: mostrar props de nodo (nombre, tipo, parametros) usando schema (apoyarse en catalogo).
   - Panel inferior: mostrar ejecucion en vivo (timeline, logs). Inyectar eventos push `node_execute_after_data`.
   - NDV: modal que recibe `execution_id` y `node_name`, renderiza json y binarios (ver `workflows.store.ts` metodos `setNodeExecutionData`).
   - Mantener estado en store `ndv` y cerrar al cambiar seleccion.
7. **Persistencia de meta**
   - Al cargar workflow, hidratar store con `dto.meta` (viewport, paneles, seleccion).
   - Usar `useEffect` para escuchar cambios en viewport (`onMoveEnd`) y llamar `saveWorkflowMeta` con `debounce`.
   - Garantizar que `runWorkflow` (boton) dispare `ExecutionService` y abra panel ejecucion.
8. **Estilos**
   - Reutilizar Tailwind tokens (`bg-gray-900`, `text-white`) y agregar CSS modules si es necesario.
   - Reproducir look del canvas n8n (grid, nodos con sombra, icono circular, badges). Revisar `CanvasNode.vue` para clases (colores `--color-primary`).
   - Mantener componentes accesibles (roles, aria-labels, focus visible).
9. **Tests**
   - `AgentCanvasMapping.test.tsx`: verificar que un `AgentWorkflowDto` simple se mapea a nodos/edges correctos, respetando `position` y `renderType`.
   - `AgentCanvasPush.test.tsx`: simular push events y comprobar actualizacion de store (usar `act()` para WebSocket mock).
   - Mock de API con MSW.
   - Documentar pendientes (ej. tests de atajos) si no se implementan.

## Riesgos y mitigaciones
- Riesgo: divergencia entre backend y frontend. Mitigacion: usar tipos generados con Zod/TypeScript desde schema (puede importarse swagger). Documentar en README si se genera codigo.
- Riesgo: React Flow performance con grafos grandes. Mitigacion: memoizar nodos y edges, usar `useMemo` y `ReactFlow.useStoreApi`.
- Riesgo: IA omita reconexion WS. Mitigacion: dejar TODO bien explicado en `useAgentPushConnection` y tests.
- Riesgo: estilos inconsistente. Mitigacion: crear `styles/agentCanvas.css` con tokens y referenciar blueprint.

## Definicion de hecho
- Canvas funcionando en `WorkspaceTab` (vista `overview`).
- WebSocket recibiendo y pintando eventos en vivo.
- Meta/viewport persistiendo tras recargar.
- Documentacion con capturas y diagrama de flujo de datos.

