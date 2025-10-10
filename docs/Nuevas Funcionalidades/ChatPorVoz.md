# Chat por voz bidireccional con LangGraph

## 1. Objetivo y resultado esperado
Implementar un modo de conversación por voz (input y output) sobre el stack actual:
- Captura de audio desde el frontend, transcripción en tiempo real (ASR) y envío al orquestador LangGraph.
- Respuesta del orquestador convertida a voz (TTS) con reproducción sincronizada y subtítulos.
- Modo demo listo para competencias: visualización del grafo, subtítulos y métricas de latencia/audio.

## 2. Arquitectura de alto nivel
1. **Frontend (Next.js)**
   - Servicio WebRTC/MediaRecorder para capturar audio.
   - WebSocket dedicado (`/ws/voice`) para streaming de audio y recepción de eventos.
   - Player HTML5 para respuesta TTS + overlay de subtítulos.
2. **FastAPI Backend**
   - Endpoint WebSocket `voice_router` que recibe audio (chunks PCM/Opus) y devuelve transcript incremental + respuestas.
   - Integración con proveedor ASR (Whisper local o API cloud) usando colas asincrónicas.
   - Hook con LangGraph (mismo `LangGraphRuntime`) para mantener contexto entre turnos.
   - Módulo TTS que sintetiza la respuesta, entrega URL/payload al frontend y almacena metadata.
3. **Servicios externos / microservicios**
   - ASR: OpenAI Whisper (local vía `whisper.cpp` o API GPT-4o-mini-transcribe), Azure Speech o Deepgram.
   - TTS: Amazon Polly, Azure Cognitive Services, ElevenLabs u OpenAI TTS.
4. **Storage y CDN**
   - Bucket S3/Azure Blob para almacenar audio de salida y logs de sesiones.
   - (Opcional) Redis para buffers y throttling.

## 3. Dependencias y preparación
### 3.1 Backend (FastAPI)
- Instalar paquetes base:
  ```bash
  pip install websockets soundfile pydub numpy aiofiles python-multipart
  ```
- Opcional según proveedor:
  - Whisper local: `pip install git+https://github.com/openai/whisper.git` y FFmpeg instalado.
  - Azure Speech: `pip install azure-cognitiveservices-speech`.
  - Amazon Polly: `pip install boto3`.
  - ElevenLabs: `pip install elevenlabs`.
- Actualizar `Backend/requirements.txt` y documentar variables `.env`:
  ```dotenv
  VOICE_MODE_ENABLED=true
  ASR_PROVIDER=whisper_local|azure|deepgram|openai
  TTS_PROVIDER=azure|polly|elevenlabs|openai
  ASR_API_KEY=...
  TTS_API_KEY=...
  AUDIO_BUCKET_URL=s3://capi-voice-demo
  ```

### 3.2 Infraestructura
- **FFmpeg** en el host o contenedor para conversiones (`apt-get install ffmpeg`).
- **GPU opcional** si se usa Whisper large local.
- Configurar bucket en S3/Azure Blob; otorgar credenciales con rol de escritura.
- (Opcional) Redis para colas / caching: `docker run -p 6379:6379 redis`.

### 3.3 Frontend
- Instalar soportes: `npm install --prefix Frontend recordrtc` (o usar API nativa `MediaRecorder`).
- Para streaming de audio a WebSocket usar `ws` en Node dev server y API nativa en browser (sin paquetes).

### 3.4 Proveedor TTS ElevenLabs (implementado)
- Configuración por variables de entorno:
  ```dotenv
  VOICE_TTS_PROVIDER=elevenlabs
  ELEVENLABS_API_KEY=tu_token
  ELEVENLABS_VOICE_ID=vgekQLm3GYiKMHUnPVvY
  ELEVENLABS_MODEL_ID=eleven_multilingual_v2
  # ELEVENLABS_VOICE_SETTINGS={"stability":0.4,"similarity_boost":0.7}
  ELEVENLABS_API_BASE_URL=https://api.elevenlabs.io
  ```
- `VOICE_TTS_PROVIDER` admite `google` (default) o `elevenlabs`. El backend selecciona dinámicamente el cliente TTS correcto al iniciar.
- `ELEVENLABS_VOICE_SETTINGS` acepta un JSON con los parámetros opcionales de la voz (stability, similarity, style, etc.).
- Tras modificar las variables, reiniciar el backend para que `VoiceOrchestrator` cargue el nuevo proveedor.

## 4. Backend paso a paso
1. **Crear módulo de configuración** `Backend/src/core/voice_config.py` que lea envs y normalice defaults.
2. **Agregar router WebSocket** en `Backend/src/api/main.py`:
   - Endpoint `/ws/voice` que acepta `client_id`, configura sesión en `LangGraphRuntime` y crea pipeline asincrónico.
3. **Pipeline ASR**
   - Crear `Backend/src/infrastructure/voice/asr_provider.py` con interfaz `transcribe_chunk(audio_bytes) -> str`.
   - Implementar adaptadores (WhisperLocalAdapter, AzureSpeechAdapter, etc.).
   - Manejar transcripción parcial (stream) vs. final: retornar `{'text': 'hola', 'is_final': False}`.
