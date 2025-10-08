# Repository Guidelines

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
