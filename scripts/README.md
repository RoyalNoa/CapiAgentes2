# Scripts

Set mínimo de utilidades para ejecutar y detener el proyecto sin ruido extra.

## Disponibles

| Script | Descripción | Parámetros |
|--------|-------------|-----------|
| `stack.ps1` | Control unificado Docker: up/down/restart/install/ps/logs/health | `-Action up|down|restart|install|ps|logs|health -FrontendOnly -BackendOnly -NoCache -Prune -ForceRancher -Follow` |
| `dev.ps1` | Levanta backend + frontend local (sin Docker) | `-BackendOnly -FrontendOnly -Port -NoReload` |
| `stop-dev.ps1` | Detiene procesos locales en puertos estándar | `-Ports` |

Ejemplos:
# Scripts

Para Docker, usa únicamente el script raíz `start.ps1` en CAPI/.

## Uso

```powershell
./start.ps1 -Action up
./start.ps1 -Action install -NoCache -Prune
./start.ps1 -Action ps
./start.ps1 -Action logs -Follow
./start.ps1 -Action down
```

Notas:
- Backend: http://localhost:8000/health
- Frontend: http://localhost:3000
- Con Rancher Desktop, añade `-ForceRancher`.

### Verificación rápida
```powershell
Invoke-WebRequest http://localhost:8000/health
```

## Puertos por Defecto

- **Backend**: 8000
- **Frontend**: 3000
- **AI Workspace**: http://localhost:3000/workspace

---
Minimal y directo.