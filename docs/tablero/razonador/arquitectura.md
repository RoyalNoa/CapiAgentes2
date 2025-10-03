# Arquitectura actual del orquestador

## Flujo principal LangGraph
- Grafo base (`graph_builder.py`): `start -> intent -> react -> reasoning -> supervisor -> loop_controller`.
- El `router` decide el agente y puede devolver multiples destinos validos segun `routing_decision` o `parallel_targets`.
- Agentes habilitados: `smalltalk`, `summary`, `branch`, `anomaly`, `capi_desktop`, `capi_datab`, `capi_noticias` (opcional). Todos conectan a `human_gate` y luego a `assemble -> finalize`.
- `loop_controller` permite cortar temprano hacia `assemble` si no hay accion pendiente.

## Clasificacion e intencion
- `router_node.py` instancia `SemanticIntentService`; usa contexto persistente via `get_global_context_manager`.
- Clasifica cada turno y registra metricas (`semantic_metrics`). Si el feature flag deshabilita NLP, cae a un fallback determinista.
- `Intent.DB_OPERATION` ruta por defecto hacia `capi_datab`. El selector anade siempre `summary`, `capi_datab`, `capi_desktop`, `assemble` como ultimos recursos.

## Nodos relevantes previos a agentes
- `ReActNode` (`react_node.py`) realiza iteraciones pensamiento/accion y deja recomendaciones en `routing_decision`.
- `ReasoningNode` y `SupervisorNode` consolidan trazas y validan limites de ciclos antes de delegar al router.
- `HumanGateNode` controla aprobaciones humanas posteriores a la ejecucion del agente seleccionado.

## Agente Capi DataB
- Nodo (`capi_datab_node.py`) carga `CapiDataBAgent`; interrumpe para aprobacion si la operacion modifica datos.
- Extrae instruccion mediante `_extract_instruction`: busca JSON estructurado o texto que cumpla patrones basicos.
- Al no encontrar instruccion clara agrega error `datab_invalid_instruction` y cierra turno sin llamar al agente.
- Tras ejecutar, fusiona resultados en `response_data` y `shared_artifacts.capi_datab`, y puede disparar exportacion via Capi Desktop.

## Handler del agente
- `prepare_operation` intenta primero JSON, luego heuristicas de lenguaje natural: casos especiales para `branch_balance` via `_branch_balance_from_llm` y regex para `insert/update/delete`.
- `_branch_balance_from_llm` usa `LLMReasoner` con prompt minimo; solo maneja balances por sucursal y retorna `SELECT` fijo.
- Resto de operaciones requieren SQL explicito; sino, termina en `_parse_natural_language` con patrones limitados.
- `execute_operation` se conecta a PostgreSQL via `asyncpg`, exporta resultados a `/ia_workspace/data/capi_DataB/` y refuerza seguridad (`WHERE` obligatorio, bloquea `DROP/TRUNCATE`).

## Limitaciones observadas
- El router depende de `Intent.DB_OPERATION`; consultas libres sobre sucursales muchas veces quedan como `Intent.UNKNOWN` y van a `assemble`/`smalltalk`.
- El planificador actual del agente no entiende agregaciones distintas a balances y su prompt no incluye catalogo de tablas/columnas.
- No hay capa semantica que traduzca filtros arbitrarios (fechas, montos, top N) a SQL parametrizado.
- Metricas de exito del agente no distinguen entre errores de parsing y falta de intencion.
