# Repository Guidelines

Use this guide to onboard quickly and keep contributions consistent across the FastAPI backend and Next.js frontend.

## Project Structure & Module Organization
- `Backend/src` hosts FastAPI services, LangGraph flows, and agent utilities; mirrored tests live in `Backend/tests` with matching layouts.
- `Frontend` contains the Next.js app; runtime builds land in `Frontend/.next` and static exports in `Frontend/out` (both ignored by git).
- Shared tooling such as `capi_docker_manager.py`, `build_executable.py`, and docs live at the repo root; AI reference material sits in `AI/`.
- Keep generated binaries (e.g. `CapiLauncher.exe`) outside tracked directories to avoid sync conflicts.

## Build, Test, and Development Commands
- `pip install -r Backend/requirements.txt` installs backend dependencies after changes to `requirements.txt`.
- `npm install --prefix Frontend` bootstraps the React/Next.js toolchain.
- `pytest Backend/tests -q` runs backend regression suites; add `-k <pattern>` for targeted flows.
- `npm test --prefix Frontend` executes Jest and RTL suites for UI components.
- `docker compose up -d` launches the integrated stack locally for end-to-end verification.
- `pyinstaller --distpath . --workpath build_cache build/CapiAgentes_Docker_Manager.spec --clean` rebuilds the desktop Docker controller when shipping installers.

## Coding Style & Naming Conventions
- Python follows PEP 8 with black-compatible formatting; use snake_case for functions and PascalCase for classes.
- TypeScript relies on repo ESLint/Prettier rules; components end in `PascalCase.tsx` and hooks in `useCamelCase.ts`.
- Keep directory names lowercase or kebab-case; avoid spaces or absolute Windows paths in code or configs.

## Testing Guidelines
- Reuse pytest fixtures under `Backend/tests` for agent workflows; name suites `test_<feature>.py`.
- Frontend tests should cover interactive states and error handling with Jest + RTL; colocate specs beside components when practical.
- Exercise LangGraph flows, Docker orchestration, and regression scenarios before merging.

## Commit & Pull Request Guidelines
- Write commits in imperative mood (e.g. `feat: add semantic metrics collection`) and keep each change focused.
- Pull requests detail impact, link related issues, show backend/frontend test evidence, and include screenshots for UI updates.
- Update `.env.example` whenever configuration inputs evolve so reviewers can reproduce local environments.

## Security & Configuration Tips
- Never commit secrets or raw `.env` files; document variables in `.env.example` and share secrets through secure channels.
- Store installers or Docker artifacts outside the repo tree; verify Docker access with the desktop manager before release.
- Audit dependencies when bumping versions and record required migrations in `docs/`.
