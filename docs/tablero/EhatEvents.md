# What Happens in Chat Events

## Fuente de la Línea de Tiempo
- El tablero ahora arma la secuencia visual exclusivamente con los eventos que envía el WebSocket de agentes (`agent_start`, `agent_progress`, `agent_end`, `node_transition`).
- Cada item conserva el orden cronológico real usando las marcas de tiempo del backend; si faltan, se respeta el orden de llegada.
- Los artefactos (`shared_artifacts`) se usan como metadatos opcionales: enriquecen el detalle de un evento pero nunca sustituyen lo que reportó LangGraph.
- Para evitar ruido, se descartan los eventos `agent_start`/`agent_end`; la UI muestra los pasos intermedios reportados en `node_transition` (p. ej. “Consultando…”, “Resultados…”, “Archivo generado…”).

## Manejo de Artefactos y Planes
- El reasoning plan y los artefactos solo sirven para saber qué agentes se esperaban y para adjuntar contexto (p. ej. `summary_message`).
- Si un agente estaba planificado pero no emitió ningún evento, la UI agrega una entrada `Sin actividad reportada` para dejar constancia explícita.
- Cuando no llegan eventos reales (p. ej. sesiones históricas sin stream), la UI cae a la narrativa heurística anterior y lo marca como reconstrucción.

## Texto que se Muestra
- Cada evento intenta usar `data.message`, `detail`, `summary` o estados del payload; si el backend no envía texto, se muestra el tipo de evento capitalizado.
- Se limita a ocho eventos por agente para evitar ruido; si hay más, se priorizan los primeros cronológicos.
- Los nombres amigables (`Capi DataB`, `Capi ElCajas`, etc.) siguen saliendo del mapeo `AGENT_FRIENDLY_NAMES` y se aplican a eventos, artefactos y alertas.
- Los eventos se acumulan en el timeline del chat: cada consulta nueva deja trazabilidad completa antes de mostrar la siguiente.

## Implicancias para QA
- Pruebas de UI deben mockear el WebSocket con cronologías completas, huecos y sesiones sin eventos para validar los tres escenarios.
- Agregar agentes o nuevos tipos de eventos solo requiere que el backend emita el mensaje: el front los mostrará automáticamente.
- Documenta cualquier cambio de contrato del stream en esta guía para mantener alineados a backend y frontend.
