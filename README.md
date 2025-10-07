# CapiAgentes - Multi-Agent Financial Platform

## Command shortcuts

### Windows (PowerShell)
```powershell
./docker-commands.ps1 start    # Start full stack
./docker-commands.ps1 stop     # Stop containers
./docker-commands.ps1 restart  # Restart without rebuilding
./docker-commands.ps1 rebuild  # Rebuild images and restart
./docker-commands.ps1 logs     # Tail container logs
./docker-commands.ps1 status   # Show running services
./docker-commands.ps1 clean    # Remove containers and data
```

### Linux / macOS (Bash)
```bash
./docker-commands.sh start
./docker-commands.sh stop
./docker-commands.sh restart
./docker-commands.sh rebuild
./docker-commands.sh logs
./docker-commands.sh status
./docker-commands.sh clean
```

## Local endpoints
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Health check: http://localhost:8000/api/health
- Elastic Observability (Kibana): http://localhost:5601

## Repository layout (working)
```
CAPI/
|-- docker-commands.ps1      # Windows orchestration helper
|-- docker-commands.sh       # Unix orchestration helper
|-- docker-compose.yml       # Compose definition for the stack
|-- Backend/                 # FastAPI services, LangGraph runtime, tests
|-- Frontend/                # Next.js app source (no build artifacts tracked)
|-- docs/                    # Architecture, process and agent documentation
|-- scripts/                 # Tooling and automation helpers
`-- launcher/                # Desktop launcher source (Tkinter, PyInstaller)
```

> El build usa la carpeta `build_cache` dentro del proyecto como temporal y deja el ejecutable directamente en la raiz del repo. Mantene virtualenvs, caches y `__pycache__` fuera del control de versiones.

## Desktop launcher
- Source lives in `launcher/` while a permanent home under `desktop/launcher/`
  is being prepared.
- Run `launcher/scripts/Build Launcher.bat` to regenerate the executable.
- El script de build (`launcher/scripts/Build Launcher.bat`) deja el `.exe` actualizado en la raiz (`CapiLauncher.exe`). Si queres archivarlo en otro lugar, movelo manualmente despues del build.

## Documentation entry points
- `docs/README.md`: overview of available documents
- `docs/reorganizacion_repo.md`: checklist for cleaning the repository root
- `docs/Nuevas Funcionalidades/LoggingJSON.md`: guía para logging JSON + stack Elastic
- `docs/mcp-server.md`: instrucciones para instalar y conectar el servidor MCP local

## Quick start
1. Run the platform with `./docker-commands.ps1 start` (Windows) or
   `./docker-commands.sh start` (Linux / macOS).
2. Open http://localhost:3000 to access the UI.
3. Use `./docker-commands.ps1 stop` or `./docker-commands.sh stop` when done.

### Required local paths and secrets
- Define `HOST_DESKTOP_PATH` in `.env` so the backend container can access the
  Windows desktop when executing Capi Desktop operations (defaults to the
  current machine path).
- Place the Google Cloud voice credentials under `secrets/voice-streaming-sa.json`
  (same file used by the launcher) or update `GOOGLE_APPLICATION_CREDENTIALS`
  to point elsewhere. The compose file mounts it read-only at
  `/run/secrets/voice-streaming-sa.json`.
- A local `voice_cache/` directory is created automatically to persist streamed
  audio chunks when using the voice chat pipeline.

One command, one action. Keep generated files out of `CAPI/`.

## Unified logging
- Backend y agentes escriben en `logs/backend.log` mediante el formateador `[YYYY-MM-DD HH:MM:SS] [Backend] [LEVEL] [logger] mensaje`.
- El frontend parchea `console.*` (ver `Frontend/src/app/utils/logger.ts`) para emitir `[timestamp] [Frontend] [LEVEL]` y alinear los eventos con el backend.
- Todas las llamadas a `print` se redirigen automáticamente al logger backend, por lo que no es necesario mantener múltiples archivos de log.

- Backend y agentes escriben exclusivamente en `logs/backend.log` mediante el formateador `[YYYY-MM-DD HH:MM:SS] [Backend] [LEVEL] [logger] mensaje contexto`.
