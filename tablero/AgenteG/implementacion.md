# Agente G - Plan de Implementacion

## Contexto General
- Objetivo: incorporar un agente LangGraph con acceso a Google Drive, Gmail y Google Calendar, llamado **Agente G**.
- Estado actual del sistema: grafo dinamico con registro de agentes (`AgentRegistryService`) y orquestacion sobre LangGraph (`LangGraphRuntime`).
- Restriccion principal: la cuenta de Google es individual (no Workspace). Se usara OAuth 2.0 con refresh token almacenado en `secrets/`.

## Principios Clave
1. **Seguridad**: ningun secreto en el repositorio. El refresh token y el JSON de credenciales se guardan en `secrets/`. `.env` solo expone rutas/IDs.
2. **Trazabilidad**: cada accion de Agente G debe registrar identidad y scopes en `response_metadata` y `shared_artifacts` para auditoria.
3. **Integracion progresiva**: introducir primero polling de Gmail; preparar estructura para futuras notificaciones push.
4. **Cooperacion entre agentes**: usar `shared_artifacts` para compartir resultados con otros nodos, y `ia_workspace/data/agent-output/agente_g/` para archivos propios.
5. **Verificabilidad**: acompanar cada cambio con pruebas unitarias/integracion y actualizacion de docs.

## Variables y Credenciales
- `.env` (y `.env.example` con placeholders):
  ```
  GOOGLE_CLIENT_ID=...
  GOOGLE_CLIENT_SECRET=...
  GOOGLE_OAUTH_SCOPES=https://www.googleapis.com/auth/drive.file,https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/calendar.events
  GOOGLE_TOKEN_STORE=secrets/google-agente-g.json
  GOOGLE_GMAIL_PUSH_TOPIC=projects/tu-proyecto/topics/agente-g-gmail
  GOOGLE_GMAIL_PUSH_VERIFICATION_TOKEN=token_seguro_para_webhook
  GOOGLE_GMAIL_PUSH_LABEL_IDS=INBOX
  GOOGLE_GMAIL_PUSH_LABEL_ACTION=include
  GOOGLE_GMAIL_PUSH_MAX_HISTORY=50
  ```
- `secrets/google-agente-g.json`: contendra `{ "refresh_token": "...", "access_token": null, ... }` tras el bootstrap.
- Script de bootstrap (ver backlog) generara/actualizara ese JSON cifrado o plano segun se defina.

## Arquitectura del Agente
- **Node LangGraph**: `Backend/src/infrastructure/langgraph/nodes/agente_g_node.py`.
  - Extiende `GraphNode`, marca `_is_agent_node = True` para eventos.
  - Resuelve clientes de Drive/Gmail/Calendar usando los helpers Google.
  - Exponer acciones: enviar correo, listar correos, crear archivos/drive, crear eventos.
  - Valida scopes antes de cada accion, registra en `response_metadata` y `shared_artifacts`.
  - Ejecuta HumanGate cuando la accion es sensible (enviar correo, compartir archivos, agendar evento).
- **Handler (Dominio)**: `Backend/ia_workspace/agentes/agente_g/handler.py`.
  - Sigue el patron `BaseAgent`: procesa instrucciones para Gmail/Drive/Calendar y adjunta artefactos + metricas (`google_api_calls`, `duration_ms`, `scopes`).
- **Registro dinamico**:
  - Manifiesto en `Backend/ia_workspace/data/agents_registry.json`, toggles en `AgentConfigService` y soporte en `SemanticIntentService`/router.
  - Intents nuevos (`google_drive`, `google_gmail`, `google_calendar`) agregados a `IntentType`.
- **Token Tracking**: HUD y agentes UI ya muestran `agente_g` con color propio.

## Infraestructura Google
- Paquete `Backend/src/infrastructure/external/google/` con:
  - `auth.py`: carga `.env`, refresca/persistencia de tokens, fabrica servicios.
  - `gmail.py`, `drive.py`, `calendar.py`: operaciones encapsuladas para cada API.
- Script `scripts/bootstrap_google_oauth.py`: lanza flujo OAuth (local server o consola) y escribe el refresh token en `GOOGLE_TOKEN_STORE`.
- Manejo de rate limiting: los helpers soportan refresh automático; falta añadir retries exponenciales si aparece limit.

## Persistencia y Auditoria
- `shared_artifacts["agente_g"]`: almacena listas de correos, archivos o eventos con metadata minimal.
- `response_metadata` incluye `google_identity`, `agente_g_operation`, `google_metrics` (llamadas, scopes, duracion, etc.) y banderas de `requires_human_approval` para acciones sensibles.
- `SessionStorage` persiste todo al cierre de turno; no hay pasos adicionales.

## Backlog (prioridad descendente)
- [x] **Bootstrap credenciales**: script creado y documentado; genera `GOOGLE_TOKEN_STORE`.
- [x] **Infraestructura Google**: helpers de auth + Gmail/Drive/Calendar implementados.
- [x] **Nuevos intents**: `IntentType`, router semantico y fallback actualizados.
- [x] **Manifiesto y config**: `agents_registry.json`, `AgentConfigService`, toggles.
- [x] **LangGraph node**: `AgenteGNode` agregado al grafo estatico/dinamico.
- [x] **Handler Agente G**: operaciones basicas con metricas y artefactos.
- [x] **HumanGate**: acciones sensibles marcan `requires_human_approval`.
- [x] **Shared artifacts**: schema consistente por operacion.
- [x] **Tests**: unitarios del nodo + suites de integracion/routing actualizadas.
- [x] **Frontend**: HUD y pagina de agentes incluyen `agente_g`.
- [x] **Docs**: `docs/CatalogoAgentes.md` actualizado.
- [x] **Observabilidad**: `google_metrics` expuesto en metadata y payload.
- [x] **Push opcional**: integrar `users.watch` + Pub/Sub (handler + endpoints listos, pendiente validar en entorno real).

## Preguntas Abiertas
- Donde guardaremos el refresh token en produccion? (Por ahora `secrets/`, evaluar vault).
- Que nivel de logging necesitamos para operaciones Google (minimo info + error, sin datos sensibles).
- Se requerira multi-identidad (enviar como varias cuentas) en el futuro? Anticipar almacenamiento de tokens por usuario.
- Implementacion de notificaciones push (`users.watch` + Pub/Sub) queda como siguiente milestone.

## Proximos Pasos Inmediatos
1. Completar las variables reales en `.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_AGENT_EMAIL`) y ejecutar `python scripts/bootstrap_google_oauth.py` para generar `GOOGLE_TOKEN_STORE`.
2. Validar en entorno real que Agente G pueda listar/enviar correos, manipular Drive y crear eventos revisando `response_metadata.google_metrics`.
3. Diseñar la siguiente iteracion para notificaciones push (`users.watch` + Pub/Sub) segun el backlog pendiente.

---
**Ultima actualizacion:** 2025-10-02 -- Codex (GPT-5)
