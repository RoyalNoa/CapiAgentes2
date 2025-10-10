# Catálogo de Agentes — CapiAgentes

Este catálogo está pensado para leerlo en 1 minuto. Cada agente en formato mínimo: Nombre → Qué hace → Entradas → Salidas → Datos → Ejemplo.

## Ficha rápida por agente

1) Summary (Resumen)
- Qué hace: Resumen financiero general (totales, neto, conteos, anomalías, sucursales).
- Entradas: ninguna obligatoria.
- Salidas: métricas agregadas y conteos; resumen por sucursales.
- Datos: archivos financieros ya cargados en el sistema (workspace).
- Ejemplo: “Dame un resumen financiero de los datos”.

2) Branch (Sucursales)
- Qué hace: Analiza desempeño por sucursal y compara entre ellas.
- Entradas: `branch_name` (opcional). Si falta, analiza todas.
- Salidas: ranking, mejores/peores, métricas y comparativas.
- Datos: los mismos del workspace financiero.
- Ejemplo: “¿Cuál es la sucursal con mejor rendimiento?”

3) Anomaly (Anomalías)
- Qué hace: Detecta irregularidades en los datos (montos atípicos, patrones raros, etc.).
- Entradas: opcionales — `threshold` (umbral), `time_range` (período), `anomaly_type`.
- Salidas: lista de anomalías y severidad (baja/med/alta/crítica), resumen.
- Datos: workspace financiero.
- Ejemplo: “Detecta anomalías del último mes”.

4) Capi Gus (Conversación y narrativa)
- Qué hace: Responde saludos, mantiene la conversación y entrega la narrativa final con datos consolidados.
- Entradas: consulta del usuario; opcionalmente métricas agregadas desde otros agentes.
- Salidas: mensaje en lenguaje natural, sugerencias y artefactos de resumen en .
- Datos: usa información proporcionada por los demás agentes y contexto del router.
- Ejemplo: “Hola, ¿qué puedes hacer?” o “¿Podés darme una conclusión rápida?”

5) Capi Desktop (Archivos Office)
- Qué hace: Lee/escribe/modifica archivos CSV/Excel/Word, backups y validaciones con foco en seguridad.
- Entradas: `intent` (p. ej., `leer_archivo_csv`, `escribir_archivo_excel`), `filename`, `data` (cuando aplica).
- Salidas: analisis, muestras de datos o confirmacion de escritura; metricas de filas/columnas. Copia automatica en `ia_workspace/data/agent-output/capi_desktop/AAAA/MM/`.
- Datos: archivos del workspace o escritorio (rutas seguras predefinidas).
- Ejemplo: “Leer el archivo `clientes.csv` y mostrar 10 filas”.

Notas de autorización por agente
- Cada agente tiene `nivel_privilegio` en BD (`public.agentes`). Valores: `restricted | standard | elevated | privileged | admin`.
- Endpoints backend:
	- GET `GET /api/agents/privileges` → lista agentes con su nivel.
	- PATCH `PATCH /api/agents/{nombre}/privilege` con body `{ "nivel_privilegio": "elevated" }` → actualiza nivel.
- Recomendación: empezar con `standard` y elevar temporalmente cuando sea necesario; auditar cambios.



## Guia detallada de nodos LangGraph

### Categorias sugeridas por un arquitecto de agentes
- **Nucleo de orquestacion**: nodos que preparan el estado, planifican, enrutan y ensamblan la respuesta final.
- **Agentes de analisis financiero**: componentes que calculan metricas, rankings y anomalas sobre los datos cargados.
- **Agentes de productividad y entrega**: automatizan tareas de archivos o entregas al usuario final.
- **Agentes de inteligencia externa**: traen informacion del exterior para enriquecer el contexto operativo.
- **Agentes de conversacion y experiencia**: mantienen una interaccion amigable cuando no hay tareas analiticas.

