# Playbook: Release Process (CapiAgentes)

## 1. Preparacion tecnica
- [ ] Confirmar rama limpia y sincronizada con main.
- [ ] Actualizar dependencias controladas (`Backend/requirements.txt`, `Frontend/package.json`) solo si hay aprobacion.
- [ ] Regenerar artifacts `.zero`:
  ```powershell
  pwsh -NoProfile -File ./.zero/scripts/pipeline.ps1 -Deep
  ```
- [ ] Ejecutar `zerograh-validation.ps1 -Deep` y archivar resultado en la sesion de release.

## 2. Verificaciones backend
- [ ] `cd Backend && pytest`
- [ ] Revisar logs (`Backend/logs/`) tras pruebas locales.
- [ ] Ejecutar analisis de agentes clave: Summary, Branch, Anomaly, Desktop (usar endpoints o scripts).
- [ ] Verificar migraciones: `psql -f database/schema.sql` en entorno staging o herramienta equivalente.

## 3. Verificaciones frontend
- [ ] `cd Frontend && npm run lint`
- [ ] `npm run build`
- [ ] Smoke test de PantallaAgentes contra backend de staging (verificar WebSocket, graficos, privilegios).

## 4. Seguridad y compliance
- [ ] Revisar cambios en `agent_privileges.json` y `agents_registry.json` (no dejar privilegios elevados temporales).
- [ ] Confirmar backups recientes en `Backend/ia_workspace/data/backups/`.
- [ ] Auditar `.env` y `.env.example` (sin secretos reales).
- [ ] Validar reglas de logging (`logging_config.json`) y rotaciones.

## 5. Documentacion
- [ ] Actualizar notas de release en `docs/` o repositorio externo.
- [ ] Sincronizar `AI/` y `.zero/context/` si hay cambios arquitectonicos.
- [ ] Adjuntar resumen operativo en `/.zero/dynamic/sessions/YYYY-MM/DD-hhmm-release.md`.

## 6. ZeroGraph y artifacts
- [ ] Si la estructura cambio, generar `zerograph-delta-YYYY-MM-DD.json` y aplicar merge manual (con backup).
- [ ] Guardar referencias de validacion (`zero-circuit-report.md`, `health.md`).
- [ ] Confirmar que `conflictos.md` no reporta duplicados criticos.

## 7. Deployment
- [ ] Construir imagenes Docker si aplica: `docker-compose build`.
- [ ] Desplegar en staging y ejecutar smoke tests (REST + WebSocket + agentes principales).
- [ ] Confirmar integracion con base de datos y repositorios de datos.
- [ ] Recopilar metrica de inicio (tiempo de respuesta, errores) y compararla con release previo.

## 8. Go/No-Go
- [ ] Checklist completo sin pendientes criticos.
- [ ] Firmar aprobacion (humano responsable + seguridad si aplica).
- [ ] Comunicar release notes y cambios de privilegios a stakeholders.

## 9. Post-release
- [ ] Monitorear logs (`app.log`, `errors.log`, `api.log`) durante las primeras horas.
- [ ] Registrar incidentes o lecciones aprendidas en `/.zero/dynamic/analysis/`.
- [ ] Planificar tareas de seguimiento (tickets, retros, mejoras).

Ultima actualizacion: 2025-09-18.
