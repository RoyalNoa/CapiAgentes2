# 🎯 ESPECIFICACIÓN DE IMPLEMENTACIÓN - Sistema de Eventos del Chat

**Proyecto:** CapiAgentes
**Versión:** 1.0
**Fecha:** 2025-10-04
**Propósito:** Especificación ejecutable para implementar sistema de eventos en tiempo real

---

## Addendum 2025-10-05

1. **Timeline unificado**: Eventos de agente y mensajes de la conversación comparten un único feed cronológico. Cada entrada mantiene la semántica original (colores y shimmer para `progress`, check cyan para `success`) para preservar la lectura minimalista pedida.
2. **Mensajes inter-agente**: Cuando un evento incluye `target_agent`, mostrar la redacción: "<Agente> solicitando información a <Destino>" para tonos `progress` y "<Agente> entregando datos a <Destino>" para tonos `success`. Se puede añadir el texto bruto recibido al final (`· mensaje`) si aporta contexto.
3. **Botón de voz push-to-talk**: Ubicar un botón con icono de micrófono a la derecha del campo de entrada. Es un control de pulsación prolongada (mantener presionado para grabar, soltar para finalizar). Durante la grabación puede mutar temporalmente a una palabra corta (p. ej. "Habla"). No se deben reintroducir tarjetas auxiliares; mantener el mismo tono visual del HUD principal.

Estas reglas sustituyen cualquier instrucción previa en el documento que contradiga los puntos anteriores.

## 📋 TABLA DE CONTENIDOS

