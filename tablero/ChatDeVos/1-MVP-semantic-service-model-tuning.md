## Objetivo
Reducir la latencia del servicio semántico configurando un modelo más liviano y robusto con validación estricta. Recuerda: eres una IA sin contexto; **investiga cada paso, valida las fuentes y asume que este documento puede contener errores**.

## Investigación Recomendada
- Explora `Backend/src/core/semantics/intent_service.py` para entender cómo se instancia `LLMReasoner`.
- Revisa `Backend/src/application/reasoning/llm_reasoner.py` para conocer opciones de modelo, timeouts y formatos de respuesta.
- Busca configuraciones actuales en `.env.example` y en la capa de settings por si existen banderas ya definidas.

## Plan de Trabajo
1. Verifica cuáles modelos están disponibles (OpenAI u otros) y si `gpt-4o-mini` u otra variante rápida es compatible con el endpoint utilizado (`responses` vs `chat`). No implementes sin confirmarlo.
2. Ajusta la inicialización de `SemanticIntentService` para parametrizar modelo, temperatura y `response_format`; considera usar `json_schema` para evitar `parse_error`.
3. Agrega manejo de fallbacks si el nuevo modelo no responde o supera tiempo límite.
4. Actualiza documentación y variables de entorno para reflejar el nuevo modelo y permitir revertirlo si es necesario.

## Validación
- Ejecuta pruebas unitarias del servicio semántico (`pytest Backend/tests/core/semantics -q` si existe) y de los módulos que lo consumen.
- Corre pruebas de integración (ej. `pytest Backend/tests/infrastructure/langgraph -q`) verificando que se respeten los contratos.
- Mide latencia real (usando logs o métricas) antes y después para comparar mejoras.

## Entregables
- Código configurado para el nuevo modelo con capacidad de fallback.
- Actualización de `.env.example` o docs si cambian variables.
- Evidencia de pruebas y mediciones de latencia.

## Impacto Estimado en Latencia
- Reducción aproximada: **≈4–5 segundos** por llamada semántica que permanezca activa.
- Fuente: cambio del modelo `gpt-5` (~5–7 s observados) a una variante rápida (`gpt-4o-mini` u otro <1 s) con validación robusta.
