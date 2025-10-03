# Nuevo chat e historiales con LangGraph

## 1. Objetivos y alcance
- Permitir que cualquier usuario inicie un hilo limpio sin perder el historial previo (feature "Nuevo chat").
- Exponer historiales navegables (lista + detalle) que reflejen lo que LangGraph recuerda por sesion y lo que se almacena de forma persistente (feature "Historiales").
- Mantener contexto conversacional coherente entre mensajes dentro de un mismo hilo usando el estado de LangGraph y la capa de memoria ya existente en `Backend/src/application/conversation` y `Backend/src/shared/memory_manager.py`.
- Unificar los puntos de entrada (REST + WebSocket) para que siempre usen el mismo identificador de sesion y escriban en los mismos repositorios de memoria.

## 2. Diagnostico actual (septiembre 2025)
- `Backend/src/infrastructure/langgraph/graph_runtime.py` crea un `GraphState` limpio en cada `process_query`; el `InMemoryCheckpointStore` no se usa, por lo que no hay continuidad entre mensajes.
- Existe un `ConversationStateManager` (ver `Backend/src/application/conversation/state_manager.py`) que implementa anti repeticion y TTL, pero no esta conectado al runtime de LangGraph ni al API.
- La API (`Backend/src/api/main.py`) ya ofrece `GET/DELETE /api/conversation/{client_id}` y `GET /api/conversations`, pero devuelven marcadores "managed_by_orchestrator" porque el orquestador no expone los metodos necesarios.
- En frontend `useOrchestratorChat` fija el `clientId` a "global" y no tiene forma de reiniciar el estado ni de listar historiales. `SimpleChatBox` tampoco ofrece un disparador visual para crear un hilo nuevo.
- `MemoryManager` escribe conversaciones en disco (`conversation_*.json`), pero hoy nadie lo invoca, por lo que los historiales no se materializan.

## 3. Flujo objetivo de extremo a extremo
1. El usuario pulsa "Nuevo chat" en la UI (o se detecta que no hay sesion vigente).
2. Frontend solicita `POST /api/conversations` -> FastAPI genera `session_id`, inicializa memoria corta (checkpoint + ConversationStateManager) y devuelve metadatos iniciales.
3. El WebSocket reutiliza la misma conexion, pero cada mensaje incluye `client_id=session_id`; el backend carga el estado previo desde el checkpoint y anade la entrada del usuario a la memoria de la sesion.
4. LangGraph ejecuta el flujo; al finalizar se guardan: (a) checkpoint (estado corto), (b) registro in-memory en `ConversationStateManager`, (c) transcript persistente via `MemoryManager.store_conversation`.
5. La respuesta vuelve por WS (o REST) y el frontend actualiza la vista de mensajes sin perder el hilo.
6. El usuario puede abrir la vista de historiales, donde se combinan sesiones activas (TTL vigente) y persistidas en disco para reanudar un hilo anterior.

## 4. Backend: implementacion detallada

### 4.1. Estado de sesion y checkpoints en `LangGraphRuntime`
1. Crear atributos nuevos en `LangGraphRuntime.__init__` (`Backend/src/infrastructure/langgraph/graph_runtime.py`):
   - `self.conversation_manager = ConversationStateManager(max_sessions=200, session_ttl_minutes=config.get("memory_ttl_minutes", 120))`.
   - `self.memory_manager = MemoryManager(Path(os.getenv("MEMORY_ROOT", "Backend/workspace/memory")))` (importar `Path`).
   - `self.memory_manager` requiere crear el directorio si no existe (`mkdir`).
2. Extraer un helper `_load_checkpoint(session_id: str) -> GraphState` que:
   - Pregunte `self.checkpoints.load(session_id)`.
   - Si hay datos, reconstruya `GraphState(**saved_state)`; si falla, loggear y devolver `_initial_state`.
   - Si no hay checkpoint, llamar `_initial_state` (el metodo actual) y guardar un primer esqueleto con `conversation_history=[]`.