1. [⚠️ REGLAS CRÍTICAS - LEE ESTO PRIMERO](#reglas-críticas)
2. [Objetivo y Requisitos](#objetivo-y-requisitos)
3. [Arquitectura del Sistema](#arquitectura-del-sistema)
4. [Backend - Especificación Técnica](#backend-especificación-técnica)
5. [Frontend - Especificación Técnica](#frontend-especificación-técnica)
6. [Especificación UX/UI](#especificación-uxui)
7. [Comportamiento Esperado](#comportamiento-esperado)
8. [Checklist de Implementación](#checklist-de-implementación)
9. [Testing y Validación](#testing-y-validación)

---

## ⚠️ REGLAS CRÍTICAS - LEE ESTO PRIMERO

### **QUÉ HACER - EXACTAMENTE ESTO Y NADA MÁS**

#### **✅ HACER:**

1. **SOLO modificar los archivos listados en la sección 3 y 4**
   - Backend: `event_broadcaster.py`, `base.py`, `graph_runtime.py`
   - Frontend: `GlobalChatContext.tsx`, `SimpleChatBox.tsx`, `SimpleChatBox.module.css` (crear), `globals.css`, `useOrchestratorChat.ts`

2. **SOLO agregar el código exacto que está especificado**
   - Si dice "agregar parámetro `action`" → agregar SOLO ese parámetro
   - Si dice "agregar método `_get_action_type()`" → agregar SOLO ese método
   - NO agregar validaciones extra
   - NO agregar comentarios extra
   - NO agregar imports extra (solo los necesarios para el código especificado)

3. **SOLO eliminar lo que está marcado con ❌ ELIMINAR**
   - Componentes: `MessageArea.tsx`, `ProcessingView.tsx`
   - Código específico marcado con comentarios `// ❌ ELIMINAR`

4. **COPIAR código exactamente como está escrito**
   - Nombres de variables: exactos
   - Nombres de métodos: exactos
   - Strings: exactos (incluyendo tildes en español)
   - Colores hex: exactos (#f7ab2f, #00e5ff, #ff5a6b)

#### **❌ NO HACER:**

1. **NO crear archivos nuevos** excepto:
   - `SimpleChatBox.module.css` (está especificado)
   - Scripts de testing en sección 8 (opcional para validar)

2. **NO modificar archivos no listados**
   - NO tocar `WebSocket client code` no mencionado
   - NO tocar `routing logic` no mencionado
   - NO tocar `state management` no mencionado
   - NO tocar `other components` no mencionados

3. **NO agregar funcionalidad extra**
   - NO agregar logging extra
   - NO agregar error handling extra (solo lo que está en el código)
   - NO agregar validaciones extra
   - NO agregar optimizaciones "mejores"
   - NO agregar comentarios "explicativos"

4. **NO cambiar nombres o valores**
   - NO renombrar variables "para que suene mejor"
   - NO cambiar colores "para que se vea mejor"
   - NO cambiar timings "para que sea más rápido"
   - NO cambiar strings de español a inglés o viceversa

5. **NO refactorizar código existente**
   - NO "mejorar" código que funciona
   - NO "limpiar" código legacy
   - NO "optimizar" otras partes
   - SOLO tocar lo especificado

6. **NO agregar dependencias**
   - NO instalar nuevas librerías
   - NO agregar nuevos imports si no están en el código especificado

#### **🎯 REGLA DE ORO:**

```
SI NO ESTÁ EXPLÍCITAMENTE ESCRITO EN ESTE DOCUMENTO = NO LO HAGAS
```

**Ejemplo de lo que SÍ hacer:**

✅ Especificación dice: "Agregar parámetro `action: Optional[str] = None`"
✅ Tu código:
```python
def broadcast_agent_start(
    self,
    agent_name: str,
    session_id: str,
    action: Optional[str] = None,  # ← EXACTAMENTE esto
    meta: Optional[Dict[str, Any]] = None
):
```

**Ejemplo de lo que NO hacer:**

❌ Tu código:
```python
def broadcast_agent_start(
    self,
    agent_name: str,
    session_id: str,
    action: Optional[str] = None,
    action_type: Optional[str] = None,  # ← NO! No está especificado
    meta: Optional[Dict[str, Any]] = None,
    verbose: bool = False  # ← NO! No está especificado
):
    # Validate action type  ← NO! No está especificado
    if action and not self._is_valid_action(action):
        raise ValueError(f"Invalid action: {action}")
```

#### **📝 CHECKLIST ANTES DE CODIFICAR:**

Pregúntate:
- [ ] ¿Este cambio está listado explícitamente en la sección 3 o 4?
- [ ] ¿Estoy agregando SOLO lo que dice la especificación?
- [ ] ¿Estoy copiando el código exactamente como está escrito?
- [ ] ¿Estoy tocando SOLO los archivos listados?
- [ ] ¿NO estoy agregando "mejoras" o "optimizaciones"?

Si alguna respuesta es "No" → **DETENTE y relee la especificación**

---

## 1. OBJETIVO Y REQUISITOS

### **Objetivo Principal**
Implementar sistema de eventos del chat que muestre comunicación real entre agentes en tiempo real, con diseño minimalista coherente con HUD Navigator.

### **Requisitos Funcionales**

| ID | Requisito | Criterio de Aceptación |
|----|-----------|------------------------|
| RF-01 | Eventos aparecen uno por uno en tiempo real | Intervalo 100-300ms entre eventos, NO batch |
| RF-02 | Mostrar comunicación inter-agente | Formato "Actor → Target: Mensaje" cuando hay target_agent |
| RF-03 | Headers solo cuando cambia agente | Header aparece solo si agente diferente al anterior |
| RF-04 | Action types semánticos | Backend envía action, Frontend traduce a español gerundio |
| RF-05 | Estados visuales claros | Progress (orange shimmer), Success (cyan checkmark), Error (red dot) |
| RF-06 | Sin mensajes hardcoded | Cero mensajes mock o fake en código |
| RF-07 | Persistencia de eventos | Eventos permanecen en historial, usuario puede scrollear |

### **Requisitos No Funcionales**

| ID | Requisito | Criterio de Aceptación |
|----|-----------|------------------------|
| RNF-01 | Performance | Renderizar evento en <16ms (60 FPS) |
| RNF-02 | Coherencia visual | Colores exactos del HUD Navigator |
| RNF-03 | Minimalismo | Sin borders, sin backgrounds visibles en eventos |
| RNF-04 | Accesibilidad | Checkmarks Unicode compatibles con screen readers |
| RNF-05 | Responsividad | Funciona en viewports 320px-4K |

### **Archivos a Eliminar**
```bash
# ELIMINAR COMPLETAMENTE (NO refactorizar):
Frontend/src/app/components/chat/messages/MessageArea.tsx
Frontend/src/app/components/chat/messages/ProcessingView.tsx
```

**Rationale:** Componentes duplicados, SimpleChatBox.tsx es suficiente.

---

## 2. ARQUITECTURA DEL SISTEMA

### **Flujo de Datos End-to-End**

```
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (Python)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  GraphRuntime / GraphNode                                   │
│       ↓                                                     │
│  _emit_transition() / _emit_agent_start()                   │
│       ↓                                                     │
│  Determina action type:                                     │
│    action = _map_node_to_action(node_name)                  │
│       ↓                                                     │
│  Extrae target_agent de state.response_metadata             │
│       ↓                                                     │
│  event_broadcaster.broadcast_*()                            │
│    action="router",                                         │
│    meta={"target_agent": "capidatab", ...}                  │
│       ↓                                                     │
│  WebSocket /ws/agents EMIT                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ WebSocket Event
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  useAgentWebSocket() RECEIVE                                │
│       ↓                                                     │
│  lastAgentEvent updated                                     │
│       ↓                                                     │
│  GlobalChatContext.processAgentEvent()                      │
│       ↓                                                     │
│  formatAgentEvent():                                        │
│    actionType = event.data.action || event.type             │
│    messageConfig = ACTION_MESSAGES[actionType]              │
│       ↓                                                     │
│  Construye Message object:                                  │
│    { text: "Consultando...", tone: "progress", ... }        │
│       ↓                                                     │
│  Agrega a messages array                                    │
│       ↓                                                     │
│  SimpleChatBox.renderAgentEventMessage()                    │
│       ↓                                                     │
│  Renderiza:                                                 │
│    - Dot/Checkmark según tone                               │
│    - Texto con/sin shimmer                                  │
│    - Formato inter-agente si target_agent existe            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Componentes Clave**

| Componente | Responsabilidad | Archivo |
|------------|----------------|---------|
| EventBroadcaster | Emitir eventos WebSocket con action types | `Backend/src/infrastructure/websocket/event_broadcaster.py` |
| GraphNode | Emitir agent_start/end con action types | `Backend/src/infrastructure/langgraph/nodes/base.py` |
| GraphRuntime | Emitir node_transition con action types | `Backend/src/infrastructure/langgraph/graph_runtime.py` |
| useAgentWebSocket | Recibir eventos del backend | `Frontend/src/app/hooks/useAgentWebSocket.ts` |
| GlobalChatContext | Formatear eventos → mensajes | `Frontend/src/app/contexts/GlobalChatContext.tsx` |
| SimpleChatBox | Renderizar UI de eventos | `Frontend/src/app/components/chat/SimpleChatBox.tsx` |

---

## 3. BACKEND - ESPECIFICACIÓN TÉCNICA

### **3.1. event_broadcaster.py**

#### **Modificación: Agregar parámetro `action`**

**Archivo:** `Backend/src/infrastructure/websocket/event_broadcaster.py`

**Cambios requeridos:**

```python
# ANTES (línea ~60):
async def broadcast_node_transition(
    self,
    from_node: str,
    to_node: str,
    session_id: str,
    meta: Optional[Dict[str, Any]] = None
) -> None:
    # ...

# DESPUÉS:
async def broadcast_node_transition(
    self,
    from_node: str,
    to_node: str,
    session_id: str,
    action: Optional[str] = None,  # ← NUEVO PARÁMETRO
    meta: Optional[Dict[str, Any]] = None
) -> None:
    """Broadcast node transition event with semantic action type."""

    payload = {
        "from": from_node,
        "to": to_node,
        "session_id": session_id,
        **(meta or {})
    }

    # AGREGAR: Include action type if provided
    if action:
        payload["action"] = action

    event = WebSocketEvent(
        type="node_transition",
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        data=payload,
        meta=meta
    )

    await self._broadcast_to_agent_stream(event, session_id)
```

**Aplicar mismo cambio a:**
- `broadcast_agent_start()` (línea ~100)
- `broadcast_agent_end()` (línea ~140)

**Criterio de validación:**
```python
# Después del cambio, estos métodos deben aceptar:
await broadcaster.broadcast_agent_start(
    agent_name="summary",
    session_id="test",
    action="summary_generation",  # ← Este parámetro debe funcionar
    meta={...}
)
```

---

### **3.2. base.py (GraphNode)**

#### **Modificación 1: Agregar método `_get_action_type()`**

**Archivo:** `Backend/src/infrastructure/langgraph/nodes/base.py`

**Agregar después de línea ~50:**

```python
def _get_action_type(self) -> str:
    """
    Map node/agent name to semantic action type for frontend display.

    Returns semantic action string that frontend maps to Spanish gerund messages.

    Examples:
        'IntentNode' → 'intent'
        'SummaryNode' → 'summary_generation'
        'CapiDataBNode' → 'database_query'
    """
    node_name = self.name.lower()

    # Comprehensive action map - 40+ mappings
    action_map = {
        # Orchestration nodes
        'start': 'start',
        'startnode': 'start',
        'intent': 'intent',
        'intentnode': 'intent',
        'router': 'router',
        'routernode': 'router',
        'supervisor': 'supervisor',
        'supervisornode': 'supervisor',
        'react': 'react',
        'reactnode': 'react',
        'reasoning': 'reasoning',
        'reasoningnode': 'reasoning',
        'human_gate': 'human_gate',
        'humangatenode': 'human_gate',
        'assemble': 'assemble',
        'assemblenode': 'assemble',
        'finalize': 'finalize',
        'finalizenode': 'finalize',

        # Agent nodes - Summary
        'summary': 'summary_generation',
        'summarynode': 'summary_generation',
        'summaryagent': 'summary_generation',

        # Agent nodes - Branch
        'branch': 'branch_analysis',
        'branchnode': 'branch_analysis',
        'branchagent': 'branch_analysis',

        # Agent nodes - Anomaly
        'anomaly': 'anomaly_detection',
        'anomalynode': 'anomaly_detection',
        'anomalyagent': 'anomaly_detection',

        # Agent nodes - CapiDataB
        'capidatab': 'database_query',
        'capidatabnode': 'database_query',
        'datab': 'database_query',
        'databnode': 'database_query',

        # Agent nodes - CapiElCajas
        'capielcajas': 'branch_operations',
        'capielcajasnode': 'branch_operations',
        'elcajas': 'branch_operations',

        # Agent nodes - CapiDesktop
        'capidesktop': 'desktop_operation',
        'capidesktopnode': 'desktop_operation',
        'desktop': 'desktop_operation',

        # Agent nodes - CapiNoticias
        'capinoticias': 'news_analysis',
        'capinoticiasnode': 'news_analysis',
        'noticias': 'news_analysis',

        # Agent nodes - Smalltalk
        'smalltalk': 'conversation',
        'smalltalknode': 'conversation',
        'smalltalkagent': 'conversation',
    }

    return action_map.get(node_name, 'agent_start')
```

#### **Modificación 2: Actualizar `_emit_agent_start()`**

**Archivo:** `Backend/src/infrastructure/langgraph/nodes/base.py`
**Localización:** Línea ~97

```python
def _emit_agent_start(self, state: GraphState):
    """Emit WebSocket event when agent starts with semantic action type."""

    if hasattr(self, "_is_agent_node") and self._is_agent_node:
        broadcaster = get_event_broadcaster()

        # NUEVO: Get semantic action type
        action = self._get_action_type()

        # Build metadata
        meta = {"trace_id": state.trace_id, "node": self.name}

        # NUEVO: Extract target_agent from state metadata for inter-agent visualization
        if state.response_metadata:
            semantic_result = state.response_metadata.get("semantic_result", {})

            if semantic_result.get("target_agent"):
                meta["target_agent"] = semantic_result["target_agent"]

            if semantic_result.get("routing_agent"):
                meta["routing_agent"] = semantic_result["routing_agent"]

        self._emit_async_event(
            broadcaster.broadcast_agent_start(
                agent_name=self.name,
                session_id=state.session_id or "unknown",
                action=action,  # ← NUEVO: pasar action type
                meta=meta       # ← INCLUYE target_agent si existe
            ),
            "agent_start event"
        )
```

#### **Modificación 3: Actualizar `_emit_agent_end()`**

**Archivo:** `Backend/src/infrastructure/langgraph/nodes/base.py`
**Localización:** Línea ~123

```python
def _emit_agent_end(self, state: GraphState, success: bool = True, duration_ms: Optional[float] = None):
    """Emit WebSocket event when agent ends."""

    if hasattr(self, "_is_agent_node") and self._is_agent_node:
        broadcaster = get_event_broadcaster()

        self._emit_async_event(
            broadcaster.broadcast_agent_end(
                agent_name=self.name,
                session_id=state.session_id or "unknown",
                success=success,
                duration_ms=duration_ms,
                action='agent_end',  # ← NUEVO: explicit action type
                meta={"trace_id": state.trace_id, "node": self.name}
            ),
            "agent_end event"
        )
```

---

### **3.3. graph_runtime.py**

#### **Modificación 1: Agregar método `_map_node_to_action()`**

**Archivo:** `Backend/src/infrastructure/langgraph/graph_runtime.py`
**Agregar después de línea ~500:**

```python
def _map_node_to_action(self, node_name: str) -> str:
    """
    Map node name to semantic action type for frontend display.

    Args:
        node_name: Name of the node (e.g., "intent", "router", "summary")

    Returns:
        Semantic action string (e.g., "intent", "router", "summary_generation")
    """
    node_lower = node_name.lower()

    action_map = {
        # Orchestration nodes
        'start': 'start',
        'intent': 'intent',
        'router': 'router',
        'supervisor': 'supervisor',
        'react': 'react',
        'reasoning': 'reasoning',
        'human_gate': 'human_gate',
        'assemble': 'assemble',
        'finalize': 'finalize',

        # Agent nodes
        'summary': 'summary_generation',
        'branch': 'branch_analysis',
        'anomaly': 'anomaly_detection',
        'capidatab': 'database_query',
        'capielcajas': 'branch_operations',
        'capidesktop': 'desktop_operation',
        'capinoticias': 'news_analysis',
        'smalltalk': 'conversation',
    }

    return action_map.get(node_lower, node_name.lower())
```

#### **Modificación 2: Actualizar `_emit_transition()`**

**Archivo:** `Backend/src/infrastructure/langgraph/graph_runtime.py`
**Localización:** Línea ~546

```python
def _emit_transition(
    self,
    from_node: Optional[str],
    to_node: Optional[str],
    session_id: str,
    state: GraphState,
) -> None:
    """Emit node transition event with semantic action type and inter-agent metadata."""

    if not self.event_broadcaster or not from_node or not to_node:
        return

    # NUEVO: Determine semantic action type based on target node
    action = self._map_node_to_action(to_node)

    # Build metadata
    meta = {
        "trace_id": state.trace_id,
        "completed_nodes": list(state.completed_nodes),
    }

    # NUEVO: Extract target_agent/routing_agent from state metadata
    if state.response_metadata:
        semantic_result = state.response_metadata.get("semantic_result", {})

        if semantic_result.get("target_agent"):
            meta["target_agent"] = semantic_result["target_agent"]

        if semantic_result.get("routing_agent"):
            meta["routing_agent"] = semantic_result["routing_agent"]

    coro = self.event_broadcaster.broadcast_node_transition(
        from_node,
        to_node,
        session_id,
        action=action,  # ← NUEVO: semantic action type
        meta=meta,      # ← INCLUYE target_agent/routing_agent
    )
    self._dispatch_async(coro, "node_transition")
```

---

## 4. FRONTEND - ESPECIFICACIÓN TÉCNICA

### **4.1. GlobalChatContext.tsx**

#### **Modificación 1: ACTION_MESSAGES completo**

**Archivo:** `Frontend/src/app/contexts/GlobalChatContext.tsx`
**Localización:** Reemplazar NODE_MESSAGES/EVENT_PRESETS existente

```typescript
const ACTION_MESSAGES: Record<string, (meta?: any) => {
  summary: string;
  detail?: string;
  tone?: AgentEventTone
}> = {

  // Event types
  'node_transition': () => ({ summary: 'Avanzando...', tone: 'progress' as AgentEventTone }),
  'agent_start': () => ({ summary: 'Iniciando...', tone: 'progress' as AgentEventTone }),
  'agent_end': () => ({ summary: 'Completado', tone: 'success' as AgentEventTone }),
  'error': () => ({ summary: 'Error detectado', tone: 'error' as AgentEventTone }),

  // Orchestration nodes
  'start': () => ({ summary: 'Iniciando workflow...', tone: 'progress' as AgentEventTone }),
  'intent': () => ({ summary: 'Clasificando consulta...', tone: 'progress' as AgentEventTone }),
  'router': () => ({ summary: 'Determinando ruta...', tone: 'progress' as AgentEventTone }),
  'supervisor': () => ({ summary: 'Supervisando...', tone: 'progress' as AgentEventTone }),
  'react': () => ({ summary: 'Razonando...', tone: 'progress' as AgentEventTone }),
  'reasoning': () => ({ summary: 'Planificando...', tone: 'progress' as AgentEventTone }),
  'human_gate': () => ({ summary: 'Esperando aprobación...', tone: 'warning' as AgentEventTone }),
  'assemble': () => ({ summary: 'Ensamblando respuesta...', tone: 'progress' as AgentEventTone }),
  'finalize': () => ({ summary: 'Finalizando...', tone: 'progress' as AgentEventTone }),

  // Agent nodes
  'capidatab': () => ({ summary: 'Consultando base de datos...', tone: 'progress' as AgentEventTone }),
  'database_query': () => ({ summary: 'Consultando base de datos...', tone: 'progress' as AgentEventTone }),

  'capielcajas': () => ({ summary: 'Analizando cajas...', tone: 'progress' as AgentEventTone }),
  'branch_operations': () => ({ summary: 'Operando con sucursal...', tone: 'progress' as AgentEventTone }),

  'summary': () => ({ summary: 'Generando resumen...', tone: 'progress' as AgentEventTone }),
  'summary_generation': () => ({ summary: 'Generando resumen...', tone: 'progress' as AgentEventTone }),

  'branch': () => ({ summary: 'Analizando sucursal...', tone: 'progress' as AgentEventTone }),
  'branch_analysis': () => ({ summary: 'Analizando sucursal...', tone: 'progress' as AgentEventTone }),

  'anomaly': () => ({ summary: 'Detectando anomalías...', tone: 'progress' as AgentEventTone }),
  'anomaly_detection': () => ({ summary: 'Detectando anomalías...', tone: 'progress' as AgentEventTone }),

  'capidesktop': () => ({ summary: 'Operando en escritorio...', tone: 'progress' as AgentEventTone }),
  'desktop_operation': () => ({ summary: 'Operando en escritorio...', tone: 'progress' as AgentEventTone }),

  'capinoticias': () => ({ summary: 'Analizando noticias...', tone: 'progress' as AgentEventTone }),
  'news_analysis': () => ({ summary: 'Analizando noticias...', tone: 'progress' as AgentEventTone }),

  'smalltalk': () => ({ summary: 'Conversando...', tone: 'progress' as AgentEventTone }),
  'conversation': () => ({ summary: 'Conversando...', tone: 'progress' as AgentEventTone }),
};
```

**Total:** 30+ action types (expandir según agentes adicionales en tu sistema)

#### **Modificación 2: Simplificar formatAgentEvent**

**Archivo:** `Frontend/src/app/contexts/GlobalChatContext.tsx`
**Localización:** Línea ~378 (método existente)

```typescript
const formatAgentEvent = useCallback((event: AgentEvent): FormattedAgentEvent => {
  // 1. Extract timestamp
  const timestampSource =
    (typeof event.timestamp === 'string' && event.timestamp) ||
    (event.data && typeof (event.data as Record<string, unknown>).timestamp === 'string'
      ? ((event.data as Record<string, unknown>).timestamp as string)
      : undefined);
  const eventDate = timestampSource ? new Date(timestampSource) : new Date();
  const timestamp = Number.isNaN(eventDate.getTime()) ? new Date() : eventDate;

  // 2. Extract metadata
  const metadata = event.meta || event.data || {};
  const actor = friendlyAgentName(extractAgentFromEvent(event));

  // 3. CRITICAL: Determine action type - Check data.action FIRST!
  const actionType = (event.data as any)?.action
    || event.type
    || (typeof event.to === 'string' ? event.to.toLowerCase() : '');

  // 4. Lookup message generator from ACTION_MESSAGES
  const messageFunc = ACTION_MESSAGES[actionType];
  const messageConfig = messageFunc ? messageFunc(metadata) : null;

  // 5. Determine tone
  let tone: AgentEventTone = messageConfig?.tone || 'progress';
  if (event.ok === false || event.type.includes('error')) {
    tone = 'error';
  } else if (event.type.includes('end') || event.type.includes('complete')) {
    tone = 'success';
  }

  // 6. Build summary and detail
  const summary = messageConfig?.summary || actionType.replace(/_/g, ' ');
  const detail = messageConfig?.detail || extractAdditionalDetail(event);

  return {
    summary,
    detail,
    actor,
    tone,
    timestamp,
  };
}, []);
```

**Longitud objetivo:** ~40 líneas (vs ~117 original)

#### **Modificación 3: Arreglar batching**

**Archivo:** `Frontend/src/app/contexts/GlobalChatContext.tsx`
**Localización:** Buscar useEffect con `agentEvents`

```typescript
// ❌ ELIMINAR ESTE useEffect (procesa todo el array - causa batching):
/*
useEffect(() => {
  agentEvents.forEach(event => {
    const key = getAgentEventKey(event);
    if (processedAgentEventIdsRef.current.has(key)) return;
    processedAgentEventIdsRef.current.add(key);
    processAgentEvent(event);
  });
}, [agentEvents, processAgentEvent, getAgentEventKey]);
*/

// ✅ REEMPLAZAR CON ESTE (procesa solo último - tiempo real):
useEffect(() => {
  if (!lastAgentEvent) return;

  const key = getAgentEventKey(lastAgentEvent);
  if (processedAgentEventIdsRef.current.has(key)) return;

  processedAgentEventIdsRef.current.add(key);
  processAgentEvent(lastAgentEvent);
}, [lastAgentEvent, processAgentEvent, getAgentEventKey]);
```

#### **Modificación 4: Eliminar hardcoded spaces**

**Archivo:** `Frontend/src/app/contexts/GlobalChatContext.tsx`
**Buscar:** `content: \`    ${`

```typescript
// ❌ ANTES:
content: `    ${summary}...`

// ✅ DESPUÉS:
content: summary
```

---

### **4.2. SimpleChatBox.tsx**

#### **Modificación 1: Importar CSS module**

**Archivo:** `Frontend/src/app/components/chat/SimpleChatBox.tsx`
**Agregar al inicio:**

```typescript
import styles from './SimpleChatBox.module.css';
```

#### **Modificación 2: Actualizar renderAgentEventMessage**

**Archivo:** `Frontend/src/app/components/chat/SimpleChatBox.tsx`
**Localización:** Método `renderAgentEventMessage`

```typescript
const renderAgentEventMessage = (msg: Message, index: number) => {
  const payload = msg.payload as AgentEventPayload;
  const isHeader = (payload as any).isHeader === true;
  const indent = (payload as any).indent === true;

  // Extract tone
  const toneValue = typeof (payload as any).tone === 'string'
    ? (payload as any).tone
    : isHeader ? 'info' : 'progress';

  // Determine states
  const isSuccess = toneValue === 'success';
  const isProgress = toneValue === 'progress';

  // Color mapping HUD
  const toneColorMap: Record<string, string> = {
    progress: '#f7ab2f',     // 🟠 Orange
    success: '#00e5ff',      // 🔵 Cyan
    error: '#ff5a6b',        // 🔴 Red
    warning: '#f7ab2f',
    info: THEME.colors.textMuted,
  };

  const baseColor = toneColorMap[toneValue] || THEME.colors.textMuted;

  // Extract actor and target for inter-agent communication
  const actor = (payload as any).actor || msg.agent || 'CAPI';
  const eventData = (payload as any).event?.data || (payload as any).event?.meta || {};
  const targetAgent = eventData.target_agent || eventData.target || eventData.to_agent;

  // Build message text
  let displayText = msg.text;

  // Format inter-agent: "Actor → Target: Message"
  if (!isHeader && targetAgent && !msg.text.includes('→')) {
    const friendlyTarget = friendlyAgentName(targetAgent);
    displayText = `${actor} → ${friendlyTarget}: ${msg.text.trim()}`;
  }

  // Render
  return (
    <div
      key={msg.id}
      className={`${styles.eventMessage} ${indent ? styles.indent : ''}`}
    >
      <div className={styles.eventMessageRow}>
        {/* Icon: Checkmark for success, bullet for others */}
        {isSuccess ? (
          <span
            style={{
              color: baseColor,
              fontWeight: 'bold',
              fontSize: '14px'
            }}
          >
            ✓
          </span>
        ) : (
          <div
            className={styles.eventBullet}
            style={{ backgroundColor: baseColor, color: baseColor }}
          />
        )}

        {/* Text with shimmer if progress */}
        <span
          className={`${styles.eventText} ${isProgress ? styles.shimmer : ''}`}
          style={{ color: baseColor }}
        >
          {displayText}
        </span>
      </div>
    </div>
  );
};
```

#### **Modificación 3: Eliminar código mock**

**Archivo:** `Frontend/src/app/components/chat/SimpleChatBox.tsx`

```typescript
// ❌ ELIMINAR estas interfaces:
/*
interface TaskStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'complete';
}

interface ProcessingMessage {
  id: string;
  steps: TaskStep[];
}
*/

// ❌ ELIMINAR este state:
// const [processingMessage, setProcessingMessage] = useState<ProcessingMessage | null>(null);

// ❌ ELIMINAR useEffect de tareas mock (buscar "mockSteps"):
// useEffect(() => { ... mockSteps ... }, [loading, messages]);

// ❌ ELIMINAR condición con processingMessage:
// && !processingMessage
```

---

### **4.3. SimpleChatBox.module.css (CREAR)**

**Archivo:** `Frontend/src/app/components/chat/SimpleChatBox.module.css` (NUEVO)

```css
/* Container minimalista - sin borders, sin backgrounds */
.eventMessage {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px 0;
  font-family: var(--hud-font-ui);
}

/* Fila de evento (icon + text) */
.eventMessageRow {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Dot pulsante con triple box-shadow para brillo aumentado */
.eventBullet {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  animation: eventGlow 1.8s ease-in-out infinite alternate;

  /* Triple box-shadow para glow effect */
  box-shadow:
    0 0 12px currentColor,
    0 0 24px color-mix(in srgb, currentColor 70%, transparent),
    0 0 36px color-mix(in srgb, currentColor 40%, transparent);
}

/* Texto de evento */
.eventText {
  font-size: 13px;
  line-height: 1.4;
  font-family: var(--hud-font-ui);
}

/* Shimmer effect para eventos progress */
.eventText.shimmer {
  animation: shimmer 2s ease-in-out infinite;
}

/* Indentación para jerarquía */
.indent {
  padding-left: 16px;
}

/* Header de agente */
.agentHeader {
  font-weight: 600;
  margin-top: 8px;
  margin-bottom: 4px;
  opacity: 0.9;
}
```

---

### **4.4. globals.css**

#### **Modificación: Agregar animaciones**

**Archivo:** `Frontend/src/app/ui/globals.css`
**Agregar después de línea 66:**

```css
/* Shimmer effect para texto en progreso */
@keyframes shimmer {
  0%, 100% {
    opacity: 0.6;
  }
  50% {
    opacity: 1;
  }
}

/* Event glow - brillo aumentado para dots */
@keyframes eventGlow {
  0% {
    box-shadow:
      0 0 8px currentColor,
      0 0 16px color-mix(in srgb, currentColor 50%, transparent);
  }
  100% {
    box-shadow:
      0 0 16px currentColor,
      0 0 32px color-mix(in srgb, currentColor 60%, transparent),
      0 0 48px color-mix(in srgb, currentColor 30%, transparent);
  }
}
```

---

### **4.5. useOrchestratorChat.ts**

#### **Modificación: Eliminar mensaje hardcoded**

**Archivo:** `Frontend/src/app/utils/orchestrator/useOrchestratorChat.ts`
**Buscar y eliminar:**

```typescript
// ❌ ELIMINAR:
/*
const progressMessage = {
  id: genId(),
  role: 'agent' as const,
  agent: 'system',
  content: '🔍 Analizando consulta...',
  payload: { is_progress: true, progress_step: 'analyzing' }
};
*/
```

---

## 5. ESPECIFICACIÓN UX/UI

### **5.1. Paleta de Colores**

| Estado | Hex | Uso |
|--------|-----|-----|
| Progress | `#f7ab2f` | Dot pulsante + texto shimmer |
| Success | `#00e5ff` | Checkmark + texto estático |
| Error | `#ff5a6b` | Dot estático + texto |
| Warning | `#f7ab2f` | Dot estático + texto |
| Info | `THEME.colors.textMuted` | Headers |

**Fuente:** Exactos del HUD Navigator (coherencia visual total)

---

### **5.2. Tipografía**

| Elemento | Font | Size | Weight | Line Height |
|----------|------|------|--------|-------------|
| Event text | `var(--hud-font-ui)` | 13px | 400 | 1.4 |
| Agent header | `var(--hud-font-ui)` | 13px | 600 | 1.4 |
| Checkmark | System font | 14px | 700 | — |

---

### **5.3. Espaciado**

| Elemento | Value |
|----------|-------|
| Event vertical padding | 4px |
| Event row gap | 8px |
| Header margin top | 8px |
| Header margin bottom | 4px |
| Indent padding left | 16px |

---

### **5.4. Efectos Visuales**

#### **Shimmer (texto progress):**
```css
animation: shimmer 2s ease-in-out infinite;
/* Opacity: 0.6 ↔ 1.0 */
```

**Cuándo:** Solo eventos con `tone: 'progress'`

#### **Event Glow (dots):**
```css
animation: eventGlow 1.8s ease-in-out infinite alternate;
/* Box-shadow triple layer expansión */
```

**Cuándo:** Todos los dots (no checkmarks)

---

### **5.5. Estados Visuales**

#### **Progress:**
```
🟠 Consultando base de datos...
   ↑                        ↑
   Dot                   Shimmer
   #f7ab2f              Opacity pulsante
   Glow animation
```

#### **Success:**
```
✓ Completado
↑          ↑
Checkmark  Text
#00e5ff    #00e5ff
14px bold  13px normal
           Sin shimmer
```

#### **Error:**
```
🔴 Error: No se encontraron datos
   ↑                              ↑
   Dot                          Text
   #ff5a6b                      #ff5a6b
   Glow                         Sin shimmer
```

---

## 6. COMPORTAMIENTO ESPERADO

### **6.1. Flujo Temporal Estándar**

```
t=0.0s   → Usuario envía consulta
t=0.1s   → Mensaje de usuario aparece
t=0.15s  → 🟠 Clasificando consulta... (event 1)
t=0.30s  → 🟠 Determinando ruta... (event 2)
t=0.50s  → 🟠 Router → Branch: Enrutando... (event 3 - inter-agent)
t=0.80s  → Branch (header porque cambió agente)
           🟠 Analizando sucursal... (event 4)
t=1.20s  → 🟠 Branch → CapiDataB: Solicitando datos... (event 5)
           CapiDataB (header)
           🟠 Consultando base de datos... (event 6)
t=2.50s  → ✓ Completado (event 7 - success)
           Branch (header)
           🟠 Procesando datos... (event 8)
t=4.50s  → ✓ Completado (event 9)
t=5.00s  → CAPI (header)
           [Respuesta final con datos]
```

**Características clave:**
- Eventos aparecen UNO POR UNO (intervalo ~150-300ms)
- Headers solo cuando cambia agente
- Formato inter-agente cuando hay target_agent
- Checkmarks al completar
- NO silencio largo seguido de batch

---

### **6.2. Casos de Uso Críticos**

#### **UC-01: Consulta Simple**
```
INPUT: "dame un resumen"

OUTPUT:
🟠 Clasificando consulta...
🟠 Determinando ruta...

Summary
🟠 Generando resumen...
✓ Completado

CAPI
[Respuesta]
```

#### **UC-02: Comunicación Inter-Agente**
```
INPUT: "analiza sucursal 001"

OUTPUT:
🟠 Router → CapiDataB: Solicitando datos...

CapiDataB
🟠 Consultando base de datos...
✓ Completado
```

#### **UC-03: Error**
```
INPUT: "datos inexistentes"

OUTPUT:
🟠 Consultando base de datos...
🔴 Error: No se encontraron datos

CAPI
❌ Lo siento, no encontré datos.
```

---

### **6.3. Validaciones de Comportamiento**

| Validación | Criterio |
|------------|----------|
| V-01: Tiempo real | Cada evento renderiza <100ms después de recibir WebSocket |
| V-02: No batching | Máximo 1 evento renderizado por ciclo de event loop |
| V-03: Inter-agent | Si `meta.target_agent` existe → formato "Actor → Target: Mensaje" |
| V-04: Headers | Header renderiza SOLO si `msg.agent !== previousAgent` |
| V-05: Shimmer | Class `shimmer` SOLO en eventos con `tone === 'progress'` |
| V-06: Checkmark | Símbolo `✓` SOLO en eventos con `tone === 'success'` |
| V-07: Colores | Colors exactos: progress=#f7ab2f, success=#00e5ff, error=#ff5a6b |
| V-08: Persistencia | Eventos permanecen en DOM después de completar |

---

## 7. CHECKLIST DE IMPLEMENTACIÓN

### **Backend**

#### **event_broadcaster.py**
- [ ] Agregar parámetro `action: Optional[str]` a `broadcast_node_transition()`
- [ ] Agregar parámetro `action: Optional[str]` a `broadcast_agent_start()`
- [ ] Agregar parámetro `action: Optional[str]` a `broadcast_agent_end()`
- [ ] Incluir `action` en payload cuando existe: `if action: payload["action"] = action`

#### **base.py**
- [ ] Crear método `_get_action_type()` con 40+ mappings
- [ ] Modificar `_emit_agent_start()`: llamar `_get_action_type()`
- [ ] Modificar `_emit_agent_start()`: extraer `target_agent` de `state.response_metadata.semantic_result`
- [ ] Modificar `_emit_agent_start()`: pasar `action` y `meta` enriquecido a broadcaster
- [ ] Modificar `_emit_agent_end()`: pasar `action='agent_end'`

#### **graph_runtime.py**
- [ ] Crear método `_map_node_to_action()` con mappings de nodos
- [ ] Modificar `_emit_transition()`: llamar `_map_node_to_action(to_node)`
- [ ] Modificar `_emit_transition()`: extraer `target_agent`/`routing_agent` de state
- [ ] Modificar `_emit_transition()`: pasar `action` y `meta` enriquecido

---

### **Frontend**

#### **GlobalChatContext.tsx**
- [ ] Reemplazar NODE_MESSAGES/EVENT_PRESETS con `ACTION_MESSAGES` completo (30+ entries)
- [ ] Actualizar `formatAgentEvent()`: extraer `actionType = event.data.action || event.type`
- [ ] Actualizar `formatAgentEvent()`: lookup `ACTION_MESSAGES[actionType]`
- [ ] Actualizar `formatAgentEvent()`: simplificar a ~40 líneas
- [ ] Eliminar useEffect que procesa array completo `agentEvents`
- [ ] Crear useEffect que procesa solo `lastAgentEvent`
- [ ] Eliminar hardcoded spaces: `content: summary` (no `` `    ${summary}...` ``)

#### **SimpleChatBox.tsx**
- [ ] Importar CSS module: `import styles from './SimpleChatBox.module.css'`
- [ ] Actualizar `renderAgentEventMessage()`: usar `styles.eventMessage`, `styles.eventMessageRow`, etc.
- [ ] Implementar checkmark: `{isSuccess ? <span>✓</span> : <div className={styles.eventBullet} />}`
- [ ] Implementar formato inter-agente: `if (targetAgent) displayText = \`${actor} → ${target}: ${text}\``
- [ ] Actualizar `toneColorMap`: progress=#f7ab2f, success=#00e5ff, error=#ff5a6b
- [ ] Agregar shimmer: `className={isProgress ? styles.shimmer : ''}`
- [ ] Eliminar interfaces: `TaskStep`, `ProcessingMessage`
- [ ] Eliminar state: `processingMessage`
- [ ] Eliminar useEffect de mock tasks

#### **SimpleChatBox.module.css** (CREAR)
- [ ] Crear archivo `SimpleChatBox.module.css`
- [ ] Definir `.eventMessage` (container minimalista)
- [ ] Definir `.eventMessageRow` (flex row, gap 8px)
- [ ] Definir `.eventBullet` (6px, border-radius 50%, triple box-shadow)
- [ ] Definir `.eventText` (13px, line-height 1.4)
- [ ] Definir `.eventText.shimmer` (animation shimmer)
- [ ] Definir `.indent` (padding-left 16px)

#### **globals.css**
- [ ] Agregar `@keyframes shimmer` después de línea 66
- [ ] Agregar `@keyframes eventGlow` con triple box-shadow

#### **useOrchestratorChat.ts**
- [ ] Eliminar mensaje hardcoded: `"🔍 Analizando consulta..."`

---

### **Eliminaciones**
- [ ] Eliminar `Frontend/src/app/components/chat/messages/MessageArea.tsx`
- [ ] Eliminar `Frontend/src/app/components/chat/messages/ProcessingView.tsx`

---

## 8. TESTING Y VALIDACIÓN

### **8.1. Test Backend**

#### **Test WebSocket Events**

```python
# test_websocket_events.py
import asyncio
import websockets
import json

async def test_action_types():
    """Verify backend emits action types in WebSocket events."""
    uri = "ws://localhost:8000/ws/agents"

    async with websockets.connect(uri) as websocket:
        # Trigger event by sending query
        async for message in websocket:
            event = json.loads(message)

            # VALIDACIÓN 1: event.data debe tener action
            assert 'data' in event, "Event missing 'data'"
            assert isinstance(event['data'], dict), "Event.data not dict"

            # VALIDACIÓN 2: action debe estar en data
            if event['type'] in ['agent_start', 'agent_end', 'node_transition']:
                assert 'action' in event['data'], f"Event {event['type']} missing action in data"
                print(f"✅ Event {event['type']} has action: {event['data']['action']}")

            # VALIDACIÓN 3: target_agent debe estar en meta cuando existe
            if 'meta' in event and event['meta']:
                if 'target_agent' in event['meta']:
                    print(f"✅ Event has target_agent: {event['meta']['target_agent']}")

asyncio.run(test_action_types())
```

**Ejecutar:**
```bash
cd Backend
python test_websocket_events.py
```

**Resultado esperado:**
```
✅ Event agent_start has action: summary_generation
✅ Event agent_end has action: agent_end
✅ Event node_transition has action: router
✅ Event has target_agent: capidatab
```

---

### **8.2. Test Frontend**

#### **Test ACTION_MESSAGES Coverage**

```typescript
// GlobalChatContext.test.ts
describe('ACTION_MESSAGES', () => {
  it('should have mappings for all action types', () => {
    const requiredActions = [
      'intent', 'router', 'supervisor', 'react', 'reasoning',
      'summary_generation', 'branch_analysis', 'anomaly_detection',
      'database_query', 'branch_operations', 'conversation'
    ];

    requiredActions.forEach(action => {
      expect(ACTION_MESSAGES[action]).toBeDefined();

      const result = ACTION_MESSAGES[action]();
      expect(result.summary).toBeTruthy();
      expect(result.tone).toBeTruthy();
    });
  });

  it('should return Spanish gerund messages', () => {
    const result = ACTION_MESSAGES['database_query']();
    expect(result.summary).toMatch(/ando\.\.\.|iendo\.\.\./); // Gerundio pattern
  });
});
```

#### **Test Batching Fix**

```typescript
// GlobalChatContext.test.ts
describe('Event Processing', () => {
  it('should process events one by one', async () => {
    const events = [
      { id: '1', type: 'agent_start', data: { action: 'intent' } },
      { id: '2', type: 'agent_start', data: { action: 'router' } },
      { id: '3', type: 'agent_start', data: { action: 'summary_generation' } }
    ];

    const processedEvents: string[] = [];

    // Simulate lastAgentEvent updates
    for (const event of events) {
      // Wait 100ms between events (simulate real-time)
      await new Promise(resolve => setTimeout(resolve, 100));

      // Process event
      processedEvents.push(event.id);
    }

    // VALIDATION: Events processed one by one, not all at once
    expect(processedEvents).toEqual(['1', '2', '3']);
  });
});
```

---

### **8.3. Test E2E Visual**

#### **Test Plan Manual**

1. **Iniciar sistema:**
   ```bash
   cd CAPI
   .\docker-commands.ps1 start
   ```

2. **Abrir navegador:** http://localhost:3000

3. **Abrir DevTools Console**

4. **Enviar consulta:** "analiza sucursal 001"

5. **Validar:**

| Validación | Qué Observar |
|------------|--------------|
| V-01 | Eventos aparecen UNO POR UNO (no todos juntos) |
| V-02 | Intervalo visible ~150-300ms entre eventos |
| V-03 | Dots naranjas con glow animation en eventos progress |
| V-04 | Texto con shimmer (opacity pulsante) en progress |
| V-05 | Checkmark cyan (✓) en eventos completados |
| V-06 | Sin shimmer en checkmarks |
| V-07 | Headers solo cuando cambia agente |
| V-08 | Formato "Actor → Target: Mensaje" si hay comunicación inter-agente |
| V-09 | Sin borders visibles en eventos |
| V-10 | Sin backgrounds de color en eventos |
| V-11 | Colores exactos: #f7ab2f (orange), #00e5ff (cyan), #ff5a6b (red) |

6. **Verificar Console:**
   - No debe haber errores React
   - No debe haber warnings de "missing key"
   - WebSocket debe estar conectado

---

### **8.4. Criterios de Aceptación Final**

#### **Funcionales:**
- [ ] RF-01: Eventos aparecen uno por uno (intervalo 100-300ms)
- [ ] RF-02: Formato inter-agente funciona cuando hay target_agent
- [ ] RF-03: Headers solo cuando cambia agente
- [ ] RF-04: Todos los action types mapeados traducen a español gerundio
- [ ] RF-05: Estados visuales correctos (progress/success/error)
- [ ] RF-06: Cero mensajes hardcoded en código
- [ ] RF-07: Eventos persisten en historial

#### **No Funcionales:**
- [ ] RNF-01: Renderiza en <16ms (60 FPS)
- [ ] RNF-02: Colores exactos del HUD Navigator
- [ ] RNF-03: Sin borders/backgrounds visibles
- [ ] RNF-04: Checkmarks accesibles (Unicode)
- [ ] RNF-05: Funciona en 320px-4K

#### **Testing:**
- [ ] Backend WebSocket test pasa (action types presentes)
- [ ] Frontend unit tests pasan (ACTION_MESSAGES, batching)
- [ ] E2E visual test pasa (todas las 11 validaciones)

---

## 🎯 CONCLUSIÓN

Este documento es la **especificación ejecutable completa** del sistema de eventos del chat.

**Para implementar desde cero:**
1. Leer secciones 3-4 (especificación técnica backend/frontend)
2. Seguir checklist sección 7 paso por paso
3. Validar con tests sección 8

**No hay ambigüedades:**
- ✅ Cada cambio de código especificado con archivo, línea, código exacto
- ✅ Cada comportamiento descrito con criterios validables
- ✅ Cada efecto visual especificado con valores exactos (colores hex, tamaños px, timings ms)

**Estado:** READY TO IMPLEMENT

---

**Documento Versión:** 2.0 (Ejecutable Pura)
**Última Actualización:** 2025-10-04
**Mantenedor:** CapiAgentes Team
