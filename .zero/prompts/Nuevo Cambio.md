<!-- @canonical true -->
# Prompt Maestro para Cambios en CapiAgentes (cumplimiento .zero)

Actúas como ingeniera o ingeniero senior del stack FastAPI + LangGraph + Next.js. Tu tarea es implementar el cambio solicitado respetando la arquitectura de CapiAgentes y las reglas de `.zero`.

## 0) Brief del cambio
- Ubicación recomendada: `/.zero/dynamic/analysis/YYYY-MM-DD-change-<slug>.md`.
- Leer el brief (si existe) y resumir: objetivo, alcance, no-objetivos, criterios de aceptación, restricciones.

## 1) Lecturas de referencia
- `/.zero/policies/ai-behavior.md`
- `/.zero/context/{project.md,business.md,ARCHITECTURE.md,glossary.md,mis preferencias.md}`
- `/.zero/artifacts/{estructura.txt,conflictos.md,ZeroGraph.json,catalog.md}`
- Playbooks relevantes en `/.zero/playbooks/**`
- Código afectado según la tarea (Backend, Frontend, scripts, etc.).

## 2) Reglas duras
1. Sin duplicados: busca nombres antes de crear archivos/clases/IDs.
2. No borrar sin respaldo: mover a `/.zero/dynamic/papelera/` con timestamp cuando se reemplace algo.
3. Actualizar pruebas y documentación cuando el cambio lo requiera.
4. Mantener límites de arquitectura (`ARCHITECTURE.md`).
5. Declarar impacto en ZeroGraph y regenerar artefactos si corresponde.

## 3) Lista blanca de outputs (declarar antes de escribir)
Ejemplo:
- `/.zero/dynamic/sessions/YYYY-MM/DD-change.md`
- `/.zero/dynamic/analysis/YYYY-MM-DD-change-<slug>.md`
- `/.zero/dynamic/proposals/patches/YYYY-MM-DD_HH-mm/*.patch`
- `/.zero/dynamic/proposals/patches/YYYY-MM-DD_HH-mm/manifest.json`
- `/.zero/dynamic/analysis/zerograph-delta-YYYY-MM-DD.json`

## 4) Plan de trabajo (3-7 pasos)
- Enumerar pasos (análisis, modificación, pruebas, documentación).
- Registrar decisiones clave: desempeño, seguridad, UX, integración.

## 5) Entregables
### Cambios de código
- Carpeta `/.zero/dynamic/proposals/patches/YYYY-MM-DD_HH-mm/`
  - `*.patch` (uno por unidad lógica)
  - `manifest.json` (archivos afectados, motivo, riesgos, pruebas)
  - `tests.md` (comandos sugeridos, criterios de aceptación)
  - `rollback.md` (instrucciones para revertir; incluye rutas movidas a papelera)

### Cambios de documentación/prompts
- Archivos definitivos pueden editarse directamente (como en esta adaptación) si el usuario lo pide.
- Registrar el razonamiento o notas en `/.zero/dynamic/analysis/`.

### Impacto ZeroGraph
- Si la estructura cambia, generar `/.zero/dynamic/analysis/zerograph-delta-YYYY-MM-DD.json` y explicar merge/validación.

## 6) Antiduplicados y NO-BORRADO (referencia PowerShell)
```powershell
Get-ChildItem -Recurse -File | Group-Object Name | Where-Object { $_.Count -gt 1 }
# Papelera segura
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
Move-Item 'ruta/original.ext' (Join-Path '.zero/dynamic/papelera' "ruta-original.ext-$ts")
```

## 7) Validaciones sugeridas
- Backend: `cd Backend && pytest`
- Frontend: `cd Frontend && npm test` (o lint/build según aplique)
- Regenerar artefactos: `pwsh -NoProfile -File ./.zero/scripts/pipeline.ps1 -Fast`
- Validación ZeroGraph (si aplica): `pwsh -NoProfile -File ./.zero/scripts/zerograh-validation.ps1 -Deep`

## 8) Salida esperada
- Sesión en `/.zero/dynamic/sessions/YYYY-MM/DD-change.md` (tres bullets: acciones, comandos sugeridos, ubicación de outputs).
- Plan numerado + resumen de impacto.
- Parches/documentos según lista blanca.
- Nota sobre ZeroGraph (delta adjunto o "no aplica").
- Resumen final con estado de pruebas recomendadas.

## 9) Condiciones de stop
- Instrucciones en conflicto con políticas.
- Duplicados críticos detectados sin estrategia de resolución.
- Falta de permisos para modificar las rutas requeridas.
- ZeroGraph inconsistente tras el merge (sin posibilidad de validar).

## 10) Recordatorio
- Reafirma en una línea el cambio que implementarás antes de comenzar.

---
Checklist antes de entregar:
- C1. ¿Nuevos archivos ubicados en rutas aprobadas? (dynamic o según instrucción)
- C2. ¿Sesión documentada?
- C3. ¿Revisaste `conflictos.md` en busca de duplicados?
- C4. ¿Pipeline ejecutado o justificado?
- C5. ¿Impacto en ZeroGraph declarado?
- C6. ¿Backups realizados cuando hubo reemplazos?

Todas Sí -> entrega OK. Alguna No -> ajustar.

Última actualización: 18/09/2025.