3. Antes de ejecutar el grafo en `process_query`:
   - Usar `state = self._load_checkpoint(session_id)` en lugar de `_initial_state`.
   - Anadir `user_turn = {"role": "user", "content": text, "timestamp": datetime.now().isoformat()}` a `conversation_history` mediante `StateMutator.append_to_list`.
   - Registrar el turno en `self.conversation_manager.add_user_turn(...)` con metadata `{"trace_id": state.trace_id}`.
4. Despues de `final_state = self.graph.run(...)`:
   - Crear `bot_turn = {"role": "assistant", "content": final_state.response_message, "agent": final_state.active_agent or final_state.routing_decision, "timestamp": datetime.now().isoformat(), "meta": final_state.response_metadata}`.
   - Actualizar el estado usando `StateMutator.append_to_list(final_state, "conversation_history", bot_turn)` y recalcular `memory_window` con las ultimas `memory_window` entradas (usar configuracion `self.config.get("memory_window", 20)`).
   - Guardar checkpoint: `self.checkpoints.save(session_id, updated_state.model_dump())` (evitar objetos no serializables limpiando `AgentResult` via `.model_dump()` antes de guardar).
   - Llamar `self.conversation_manager.add_agent_turn(...)`.
   - Enviar a disco: `self.memory_manager.store_conversation(session_id, messages=updated_state.conversation_history, metadata={"user_id": user_id, "trace_id": updated_state.trace_id})`.
5. Devolver un `ResponseEnvelope` construido desde `updated_state` manteniendo la logica existente.

### 4.2. Exponer API de historial via adapter
En `Backend/src/infrastructure/langgraph/adapters/orchestrator_adapter.py`:
1. Guardar referencias a `self.runtime.conversation_manager` y `self.runtime.memory_manager`.
2. Implementar metodos publicos:
   - `def get_session_history(self, session_id: str) -> list[dict]:` -> intentar primero `self.runtime.checkpoints.load(session_id)`; si existe, devolver `conversation_history`. Si no, consultar `self.runtime.memory_manager.retrieve_conversation(session_id)` y extraer `messages`.
   - `def clear_session_history(self, session_id: str) -> None:` -> llamar `self.runtime.checkpoints.delete(session_id)`, `self.runtime.conversation_manager.clear_session(session_id)` (agregar metodo), borrar archivo persistente (`memory_manager.delete_conversation(session_id)`, agregar helper en MemoryManager si no existe).
   - `def get_active_sessions(self) -> list[str]:` -> exponer `self.runtime.conversation_manager.list_active_sessions()` (nuevo metodo que devuelva IDs ordenados por `updated_at`).
   - `def list_session_summaries(self, limit: int = 20) -> dict:` -> combinar `conversation_manager.get_session_stats()` + `memory_manager.list_conversations(limit)`.
3. Asegurarse de que `ConversationStateManager` ofrezca `clear_session` y `list_active_sessions`. Si no existen, agregarlos anadiendo metodos en `state_manager.py` (usar `_sessions.keys()` y limpiar caches asociadas).
4. Actualizar los imports al inicio del archivo (ConversationStateManager ya vive en `src/application/conversation`).

### 4.3. Persistencia en disco y utilidades
1. Extender `MemoryManager` (`Backend/src/shared/memory_manager.py`) con:
   - `def delete_conversation(self, session_id: str) -> None` que elimine archivo + indice.
   - `def get_conversation_metadata(self, session_id: str) -> dict | None` para obtener resumen sin leer los mensajes completos.
2. Verificar que `store_conversation` permita sobrescritura idempotente (ya usa el mismo nombre de archivo, por lo que se reemplaza sin problemas).
3. Anadir un modulo ligero `Backend/src/application/conversation/history_service.py` que encapsule llamadas comunes (opcional pero recomendado para separar API de infraestructura).

### 4.4. FastAPI: endpoints REST y WebSocket
1. En `Backend/src/api/main.py`:
   - Cambiar los handlers existentes (`get_conversation_history`, `clear_conversation_history`, `list_active_conversations`) para que utilicen los nuevos metodos del orquestador y devuelvan payloads reales (`messages`, `metadata`, `active_sessions`, etc.).
   - Agregar `@app.post("/api/conversations")` que cree sesion nueva: generar `session_id = uuid.uuid4()`, opcionalmente aceptar `user_id` en el body, inicializar checkpoint vacio (`orchestrator.get_session_history(session_id)` al vuelo) y devolver `{ "session_id": ..., "created_at": ... }`.
   - Exponer `@app.get("/api/conversations/{session_id}/summary")` que sirva un resumen rapido (`MemoryManager.get_conversation_summary`).
