# Repository Guidelines

<<<<<<< HEAD
## Estructura del Proyecto y Organización de Módulos
- `Backend/src` concentra servicios FastAPI, flujos LangGraph y adaptadores; las pruebas espejo están en `Backend/tests`.
- `Frontend/src/app` aloja la app Next.js, con componentes en `components/`, hooks en `hooks/` y contextos en `contexts/`; el tablero en vivo se abastece desde `contexts/GlobalChatContext.tsx` y `components/chat/SimpleChatBox.tsx`.
- Archivos generados (`Frontend/.next`, `Frontend/out`, binarios como `CapiLauncher.exe`) permanecen fuera de Git.
- Scripts (`build_executable.py`, `capi_docker_manager.py`, `docker-compose.yml`) y documentación viven en la raíz; `AI/` guarda material de referencia.

## Comandos de Build, Test y Desarrollo
- `pip install -r Backend/requirements.txt` instala las dependencias del backend.
- `pytest Backend/tests -q` corre la regresión; combine con `-k` para escenarios puntuales.
- `npm install --prefix Frontend` prepara el toolchain de Next.js.
- `npm run dev --prefix Frontend` inicia el frontend con recarga; `npm run build --prefix Frontend` genera la versión productiva.
- `npm test --prefix Frontend` ejecuta la suite de Vitest que monitorea el chat y los hooks.
- `docker compose build frontend` y `docker compose up -d frontend` reconstruyen y exponen el tablero ChatDeVos.

## Estilo de Código y Convenciones de Nombres
- Python sigue PEP 8 y Black; módulos en `snake_case`, clases en `PascalCase`, constantes en `UPPER_SNAKE_CASE`.
- TypeScript se alinea con ESLint/Prettier (indentación 2 espacios). Componentes terminan en `PascalCase.tsx`, hooks en `useCamelCase.ts`.
- Evite textos hardcodeados en el UI: obtenga mensajes desde el orquestador o utilidades compartidas en `Frontend/src/app/utils`.

## Guía de Testing
- Reutilice fixtures de `Backend/tests/fixtures`; nombre suites `test_<feature>.py` y cubra LangGraph, endpoints y almacenamiento de sesiones.
- En frontend, ubique pruebas de Vitest junto al componente (`__tests__/`) para validar interacciones y streaming en tiempo real.
- Antes de publicar ejecute `pytest`, `npm test` y verifique `docker compose up -d` para confirmar eventos secuenciales.

## Commits y Pull Requests
- Redacte commits en modo imperativo (`feat: habilitar streaming de eventos`), cada uno con un objetivo claro.
- Las PR detallan impacto, enlazan issues, muestran evidencia (`pytest`, `npm test`, `docker compose up`) y capturas cuando hay cambios de UI.
- Actualice `.env.example` y la documentación en `docs/` al añadir variables o pasos de despliegue.

## Seguridad y Configuración
- No suba secretos ni `.env`; documente variables en `.env.example` y compártalas de forma segura.
- Mantenga fuera del repo los artefactos voluminosos (builds, sesiones).
- Audite dependencias al actualizarlas y registre migraciones en `docs/`.
=======
## Project Structure & Module Organization
- `Backend/src/`: FastAPI services, LangGraph flows, and adapter layers.
- `Backend/tests/`: Mirrors backend modules; reuse fixtures from `fixtures/`.
- `Frontend/src/app/`: Next.js app shell with `components/`, `hooks/`, `contexts/`.
- `Frontend/src/app/contexts/GlobalChatContext.tsx` and `components/chat/SimpleChatBox.tsx`: Power the live chat dashboard.
- Root: deployment scripts (`docker-compose.yml`, `build_executable.py`, `capi_docker_manager.py`) and docs; `AI/` holds architectural references.

## Build, Test, and Development Commands
- `pip install -r Backend/requirements.txt`: Install backend dependencies.
- `pytest Backend/tests -q`: Run the backend regression suite; add `-k name` for targeted cases.
- `npm install --prefix Frontend`: Prepare the Next.js toolchain.
- `npm run dev --prefix Frontend`: Launch the frontend with live reload.
- `npm run build --prefix Frontend`: Produce the production bundle.
- `npm test --prefix Frontend`: Execute the Vitest suite covering chat flows and hooks.
- `docker compose build frontend && docker compose up -d frontend`: Refresh and expose the ChatDeVos board.

## Coding Style & Naming Conventions
- Python: PEP 8, Black formatting; modules `snake_case.py`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- TypeScript: ESLint/Prettier, 2-space indentation; components `PascalCase.tsx`, hooks `useCamelCase.ts`.
- Avoid hardcoded UI strings—source them from orchestrators or `Frontend/src/app/utils`.

## Testing Guidelines
- Backend tests live beside features (`test_<feature>.py`); cover LangGraph paths, REST endpoints, and session storage.
- Frontend Vitest suites sit in `__tests__/` alongside components; validate streaming and user interactions.
- Before merging, run `pytest`, `npm test`, and verify `docker compose up -d` to ensure sequential event handling.

## Commit & Pull Request Guidelines
- Commits are imperative (e.g., `feat: habilitar streaming de eventos`) and scoped to one objective.
- Pull requests describe impact, link issues, and provide evidence (command output, screenshots for UI changes).
- Update `.env.example` and `docs/` whenever configuration or deployment steps change.

## Security & Configuration
- Never commit secrets or `.env` files; document required variables in `.env.example`.
- Keep generated artifacts (`Frontend/.next`, `Frontend/out`, binaries like `CapiLauncher.exe`) out of Git.
- Audit dependency updates and record migrations or schema changes in `docs/`.
>>>>>>> origin/develop
