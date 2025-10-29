## Objetivo
Modernizar la captura de audio en el frontend usando AudioWorklet o MediaStreamTrackProcessor para reducir latencia y jitter. Eres una IA sin contexto: **investiga todo y verifica; este documento puede contener errores**.

## Investigación Recomendada
- Revisa `Frontend/src/app/hooks/useVoiceStream.ts` para entender la cadena actual (`ScriptProcessor`, resampling, envío WebSocket).
- Evalúa compatibilidad de AudioWorklet y MediaStreamTrackProcessor en navegadores objetivo; revisa caniuse.com u otras fuentes confiables.
- Busca componentes compartidos que dependan del buffer actual (`useVoiceInterface`, pruebas en `Frontend/src/app/components/chat/hooks/__tests__`).

## Plan de Trabajo
1. Define la estrategia principal (AudioWorklet vs MediaStreamTrackProcessor) y documenta el fallback necesario para navegadores sin soporte. No avances sin confirmar compatibilidad.
2. Implementa el nuevo capturador produciendo frames de ~20 ms PCM 16-bit a 16 kHz. Asegura que el resampling continúe funcionando si la fuente no es 16 kHz.
3. Ajusta el pipeline de envío WebSocket para aceptar `ArrayBuffer` desde la nueva API sin bloquear el hilo principal.
4. Actualiza pruebas y mocks que dependan del `ScriptProcessor`.

## Validación
- Ejecuta `npm test --prefix Frontend` y cualquier suite que cubra voz.
- Prueba manualmente en Chrome/Edge/Safari. Confirma que la transcripción parcial llega más rápido y sin cortes.
- Verifica que el fallback legacy siga disponible y documentado.

## Entregables
- Código del nuevo capturador con fallback.
- Evidencia de pruebas automatizadas y manuales (incluye navegadores probados).
- Documentación de compatibilidad y consideraciones de despliegue.

## Impacto Estimado en Latencia
- Reducción aproximada: **≈0.2 segundos** de tiempo hasta la transcripción parcial.
- Fuente: reemplazo de `ScriptProcessor` (buffers de 4096 ≈92 ms) por AudioWorklet/MediaStreamTrackProcessor con frames de 20 ms, mejorando continuidad y reduciendo jitter.