2. WebSocket `/ws`:
   - Validar que cada payload traiga `client_id`; si falta, generar uno y devolver mensaje de control `{ "type": "session_assigned", "session_id": ... }` antes de procesar.
   - Despues de enviar la respuesta principal, emitir tambien `{ "type": "history_snapshot", "session_id": client_id, "messages": updated_state.conversation_history[-5:] }` para que el frontend pueda sincronizar.
   - Anadir bloque `finally` para grabar checkpoint incluso si el grafo falla (utilizar `self.runtime.checkpoints.save`).
3. Actualizar `event_broadcaster` si se desea notificar la creacion/eliminacion de sesiones (opcional pero util).

### 4.5. Pruebas
- Crear `Backend/tests/test_conversation_history.py` con escenarios:
  1. `test_context_persists_between_queries`: enviar dos consultas con el mismo `session_id` y verificar que el segundo estado contiene el mensaje del primero.
  2. `test_clear_session_history_removes_checkpoint`: crear sesion, limpiar, comprobar que `get_session_history` devuelve lista vacia.
  3. `test_memory_manager_persistence`: tras dos mensajes, asegurarse de que exista archivo en `Backend/workspace/memory/conversations` y que `MemoryManager.retrieve_conversation` coincida con lo enviado.
- Reutilizar `pytest` con `tmp_path` para redirigir `MEMORY_ROOT` durante las pruebas.

## 5. Frontend: implementacion detallada

### 5.1. Gestion del identificador de sesion
1. Extender `GlobalChatContext` (`Frontend/src/app/contexts/GlobalChatContext.tsx`) con estado `sessionId` y acciones:
   - `startNewChat = async () => { ... }` que haga `fetch('/api/conversations', { method: 'POST' })`, actualice `sessionId`, limpie `messages`, `summary`, `anomalies`, etc.
   - `loadConversation = async (sessionId: string) => { ... }` que obtenga historial via `GET /api/conversation/{sessionId}` y llene `messages` antes de reabrir el overlay.
2. Pasar `sessionId` al hook: `const orchestrator = useOrchestratorChat(sessionId);`.

### 5.2. Hook `useOrchestratorChat`
- Aceptar `clientId` como dependencia. En `useEffect` principal, si cambia `clientId`:
  - Reiniciar `messages` (`setMessages([])`), `summary`, `anomalies`.
  - Forzar envio de mensaje de control al WS: `sock.send({ type: 'switch_session', client_id })` para que el backend pueda rehidratar el estado.
- Incluir handler para mensajes `session_assigned` y `history_snapshot` que envie el historial completo al estado local (transformar a `OrchestratorMessage`).
- Evitar colisiones del comando "Nuevo chat" cancelando timers de progreso existentes.

### 5.3. UI "Nuevo chat"
1. Agregar boton destacado en `SimpleChatBox` (por ejemplo junto a los tabs de sucursal) que llame `startNewChat`.
2. Mostrar modal de confirmacion si hay mensajes sin enviar (`loading === true`).
3. Cuando se confirma, cerrar overlays auxiliares y hacer scroll al inicio.

### 5.4. Vista de historiales
- Crear componente `ChatHistoryPanel.tsx` (carpeta `Frontend/src/app/components/chat/`) que reciba `histories` y callbacks `onSelect`, `onDelete`.
- Obtener datos via nuevo hook `useChatHistory` que llame `GET /api/conversations` y `GET /api/conversations/{id}/summary` para enriquecer cada fila (ultimo mensaje, fecha, agente). Actualizar cada 30 s o cuando se reciba `history_snapshot`.
- Integrar panel en `GlobalChatOverlay` como drawer lateral (usar `showSidebar` ya disponible en el contexto).

