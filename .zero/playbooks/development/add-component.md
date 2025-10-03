# Playbook: Agregar Componente / Feature (CapiAgentes)

## Checklist previo
- [ ] Leer `/.zero/context/project.md`, `business.md`, `ARCHITECTURE.md`.
- [ ] Revisar `/.zero/artifacts/estructura.txt` y `conflictos.md` (evitar duplicados).
- [ ] Consultar `AI/Tablero/PantallaAgentes/` si impacta UI.
- [ ] Confirmar nivel de privilegio requerido (agents, API, DB).

## 1. Analisis y diseno
- Identificar capa afectada (Backend domain/application/infrastructure/presentation, ia_workspace, Frontend).
- Mapear dependencias existentes; validar ley de dependencias.
- Definir contratos (pydantic schemas, TypeScript types, interfaces) antes de codificar.
- Evaluar impacto en ZeroGraph y documentacion.

## 2. Implementacion Backend
- Crear/modificar modulos dentro de la capa correcta.
- Agregar validaciones de entrada (pydantic, typing) y logging estructurado.
- Actualizar servicios/orquestador si el flujo involucra nuevos nodos o agentes.
- Respetar privilegios: verificar `agents_registry.json`, `agent_privileges.json` y APIs correspondientes.

## 3. Implementacion Frontend (si aplica)
- Crear componentes en `Frontend/src/app` o `Frontend/src/components` siguiendo tokens de estilo.
- Mantener sincronizados los tipos con DTOs backend (`Frontend/src/app/types`).
- Integrar WebSocket o REST a traves de `Frontend/src/app/services`.

## 4. Pruebas
```powershell
# Backend
cd Backend
pytest -q

# Frontend (si aplica)
cd ../Frontend
npm test
```
- Agregar tests unitarios y de integracion. Para nuevos agentes: minimo 1 unit + 1 integration (`Backend/tests/`).
- Documentar comandos utilizados en `tests.md` dentro de la propuesta.

## 5. Documentacion y ZeroGraph
- Actualizar especificaciones pertinentes (`AI/`, `.zero/context/`) solo si cambia el modelo.
- Generar delta de ZeroGraph si aparecen nodos/relaciones nuevas.
- Registrar sesion en `/.zero/dynamic/sessions/YYYY-MM/DD-hhmm-add-component.md`.

## 6. Validaciones finales
```powershell
pwsh -NoProfile -File ./.zero/scripts/pipeline.ps1 -Fast
pwsh -NoProfile -File ./.zero/scripts/zerograh-validation.ps1 -Deep  # si hubo delta
```
- Revisar `conflictos.md` para confirmar que no aparecieron duplicados.
- Verificar logs relevantes en `Backend/logs/` si el cambio corre localmente.

## 7. Checklist de termino
- [ ] Codigo ubicado en capas correctas.
- [ ] Tests nuevos o actualizados y comandos documentados.
- [ ] Documentacion/ZeroGraph sincronizados.
- [ ] Sesion y analisis guardados en `.zero/dynamic/`.
- [ ] Riesgos o pendientes explicitados en la respuesta final.

Ultima actualizacion: 2025-09-18.
