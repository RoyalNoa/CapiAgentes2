# Pipeline .Zero - Proyecto CapiAgentes

Sistema de colaboración entre IAs para la plataforma financiera multiagente. Sigue estas indicaciones para ejecutar análisis, mantener el contexto y apoyar el desarrollo.

## Inicio rápido

### Ejecución automática (scripts)
```powershell
# Regenerar estructura + reportes de salud (modo rápido)
pwsh -NoProfile -ExecutionPolicy Bypass -File ./.zero/scripts/pipeline.ps1 -Fast

# Pasada profunda (incluye análisis de duplicados y validación de ZeroGraph)
pwsh -NoProfile -ExecutionPolicy Bypass -File ./.zero/scripts/pipeline.ps1 -Deep
```

### Análisis manual (IA)
1. Lee `/.zero/context/` para comprender objetivos, arquitectura y preferencias.
2. Revisa los artefactos recientes en `/.zero/artifacts/` (estructura.txt, conflictos.md, ZeroGraph.json, health.md).
3. Usa los prompts de `/.zero/prompts/` para estructurar análisis detallados.
4. Escribe hallazgos o cambios en `/.zero/dynamic/analysis/` siguiendo el formato `YYYY-MM-DD-*`.

## Mapa de directorios
```
/.zero/
    artifacts/   # Salidas generadas (estructura.txt, conflictos.md, ZeroGraph.json, health.md)
    context/     # Documentación canónica (proyecto, negocio, arquitectura, glosario, preferencias)
    dynamic/     # Espacio escribible para IA (analysis, sessions, proposals, temp)
    playbooks/   # Procedimientos de desarrollo y operación
    policies/    # Reglas obligatorias para colaboradores IA
    prompts/     # Plantillas de prompts (ZeroGraph, detectores de errores, propuestas de cambio)
    scripts/     # Utilidades de automatización (pipeline, estructura, conflictos, validaciones)
    README.md    # Esta guía
```

## Flujo de trabajo
1. **Regenerar artefactos**
   - Ejecuta `./.zero/scripts/pipeline.ps1` después de cambios estructurales.
   - `estructura.txt` captura el árbol del proyecto.
   - `conflictos.md` detecta duplicados por nombre o contenido.
2. **Analizar y documentar**
   - Usa los prompts para revisar lógica de negocio, seguridad o rendimiento.
   - Guarda resultados en `/.zero/dynamic/analysis/` (un archivo por foco, con fecha).
3. **Actualizar ZeroGraph**
   - Genera un delta (`zerograph-delta-YYYY-MM-DD.json`) con nodos/relaciones nuevas.
   - Genera un respaldo antes de fusionar `ZeroGraph.json`.
4. **Sincronizar contexto**
   - Ante cambios de rumbo, edita `/.zero/context/*` (curado por humanos) para mantener la fuente de verdad.

## Artefactos en `artifacts/` (no editar manualmente)
- `estructura.txt` - instantánea de estructura.
- `conflictos.md` - análisis de duplicados.
- `scripts-health.md` - inventario y estado de scripts.
- `prompts-health.md` - cobertura de prompts.
- `catalog.md` - catálogo combinado de scripts y prompts.
- `health.md` - resumen de salud.
- `ZeroGraph.json` - representación del grafo del proyecto.

## Casos de uso
- **Antes de refactorizar**: ejecuta el pipeline, revisa estructura y conflictos, planifica ajustes.
- **Tras agregar un agente**: actualiza contexto si aplica, regenera artefactos, crea delta de ZeroGraph y registra el análisis.
- **Preparación de release**: corre el pipeline en modo Deep, revisa conflictos, verifica prompts/scripts y crea resumen de sesión.

## Notas de configuración
- Los scripts excluyen directorios pesados (`node_modules`, `.venv`, `.next`, `__pycache__`, artefactos de build`).
- Ajusta exclusiones en `./.zero/scripts/estructura.ps1` cuando aparezcan nuevas carpetas generadas.
- Validaciones adicionales están en `zerograh-validation.ps1` (se ejecuta en modo Deep).

## Solución de problemas
- **ExecutionPolicy**: ejecuta `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` una vez.
- **Artefactos desactualizados**: confirma que los scripts tienen permisos para escribir en `/.zero/artifacts/`.
- **Conflictos en ZeroGraph**: crea un respaldo con fecha antes de editar y aplica el delta manualmente.

Última actualización: 18/09/2025 (curado por humanos).
