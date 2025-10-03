# Registro de Errores Detectados

> Referencia rápida de reproducción: ejecutar `python -m pytest Backend/tests -q` produce 7 fallos al 19/09/2025.

## Problemas de clasificación semántica

1. **Saludo `"¿Qué tal?"` clasificado como small talk**     - Prueba: `Backend/tests/test_intent_classifier.py::test_greeting_intent`.     - Resultado observado: `Intent.SMALL_TALK` con `confidence=0.088`, mientras que se espera `Intent.GREETING`.     - Impacto: respuestas incorrectas para saludos cortos; afecta la UX inicial del chat.     - Código relacionado: heurísticas actuales en `Backend/src/core/semantics/intent_service.py` y combinación semántica/legacy en `Backend/src/application/nlp/intent_classifier.py`.

2. **Consultas de resumen terminan etiquetadas como branch**     - Prueba: `Backend/tests/test_intent_classifier.py::test_summary_request_intent` con el caso `"Estado actual de los datos"`.     - Resultado observado: `Intent.BRANCH_QUERY` con `confidence≈0.345`.     - Impacto: desvío de la petición hacia agentes equivocados (branch en lugar de summary).     - Código relacionado: boosts de `_calculate_concept_boost` en `Backend/src/core/semantics/intent_service.py` favorecen keywords de sucursal frente a términos de resumen.

3. **Texto aleatorio no cae en UNKNOWN**     - Prueba: `Backend/tests/test_intent_classifier.py::test_unknown_intent`.     - Ejemplos: `"Texto completamente aleatorio sin sentido"` retorna `Intent.FILE_OPERATION`; `"xyz123 test random"` se marca como `Intent.ANOMALY_QUERY`.     - Impacto: el router activa agentes innecesarios y pierde la posibilidad de pedir aclaraciones.     - Código relacionado: la normalización y los boosts de `_calculate_intent_similarities` en `Backend/src/core/semantics/intent_service.py` nunca devuelven valores bajos suficientes para caer en UNKNOWN.

4. **Confianza excesiva en consultas vagas**     - Prueba: `Backend/tests/test_semantic_nlp_system.py::test_confidence_levels`.     - Caso: `"ver eso"` arroja `confidence=1.0`.     - Impacto: se reportan niveles de certeza falsamente altos, dificultando A/B testing y monitoreo.     - Código relacionado: `_adjust_confidence` en `Backend/src/core/semantics/intent_service.py` no penaliza consultas cortas sin entidades.

5. **Confianza insuficiente para `"encontrar outliers"`**     - Prueba: `Backend/tests/test_production_integration.py::test_production_critical_scenarios`.     - Resultado observado: `Intent.ANOMALY_QUERY` con `confidence≈0.2` (<0.5 esperado).     - Impacto: bloquea flujos críticos de detección de anomalías y dispara el fallback legacy.     - Código relacionado: valores base/boost de `_calculate_concept_boost` para `Intent.ANOMALY_QUERY` en `Backend/src/core/semantics/intent_service.py`.

## Problemas de extracción de entidades

6. **Nombres de archivo contaminados con partículas**     - Prueba: `Backend/tests/test_semantic_nlp_system.py::test_filename_extraction_patterns` y `test_production_integration.py::test_production_critical_scenarios`.     - Ejemplos:       • `"archivo se llama hola mundo"` → `"llama hola mundo"`       • `"leer archivo llamado reporte final"` → `"llamado reporte final"`       - Impacto: rutas generadas con nombres erróneos, rompiendo automatizaciones de escritorio.       - Código relacionado: limpieza en `_clean_filename` y filtros en `extract_primary_entities` dentro de `Backend/src/core/semantics/entity_extractor.py`.

7. **Caso fundacional sigue sin resolver el filename**     - Prueba: `Backend/tests/test_semantic_nlp_system.py::TestSystemIntegration::test_original_problem_case`.     - Resultado observado: `entities['filename'] == "que esta"` en lugar de `"hola mundo"`.     - Impacto: reintroduce el bug original que motivó la migración semántica.     - Código relacionado: selección primaria en `_select_primary_filename` y tokens descartados en `extract_primary_entities` (`Backend/src/core/semantics/entity_extractor.py`).

## Cobertura y métricas

8. **Métricas de error potencialmente infladas**     - Durante la corrida de `pytest`, se registraron 7 fallos sobre 127 pruebas.     - Revisión necesaria para ajustar dashboards (`Backend/src/core/monitoring/semantic_metrics.py`) antes de habilitar alertas basadas en producción.

---

### Manejo de errores añadido durante la auditoría
- Se incorporó captura genérica en `Backend/src/core/semantics/intent_service.py` (`classify_intent`) para registrar y devolver un fallback seguro (`Intent.UNKNOWN`) ante excepciones inesperadas.
- `Backend/src/core/semantics/entity_extractor.py` ahora encapsula `extract_primary_entities` con `try/except`, evitando que errores en patrones individuales interrumpan la respuesta del orquestador.

- `Backend/src/core/logging.py` ahora centraliza toda la salida en `logs/backend.log` con formato `[YYYY-MM-DD HH:MM:SS] [Backend] [LEVEL] [logger] mensaje`.
- `Frontend/src/app/utils/logger.ts` envuelve `console.*` para añadir `[timestamp] [Frontend] [LEVEL]` y facilitar la correlación con los eventos del backend.
- `Backend/src/presentation/websocket_langgraph.py` usa ahora `get_logger` y reporta desconexiones/errores mediante `[Backend]` en lugar de `print`.
- `Backend/src/shared/memory_manager.py` reemplaza prints por `logger.exception` y conserva el flujo con mensajes claros por sesión/archivo.
- `Backend/src/api/main.py` añade metadatos (`request_id`, `client_id`, `trace_id`) a los logs del orquestador para que una IA pueda correlacionar cada instrucción y respuesta.
- Los logs siguen en `logs/backend.log` (único punto backend) y el frontend usa `[Frontend] [LEVEL] [path=/...]` para sincronizar eventos.

