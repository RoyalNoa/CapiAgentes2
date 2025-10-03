# Logging JSON estructurado con pipeline de observabilidad

Este documento describe cómo llevar nuestro sistema de logging al siguiente nivel: logs en JSON ricos en contexto, recolectados por un stack Elastic, integrados a los scripts de arranque y listos para consumo automático por agentes.

## 1. ¿Un único log o dos canales?
Mantener un solo pipeline es más simple y reduce desincronizaciones. Conviene generar un único flujo JSON rico en contexto y, para lectura humana, añadir un handler opcional que renderice en texto (por ejemplo, usando `python-json-logger` + `jq` o un `StreamHandler` reducido). Duplicar la bitácora (texto + JSON) suele generar divergencias y carga adicional.

## 2. Dependencias y prerequisites
1. **Backend**
   - Añadir a `Backend/requirements.txt`:
     ```text
     python-json-logger>=2.0.7
     ````
   - Instalar: `pip install -r Backend/requirements.txt`.
2. **Stack Elastic (Docker)**
   - Recomendación minimal: ElasticSearch + Logstash + Kibana usando `docker-compose`. 
   - Directorio sugerido: `observability/elastic/`. Añadir archivos:
     - `docker-compose.elastic.yml` (ver §5.1)
     - `logstash.conf` (ver §5.2)
   - Requiere al menos 4 GB de RAM disponibles.

## 3. Backend: formatter JSON + configuración
### 3.1 Crear `JsonFormatter`
Modifica `Backend/src/core/logging.py`:
```python
import json
from pythonjsonlogger import jsonlogger

class JsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.fromtimestamp(record.created).isoformat()
        log_record['service'] = 'backend'
        log_record['logger'] = record.name
        log_record['level'] = record.levelname.upper()
        # Estos atributos ya los añadimos desde extra
        for key in ('request_id', 'session_id', 'client_id', 'trace_id', 'agent_name', 'log_context'):
            value = getattr(record, key, None) or record.__dict__.get(key)
            if value is not None:
                log_record[key] = value
```

### 3.2. Cambiar el handler de archivo
En `setup_unified_logging()` agrega una selección por variable de entorno:
```python
use_json = os.getenv('LOG_FORMAT', 'text').lower() == 'json'
formatter = JsonFormatter() if use_json else UnifiedFormatter()
```
Aplica `formatter` tanto al `StreamHandler` como al `RotatingFileHandler`.

### 3.3. Ajustar llamadas `logger.*`
Los módulos críticos (`api/main.py`, `presentation/websocket_langgraph.py`, `shared/memory_manager.py`) ya usan `extra={...}`. Con el JSON quedarán serializados automáticamente. Revisa cualquier nuevo `logger.*` para incluir contexto relevante (`request_id`, `session_id`, etc.).

## 4. Frontend: logs estructurados opcionales
El wrapper actual imprime `[timestamp] [Frontend] [LEVEL] [path=/...]`. Para exportar al backend/Elastic:
1. Añade un endpoint `/api/logs` en FastAPI (opcional) o usa directamente Logstash.
2. Envolver `console.*` con envío HTTP (beacon) si quieres centralizar logs de navegador.
   - Librería sugerida: `navigator.sendBeacon` con payload JSON.

## 5. Stack Elastic
### 5.1. `docker-compose.elastic.yml`
```yaml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.14.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - '9200:9200'
    volumes:
      - elastic-data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.14.0
    volumes:
      - ./logstash/logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - '5044:5044'
      - '9600:9600'
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.14.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - '5601:5601'
    depends_on:
      - elasticsearch

volumes:
  elastic-data:
```

### 5.2. `logstash/logstash.conf`
```conf
input {
  beats {
    port => 5044
  }
  http {
    port => 8080
  }
}

filter {
  if [message] {
    json {
      source => "message"
      skip_on_invalid_json => true
      target => "json"
    }
    if [json] {
      mutate {
        add_field => { "service" => "%{[json][service]}" }
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "capi-logs-%{+YYYY.MM.dd}"
    document_type => "_doc"
  }
  stdout {
    codec => rubydebug
  }
}
```
Si prefieres evitar Beats, puedes usar `http` input con `curl`. Ajusta `docker-compose` y la salida de Logstash según tus necesidades.

## 6. Integración con nuestros scripts/launcher
### 6.1. `docker-compose.yml`
Añade (o incluye desde `docker-compose.elastic.yml`) el bloque:
```yaml
  log-collector:
    extends:
      file: observability/docker-compose.elastic.yml
      service: logstash
```

### 6.2. `docker-commands.ps1` y `docker-commands.sh`
- Añade comandos `./docker-commands.ps1 observability-start` que ejecuten `docker compose -f docker-compose.elastic.yml up -d`.
- En los comandos `start` y `stop`, llama primero a `observability-start` para que Elastic esté listo antes que el backend.

### 6.3. Launcher desktop
Si el launcher ejecuta scripts (Tkinter + PyInstaller):
- Actualiza `launcher/scripts/create_shortcut.py` o el script que levante el backend para que llame a `docker-commands.ps1 observability-start` antes de iniciar la app.
- Documenta el requisito en `launcher/docs/README.md`.
- El launcher incorpora la tarjeta **Elastic Observability** para iniciar/detener `observability/docker-compose.elastic.yml`; asegurate de que todos los nuevos servicios apunten a ese stack de logs.

## 7. Validación
1. Arranca el stack: `docker compose -f docker-compose.elastic.yml up -d` + `./docker-commands.ps1 start`.
2. Verifica que `logs/backend.log` contenga JSON (si `LOG_FORMAT=json`).
3. Envía un request (`/api/command`) y comprueba que `http://localhost:5601` muestre el índice `capi-logs-*` con campos estructurados.
4. Usa `curl -X GET http://localhost:9200/capi-logs-*/_search?pretty` para validar sin Kibana.

## 8. Mejores prácticas
- Definir un índice daily, política de retención (ILM) para Elastic.
- Revisar privacidad: enmascara datos sensibles antes de loguear.
- Automatiza dashboards en Kibana (exporta JSON) para que la IA tenga vistas listas.
- Considera Loki + Grafana si prefieres un stack liviano (mismo principio, diferente tecnología).

Con estos pasos, todo el logging del proyecto queda estructurado, centralizado y listo para análisis automático por agentes y humanos.