### 5.5. UX y estados especiales
- Marcar la sesion activa; si se carga un historial viejo, enviar mensaje informativo "Contexto restaurado".
- Deshabilitar envio mientras `connection.status` sea `connecting` o `reconnecting`.
- Sincronizar eliminacion: tras `DELETE /api/conversation/{session_id}` actualizar lista local y, si la sesion eliminada era la activa, disparar `startNewChat` automaticamente.

## 6. Observabilidad y gobernanza
- Extender los logs (via `get_logger`) en puntos clave: creacion de sesion (`event: conversation_started`), persistencia (`conversation_checkpoint_saved`), restauracion (`conversation_restored`).
- Publicar contadores en `TokenUsageService` o en un nuevo `ConversationMetricsService` para rastrear cantidad de mensajes por sesion.
- Asegurar que los archivos bajo `Backend/workspace/memory` se excluyan del repositorio (.gitignore ya lo cubre, revisar).

## 7. Checklist de validacion
- [ ] Ejecutar `pytest Backend/tests -q` y asegurar que los nuevos casos pasen.
- [ ] Probar manualmente via WebSocket (`wscat` o la UI) el flujo "mensaje A" -> "mensaje B" con mismo `session_id` verificando que el segundo incluye contexto.
- [ ] Confirmar que `GET /api/conversations` devuelve elementos con `last_message` y `updated_at`.
- [ ] Verificar que un "Nuevo chat" crea un nuevo archivo `conversation_<id>.json` y que borrar la sesion elimina el archivo.
- [ ] Revisar que el frontend reciba `history_snapshot` inmediatamente despues de cada respuesta.

## 8. Roadmap incremental sugerido
1. **Fase 1**: Implementar backend (checkpoint + API) y exponer nuevos endpoints, manteniendo la UI actual. Validar con scripts `curl`/`wscat`.
2. **Fase 2**: Integrar frontend con soporte de sesion basico (boton "Nuevo chat", reutilizar hook existente).
3. **Fase 3**: Agregar panel de historiales, mejoras UX (labels, preview de ultimo mensaje), pruebas E2E.
4. **Fase 4**: Optimizar almacenamiento (migrar a SQLite u otro store si el volumen crece) y agregar features avanzadas (busqueda semantica sobre historiales, exportacion a PDF).

Con estos pasos, "Nuevo chat" y "Historiales" quedan alineados con LangGraph, preservan contexto en memoria corta, materializan historiales persistentes y ofrecen una experiencia coherente en la interfaz.

## 9. Funcionalidades complementarias recomendadas
Se priorizan propuestas con potencial alto de impacto visual y tecnico. La lista esta ordenada de mayor a menor score integral (1-10), manteniendo las iniciativas clave de playback contextual y soporte de archivos.

1. **Playback contextual (replay visual)**
   - Dificultad: **** (4/5)
   - Tiempo estimado: 6 dias
   - Beneficio: ***** (5/5)
   - Que hace: reproduce cada sesion mostrando en paralelo los pasos del LangGraph (intentos, nodos visitados, decisiones) sincronizados con los mensajes.
   - Por que implementarlo: genera un efecto “wow” en demostraciones de innovacion, facilita debugging y evidencia en vivo la inteligencia del orquestador.
   - Dependencias/instalacion: reutiliza `event_broadcaster`; puede requerir WebSocket adicional para snapshots historicos.
   - Score: 8.8/10

2. **Resumes automatizados de sesiones largas**
   - Dificultad: ** (2/5)
   - Tiempo estimado: 2 dias
   - Beneficio: **** (4/5)
   - Que hace: genera resumentes parciales cuando la sesion supera cierto numero de turnos y los guarda en metadata.
   - Por que implementarlo: reduce carga cognitiva y acelera las reanudaciones, mostrando inteligencia narrativa continua.
   - Dependencias/instalacion: reutiliza LangGraph; sin paquetes extra.
   - Score: 8.5/10