4. **Integración LangGraph**
   - Reutilizar memoria de sesión (`ConversationStateManager`). Cada transcripción final se envía via `runtime.process_query`.
   - Mantener `session_id` consistente con historial textual.
5. **Pipeline TTS**
   - `Backend/src/infrastructure/voice/tts_provider.py` con interfaz `synthesize(text, voice_id) -> bytes | url`.
   - Guardar audio en bucket y devolver URL; para modo demo rápido se puede devolver `base64` en la respuesta.
6. **Estructura WebSocket**
   - Mensajes entrantes: `{'type': 'audio_chunk', 'chunk_id': '...', 'payload': <base64 pcm>, 'sample_rate': 16000}`.
   - Eventos salientes:
     - `transcript_partial`: texto parcial (para subtítulos en vivo).
     - `transcript_final`: texto final + timestamp.
     - `llm_response`: payload LangGraph (texto, metadata, grafo, reasoning).
     - `tts_ready`: URL/base64 del audio sintetizado.
     - `telemetry`: latencias (ASR, LLM, TTS) para dashboard.
7. **Manejo de colas**
   - Usar `asyncio.Queue` para separar threads (captura -> ASR -> LLM -> TTS).
   - Considerar `asyncio.create_task` para pipeline sin bloquear WS.
8. **Logs y métricas**
   - Extend `get_logger` con `event: voice_pipeline_event`, `latency_ms`, `session_id`.
   - Exponer contador en `/api/metrics`: `voice_sessions_active`, `voice_avg_latency`.

## 5. Frontend paso a paso
1. **Hook `useVoiceChat`** (`Frontend/src/app/hooks/useVoiceChat.ts`):
   - Gestiona permisos micro (`navigator.mediaDevices.getUserMedia`).
   - Inicia `MediaRecorder` (audio/webm o pcm) y envía chunks al WebSocket.
   - Mapea mensajes WS a estado local: transcript parcial, transcript final, audio response.
2. **Componente `VoiceChatOverlay.tsx`**:
   - Botón `Hold to Talk` o toggle de grabación.
   - Barra de niveles de audio (analyzer node) + indicador de latencia.
   - Subtítulos en tiempo real (partial transcripts) y panel LangGraph (reuse `GlobalChatOverlay`).
   - Player `<audio src={ttsUrl} autoPlay />` con fallback de texto.
3. **Visualización**
   - Integrar con `event_broadcaster` para mostrar nodos activos mientras se reproduce audio.
   - Sincronizar subtítulos con timestamps (`requestAnimationFrame`).
4. **Fallback / errores**
   - Manejar `connection.status` (idle/connecting/reconnecting).
   - Mostrar mensajes en caso de latencia alta o ASR fallido.

## 6. Seguridad y gobernanza
- Sanitizar audio antes de enviar a servicios externos (reducir metadata).
- En el backend enmascarar credenciales de API en logs.
- Considerar anonimización de transcripciones si hay datos sensibles.
- Limitar duración de sesiones y tamaño de audio por chunk (ej: 2MB).
- TLS obligatorio para WebSocket wss://.

## 7. Pruebas y validación
1. **Unit tests**
   - Probar adaptadores ASR/TTS con mocks (`pytest` + `pytest-asyncio`).
   - Validar pipeline: chunks -> transcript -> LangGraph -> TTS.
2. **Integration tests**
   - Script `tests/integration/test_voice_pipeline.py` que alimenta audio sample y verifica respuesta.
   - Utilizar clips WAV con frases conocidas.
3. **Performance**
   - Medir latencia end-to-end (< 2.5s ideal). Logging con `processing_time_ms`.
4. **UX testing**
   - Verificar comportamientos en Chrome, Edge, Safari (MediaRecorder compatibilidad).
   - Probar con red limitada (modo offline + reconexión).

## 8. Roadmap incremental
1. **MVP (2-3 semanas)**
   - Whisper API o Azure Speech + Polly (cloud), WebSocket streaming, UI básica con subtítulos.
2. **Optimización**
   - Caching de prompts, ajuste de voces TTS, soporte de múltiples idiomas (config en LangGraph).
3. **Modo demo avanzado**
   - Playback sincronizado con visualización de grafo en 3D, scoreboard de latencias, grabación de sesión en video.
4. **Evolución**
   - Integrar diarización (identificar locutor), comandos por voz para controlar UI (abrir paneles, cambiar dataset).

## 9. Recursos sugeridos
- Whisper docs: <https://platform.openai.com/docs/guides/speech-to-text>
- Azure Speech SDK: <https://learn.microsoft.com/azure/ai-services/speech-service/>
- Amazon Polly: <https://docs.aws.amazon.com/polly>
- Ejemplos WebRTC/MediaRecorder: <https://developer.mozilla.org/docs/Web/API/MediaRecorder>
- Referencia LangGraph + audio streaming (repos community) para ideas de visualización.

Siguiendo estos pasos el equipo puede habilitar un canal de chat por voz completamente integrado, listo para demostraciones de innovación y extensible a nuevos canales (call center, kioskos, dispositivos IoT).
