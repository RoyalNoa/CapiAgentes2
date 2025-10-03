# Logging & Observability Snapshot

## Estado Actual
- Backend escribe en `logs/backend.log` (rotativo, captura `sys.excepthook` y excepciones `asyncio`).
- Frontend servidor intercepta `console.*`, `uncaughtException` y `unhandledRejection`, persistiendo en `logs/front.log`.
- Frontend cliente envia `console.error/warn`, `window.onerror` y `unhandledrejection` a `/api/logs/client`, que tambien terminan en `logs/front.log`.
- `Frontend/scripts/check_graph_layout.js` genera `logs/graph_layout_diagnostics.jsonl`; Logstash la mantiene como fuente JSON.
- Logstash (`observability/logstash/logstash.conf`) monta `Backend/logs` y `logs/` en `/app/backend_logs` y `/app/logs`, e ingiere backend, frontend, diagnosticos de grafo y `agent_metrics*.jsonl`, normalizando `@timestamp`, `service`, `level`, `origin`, `logger` y `context` segun corresponda.
- `docs/observabilidad.md` describe la operativa de Kibana (data views, consultas base, alertas) y enlaza con el indice `agent-metrics-*`.
- El backend escribe eventos conversacionales en `logs/agent_metrics.jsonl` a traves de `src/observability/agent_metrics.py`, registrando latencia, tokens, costos y errores por turno.

## Siguientes pasos operativos
- Reiniciar la pipeline tras los cambios: `docker compose -f observability/docker-compose.elastic.yml restart logstash`.
- En Kibana:
  - Data view `capi-logs-*` para backend, frontend y grafo; validar campos `service`, `origin` y `context`.
  - Data view `agent-metrics-*` para revisar los eventos `agent_turn_completed`, `agent_error` (incluidos `agent_response_error`) y `feedback_recorded` generados por el backend.
  - Construir un dashboard inicial con latencia promedio, tokens y tasa de errores por agente.

## Pendiente (post-compact)
1. **Dashboards y alertas**: materializar en Kibana las visualizaciones y reglas descritas (errores backend/frontend, overlapCount, latencias de agentes) y versionar los `saved objects`.
2. **Automatizacion**: evaluar exportar dashboards/reglas a Terraform o Fleet para reproducibilidad en otros entornos.
3. **Feedback analytics**: crear vistas que crucen `feedback_recorded` con latencia/costo para priorizar mejoras conversacionales.

Con esto puedes retomar despues de usar `/compact` sin perder el contexto del trabajo restante.
