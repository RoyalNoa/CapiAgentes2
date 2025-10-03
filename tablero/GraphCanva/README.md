# Tablero - GraphCanva

## Guardrails obligatorios
- No asumir ni inferir requisitos fuera de este tablero y del blueprint en `docs/Nuevas Funcionalidades/grafo_n8n_blueprint.md`.
- Consultar siempre los archivos de referencia descargados de n8n en `tablero/GraphCanva/references/` antes de codificar.
- Si falta informacion o hay conflicto entre fuentes, detenerse y escalar al responsable antes de continuar.
- Prohibido renombrar campos existentes en `GraphState` o cambiar contratos API sin documentar impacto y obtener aprobacion.
- Mantener compatibilidad con la infra actual (FastAPI + LangGraph en backend, Next.js + React en frontend) y seguir PEP8/ESLint.

## Tasks
- [Task 01](./01_backend_contratos.md) - Normalizar contratos de grafo y catalogos.
- [Task 02](./02_backend_ejecucion_push.md) - Orquestacion, ejecucion y streaming de estado.
- [Task 03](./03_frontend_canvas.md) - Canvas interactivo estilo n8n en Next.js.
- [Task 04](./04_quality_adopcion.md) - Quality, pruebas y adopcion gradual.

Orden sugerido: Task 01 -> Task 03 en paralelo con Task 02 (sin romper contratos) -> Task 04.

Consulta obligatoria: [N8N algorithms](./references/n8n_algorithms.md) para entender las rutinas que se deben adaptar.
