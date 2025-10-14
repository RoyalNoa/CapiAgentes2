# Eventos / Artefactos

- [X] `agent_start`: placeholder genérico.
- [X] `agent_end`: placeholder genérico.
- [ ] `node_transition`: llega, pero la simulación lo ignora.
- [X] `shared_artifacts` / `response_metadata`: contienen la tarea real (SQL, resultados, alertas, exports).

## Acción requerida
- Procesar `shared_artifacts` al construir la narrativa (ver `tablero/ChatEvents/README.md`).
- `agent_start`/`agent_end` sólo se usan como respaldo si faltan artefactos.
