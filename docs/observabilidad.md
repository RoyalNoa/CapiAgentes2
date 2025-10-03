# Observabilidad con Elastic & Kibana

## 1. Servicios y prerrequisitos
- `docker-compose.elastic.yml` levanta Elasticsearch (`9200`), Logstash (`5044`, `9600`) y Kibana (`5601`) sin seguridad.
- Logstash monta `Backend/logs` en `/app/backend_logs` (backend y métricas) y la carpeta `logs/` raíz en `/app/logs` (frontend y diagnóstico del grafo). Verifica que `Backend/logs/backend.log`, `Backend/logs/agent_metrics.jsonl` y `logs/front.log` existan antes de iniciar Logstash para evitar warnings de archivos ausentes.
- Opcional: exporta `CAPI_LOG_DIR` cuando ejecutes backend/frontend fuera del repo para mantener la carpeta de logs alineada.

## 2. Puesta en marcha rapida
1. Arranca el stack: `docker compose -f observability/docker-compose.elastic.yml up -d`.
2. Comprueba salud basica:
   - `curl http://localhost:9200/_cluster/health?pretty` deberia devolver `status` `yellow` o `green`.
   - `curl http://localhost:9600/_node/pipelines?pretty` verifica que Logstash cargo la pipeline `main`.
3. Accede a Kibana en `http://localhost:5601`. Con seguridad deshabilitada no se solicita login.

## 3. Crear un data view para los logs unificados
1. En Kibana abre `Stack Management > Kibana > Data Views` y pulsa `Create data view`.
2. Nombre sugerido: `CAPI Logs`.
3. Index pattern: `capi-logs-*`.
4. Time field: selecciona `@timestamp`.
5. Guarda el data view y navega a `Discover`.

### 3.1 Validaciones iniciales en Discover
- Filtra `service: backend` para revisar trazas del backend; verifica campos `logger`, `origin` y `context.request_id`.
- Filtra `service: frontend AND origin: "FrontendClient"` para ver eventos enviados desde el navegador con sus `context.timestamp`.
- Para el script del grafo: `tags: graph_layout` muestra eventos JSON directos, con metricas como `overlapCount`.
- Guarda busquedas frecuentes (`Save` > `Save search`) para reutilizarlas en dashboards.

## 4. Visualizaciones recomendadas
- **Errores recientes**: Lens > Bar horizontal, metrica `count` filtrando `level: ERROR`, desglosado por `service` y `logger`.
- **Actividad de frontend**: crea un panel de lineas con `count` por `origin.keyword` para monitorear cliente vs servidor.
- **Solapamiento del grafo**: para `graph_layout_diagnostics`, usa el campo `overlapCount` en una visualizacion de metrica, agregando una alerta cuando `max(overlapCount) > 0` (ver seccion 6).

## 5. Guardar dashboards y compartir
- Construye un dashboard `CAPI - Salud Logs` que combine widgets anteriores.
- Usa `Share > Permalinks` para proporcionar URLs a QA u otros agentes.
- Exporta/Importa dashboards desde `Stack Management > Saved Objects` para versionar configuraciones relevantes.

## 6. Alertas basicas en Kibana
1. Ve a `Stack Management > Rules` (antes `Stack Management > Alerts` en versiones previas).
2. Crea reglas de tipo `Log threshold`:
   - **Errores Backend**: condicion `service: backend AND level: ERROR`, `is above 0` en 5 minutos, notifica por correo o webhook.
   - **Frontend Noise**: `service: frontend AND level: WARN`, umbral > 20 en 10 minutos para detectar spam de advertencias.
   - **Solapamiento de grafo**: `tags: graph_layout AND overlapCount > 0` usando query KQL.
3. Define conectores (email, Slack, webhook) desde `Stack Management > Connectors` si requieres notificaciones externas.

## 7. Preparando el indice de metricas conversacionales
- En cuanto exista el pipeline `agent-metrics-*`, crea otro data view `Agent Metrics` con patron `agent-metrics-*` y `@timestamp`.
- Visualizaciones sugeridas:
  - Serie temporal de `avg(latency_ms)` por `agent_name`.
  - Tabla con `sum(tokens_total)` y `sum(cost_usd)` por `session_id`.
  - Metrica de satisfaccion (`avg(feedback_score)`) cuando se disponga del campo.

## 8. Limpieza y troubleshooting
- Para reiniciar la pipeline tras editar `observability/logstash/logstash.conf`: `docker compose -f observability/docker-compose.elastic.yml restart logstash`.
- Elimina offsets de lectura si necesitas reprocesar logs: borra `./logs/*.sincedb*` dentro del contenedor (`docker exec -it capi-logstash rm /tmp/sincedb_*`).
- Si Discover no muestra datos:
  - Revisa que los logs tengan permisos de lectura (`icacls logs /grant *S-1-1-0:(R)` en Windows si fuera necesario).
  - Comprueba `docker logs capi-logstash` para detectar errores de parseo.

Con estas pautas puedes levantar la observabilidad integral en minutos y validar tanto errores como metricas clave de los agentes.
