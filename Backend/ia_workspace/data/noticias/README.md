# Datos del agente Capi Noticias

Este es el almacenamiento oficial de todas las corridas.

- `config.json`, `status.json`, `news_history.json`: configuracion y estado del scheduler.
- `runs/AAAA/MM/`: salidas completas de cada corrida (Markdown, JSON, indice diario `.index.jsonl` e `index.json` global).
- `segments/`: agregados curados para el siguiente agente (`daily.json`, `weekly.json`, `monthly.json`).

El directorio `agentes/capi_noticias/data/` ya no se utiliza; cualquier archivo previo fue migrado a esta ubicacion.