### Nucleo de orquestacion
#### StartNode (`start`)
- **Proposito**: inicializa el flujo marcando `status=PROCESSING`, establece `current_node` y arranca el historial de nodos completos.
- **Entradas que lee**: identificadores de sesion (`session_id`, `trace_id`, `user_id`) y la consulta original.
- **Salidas que escribe**: `status`, `current_node`, `completed_nodes`.
- **Ejemplo de uso**: todo turno comienza aqui; antes de clasificar un "Que sucedio hoy?" StartNode deja el estado listo para los nodos siguientes.
- **Notas**: no requiere configuracion adicional y es un buen punto para instrumentar diagnosticos tempranos.

#### IntentNode (`intent`)
- **Proposito**: clasifica la consulta con `IntentClassifier` y adjunta el razonamiento utilizado.
- **Entradas que lee**: `original_query` y cualquier contexto previo en `response_metadata`.
- **Salidas que escribe**: `detected_intent`, `intent_confidence`, `response_metadata.intent_reasoning`.
- **Ejemplo de uso**: "Resumeme septiembre" produce la etiqueta `summary_request` con una confianza aproximada del 0.9.
- **Notas**: si necesitas forzar una intencion durante pruebas, modifica temporalmente `IntentClassifier` o inicializa el estado con un hint.

#### ReActNode (`react`)
- **Proposito**: ejecuta un ciclo razonamiento+accion acotado; invoca herramientas internas y puede proponer el agente ideal.
- **Entradas que lee**: consulta, contexto resumido, resultados de turnos anteriores.
- **Salidas que escribe**: `response_metadata.react_trace`, `response_data.react_observations`, `routing_decision` opcional.
- **Ejemplo de uso**: ante "Hay operaciones sospechosas?" deja una traza con los tools consultados y recomienda `anomaly` si detecta indicios.
- **Notas**: controla la cantidad de iteraciones con `max_iterations`; cada observacion se refleja luego en la vista de grafo.

#### ReasoningNode (`reasoning`)
- **Proposito**: genera o actualiza un `ReasoningPlan` multi-paso con agentes cooperativos y progreso estimado.
- **Entradas que lee**: consulta, `detected_intent`, plan previo en `response_metadata.reasoning_plan`.
- **Salidas que escribe**: `response_metadata.reasoning_plan`, `reasoning_trace`, metricas `processing_metrics.reasoning_*`.
- **Ejemplo de uso**: "Prepara informe y enviamelo" crea un plan con pasos `summary -> capi_desktop` y la confianza asociada.
- **Notas**: si `needs_replan` detecta cambios, se conserva el historico en `reasoning_trace` para auditar decisiones.

#### SupervisorNode (`supervisor`)
- **Proposito**: construye la cola de agentes a ejecutar combinando plan, recomendaciones de ReAct y prioridades por defecto.
- **Entradas que lee**: `response_metadata.reasoning_plan`, `response_metadata.react_recommended_agent`, `supervisor_queue` anterior.
- **Salidas que escribe**: `routing_decision`, `active_agent`, `response_metadata.supervisor_queue`.
- **Ejemplo de uso**: con un plan que incluye `summary` y `anomaly`, el supervisor los ordena y entrega el primero al router.
- **Notas**: ajusta la lista por defecto via `default_queue` si agregas agentes core nuevos.

#### RouterNode (`router`)
- **Proposito**: selecciona el nodo agente segun intencion, resultados semanticos y disponibilidad.
- **Entradas que lee**: `detected_intent`, `intent_confidence`, `response_metadata.semantic_result`, banderas de configuracion.
- **Salidas que escribe**: `routing_decision`, `active_agent`, metricas de clasificacion en `processing_metrics`.
- **Ejemplo de uso**: "Copia el CSV al escritorio" redirige a `capi_desktop` cuando la intencion `file_operation` esta activa.
- **Notas**: respeta los flags de habilitacion en `ia_workspace/data/agents_config.json`; si un agente esta deshabilitado, cae en `assemble`.

