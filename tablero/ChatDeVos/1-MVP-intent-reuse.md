## Objetivo
Evitar la doble invocación del clasificador semántico reutilizando el intent ya calculado en el pipeline. Eres una IA sin contexto previo: **investiga todo y valida cada afirmación**. Este documento puede tener errores; no confíes ciegamente.

## Investigación Recomendada
- Revisa `Backend/src/infrastructure/langgraph/nodes/intent_node.py` para ver qué información produce y cómo se almacena.
- Inspecciona `Backend/src/application/reasoning/advanced_reasoner.py` para ubicar las llamadas a `SemanticIntentService.classify_intent`.
- Entiende la estructura de `GraphState` y `StateMutator` (`Backend/src/infrastructure/langgraph/state_schema.py`).

## Plan de Trabajo
1. Analiza cómo fluye `response_metadata` y determina dónde guardar el resultado completo del intent (incluyendo confianza y entidades). Documenta el formato exacto antes de codificar.
2. Modifica `IntentNode` para serializar el `IntentClassificationResult` en el estado de forma compatible con consumidores existentes. Sin agotar la investigación no implementes.
3. Cambia `AdvancedReasoner.generate_plan` y métodos relacionados para leer el intent del estado antes de llamar al servicio semántico. Ten lista una ruta de fallback si el dato no existe o está corrupto.
4. Revisa fixtures y tests que dependan del formato de `response_metadata`; actualízalos para cubrir ambos caminos (con y sin reuse).

## Validación
- Ejecuta `pytest Backend/tests -k intent -q` y cualquier suite del reasoner.
- Corrige o agrega pruebas end-to-end que verifiquen que el plan se construye usando el intent cacheado.
- Revisa logs para asegurar que las llamadas repetidas al LLM desaparecieron (no debe haber dos `semantic_intent_llm_*` por turno).

## Entregables
- Código con el almacenamiento del intent y el consumo en el reasoner.
- Nuevas pruebas o ajustes necesarios.
- Reporte de métricas de latencia comparando antes/después.

## Impacto Estimado en Latencia
- Reducción aproximada: **≈5.5 segundos** por turno (de ~5.5 s restantes a ~0 s adicionales).
- Fuente: se evita la segunda llamada a `SemanticIntentService` (~5.5 s registrados en logs) reutilizando el intent cacheado.
