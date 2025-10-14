# Flujo de visualización de agentes (post LangGraph)

## Objetivo
Mostrar al usuario, antes del mensaje final del orquestador, una simulación fiel de lo que generaron los agentes durante el batch de LangGraph.

## Resumen de alto nivel
1. El usuario lanza una consulta.
2. LangGraph la ejecuta y genera eventos + artefactos (`shared_artifacts`, `response_metadata`).
3. El backend envía el evento final con el resultado (batch completo ya terminado).
4. Antes de mostrar la respuesta al usuario, la UI debe:
   - Detener el mensaje final del orquestador.
   - Construir una narrativa con las frases descritas en `agent_action_phrases.md` usando los artefactos reales.
   - Reproducir esa narrativa (simulación)
   - Recién al terminar, inyectar el mensaje final en el chat.

## Pasos exactos en el frontend

### 1. Recepción del batch final
Cuando el hook (`useOrchestratorChat` / `SimpleChatBox`) detecta que `loading=false` y que hay nuevo contenido:
- Obtener los artefactos de la respuesta:
  ```ts
  const artifacts = shared_artifacts; // por agente
  const metadata = response_metadata;
  ```
- **No** mostrar aún el mensaje final al usuario.

### 2. Seleccionar frases por agente
Para cada agente con información en `shared_artifacts` o `response_metadata`:
- Determinar el `action type` (ej. `database_query`, `branch_operations`).
- Revisar qué campos hay disponibles (`rows`, `filters`, `analysis`, `alerts_to_persist`, etc.).
- Usar el catálogo `agent_action_phrases.md` así:
  1. **Frases contextuales** (si el campo coincide). Ej.: `rows` + `planner_metadata.branch` → usar bloque `sucursal_objetivo` de Capi DataB.
  2. Si no hay contexto, usar la **secuencia progresiva** del agente.
  3. Si no aplica ninguna, usar el **fallback genérico** (solo en casos raros).
- Armamos un array `SimulatedEvent[]` con `{agent, primaryText, detail?, status:'pending'}`.

### 3. Orden de la simulación
1. Mostrar la simulación del **orquestador** (lo existente hoy: morphing, etc.).
2. Inmediatamente después (sin mostrar la respuesta final), reproducir la lista `SimulatedEvent` de los agentes, cambiando el `status` a `active`, luego a `completed` (como ya hace `useEventSimulation`).
   - Tres pasos por agente, o menos si el artefacto solo amerita uno.
   - Respetar el orden en el que llegan los agentes (el mismo orden de `shared_artifacts`).

### 4. Liberar el mensaje final
Cuando la simulación termina (último evento `status='completed'`):
- Inyectar el texto final en el chat con `appendLocalMessage` / `hydrateMessages`.
- La UI debe mostrarlo solo en ese momento (no antes).

### 5. Validaciones
- Solo se usan datos reales del backend (no se generan textos sintéticos que no reflejen `shared_artifacts`).
- Si un agente no dejó artefacto, simplemente se omite de la narrativa.
- `agent_start`/`agent_end` **no** se muestran; la simulación viene exclusivamente de la data del batch.

## Notas finales
- Cada frase debe mantener el tono técnico definido (ver `agent_action_phrases.md`).
- Si en el futuro añadimos nuevos agentes o campos, debemos extender ese catálogo y este flujo.
- El objetivo es que el usuario perciba claramente qué trabajo hizo cada agente antes de recibir la respuesta final.