#### HumanGateNode (`human_gate`)
- **Proposito**: pausa el flujo cuando una accion requiere aprobacion humana (escrituras, eliminaciones, etc.).
- **Entradas que lee**: `response_metadata.semantic_action`, `response_metadata.requires_human_approval`.
- **Salidas que escribe**: `response_metadata.human_decision`, posible `status=PAUSED`, mensaje de rechazo por defecto.
- **Ejemplo de uso**: despues de `capi_desktop` en una operacion WRITE_FILE, emite un `interrupt` hasta recibir la decision via API.
- **Notas**: las decisiones se inyectan a traves de `POST /api/orchestrator/human/decision`; sin ella el flujo queda pausado.

#### AssembleNode (`assemble`) y FinalizeNode (`finalize`)
- **Proposito**: consolidan mensaje, datos y metadatos antes de cerrar el turno.
- **Entradas que leen**: respuesta parcial de agentes, `completed_nodes`.
- **Salidas que escriben**: `response_message` definitivo, `response_metadata.workflow_completed`, `status=COMPLETED`.
- **Ejemplo de uso**: compone "Se genero ingresos_Q3.xlsx en el escritorio" tras que el desktop agent complete la tarea.
- **Notas**: si ningun agente genero mensaje, Assemble crea un fallback amigable para evitar respuestas vacias.

### Agentes de analisis financiero
#### SummaryNode (`summary`)
- **Proposito**: calcula agregados y KPIs financieros reutilizando `SummaryAgent`.
- **Entradas que lee**: datasets cargados en el workspace, parametros opcionales en el estado.
- **Salidas que escribe**: `response_message` con el resumen, `response_data` (totales, neto, resumen por sucursal), `response_metadata.summary_hash`.
- **Ejemplo de uso**: "Dame el resumen financiero del mes" devuelve ingresos, egresos, variacion y cuentas destacadas.
- **Notas**: usa hashes para deduplicar llamadas; el resultado aparece en la vista HUD en el panel de resumen.

#### BranchNode (`branch`)
- **Proposito**: analiza rendimiento por sucursal (ranking, top/bottom, comparativas).
- **Entradas que lee**: datos financieros y opcionalmente filtros de sucursal.
- **Salidas que escribe**: `response_data.branch_summary`, `response_metadata.branch_hash`, mensaje contextual.
- **Ejemplo de uso**: "Que sucursal vendio mas?" lista top 5 sucursales con sus metricas clave.
- **Notas**: ideal para dashboards; si incorporas nuevos campos, extiende `branch_data` para reflejarlos.

#### AnomalyNode (`anomaly`)
- **Proposito**: detecta transacciones irregulares con `AnomalyAgent`.
- **Entradas que lee**: historial financiero y la pregunta del usuario.
- **Salidas que escribe**: `response_data.anomalies`, `response_metadata.anomaly_hash`, mensaje de hallazgos.
- **Ejemplo de uso**: "Hay transacciones sospechosas hoy?" devuelve registros con montos fuera de rango.
- **Notas**: las mismas banderas de deduplicacion permiten evitar recomputos si la misma consulta llega varias veces seguidas.

### Agentes de productividad y entrega
#### CapiDesktopNode (`capi_desktop`)
- **Proposito**: interpreta operaciones sobre archivos (leer, transformar, mover) y delega en Capi Desktop.
- **Entradas que lee**: consulta natural, contexto semantico, historial reciente.
- **Salidas que escribe**: `response_message` con resultado de la operacion, `response_data` (paths, contenido, archivos encontrados), `response_metadata.semantic_action` y banderas de aprobacion.
- **Ejemplo de uso**: "Crea un Excel con los ingresos del trimestre en el escritorio" genera el archivo y marca `requires_human_approval` antes de escribir.
- **Notas**: si la accion es de escritura o borrado, HumanGate exigira aprobacion; revisa `agents_registry` para confirmar rutas de handler.

