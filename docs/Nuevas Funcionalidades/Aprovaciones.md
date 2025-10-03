# Aprobaciones Human-in-the-Loop

> Estado: **planeado**. El backend ya expone la interfaz (`POST /api/orchestrator/human/decision`) pero la integración frontend y las pantallas quedan pendientes.

## Contexto
- LangGraph detiene la ejecución en el nodo `human_gate` para esperar una decisión humana.
- El backend devuelve `meta.requires_human = true` y un vector `meta.interrupt` en cada `ResponseEnvelope` (las actualizaciones websocket también lo incluyen).
- Cuando un operador responde, se debe invocar el endpoint de reanudación con el payload adecuado.

## Endpoint a consumir
```
POST /api/orchestrator/human/decision
```
Payload:
```
{
  "session_id": "<id de sesión LangGraph>",
  "approved": true|false,
  "interrupt_id": "<opcional, si LangGraph especifica un id>",
  "message": "<opcional, mensaje mostrado al usuario>",
  "reason": "<opcional, justificación interna>",
  "approved_by": "<opcional, operador>",
  "metadata": { "...": "..." }  # opcional
}
```
Respuesta:
- `success`: bandera booleana.
- `decision`: payload sin valores nulos (útil para auditar).
- `resume_payload`: estructura enviada internamente al runtime.
- `response`: `ResponseEnvelope` serializado tras reanudar el grafo.

## Flujo UI propuesto
1. **Detección**: cualquier componente que lee `sessionState` debe marcar la sesión como “en espera” cuando `meta.requires_human` sea verdadero.
2. **Presentación**: mostrar la información relevante del primer elemento de `meta.interrupt` (ej. `value.context.reason`, `node`).
3. **Formulario de decisión**:
   - Botones “Aprobar” / “Rechazar”.
   - Campo opcional para comentario (`message`).
   - Campo opcional `reason` (motivo interno) y `approved_by` (operador).
   - Permitir adjuntar metadatos adicionales si el flujo lo requiere.
4. **Invocación**: al confirmar, enviar `fetch`/`axios` al endpoint anterior; los componentes deben incluir el token de sesión o cabeceras vigentes.
5. **Actualización en vivo**: tras la respuesta, vaciar el formulario; el WebSocket emitirá un update con `human_gate` marcado como completado y se debe refrescar la vista.
6. **Histórico (opcional)**: registrar las decisiones en la UI (ej. tabla o timeline) reutilizando `decision` y `resume_payload`.

## Puntos pendientes
- Definir qué componente del HUD mostrará la cola de aprobaciones (sugerido: panel lateral y badge en el nodo `human_gate`).
- Diseñar los estilos y tokens visuales para “espera de aprobación”.
- Revisar permisos/autenticación antes de habilitar el formulario.
- Añadir pruebas e2e una vez que la UI esté lista.

> Nota: no se implementó lógica en el frontend; este documento sólo describe los pasos para la próxima etapa.
