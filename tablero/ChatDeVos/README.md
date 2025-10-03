# Tablero ChatDeVos

## Objetivo General
Integrar entrada y salida de voz en tiempo real en el chat existente utilizando Google Cloud Speech-to-Text y Text-to-Speech, manteniendo la arquitectura FastAPI + LangGraph + Next.js.

## Estado Actual
- Evaluacion de proveedores completada; se selecciono Google Cloud para STT/TTS.
- Servicios backend (STT/TTS, almacenamiento local y WebSocket `/api/voice/stream`) implementados en entorno local.
- Hook frontend `useVoiceStream` y panel de voz integrados en SimpleChatBox; boton de microfono iconico reintegrado y `appendExternalMessage` listo para canal voz.
- Guardas de duracion y metricas de voz implementadas; pruebas locales cubren limite de captura y advertencias.
- Suite Vitest para `useVoiceStream` cubre advertencias/errores y confirma manejo de cliente.
- Aprovisionamiento GCP completado: proyecto `capi-473913`, APIs Speech/TTS/Storage habilitadas y service account `voice-streaming-sa` activa.
- Credenciales montadas como secreto Docker (`/run/secrets/voice-streaming-sa.json`) y variables `.env` actualizadas para voz.
- Nodos LangGraph `voice_transcription` y `voice_synthesis` integrados al flujo principal para propagar metadata de voz.
- Pipeline Docker recompilado y contenedores levantados con credenciales reales (STT/TTS listos para pruebas).
- Script scripts/run_voice_e2e.py corrido contra backend dockerizado; respuesta de voz y audio base64 devueltos sin errores de encoding.

## Tablero de Tareas
| ID | Tarea | Responsable sugerido | Detalle | Estado | ETA estimada |
|----|-------|----------------------|---------|--------|--------------|
| T1 | Crear proyecto y claves GCP | Ops (usuario) | Alta de proyecto, habilitar APIs Speech/TTS/Storage, generar service account `voice-streaming-sa`, definir budgets. | Completado | 1 dia |
| T2 | Montar secretos en entorno Docker | Ops + Backend | Guardar JSON de credenciales fuera del repo, definir secretos en docker-compose, actualizar `.env.example`. | Completado | 0.5 dia |
| T3 | Preparar dependencias backend | Backend | Actualizar `requirements.txt`, Dockerfile e imagen base con libs de audio. | Completado | 0.5 dia |
| T4 | Endpoint WebSocket FastAPI | Backend | Implementar `/api/audio/stream`, colas async, autenticacion y envio de parciales. | Completado | 2 dias |
| T5 | Cliente gRPC Google STT | Backend | Servicio `google_stt.py`, manejo de reintentos, normalizacion audio. | Completado | 1 dia |
| T6 | Nodo LangGraph transcribe_audio | Backend | Canal "voice" propagado en LangGraph; falta evaluar nodos dedicados. | Completado | 1 dia |
| T7 | Nodo LangGraph synthesize_speech | Backend | Metadata de audio expuesta a LangGraph/voz; pendiente evaluar nodo especifico. | Completado | 1 dia |
| T8 | Hook Next.js `useVoiceStream` | Frontend | Captura microfono, WebSocket, estados UI y fallback. | Completado | 1.5 dias |
| T9 | UI Chat con control de voz | Frontend | Boton sin texto para grabar/detener, parciales visibles y respuesta TTS; falta validacion UX. | En validacion | 1 dia |
| T10 | Almacenamiento temporal audio | Backend/Ops | Definir bucket o almacenamiento local, lifecycle <24h. | Completado | 0.5 dia |
| T11 | Observabilidad y alertas | Ops + Backend | Metricas Prometheus, logs estructurados, alertas de cuota. | En validacion | 1 dia |
| T12 | Bateria de pruebas (unit/E2E) | QA + Backend + Frontend | Tests gRPC mock, E2E ws, RTL frontend, stress; E2E Google ok, falta reparar `test_langgraph_integration`. | En validacion | 1.5 dia |
| T13 | Revision de seguridad y compliance | Ops | Politicas de retencion, manejo PII, documentacion. | Pendiente | 0.5 dia |
| T14 | Deploy en staging y smoke tests | Backend + Frontend | Validar latencia, WER, reproducciones, costes. | Pendiente | 1 dia |
| T15 | Preparar runbook y handoff | Ops + Producto | Documentar procedimiento, incidencias y plan de fallback. | Pendiente | 0.5 dia |

## Bloqueos y Solicitudes
- Validar costos y cuotas GCP tras habilitar STT/TTS (definir budgets y alertas).
- Confirmar estrategia de almacenamiento temporal: bucket GCS vs. filesystem + purga programada.
- Coordinar validaciones de compliance/PII antes de habilitar grabacion en entornos productivos.
- Corregir corrupcion en `Backend/ia_workspace/agentes/agente_g/__init__.py` para que vuelvan a pasar los tests `test_langgraph_integration`.
## Registro de Avances
- 2025-09-28: Creado tablero `README.md` y documento tecnico `google_voice_streaming.md`.
- 2025-09-29: Servicios STT/TTS implementados, WebSocket `/api/voice/stream` y panel de voz en SimpleChatBox.
- 2025-09-30: Reincorporado boton de microfono sin texto, manejador de turnos de voz vinculado al chat global y hook expuesto para canal voz.
- 2025-09-30: Se agregaron limites de duracion, metricas Prometheus y pruebas WebSocket para el stream de voz.
- 2025-10-02: Nodos LangGraph de transcripcion y sintesis de voz agregados; pruebas unitarias `test_voice_nodes.py` creadas.
- 2025-10-02: GCP aprovisionado, service account `voice-streaming-sa` configurada, credenciales montadas en Docker y `docker compose build && up -d` ejecutados con exito.
- 2025-10-02: Corregido `google_tts` para entornos sin enums, `pytest Backend/tests/voice -q` en verde y E2E de voz completado contra backend actualizado.
- (Agregar nuevas entradas a medida que avance el desarrollo).

## Referencias
- Guia tecnica detallada: `tablero/ChatDeVos/google_voice_streaming.md`
- Repositorio backend/frontend: ver README principal del proyecto.

## Proximos Pasos Inmediatos
1. Ejecutar pruebas end-to-end con Google STT/TTS en entorno dockerizado y medir latencia/costos (T12/T14).
2. Completar observabilidad/alertas para voz (T11) con las nuevas metricas y monitoreo de cuotas.
3. Avanzar con revision de seguridad/compliance y runbook (T13/T15) tras validar el flujo de voz.



