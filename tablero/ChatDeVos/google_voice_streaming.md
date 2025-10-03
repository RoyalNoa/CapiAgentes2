# Integracion de Voz en Tiempo Real con Google Cloud Speech/TTS

## 1. Objetivo
Anadir captura de voz, transcripcion en streaming (STT) y sintesis de respuesta (TTS) al chat existente basado en FastAPI + LangGraph + Next.js, usando Google Cloud como proveedor empresarial y manteniendo el stack Dockerizado actual.

## 2. Arquitectura Propuesta
- **Frontend (Next.js)**: captura audio con `MediaRecorder`, envia chunks via WebSocket seguro (`wss://`) al backend y reproduce la respuesta TTS.
- **Backend (FastAPI)**: expone WebSocket `/api/audio/stream`, normaliza audio (16 kHz PCM mono), envia streaming gRPC a Google Speech-to-Text, orquesta LangGraph con el texto recibido y solicita TTS. Devuelve texto final y URL/base64 de audio.
- **LangGraph**: nuevo `transcribe_audio` node (STT) + `synthesize_speech` node (TTS). Mantiene control de flujo existente.
- **Almacenamiento Temporal**: bucket compatible S3/GCS o disco efimero para blobs de audio de entrada/salida (purga programada).
- **Observabilidad**: metricas de latencia, ratio de errores y coste por sesion, enviadas a Prometheus/Logging existente.

## 3. Requisitos Previos
1. Cuenta activa en Google Cloud Platform (GCP).
2. `gcloud` CLI instalado en la maquina de operaciones o pipeline CI.
3. Proyecto GCP dedicado para voz (recomendado: `capi-voice-prod`).
4. Acceso a `docker compose`, `npm`, `python` segun README del repo.

## 4. Aprovisionamiento GCP
1. Crear proyecto: `gcloud projects create capi-voice-prod` y asociarlo a la organizacion/facturacion.
2. Habilitar APIs:
   ```bash
   gcloud services enable speech.googleapis.com texttospeech.googleapis.com storage.googleapis.com
   ```
3. Crear Service Account (SA) `voice-streaming-sa` con roles minimos:
   - `roles/speech.client`
   - `roles/texttospeech.user`
   - `roles/storage.objectAdmin` (si usas GCS para audio temporal)
4. Generar key JSON y guardarla fuera del repo (por ejemplo, `infra/keys/voice-streaming-sa.json`).
5. Configurar budget alerts en Billing para controlar consumo.

## 5. Variables de Entorno
Actualizar `.env.example` y `.env` (sin subir claves reales):
```
GCP_PROJECT_ID=
GCP_REGION=europe-west1
GCP_APPLICATION_CREDENTIALS=/run/secrets/voice-streaming-sa.json
GOOGLE_SPEECH_LANGUAGE=es-ES
GOOGLE_TTS_VOICE=es-ES-Wavenet-D
GOOGLE_TTS_AUDIO_ENCODING=MP3
VOICE_STREAM_BUCKET=gs://capi-voice-stream
```
- Montar el JSON como secreto en Docker (`docker-compose.yml` -> `secrets`).
- Exponer ruta dentro del contenedor (`/run/secrets/...`) y exportar `GOOGLE_APPLICATION_CREDENTIALS` antes de lanzar el backend.

## 6. Dependencias Backend
1. Anadir a `Backend/requirements.txt`:
   ```
   google-cloud-speech>=2.26.0
   google-cloud-texttospeech>=2.19.0
   soundfile>=0.12.1  # normalizar audio si se requiere
   ```
2. Ejecutar `pip install -r Backend/requirements.txt` localmente o en imagen Docker.
3. Ajustar `Backend/Dockerfile`:
   - Instalar `ffmpeg` o `libsox` si necesitas conversion de formatos.
   - Anadir `libogg`, `libopus` cuando se use audio Opus del navegador.

## 7. Endpoint WebSocket FastAPI
1. Crear modulo `Backend/src/api/routes/audio_stream.py` con un router `APIRouter(prefix="/audio")`.
2. Implementar `@router.websocket("/stream")` que:
   - Reciba frames binarios (chunks `Blob` -> `.arrayBuffer` -> `Int16Array`).
   - Acumule y envie a una cola async interna (`asyncio.Queue`).
   - Lance tarea `StreamingSpeechClient` para hablar con Google STT via gRPC bidireccional.
   - Envie mensajes JSON al frontend: `{"type":"partial", "text":"..."}` y `{"type":"final", "text":"...", "segment_id":1}`.
