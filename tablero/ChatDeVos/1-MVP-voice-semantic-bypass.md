## Objetivo
Reducir la latencia de los turnos de voz deshabilitando la rama semántica lenta durante la transcripción y orquestación. Eres una IA sin contexto previo: **investiga cada paso y valida todo**. Este documento puede contener errores u omisiones; no asumas nada.

## Investigación Recomendada
- Revisa `Backend/src/application/nlp/intent_classifier.py` para entender cómo se invoca `SemanticIntentService`.
- Rastrea cómo se arma el `channel` dentro del flujo de voz (`Backend/src/voice/manager.py`, `Backend/src/api/voice_endpoints.py`) y confirma si llega hasta el classifier.
- Identifica pruebas automatizadas asociadas (probablemente en `Backend/tests/voice` y `Backend/tests/application/nlp`).

## Plan de Trabajo
1. Confirma si `IntentClassifier.classify` recibe información sobre el canal; si no, evalúa propagarla desde la voz. No avances sin trazar la ruta de datos.
2. Diseña la bandera o condición para saltar `SemanticIntentService` cuando `channel == "voice"` (o configuración equivalente). Documenta dónde se lee.
3. Implementa el bypass asegurando que el clasificador heurístico legacy siga funcionando para voz.
4. Ajusta pruebas unitarias o agrega nuevas que cubran el caso de voz sin semántica.

## Validación
- Ejecuta `pytest Backend/tests/voice -q` y suites relevantes del classifier.
- Recolecta métricas `VOICE_TURN_LATENCY` antes y después si es posible.
- Escucha manualmente un turno de voz para comprobar que la respuesta se emite sin retrasos.

## Entregables
- Código actualizado con bypass condicionado.
- Evidencia de pruebas y cualquier métrica comparativa.
- Nota en el tablero sobre nuevas banderas/configuración necesarias.

## Impacto Estimado en Latencia
- Reducción aproximada: **≈7 segundos** por turno de voz (de ~12.5 s a ~5.5 s).
- Fuente: eliminación de la llamada `SemanticIntentService` que hoy tarda ~7 s y concluye en fallback.