3. **Soporte de archivos y capturas**
   - Dificultad: *** (3/5)
   - Tiempo estimado: 4 dias
   - Beneficio: ***** (5/5)
   - Que hace: permite subir documentos o imagenes (PDF, CSV, fotos) y ponerlos a disposicion del grafo para analisis contextual en la respuesta.
   - Por que implementarlo: multiplica casos de uso (estados de cuenta, tickets, comprobantes) y refuerza la capacidad multimodal en demos.
   - Dependencias/instalacion: requiere almacenamiento (S3, Azure Blob o similar) y pipeline de ingestion (p.ej. LangChain loaders).
   - Score: 8.4/10

4. **Personalizacion basada en roles**
   - Dificultad: ** (2/5)
   - Tiempo estimado: 2 dias
   - Beneficio: **** (4/5)
   - Que hace: ajusta prompts, vistas y permisos segun rol (ejecutivo, analista, auditor).
   - Por que implementarlo: mejora adopcion interna y reduce riesgo de fuga de datos, alineando la demo a distintos perfiles.
   - Dependencias/instalacion: requiere middleware de autenticacion y roles; sin librerias extra.
   - Score: 8.3/10

5. **Busqueda semantica en historiales**
   - Dificultad: **** (4/5)
   - Tiempo estimado: 6-7 dias
   - Beneficio: ***** (5/5)
   - Que hace: indexa mensajes con embeddings para buscar por significado (ejemplo: "cuando hablamos de fraude").
   - Por que implementarlo: acelera recuperacion de contexto para agentes humanos y la IA, mostrando capacidades NLP avanzadas.
   - Dependencias/instalacion: requiere libreria de vectores (faiss-cpu o chromadb) y pipeline de embeddings.
   - Score: 8.0/10

6. **Modo offline y resiliencia**
   - Dificultad: *** (3/5)
   - Tiempo estimado: 3 dias
   - Beneficio: **** (4/5)
   - Que hace: cachea mensajes recientes en el navegador y permite reintentos cuando se pierde conectividad.
   - Por que implementarlo: mejora UX en ambientes con red inestable, clave para pilotos en campo.
   - Dependencias/instalacion: requiere IndexedDB o Service Worker (Workbox recomendado).
   - Score: 7.9/10

7. **Alertas de eventos clave en tiempo real**
   - Dificultad: **** (4/5)
   - Tiempo estimado: 5 dias
   - Beneficio: **** (4/5)
   - Que hace: detecta heuristicas (sentimiento negativo, menciones de fraude) y dispara alertas via WebSocket o correo.
   - Por que implementarlo: habilita intervencion temprana y eleva calidad de servicio, mostrando gobernanza proactiva.
   - Dependencias/instalacion: requiere analisis de sentimiento (API externa o modelo local) y cola de eventos (Redis o RabbitMQ recomendado).
   - Score: 7.7/10

8. **Historial unificado multicanal**
   - Dificultad: *** (3/5)
   - Tiempo estimado: 4-5 dias
   - Beneficio: **** (4/5)
   - Que hace: fusiona interacciones de chat web, mobile y telefono transcrito en una unica linea de tiempo etiquetada por canal.
   - Por que implementarlo: habilita continuidad real con clientes multicanal y mejora la analitica de soporte.
   - Dependencias/instalacion: requiere pipeline de transcripcion si se integra voz; sin librerias adicionales si ya existe.
   - Score: 7.5/10

9. **Panel de metricas de conversacion**
   - Dificultad: ** (2/5)
   - Tiempo estimado: 2-3 dias
   - Beneficio: *** (3/5)
   - Que hace: entrega dashboard (Next.js) con KPIs de sesion (duracion, resolucion, intents frecuentes).
   - Por que implementarlo: da visibilidad al negocio y permite iterar sobre el orquestador.
   - Dependencias/instalacion: reutiliza `TokenUsageService`; puede requerir nuevas rutas API.
   - Score: 7.0/10

10. **Anotaciones colaborativas**
    - Dificultad: *** (3/5)
    - Tiempo estimado: 3-4 dias
    - Beneficio: *** (3/5)
    - Que hace: permite agregar notas o etiquetas de seguimiento en mensajes especificos.
    - Por que implementarlo: mejora auditoria y handoff entre equipos.
    - Dependencias/instalacion: requiere tabla o coleccion adicional y componentes UI para notas.
    - Score: 6.8/10

