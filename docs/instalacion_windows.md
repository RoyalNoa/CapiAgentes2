# Guia de instalacion en Windows desde cero

Este instructivo asume una instalacion limpia de Windows 11/10 con permisos de administrador.

## 1. Habilitar requisitos del sistema
1. Asegurate de que la virtualizacion este activa en BIOS/UEFI.
2. Habilita WSL2 y la plataforma de contenedores:
   ```powershell
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   ```
3. Reinicia el equipo para aplicar los cambios.

## 2. Instalar herramientas base (PowerShell con privilegios)
```powershell
winget install -e --id Git.Git             # Control de versiones
winget install -e --id Docker.DockerDesktop # Motor de contenedores (incluye WSL2 backend)
winget install -e --id Python.Python.3.11  # Python 3.11 64-bit
winget install -e --id OpenJS.NodeJS.LTS   # Node.js LTS (incluye npm)
winget install -e --id Microsoft.VisualStudioCode # Opcional, editor
```
> Abre Docker Desktop una vez finalizada la instalacion y habilita "Use WSL 2 based engine".

## 3. Clonar el repositorio
```powershell
cd C:\
mkdir Projects && cd Projects
git clone https://github.com/TU_ORG/CAPI.git
cd CAPI
```

## 4. Configurar variables de entorno
1. Duplica el archivo de ejemplo y completa tus claves:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Edita `.env` y define al menos:
   - `OPENAI_API_KEY`: tu clave de OpenAI (obligatoria para agentes LLM).
   - `SECRET_KEY` y `API_KEY_BACKEND`: genera valores propios.
   - `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`: credencial de uso del nuevo mapa Google (solo lectura del lado frontend).
   - Ajusta `CAPI_BACKEND_SRC` y `CAPI_IA_WORKSPACE` a tus rutas locales (usa `/` o `\`).
3. No compartas `.env`; contiene secretos.

## 5. Preparar entorno Backend
```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
cd ..
```
> El virtualenv queda ignorado por git (`.venv/`). Reactiva con `.\.venv\Scripts\Activate.ps1` cuando regreses.

## 6. Preparar Frontend
```powershell
npm install --prefix Frontend
```
Esto genera `Frontend/node_modules/` (ignorados por git).

## 7. Ajustes especificos (solo una vez)
- Revisa `docker-compose.yml` y cambia los mapeos de volumen que apunten a `C:/Users/lucas/...` por tu propio usuario.
- Si necesitas el launcher de escritorio, instala PyInstaller en el virtualenv: `pip install pyinstaller`.

## 8. Ejecutar con Docker (recomendado)
```powershell
./docker-commands.ps1 start   # Levanta PostgreSQL, backend y frontend
```
Servicios disponibles:
- Frontend: http://localhost:3000
- Backend API y docs: http://localhost:8000
detener: `./docker-commands.ps1 stop`
reiniciar: `./docker-commands.ps1 restart`

## 9. Ejecutar manualmente (opcional para desarrollo)
_Backend_
```powershell
cd Backend
.\.venv\Scripts\Activate.ps1
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
_Frontend_
```powershell
cd Frontend
npm run dev
```

## 10. Bases de datos y migraciones
- El servicio `postgres` se inicializa automaticamente con `Backend/database/schema.sql` y `seed_data.sql`.
- Los datos se persisten en el volumen Docker `postgres_data`. Reinicia limpio con `./docker-commands.ps1 clean` (borra datos).

## 11. Pruebas
```powershell
pytest Backend/tests -q
npm test --prefix Frontend
```

## 12. Launcher de escritorio (opcional)
```powershell
cd launcher
pip install -r requirements.txt
pyinstaller --distpath . --workpath build_cache pyinstaller/CapiAgentes_Docker_Manager.spec --clean
```
Guarda el `.exe` en la raiz del repo (`CAPI/CapiLauncher.exe`).

## 13. Buenas practicas de git
- Ejecuta `git status` antes de subir cambios.
- No confirmes binarios, `node_modules/`, virtualenvs ni caches (controlado por `.gitignore`).
- Mantén secretos fuera del repositorio; utiliza `.env.example` para documentar nuevas variables.

## 14. Troubleshooting rapido
- Docker no arranca: verifica que WSL2 este activo y reinicia Docker Desktop.
- Backend falla con OpenAI: confirma `OPENAI_API_KEY` y cuota en la cuenta.
- Cambios en `docker-compose.yml` sin efecto: ejecuta `docker compose build --no-cache` y luego `./docker-commands.ps1 restart`.

