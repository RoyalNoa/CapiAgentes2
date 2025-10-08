# Manual backend probes

Scripts para verificar el broadcast de eventos cuando el backend esta corriendo en localhost:8000.
No forman parte de la regresion automatica; ejecutalos como scripts con el servidor activo.

## Incluye
- `agent_events_manual.py`: escucha eventos por agente y los imprime en tiempo real.
- `all_agent_events_manual.py`: dispara multiples consultas y agrupa eventos finales.
- `saldo_palermo_manual.py`: valida el flujo de saldo de la sucursal Palermo.
- `run_e2e_ws.py`: ejercicio rapido contra `/ws` para validar el flujo E2E.
