# Funcionalidades backend pendientes de UI

- **Aprobaciones human-in-the-loop**: el backend puede pausar el LangGraph en el nodo `human_gate`, mostrar la solicitud al operador y reanudar o abortar según la decision que se envíe a `POST /api/orchestrator/human/decision`. Todavia falta disenar dónde y como se pedira esa aprobación en la interfaz.
- **Métricas y feedback**: `POST /api/feedback` ya guarda quien envió el comentario, en que canal, con que intención y la calificación. La UI aún no muestra estos datos ni ofrece un panel de analisis.
- **Visualizacion de flujos paralelos**: el router agrega `response_metadata.parallel_targets` cuando planea ejecutar dos nodos simultaneamente (por ejemplo `branch` y `anomaly`). Falta decidir en que parte del HUD se reflejara esa ruta paralela.

