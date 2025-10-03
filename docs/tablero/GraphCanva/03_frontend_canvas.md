# Task 03 - Canvas interactivo estilo n8n en Next.js

## Objetivo
Crear un canvas de workflow inspirado en el editor de n8n usando React Flow (o libreria equivalente), conectado al contrato definido en Task 01 y a los eventos push de Task 02.

## Alcance
- Nuevo modulo `Frontend/src/app/workspace/canvas` con componentes `AgentCanvas`, `AgentNode`, `AgentConnection`, paneles contextuales, minimapa, toolbar.
- Stores/hooks (Zustand o Context) para gestionar seleccion, shortcuts, viewport, ejecuciones en vivo y catalogos de nodos.
- Integracion con servicios API (`GET /agents/workflows`, `PATCH /agents/workflows`, `POST /agents/workflows/run`, catalogos).

## Pasos sugeridos
1. Elegir motor (React Flow recomendado); bootstrap de estilos y tematizacion siguiendo tokens en `tailwind.config.js`.
2. Implementar un mapper `useAgentCanvasMapping` que transforme `AgentWorkflowDto` -> `ReactFlow` nodes/edges, incluyendo estado (`running`, `success`, `error`, `disabled`).
3. Construir componentes UI clave: sidebar de nodos, panel de propiedades, menu contextual, overlays de ejecucion en vivo.
4. Conectar `useEffect`/WebSocket hook para escuchar eventos push y actualizar nodos/edges en tiempo real (animaciones, badges de items, logs).
5. Persistir `meta.viewport`, `node_positions`, `panelState` en backend al guardar el workflow.
6. Agregar pruebas unitarias (Jest/RTL) para el mapper y componentes criticos; documentar manual de uso en `docs/frontend`.

## Criterios de aceptacion
- Canvas soporta drag & drop, crear/borrar conexiones, zoom/pan suave, atajos basicos (duplicar, borrar, auto-layout en backlog).
- Live execution overlay muestra progreso por nodo y permite abrir detalles (modal NDV) con datos de `nodeExecuteAfterData`.
- Diseno responsivo, accesible y consistente con el resto del dashboard.
