# Contributing to AirmonGUI

Thanks for helping improve AirmonGUI. This project touches wireless interfaces and
security tooling, so contributions should keep safety, clarity, and local-only defaults
front and center.

## Ground Rules

- Use AirmonGUI only for networks and devices you own or have explicit permission to test.
- Keep the backend bound to `127.0.0.1` by default.
- Do not add telemetry, remote command execution, or network exposure without a clear opt-in.
- Keep process-killing behavior targeted to the selected interface. Do not reintroduce a global
  `airmon-ng check kill` flow from the UI or default API path.
- Avoid committing generated folders such as `.venv/`, `node_modules/`, or `dist/`.

## Project Layout

- `backend/` - FastAPI API that wraps the aircrack-ng suite.
- `frontend/` - Vue 3 desktop-style control UI for the local backend.
- `website/` - React/Vite marketing and project website.

Each folder has its own README with setup, scripts, and maintenance notes.

## Local Setup

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
```

Website:

```bash
cd website
npm install
```

## Running Locally

Run the backend and frontend in separate terminals:

```bash
cd backend
source .venv/bin/activate
sudo -E .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

```bash
cd frontend
npm run dev
```

The app opens at `http://localhost:5173`. Backend Swagger docs are at
`http://127.0.0.1:8000/docs`.

Run the website separately:

```bash
cd website
npm run dev
```

The website opens at `http://localhost:8080`.

## Verification

Before submitting changes, run the checks that match the files you touched:

```bash
python -m compileall backend/app backend/main.py
```

```bash
cd frontend
npm run build
```

```bash
cd website
npm run lint
npm run build
```

If you cannot run a check because of missing system tools or hardware, mention that clearly
in your change notes.

## Backend Guidelines

- Validate all user-provided interface names, file names, MAC addresses, channels, and paths.
- Prefer existing helpers in `app/utils.py` for subprocess execution and path handling.
- Keep long-running commands in `app/state.py` through job records so they can be stopped.
- Preserve Swagger/OpenAPI descriptions when adding or changing endpoints.
- Keep `.env.example` updated when adding configuration.

## Frontend Guidelines

- Keep actions disabled while their request is in flight.
- Use shared composables for cross-view state such as interfaces, scan jobs, targets, and logs.
- Keep destructive or disruptive controls explicit and tied to the selected interface or job.
- Keep endpoint wrappers in `src/api/index.js` in sync with backend routes.

## Website Guidelines

- Keep the website focused on what AirmonGUI actually does today.
- Avoid implying unauthorized use or remote/cloud operation.
- Keep install and GitHub links current.
- Run `npm run lint` and `npm run build` after content or component changes.

## Pull Request Checklist

- The change is scoped and documented.
- Relevant README files were updated.
- `.env.example` was updated for new configuration.
- Swagger/OpenAPI docs remain accurate for backend API changes.
- Build or compile checks were run, or skipped with a clear reason.
- Security-sensitive behavior was reviewed for local-only and authorized-use assumptions.
