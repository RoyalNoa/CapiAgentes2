<!-- @canonical true -->
# Especificación ZeroGraph - Reglas Extendidas (CapiAgentes)

## 1. Clasificación avanzada de nodos
### 1.1 Subtipos de ApplicationLayer
- `application:reasoning` -> coordina LangGraph (state_manager, pipeline, servicios del orquestador).
- `application:alerts` -> genera y despacha alertas; requiere relación `exposes` con Presentation.
- `application:document_generation` -> integra agentes de escritura; debe relacionarse con `Dataset` de respaldos.

### 1.2 Agentes especializados
| Agente | Handler | Privilegio mínimo | Notas |
|--------|---------|-------------------|-------|
| summary | `Backend/ia_workspace/agentes/summary/handler.py` | `standard` | Agrega métricas globales |
| branch | `Backend/ia_workspace/agentes/branch/handler.py` | `standard` | Comparativa entre sucursales |
| anomaly | `Backend/ia_workspace/agentes/anomaly/handler.py` | `elevated` | Acceso extendido a históricos |
| smalltalk | `Backend/ia_workspace/agentes/smalltalk_fallback/handler.py` | `restricted` | Conversación / fallback |
| desktop | `Backend/ia_workspace/agentes/capi_desktop/handler.py` | `privileged` | Lectura/escritura de archivos |
| file_scribe | `Backend/ia_workspace/agentes/file_scribe/handler.py` | `privileged` | Operaciones de archivo asistidas |

## 2. Mapeo de endpoints
- `Backend/src/api/agents_endpoints.py` -> nodo `PresentationLayer:agents_api`.
  - Cada ruta crea relación `exposes` con el ApplicationLayer correspondiente.
- `Backend/src/api/main.py` -> relación `entrypoint` hacia nodos `PresentationLayer:*`.
- WebSocket (`Backend/src/presentation/websocket_langgraph.py`) -> relación `exposes` tipo `WebSocket` con canales documentados.

## 3. Privilegios y cumplimiento
- Todo nodo Agent debe vincularse a `Dataset` o `ApplicationLayer` donde se valida el privilegio (`privilege_controls`).
- Los Dataset con datos sensibles agregan propiedad `sensitivity` (`normal`, `restricted`, `secret`).
- Relaciones `persists_to` deben indicar `guard` (ej.: `privilege_check + schema`).
- Scripts que modifican datos (`docker-commands clean`, `safe-move-to-papelera.ps1`) necesitan relación `generates` con descripción de impacto (`data_loss`, `cleanup`).

## 4. Pruebas y cobertura
- Los nodos de prueba (`Backend/tests/*.py`) se modelan como `Script` con `scope: testing`.
- La relación `tests` incluye `coverage` (unit/integration/e2e) y `status` (pass/fail/unknown).
- `test_production_integration.py` debe enlazar con:
  - Nodos del orquestador LangGraph.
  - Agentes summary, branch, anomaly, smalltalk, desktop.
  - Endpoints API.

## 5. Frontend específico
- Rutas principales: `/dashboard`, `/workspace`, `/health` -> nodos `FrontendFeature`.
- Componentes clave (`AgentGrid`, `AlertStream`, `MetricsPanel`) deben tener relación `renders` hacia endpoints/WS.
- Incluir propiedad `depends_on_tokens` (lista) para vincular con `AI/Tablero/PantallaAgentes/STYLE_TOKENS.md` (ej.: `color.alertCritical`).

## 6. Integraciones externas
- Registrar nodos `Integration` si se habilitan conectores externos (LLM, almacenamiento). Propiedades mínimas: `provider`, `mode`, `requires_network` (bool).
- Relación `depends_on` entre `InfrastructureLayer` e `Integration` con atributo `auth_method`.

## 7. Lineamientos para ZeroGraph Delta
- `add_nodes`: arreglo de nodos completos (ID + propiedades).
- `update_nodes`: nodos existentes con propiedades modificadas.
- `add_relationships`: relaciones nuevas (origen, destino, tipo, propiedades).
- `remove_nodes` / `remove_relationships`: solo cuando se elimina el componente; incluir `reason`.
- Incluir campo `summary` con el motivo del delta (1-3 frases).

## 8. Auditoría
- Guardar resultados de validaciones en `/.zero/dynamic/analysis/zerograph-validation-YYYY-MM-DD.md` cuando existan cambios mayores.
- Mantener historial de respaldos (`ZeroGraph.json.bak-*`). No eliminarlos.

Última actualización: 18/09/2025.
