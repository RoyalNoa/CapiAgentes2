# capi-mcp-server

Servidor MCP basado en STDIO para exponer utilidades de navegacion sobre el repositorio CAPI.

- Codigo fuente: `server.mjs`
- Documentacion detallada y pasos de configuracion: consulta `../docs/mcp-server.md`.

## Desarrollo rapido

```bash
npm install --prefix mcp
npm run --prefix mcp start
```

El script `start` lanza el servidor en modo STDIO listo para conectarse desde Codex, Claude Code u otros clientes MCP compatibles.
