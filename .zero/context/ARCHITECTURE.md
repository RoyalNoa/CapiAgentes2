## CAPI / Arquitectura Canónica para Co-Desarrollo con IA
Este documento es la fuente de verdad sobre cómo debe organizarse el repositorio CapiAgentes. Cualquier automatización tiene que respetar estas reglas. Si el repositorio se desvía, ajusta el código hasta que vuelva a alinearse con este archivo.

---
### 1. Intención Arquitectónica (Screaming Architecture)
El repositorio debe comunicar al instante: ORQUESTACIÓN FINANCIERA MULTIAGENTE SOBRE FASTAPI + NEXT.JS. Elimina o archiva cualquier artefacto que confunda ese mensaje.

---
### 2. Estructura Raíz Autorizada
```
/Backend/                  # Backend en Python (FastAPI) con arquitectura hexagonal
    src/
        domain/            # Entidades, objetos de valor, servicios de dominio, contratos
        application/       # Casos de uso, orquestaciones, servicios de lógica de negocio
        infrastructure/    # Adaptadores de framework (LangGraph, persistencia, mensajería, websocket)
        presentation/      # Capa API (endpoints FastAPI, presentadores WebSocket)
        core/              # Transversales (logging, settings)
        shared/            # Utilidades reutilizables (gestión de archivos, schedulers)
    ia_workspace/          # Activos de tiempo de ejecución: agentes, extensiones del orquestador, snapshots de datos
        agentes/
        data/
        orchestrator/
    database/              # Esquema SQL + seeds (PostgreSQL)
    logs/                  # ÚNICO lugar para logs de ejecución (app.log, errors.log, api.log)
    tests/                 # Suites de Pytest (unitarias, integración, orquestación)

/Frontend/                 # Dashboard Next.js 14 (PantallaAgentes)
    src/
        app/               # Entradas del App Router, contextos, hooks
        components/
        services/
        utils/
    public/
    scripts/

/AI/                       # Documentación, especificaciones y prompts curados por humanos (solo lectura para agentes)
/.zero/                    # Sistema de colaboración IA (contexto, prompts, scripts, artefactos)
```
Reglas:
- Backend y Frontend mantienen árboles `src/` separados.
- Prohibido importar desde `Backend/ia_workspace/` hacia `Backend/src/`.
- Solo `.zero/scripts` pueden escribir dentro de `.zero/artifacts/`.
- `AI/` y `docs/` son inmutables para agentes autónomos (solo humanos).

---
### 3. Ley de Dependencias (Hexagonal)
```
domain  ->  application  ->  presentation/infrastructure
shared/core proveen ayudas (dependencias solo descendentes)
```
- `domain` no conoce FastAPI, LangGraph ni bases de datos.
- `application` coordina la lógica de dominio y expone contratos consumidos por presentation/infrastructure.
- `infrastructure` conecta nodos LangGraph, repositorios, servicios externos.
- `presentation` expone interfaces HTTP/WebSocket. Puede depender de application y domain, nunca de `ia_workspace`.
- `shared` guarda utilidades (file_manager, knowledge_base, task_scheduler) compartidas y agnósticas al framework.
- `core` aloja configuración (logging, settings). Sin lógica de negocio.

**Política para ia_workspace**
- `agentes/` contiene handlers por agente, prompts y adaptadores ligeros.
- `orchestrator/` incluye ayudantes de ejecución (memoria, etapas de pipeline) que orquestan contratos existentes de `Backend/src`.
- `data/` almacena archivos CSV/JSON/respaldo. Nada ejecutable salvo helpers necesarios del orquestador.
- Los agentes importan desde `Backend/src/*`; la dirección inversa está prohibida.

---
### 4. Subsistemas Backend
1. **Capa API (`src/api/`)**
   - `main.py`: arranque FastAPI, ruteo, endpoints websocket.
   - `agents_endpoints.py`, `alerts_endpoints.py`, `workspace_endpoints.py`: entradas REST.
   - `middleware.py`: middleware personalizado (logging, auth, rate limits).

2. **Presentation (`src/presentation/`)**
   - `demo_interface.py`, `websocket_langgraph.py`, `orchestrator_factory.py` coordinan flujos orientados a UI.
   - Funciona como capa de traducción entre HTTP/WebSocket y servicios del orquestador.

3. **Application**
   - `analysis/`, `alerts/`, `reasoning/`, `document_generation/`, `nlp/`, `services/`, `use_cases/` implementan lógica de negocio.
   - Servicios específicos del orquestador (estado conversacional, pipeline de razonamiento) viven aquí.

4. **Domain**
   - Entidades (`entities/`), contratos (`contracts/`), servicios (`services/`) describen definiciones puramente de negocio.
   - Sin imports externos salvo typing, dataclasses, etc.

5. **Infrastructure**
   - `langgraph/`: construcción de grafos, nodos, adaptadores de persistencia.
   - `persistence/`: repositorios para configuraciones de agentes y datos del workspace.
   - `websocket/`: difusión de eventos.
   - `integrations/`: conectores con proveedores LLM o servicios externos (respetar seguridad).

6. **Shared/Core**
   - Proveen utilidades transversales (gestores de memoria, IO de archivos, scheduler, configuración de logging) reutilizadas por orquestador y agentes.

7. **Tests**
   - Cada feature relevante debe tener cobertura unitaria e integración (`tests/test_*`).
   - Funcionalidades nuevas agregan al menos una prueba unitaria + una de integración siguiendo los patrones existentes.

