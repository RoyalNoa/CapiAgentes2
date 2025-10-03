<!-- @canonical true -->
# Especificación ZeroGraph - CapiAgentes

ZeroGraph representa la topología del proyecto CapiAgentes. Este documento define nodos, relaciones y reglas obligatorias para el grafo. Toda automatización que lo actualice debe obedecer estas secciones.

## 1. Objetivo
- Modelar componentes clave del backend (FastAPI + LangGraph) y frontend (Next.js) junto con artefactos de agentes.
- Permitir análisis de dependencias, privilegios y superficies de riesgo.
- Facilitar onboarding ágil de IAs y humanos mostrando conexiones esenciales.

## 2. Jerarquía de nodos
```
Project
 ├─ DomainLayer
 ├─ ApplicationLayer
 ├─ InfrastructureLayer
 ├─ PresentationLayer
 ├─ SharedCore
 ├─ OrchestratorRuntime
 ├─ Agent
 ├─ FrontendFeature
 ├─ Dataset
 └─ Script
```

### 2.1 Project
- Nodo único (`project:capiagentes`).
- Propiedades: `name`, `description`, `stack` ("python-fastapi, langgraph, nextjs"), `status` ("production_ready").

### 2.2 DomainLayer
- Un nodo por submódulo en `Backend/src/domain/` (`entities`, `contracts`, `services`).
- Propiedades: `module_path`, `purpose`.

### 2.3 ApplicationLayer
- Un nodo por submódulo en `Backend/src/application/` (`analysis`, `alerts`, `nlp`, `reasoning`, `services`, `use_cases`, `document_generation`, `conversation`).
- Propiedades: `module_path`, `responsibilities`, `depends_on` (lista de IDs DomainLayer).

### 2.4 InfrastructureLayer
- Representa adaptadores (`langgraph`, `persistence`, `websocket`, `integrations`).
- Propiedades: `module_path`, `framework`, `exposes`.

### 2.5 PresentationLayer
- Modela API y WebSocket (`Backend/src/api`, `Backend/src/presentation`).
- Propiedades: `module_path`, `entrypoints` (lista de endpoints).

### 2.6 SharedCore
- Incluye `Backend/src/shared` y `Backend/src/core`.
- Propiedades: `module_path`, `utilities`.

### 2.7 OrchestratorRuntime
- Nodos para `Backend/ia_workspace/orchestrator/**` y `Backend/src/infrastructure/langgraph/**` cuando no encajen en infra estándar.
- Propiedades: `module_path`, `graph_role` (p. ej. `builder`, `memory_adapter`, `pipeline_stage`).

### 2.8 Agent
- Un nodo por carpeta en `Backend/ia_workspace/agentes/*`.
- Propiedades: `name`, `handler_path`, `privilege_level`, `capabilities`.

### 2.9 FrontendFeature
- Representa vistas y carpetas de feature en `Frontend/src/app/**` y `Frontend/src/components/**` relevantes para PantallaAgentes.
- Propiedades: `route`, `description`, `consumes_api` (lista de IDs de endpoint), `consumes_ws` (lista de canales).

### 2.10 Dataset
- Archivos de apoyo en `Backend/ia_workspace/data/*.json` y `Backend/database/*.sql`.
- Propiedades: `path`, `type` (json/sql/csv), `purpose`.

### 2.11 Script
- Scripts operativos (`docker-commands.ps1`, `.zero/scripts/*.ps1`, `build_executable.py`).
- Propiedades: `path`, `scope` (devops/pipeline/testing), `effects`.

## 3. Relaciones
| Tipo | Descripción | Regla |
|------|-------------|-------|
| `contains` | Jerarquía de directorios/nodos | Project contiene capas; las capas contienen módulos/archivos |
| `depends_on` | Uso directo de funciones/clases | Prohibido Domain -> Infrastructure; validar contra la arquitectura |
| `exposes` | Entrypoint que publica funcionalidad | Presentation -> Agent/Application |
| `invokes` | Orquestador llama agente/servicio | OrchestratorRuntime -> Agent/Application |
| `persists_to` | Acceso a datos/DB | Application/Infrastructure -> Dataset |
| `renders` | Frontend consume API/WS | FrontendFeature -> Presentation |
| `privilege_controls` | Gestión de privilegios | Presentation/Application -> Agent |
| `tests` | Cobertura de pruebas | Script/Test -> Nodo cubierto |
| `generates` | Script produce artefacto | Script -> Dataset/Artifact |

## 4. Atributos obligatorios por relación
- `depends_on`: `reason` ("import", "http_call", "filesystem", etc.).
- `exposes`: `interface` ("REST:/api/...", "WebSocket:/ws/..."), `method`.
- `invokes`: `trigger` ("intent", "scheduled", "manual"), `path` (función invocada).
- `renders`: `channel` ("REST", "WebSocket"), `cadence` ("live", "poll").
- `persists_to`: `operation` ("read", "write", "backup"), `guard` ("privilege_check", "schema_validation").

## 5. Políticas de consistencia
- Nunca crear relaciones `depends_on` que violen la ley de dependencias (Domain jamás depende de Infrastructure).
- Todo Agent debe tener al menos una relación `invokes` y `privilege_controls`.
- Cada FrontendFeature debe enlazar con Presentation o justificar por qué es estático.
- Los Dataset usados por agentes necesitan relación `persists_to` con `guard` documentado.

## 6. Identificadores
- Formato `layer:module` o `agent:<nombre>` para IDs.
- Agregar hash (8 caracteres) cuando se requiera unicidad (`agent:summary:1a2b3c4d`).
- Evitar espacios y mayúsculas en los IDs.

## 7. Artefactos derivados
- `ZeroGraph.json` debe reflejar el grafo completo.
- `ZeroGraph.json.bak-<timestamp>` se crea antes de fusionar cambios.
- `zerograph-delta-YYYY-MM-DD.json` incluye `add_nodes`, `update_nodes`, `add_relationships`, `update_relationships`, `remove_*` (si aplica).

## 8. Validación
- Ejecutar `./.zero/scripts/zerograh-validation.ps1` tras cada merge relevante.
- Validaciones mínimas: IDs únicos, tipos permitidos, atributos obligatorios y respeto a restricciones de capa.
- Registrar resultados en `/.zero/artifacts/zero-health.md` (generado por scripts).

## 9. Evolución
- Cambios en la arquitectura requieren actualizar este documento y `Zero2.md` antes de tocar ZeroGraph.
- Mantener historial de decisiones en `/.zero/dynamic/analysis/` (ej.: `zerograph-delta-*`).

Última actualización: 18/09/2025.