3. Reutilizar `Backend/src/core/logging` para trazar latencias y errores.
4. Anadir autenticacion opcional (token del chat) via query o header antes de aceptar la conexion.

## 8. Cliente gRPC Speech-to-Text
1. Crear servicio `Backend/src/voice/google_stt.py` que exponga:
   ```python
   async def stream_transcribe(audio_iterator, language_code="es-ES", sample_rate=16000):
       # usa google.cloud.speech.SpeechAsyncClient
   ```
2. Configurar request con:
   - `enable_automatic_punctuation=True`
   - `model="latest_long"` o `"latest_short"` segun casos (<60s audio).
   - `audio_channel_count=1`, `encoding=LINEAR16` (convertir si llega Opus).
3. Manejar reintentos con `tenacity` o backoff exponencial ante errores `429/5xx`.
4. Emitir eventos parciales/finales a LangGraph mediante `asyncio.Queue` o `async generator`.

## 9. Integracion LangGraph
1. Anadir nodo `transcribe_audio` en el flujo existente (p.ej. `Backend/src/flows/chat_flow.py`).
2. Nodo recibe `AudioStreamPayload` (referencia a archivo temporal o stream ID) y devuelve `TranscriptionResult`.
3. Enlazar con nodos actuales de intencion/respuesta; propagar `user_message` = texto transcrito.
4. Nodificar `synthesize_speech` tras obtener respuesta del LLM:
   - Usa `google.cloud.texttospeech.TextToSpeechAsyncClient`.
   - Configurar `voice={language_code: "es-ES", name: env.GOOGLE_TTS_VOICE}`.
   - Output en base64 o subir a `VOICE_STREAM_BUCKET` (pre-signed URL).

## 10. Frontend Next.js
1. Crear hook `Frontend/src/app/hooks/useVoiceStream.ts` que gestione:
   - Permiso microfono (`navigator.mediaDevices.getUserMedia`).
   - `MediaRecorder` con `mimeType: "audio/webm;codecs=opus"`.
   - Conversion a PCM antes de enviar (usar `@jsprism/opus-decoder` o enviar Opus y convertir server-side con `ffmpeg`).
   - WebSocket client con reconexion y heartbeat.
2. Actualizar componente de chat para mostrar:
   - Estado `grabando`, transcripcion parcial, loader mientras LangGraph responde.
   - Boton reproducir audio TTS (`<audio controls src={ttsUrl}>`).
3. Anadir fallback texto si microfono no disponible.

## 11. Pruebas
- **Backend unit** (`Backend/tests/voice/test_google_stt.py`): mocks de gRPC, verifica reintentos y parseo parciales.
- **E2E** (`run_e2e_ws.py`): script que envia WAV espanol y valida respuesta texto/audio.
- **Frontend**: pruebas RTL del componente de voz, mock WebSocket y estados de interfaz.
- **Performance**: stress test con `locust` o `k6` (simular sesiones simultaneas).

## 12. Observabilidad y Seguridad
- Registrar latencia STT/TTS, uso por usuario, codigos de error.
- `VoiceOrchestrator` emite `record_turn_event`/`record_error_event` con canal `voice`, trazando transcript y URL de audio.
- Sanitizar logs: nunca guardar audio sin consentimiento.
- Purgar blobs cada `X` minutos (cron job) o usar bucket con lifecycle <24h.
- Limitar tamano de audio recibido (p.ej. 5 minutos) y validar MIME.
- Anadir alertas en GCP por cuota y errores 5xx.

## 13. Despliegue
1. Ajustar `docker-compose.yml` para montar credenciales y exponer puerto WebSocket (Backend ya usa 8000, revisar CORS/ws).
2. Reconstruir y levantar despues de cambios:
   ```bash
   docker compose build
   docker compose up -d
   ```
3. Validar en entorno staging: comprobar latencia, calidad transcripcion y coste estimado.
4. Documentar proceso de rotacion de claves y plan de recuperacion ante failover (fallback a modo texto).

## 14. Roadmap Futuro (Opcional)
- Soporte multi-idioma (configurable por usuario).
- Normalizacion y diarizacion (Speech Adaptation con frases clave propias).
- Integrar subtitulos en tiempo real usando los parciales del STT.
- Evaluar caching TTS para respuestas repetidas.

---
Responsables sugeridos:
- Backend Voice Lead: coordina STT/TTS y LangGraph.
- Frontend Voice UX: experiencia de grabacion y reproduccion.
- Ops: credenciales, monitoreo y costes.

Tiempo estimado inicial: 7-10 dias habiles para MVP listo para produccion.