---
### 5. Orquestador y Agentes
- La base del orquestador vive en `Backend/src/infrastructure/langgraph/`.
- Cada agente en `Backend/ia_workspace/agentes/<nombre>/handler.py` implementa el contrato `Backend/src/domain/agents/agent_protocol.py`.
- El registro/configuración de agentes está en `Backend/ia_workspace/data/agents_registry.json` y `agents_config.json`.
- La verificación de privilegios usa la tabla `public.agentes` (schema.sql) con endpoints en `Backend/src/api/agents_endpoints.py`.
- Los pipelines LangGraph (nodos, transiciones, estados) deben ser deterministas y auditables. Los nodos nuevos van en `langgraph/nodes/` y se registran en las factorías del orquestador.

---
### 6. Frontend (PantallaAgentes)
- App Router de Next.js en `Frontend/src/app/`.
- Componentes por feature en `Frontend/src/app/dashboard/` y `Frontend/src/components/`.
- El cliente WebSocket se conecta al broadcaster del backend para métricas en vivo.
- Reutiliza contratos TypeScript desde `Frontend/src/app/types/` para reflejar DTOs del backend.
- Estilos alineados con los tokens definidos en `AI/Tablero/PantallaAgentes/STYLE_TOKENS.md`.

---
### 7. Logging, Telemetría y Observabilidad
- Configuración en `Backend/src/core/logging_config.json`.
- Los logs se emiten con `logging` de Python y deben ir a:
  - `Backend/logs/app.log`
  - `Backend/logs/errors.log`
  - `Backend/logs/api.log`
- Prohibido usar `print()` en código productivo. Las pruebas pueden usar `capsys` para asserts.
- Los registros incluyen metadatos estructurados: `timestamp`, `level`, `logger`, `message`, `module`, `function`, `line`, `taskName`.
- Rotación por tamaño/tiempo: 10MB app/errors, 5MB api. No crear archivos de log adicionales.

---
### 8. Reglas de Despliegue y Ejecución
- Docker Compose orquesta Backend + Frontend + Postgres via `docker-compose.yml`.
- Scripts `docker-commands.ps1` / `.sh` encapsulan acciones (start, stop, restart, rebuild, logs, status, clean).
- Ejecución local usa virtualenv en `/Backend/.venv` (opcional) y `npm`/`pnpm` para frontend.
- Agentes que acceden a documentos deben permanecer en directorios permitidos por la configuración del orquestador. El agent Desktop es el único autorizado a modificar archivos y debe registrar respaldos.

---
### 9. Estrategia de Pruebas
1. **Unitarias**: modelos de dominio, servicios de application, lógica pura de agentes.
2. **Contrato**: validar esquemas IO de agentes con fixtures en `Backend/tests/fixtures/`.
3. **Integración**: pipelines completos del orquestador (`test_langgraph_integration.py`, `test_production_integration.py`).
4. **End-to-End**: opcional; usar docker compose y ejecutar smoke tests sobre REST + WebSocket.
5. **Frontend**: stack de pruebas Next.js (Jest/Testing Library) cuando haya cambios de UI; seguir la documentación en `AI/`.

Regla: toda feature de agente u orquestación debe incluir pruebas unitarias e integración. Actualiza README/docs con los comandos de ejecución.

---
### 10. Seguridad y Cumplimiento
- Escalera de privilegios: `restricted -> standard -> elevated -> privileged -> admin`. Por defecto `standard`.
- Cada endpoint privilegiado se valida contra la base de datos y los JSON de configuración.
- Los secretos viven en `.env`/`.env.example` y se consumen vía `Backend/src/core/settings.py` (sin hardcodear).
- Operaciones sobre documentos generan respaldos con timestamp y nunca sobrescriben sin copia previa.
- Las respuestas sensibles deben anonimizar PII; usa sanitizadores en la capa `application`.

---
### 11. Alineación con Zero-System
- Los documentos en `.zero/context/*` son canónicos y solo se actualizan de forma humana (esta tarea los alinea con CAPI).
- `.zero/scripts/` regenera artefactos que reflejan la estructura backend/frontend.
- `.zero/dynamic/` guarda análisis y notas de sesión; mantenlo organizado por fecha.
- `ZeroGraph.json` resume la estructura (ver Zero.md para expectativas de esquema).

---
### 12. Zonas Protegidas (sin cambios IA salvo instrucción)
```
AI/
docs/
```
- Los agentes deben tratarlas como solo lectura. Los borradores van a `.zero/dynamic/` o `Backend/ia_workspace/data/` hasta revisión humana.

---
### 13. Checklist de Gestión de Cambios
Antes de fusionar cualquier cambio:
1. Ejecuta `.zero/scripts/pipeline.ps1` para regenerar estructura y conflictos.
2. Corre pruebas backend: `cd Backend && pytest` (usa markers si necesitas suites específicas).
3. Ejecuta lint/pruebas de frontend cuando haya cambios de UI.
4. Actualiza documentación: `.zero/context`, `AI/Tablero`, `docs/` según corresponda.
5. Registra decisiones o pendientes en `.zero/dynamic/sessions/`.

---
### 14. Manejo de Deriva
Si el contenido del repositorio viola esta arquitectura:
- Prioriza refactorizar hasta alinearlo.
- Actualiza `ZeroGraph.json` mediante un delta en `.zero/dynamic/analysis/` y fusión controlada.
- Documenta excepciones temporales con fecha de caducidad.

Última actualización: 18/09/2025 (curado por humanos).
