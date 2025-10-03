<!-- @canonical true -->
# Guía Operativa - .Zero (CapiAgentes)

Objetivo: unificar cómo trabajar con `.zero` dentro del proyecto CapiAgentes. Esta guía define qué leer, dónde escribir y cómo mantener los artefactos sin generar deuda.

## 1. Fuentes de verdad
- Política obligatoria: `/.zero/policies/ai-behavior.md`.
- Contexto canónico: `/.zero/context/` (solo se edita cuando cambia la dirección del proyecto y siempre por instrucción humana explícita).
- Artefactos generados: `/.zero/artifacts/` (se regeneran con scripts, no se editan a mano).
- Playbooks y prompts: `/.zero/playbooks/`, `/.zero/prompts/`.
- Zona de trabajo IA/humano: `/.zero/dynamic/` (analysis, sessions, proposals, temp, papelera).

## 2. Principios clave
1. **Transparencia**: cada sesión deja evidencia (analysis o session note) si hubo cambios relevantes.
2. **Antiduplicados**: antes de crear archivos nuevos corre `pipeline.ps1` o revisa `conflictos.md`.
3. **Estructura**: el repositorio debe seguir `/.zero/context/ARCHITECTURE.md` y el ZeroGraph vigente.
4. **Backups**: cualquier archivo reemplazado se copia primero a `/.zero/dynamic/papelera/` con timestamp.
5. **Escala IA**: preferir actualizaciones incrementales (patches, diffs) y describir decisiones en la respuesta final.

## 3. Áreas de escritura
- **Permitido**: `/.zero/dynamic/**`, archivos de código/documentación cuando el ticket lo requiera.
- **Restringido**: `/.zero/context/**`, `AI/**`, `docs/**`. Solo se modifican con instrucción humana explícita (como esta adaptación).
- **Artefactos**: `/.zero/artifacts/**` se regeneran ejecutando scripts.

## 4. Sesiones y entregables
- `/.zero/dynamic/analysis/`: análisis temáticos (business, security, performance) con formato `YYYY-MM-DD-topic.md`.
- `/.zero/dynamic/sessions/YYYY-MM/`: bitácoras breves (`YYYY-MM-DD-hhmm-topic.md`).
  - Incluyen: acciones realizadas, comandos ejecutados, ubicación de salidas.
- `/.zero/dynamic/proposals/`: carpetas para parches (`patches/YYYY-MM-DD_HH-mm/` con diff, tests, rollback).
- `/.zero/dynamic/temp/`: staging para archivos temporales (limpiar al cerrar la sesión).
- `/.zero/dynamic/papelera/`: resguardo de archivos reemplazados (prefijo timestamp + ruta original).

## 5. Pipeline y artefactos
```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File ./.zero/scripts/pipeline.ps1 -Fast
pwsh -NoProfile -ExecutionPolicy Bypass -File ./.zero/scripts/pipeline.ps1 -Deep
```
Genera o actualiza:
- `estructura.txt`
- `conflictos.md`
- `scripts-health.md`
- `prompts-health.md`
- `catalog.md`
- `health.md`
- `ZeroGraph.json`

El modo `-Deep` ejecuta validaciones adicionales (`zerograh-validation`, `zero-circuit-validate` cuando estén disponibles).

## 6. Aplicar delta de ZeroGraph
1. Crear delta en `/.zero/dynamic/analysis/zerograph-delta-YYYY-MM-DD.json`.
2. Respaldar `ZeroGraph.json`:
   ```powershell
   $ts = Get-Date -Format 'yyyyMMdd-HHmmss'
   Copy-Item '.zero/artifacts/ZeroGraph.json' ".zero/artifacts/ZeroGraph.json.bak-$ts"
   ```
3. Aplicar merge manual (base vs delta) manteniendo IDs únicos y sin duplicar relaciones.
4. Ejecutar `./.zero/scripts/zerograh-validation.ps1 -Deep` para validar.
5. Documentar el cambio en `/.zero/dynamic/analysis/` o en la respuesta final.

## 7. Comandos útiles (PowerShell)
```powershell
# Crear directorios seguros
grid = '.zero/dynamic/papelera','.zero/dynamic/temp'
foreach ($dir in $grid) { if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null } }

# Buscar duplicados rápidos (por nombre)
Get-ChildItem -Recurse -File | Group-Object Name | Where-Object { $_.Count -gt 1 }

# Ver últimos artefactos
Get-Content '.zero/artifacts/conflictos.md' -TotalCount 60
Get-Content '.zero/artifacts/health.md' -TotalCount 80
```

## 8. Flujo recomendado por tipo de tarea
- **Actualizar contexto**: confirmar con humano, editar archivos canónicos, regenerar artefactos, anotar sesión.
- **Agregar agente**: seguir playbook, implementar código, agregar pruebas, correr pipeline y `pytest`, generar delta de ZeroGraph, registrar sesión.
- **Investigar bug**: correr pipeline (fast), revisar `conflictos.md`, dejar nota en `analysis/` o `sessions/` con hallazgos.
- **Frontend**: coordinar con `AI/Tablero/PantallaAgentes/`, actualizar `Frontend/`, ejecutar pipeline para revisar estructura.

## 9. Señales de stop
Detenerse y pedir claridad si:
- El pipeline reporta colisiones críticas que no puedes resolver sin borrar archivos.
- Falta permiso para escribir en la ruta requerida.
- Las instrucciones del usuario chocan con políticas (`ai-behavior.md`).
- ZeroGraph queda inconsistente tras un merge (la validación falla).

---
Última actualización: 18/09/2025
