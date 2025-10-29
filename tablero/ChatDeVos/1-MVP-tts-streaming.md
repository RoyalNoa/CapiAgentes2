## Objetivo
Implementar streaming de TTS (ElevenLabs o Google) para que el audio de respuesta comience a reproducirse apenas lleguen los primeros chunks. Como IA sin contexto, **investiga cada detalle y valida todo; este documento puede contener errores**.

## Investigación Recomendada
- Examina `Backend/src/voice/elevenlabs_tts.py` y `Backend/src/voice/google_tts.py` para conocer las interfaces actuales.
- Consulta la documentación oficial de ElevenLabs y Google TTS para confirmar soporte de streaming, formatos y límites.
- Revisa `Frontend/src/app/hooks/useVoiceStream.ts` y `useVoiceInterface` para entender cómo se consume actualmente `audioUrl` o `base64`.

## Plan de Trabajo
1. Define qué proveedor se actualizará primero (ElevenLabs vs Google) y confirma cómo recibir chunks (WebSocket, streaming HTTP). No implementes sin validar el API real.
2. Ajusta el backend para exponer audio incremental: considera emitir eventos extra por WebSocket (`voice_stream`) con los fragmentos conforme llegan.
3. Actualiza el frontend para construir un `MediaSource` o `AudioContext` que consuma los chunks en vivo, manteniendo compatibilidad con el método actual (base64 final).
4. Maneja casos de error (stream interrumpido, chunk incompleto) y asegúrate de limpiar recursos en ambos extremos.

## Validación
- Ejecuta pruebas backend (`pytest Backend/tests/voice -q`) y agrega nuevas para el flujo streaming si no existen.
- En frontend, corre `npm test --prefix Frontend` y realiza pruebas manuales verificando que el audio comience antes de completarse el texto.
- Mide la reducción del tiempo “silencioso” entre el mensaje y el audio.

## Entregables
- Implementación streaming con fallback al modo actual.
- Pruebas y métricas que demuestren la mejora.
- Documentación sobre configuración adicional (keys, flags, endpoints).

## Impacto Estimado en Latencia
- Reducción aproximada: **≈0.4 segundos** en el “silencio” previo a la respuesta hablada.
- Fuente: inicio de reproducción al recibir los primeros chunks en vez de esperar el MP3 completo (síncrono actual ~0.6 s).
