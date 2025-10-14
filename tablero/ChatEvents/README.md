# Evento → Trabajo → Narrativa

## Qué tenemos hoy
- Los eventos `agent_start`/`agent_end` enviados por LangGraph son placeholders con texto genérico (ej. "Consultando base de datos...").
- La información real de cada agente se guarda en `shared_artifacts` y `response_metadata`: sentencia SQL, filas, exports, alertas, recomendaciones, etc.
- La UI actual ignora esos artefactos porque `buildAgentTaskEvents` retorna cuando detecta un `agent_event`; el usuario sólo ve la animación estática.

## Camino recomendado
1. **Extraer la tarea del artefacto.**
   - Para cada agente leer `shared_artifacts.<agent>` (apoyarse en `response_metadata` si hace falta).
   - Ejemplo real: `Backend/ia_workspace/data/sessions/session_global/session_global.json:1823`.
2. **Transformar en narrativa.**
   - Construir frases ordenadas (entrada → acción → artefacto → efecto) en vez de los placeholders.
   - Guardar esas frases (lista `taskSteps`) para pasarlas a la simulación.
3. **Actualizar la simulación.**
   - Modificar `buildAgentTaskEvents` (`Frontend/src/app/utils/chatHelpers.ts:735`) para priorizar `shared_artifacts` antes de caer en `agent_event`.
   - Cada frase se convierte en `SimulatedEvent` con `primaryText`, `detail` y agente asociado.
4. **Mostrar primero la narrativa.**
   - `SimpleChatBox` (`Frontend/src/app/components/chat/SimpleChatBox.tsx`) debe reproducir la narrativa completa antes de insertar el mensaje final del orquestador.

## Expectativas por equipo
- **Backend**: seguir registrando la tarea completa en los artefactos. No tocar los eventos start/end.
- **Frontend**: implementar la capa narrativa descrita y reemplazar los placeholders en la simulación.
- **QA**: validar que diferentes consultas generan narrativas coherentes con los artefactos y que siempre se ve la secuencia antes de la respuesta final.