#### AgenteGNode (`agente_g`)
- **Proposito**: interactua con Gmail, Drive y Calendar para automatizar comunicacion y recordatorios.
- **Entradas que lee**: instrucciones en `response_metadata.agente_g_instruction` (operation + parameters) o consultas con palabras clave detectadas por el router.
- **Salidas que escribe**: `response_message`, `response_data` con resumen de la API y artefactos en `shared_artifacts['agente_g']`.
- **Ejemplo de uso**: "Listar correos no leidos" devuelve encabezados; una instruccion `create_calendar_event` agenda una reunion.
- **Notas**: operaciones sensibles (enviar correo, compartir archivo, habilitar/deshabilitar push de Gmail) requieren aprobación a través de HumanGate.
- **Actualizacion 2025-10**: el nodo infiere operaciones `send_gmail`, `list_drive` o `create_calendar_event` automaticamente y delega redaccion de correos al LLM integrado.
- **Metricas**: agrega `google_metrics.llm_*` cuando se usa la composicion asistida de correos.

#### CapiDataBNode (`capi_datab`)
- **Proposito**: orquesta operaciones ABMC sobre PostgreSQL y deja evidencia en `ia_workspace/data/capi_DataB/`.
- **Entradas que lee**: instrucciones en texto/JSON con la consulta o comando SQL, formato deseado (`json`, `csv`, `txt`).
- **Salidas que escribe**: `response_message` con el resumen, `response_data` con `file_path`, `rowcount`, SQL ejecutado y metadatos de sesión.
- **Ejemplo de uso**: "Consulta base de datos clientes" o `{"operation":"update",...}` genera el archivo `DataB_AAAA_MM_DD_*.json` con el resultado.
- **Notas**: bloquea `DROP/TRUNCATE`, solicita aprobación humana para updates/delete y usa las credenciales definidas en `.env` (`DATABASE_URL` o `POSTGRES_*`).

### Agentes de inteligencia externa
#### CapiNoticiasNode (`capi_noticias`)
- **Proposito**: obtiene noticias y alertas relevantes mediante el scheduler de Capi Noticias.
- **Entradas que lee**: tema de la consulta, configuracion activa en el scheduler.
- **Salidas que escribe**: `response_message`, `response_data` con articulos/alertas, `response_metadata.news_article_count`.
- **Ejemplo de uso**: "Hay alertas de liquidez hoy?" devuelve titulares y marca cuantas alertas de alto impacto encontro.
- **Notas**: depende del servicio programado; usa `/api/agents/capi_noticias/status` para comprobar la frecuencia y ultimas ejecuciones.

### Agentes de conversacion y experiencia
#### Capi GusNode (`capi_gus`)
- **Proposito**: responde saludos y cortesias sin requerir LLM.
- **Entradas que lee**: texto original en minúsculas.
- **Salidas que escribe**: `response_message` con una respuesta amable, `response_metadata.response_source`.
- **Ejemplo de uso**: "Hola, estas ahi?" devuelve un saludo amistoso y mantiene la conversacion cercana.
- **Notas**: extiende los arrays de frases para personalizar el tono segun la marca.

### Informacion adicional para nuevos integrantes
- **Archivos de control**: los manifiestos viven en `Backend/ia_workspace/data/agents_registry.json` y las banderas en `agents_config.json`; alli habilitas o deshabilitas nodos sin tocar codigo.
- **Pruebas**: `pytest Backend/tests -q` incluye `test_langgraph_integration.py`, excelente punto de partida para validar cambios en el pipeline.
- **Observabilidad**: cada nodo anota eventos (`logger.info`) y metricas en `processing_metrics`; revisa `logs/langgraph` cuando algo no rote como esperabas.
- **Integracion frontend**: el HUD consume `response_metadata` y `reasoning_trace`. Mantener esos campos consistentes facilita explicar decisiones a usuarios finales.
- **Checklist de onboarding**: repasar este catalogo, ejecutar un flujo end-to-end (saludo, resumen, operacion de escritorio) y practicar el uso del HumanGate via API para comprender pausas y reanudaciones.

