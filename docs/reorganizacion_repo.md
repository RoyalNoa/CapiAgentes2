# Guia de limpieza y reorganizacion del repositorio

## Objetivo
Mantener la raiz del proyecto libre de artefactos temporales y ordenar la documentacion para que refleje la arquitectura actual.

## Acciones inmediatas
- Reubicar el codigo de `launcher/` a `desktop/launcher/` o `tools/launcher/` y eliminar los binarios generados (`dist/`, `build/`, `Capi Launcher.exe`).
- Limpiar caches locales (`.venv/`, `.pytest_cache/`, `__pycache__/`, `workspace/`, directorio `C/`) y mantenerlos ignorados por git.
- Revisar carpetas heredadas de asistentes (`.claude/`, `.zero/`) y retirarlas si no aportan valor operativo.
- Eliminar archivos puntuales (`_tmp_run.py`, `test_gui_with_icon.py`, `prompt_master.txt`, `request.json`, `request2.json`, `temp.txt`) o moverlos a `scripts/experimental/` si deben conservarse.

## Reorganizacion de docs/
- Unificar `docs/estructura.md` como fuente unica y eliminar `docs/estructura.txt`.
- Normalizar nombres en kebab-case sin espacios, por ejemplo `docs/architecture/cabeceras-aplicadas-informe.md`.
- Agrupar documentos por tema:
  - `docs/architecture/`: vistas de sistema y flujos (`estructura.md`, `orchestrator_roadmap.md`).
  - `docs/agents/`: catalogos y guias de agentes (`CatalogoAgentes.md`, `implementacion_primerAgente.md`).
  - `docs/process/`: guias operativas (`CREATE.md`, checklists).
  - `docs/roadmap/`: planes y MVP (`MVP pendiente.md`).
- Crear un `docs/README.md` que actue como indice y enlace a los subdirectorios.

## Tareas de seguimiento
- Actualizar `.gitignore` para cubrir binarios y caches que aun no esten listados.
- Documentar en `README.md` la ubicacion del nuevo modulo `desktop/launcher`.
- Revisar periodicamente la raiz del repo tras cada corrida de agentes para detectar residuos tempranamente.

## Estado y responsables
- Responsable sugerido: propietario del repositorio.
- Ventana recomendada: antes del proximo corte de release.
