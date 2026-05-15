# AirmonGUI Frontend

Vue 3 control interface for the local AirmonGUI backend. It provides the operator UI for
monitor mode, scanning, deauthentication, handshake capture, cracking, captures, reports,
logs, and the integrated terminal.

## Stack

- Vue 3
- Vite 5
- Tailwind CSS 3
- lucide-vue-next

## Setup

```bash
cd frontend
npm install
```

## Running

Start the backend first on `127.0.0.1:8000`, then run:

```bash
npm run dev
```

Open `http://localhost:5173`.

The Vite dev server proxies:

- `/api/*` to `http://127.0.0.1:8000`
- `/ws/*` to `ws://127.0.0.1:8000`

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Start Vite dev server |
| `npm run build` | Build production assets into `dist/` |
| `npm run preview` | Preview the production build |

## Project Structure

```text
frontend/
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── src/
    ├── App.vue
    ├── main.js
    ├── api/
    │   └── index.js
    ├── assets/
    │   └── main.css
    ├── components/
    │   ├── AppSidebar.vue
    │   └── ToastContainer.vue
    ├── composables/
    │   ├── useCrack.js
    │   ├── useHandshake.js
    │   ├── useInterfaces.js
    │   ├── useLogs.js
    │   ├── useNav.js
    │   ├── useScan.js
    │   ├── useTarget.js
    │   └── useToast.js
    └── views/
        ├── CapturesView.vue
        ├── CrackView.vue
        ├── DeauthView.vue
        ├── HandshakeView.vue
        ├── LogsView.vue
        ├── MonitorView.vue
        ├── OverviewView.vue
        ├── ReportsView.vue
        ├── ScanView.vue
        ├── SignalView.vue
        └── TerminalView.vue
```

## Important Flows

- Interface state lives in `src/composables/useInterfaces.js`.
- Backend calls are centralized in `src/api/index.js`.
- The selected target is shared through `src/composables/useTarget.js`.
- Command output history is stored through `src/composables/useLogs.js`.
- Navigation is controlled by `src/composables/useNav.js`.

The release/check-kill action must always pass the selected interface. The UI disables
that action until an interface is selected, and the backend rejects requests without one.

## Build

```bash
npm run build
```

The output lands in `frontend/dist/`. The root `.gitignore` excludes `dist/`, so commit
source changes rather than built assets unless a release process explicitly asks for them.

## Maintenance Notes

- Keep route names in `src/api/index.js` aligned with the backend OpenAPI docs.
- Keep long-running actions guarded by loading states to avoid duplicate submissions.
- Prefer existing composables over adding duplicated view-local API state.
- Keep labels explicit for disruptive wireless actions.
