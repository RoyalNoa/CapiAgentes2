# Pipeline de metricas de agentes

## Objetivo
Centralizar telemetria conversacional (latencia, tokens, costos, feedback) para evaluar y optimizar agentes CAPI. Los eventos se escriben en `logs/agent_metrics.jsonl` y Logstash los envia al indice `agent-metrics-*` en Elasticsearch.

## Helper disponible
- `src/observability/agent_metrics.py` expone `record_turn_event`, `record_error_event` y `record_feedback_event`.
- El `LangGraphOrchestratorAdapter` invoca automaticamente `record_turn_event` y `record_error_event` al procesar cada turno, generando `agent_turn_completed` y `agent_error`.
- El endpoint `/api/feedback` utiliza `record_feedback_event` para persistir `feedback_recorded` con rating, comentarios y contexto basico.
- Otros servicios pueden reutilizar el helper para registrar eventos propios (asegura escribir JSON por linea).

## Especificacion del evento JSON
Cada linea del archivo debe contener un objeto JSON con los campos siguientes:

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `timestamp` | string ISO8601 | Momento en que se cierra el turno o evento medido. Si falta, Logstash asigna la hora de ingesta. |
| `agent_name` | string | Identificador del agente que respondio (ej. `capi_desktop`). |
| `session_id` | string | ID de sesion/conversacion (UUID generado en backend). |
| `turn_id` | integer | Numero incremental del turno dentro de la sesion. |
| `event_type` | string | `agent_turn_completed`, `agent_error`, `feedback_recorded`, etc. |
| `latency_ms` | integer | Duracion total del turno en milisegundos desde la solicitud hasta la respuesta final. |
| `input_tokens` | integer | Tokens estimados del prompt/entrada. |
| `output_tokens` | integer | Tokens de la respuesta del agente. |
| `tokens_total` | integer | Suma de `input_tokens` + `output_tokens` (para consultas rapidas en Kibana). |
| `cost_usd` | float | Costo estimado del turno (segun pricing del modelo). |
| `model` | string | Modelo utilizado (`gpt-4o`, `claude-3-5-sonnet`, etc.). |
| `channel` | string | Origen del mensaje (`web`, `desktop`, `api`). |
| `user_feedback_score` | float opcional | Puntuacion de feedback (0-5 o 0-1 segun la metrica que definas). |
| `user_feedback_text` | string opcional | Comentario textual del usuario. |
| `error_code` | string opcional | Codigo interno cuando `event_type=agent_error`. |
| `metadata` | object opcional | Campos adicionales (ej. `router_decision`, `tools_invoked`, `trace_id`). |

### Ejemplo de linea valida
```json
{"timestamp":"2025-09-20T17:45:12.481Z","agent_name":"capi_desktop","session_id":"8b7c3c64-5e52-4f3d-b4f0-5e6dacec6f30","turn_id":4,"event_type":"agent_turn_completed","latency_ms":1840,"input_tokens":724,"output_tokens":512,"tokens_total":1236,"cost_usd":0.047,"model":"gpt-4o","channel":"web","metadata":{"trace_id":"trace-01HZZ2VF4K4P9","router_decision":"default"}}
```

## Donde escribir los eventos
- Ruta física: `Backend/logs/agent_metrics.jsonl`. El contenedor de Logstash monta esa carpeta en `/app/backend_logs`, por lo que cualquier evento escrito ahi se ingiere automaticamente.
- Formato: JSON Lines (una linea por evento, sin comas ni corchetes).
- Permisos: asegurar que el proceso backend pueda crear el archivo (`Path("Backend/logs").mkdir(parents=True, exist_ok=True)`).

## Instrumentacion en backend
1. `LangGraphOrchestratorAdapter.process_query` registra `agent_turn_completed` y `agent_error`, calculando tokens, costo estimado, latencia y registrando `agent_response_error` cuando la respuesta no fue exitosa.
2. `record_error_event` se dispara ante excepciones en el runtime antes de propagar el error.
3. `/api/feedback` añade eventos `feedback_recorded` con rating opcional, comentarios y contexto; reutiliza `record_feedback_event`.
4. Evita objetos no serializables en `metadata`; prioriza strings, enteros y diccionarios simples.

## Logstash y Elastic
- La configuracion en `observability/logstash/logstash.conf` monta `Backend/logs` como `/app/backend_logs` y usa `agent_metrics*.jsonl` desde ahi.
- El filtro asigna `service=agent_metrics`, aplica `date` al campo `timestamp` y envia el evento al indice `agent-metrics-%{+YYYY.MM.dd}`.
- Para reprocesar datos, borra `/tmp/sincedb_agent_metrics` dentro del contenedor de Logstash y reinicia el servicio.

## Consultas en Kibana
- Data view recomendado: `Agent Metrics` (`agent-metrics-*`, campo de tiempo `@timestamp`).
- KQL utiles:
  - `event_type: agent_turn_completed AND agent_name: "capi_desktop"`
  - `latency_ms > 3000`
  - `event_type: agent_error AND error_code: "graph_layout_failed"`
  - `event_type: agent_error AND error_code: "agent_response_error"`
  - `event_type: feedback_recorded AND feedback_score < 3`
- Visualizaciones iniciales:
  - Promedio de `latency_ms` por `agent_name`.
  - Sumatoria de `cost_usd` por dia.
  - Tasa de errores: metric `count(event_type:agent_error)` sobre `count(event_type:agent_turn_completed)` usando Lens formulas.
  - Distribucion de `feedback_score` por agente y canal.

## Roadmap
- Automatizar la publicacion de metricas en tiempo real via WebSocket o HTTP cuando se requiera SLA estricto.
- Agregar normalizacion de `metadata.tools_invoked` para poder explotar la informacion en tablas separadas.
- Conectar alertas de Kibana al canal de incidentes (Slack u otro) filtrando `event_type:agent_error` con `latency_ms` elevado.
