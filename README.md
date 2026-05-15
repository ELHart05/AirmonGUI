# AirmonGUI

A locally-hosted graphical interface for the aircrack-ng wireless auditing suite.
AirmonGUI wraps `airmon-ng`, `airodump-ng`, `aireplay-ng`, and `aircrack-ng` behind a
REST API and presents them through a modern, single-page web application — removing the
need to remember command-line flags while keeping the full power of each tool accessible.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Folder Documentation](#folder-documentation)
- [Contributing](#contributing)
- [Security and Legal Notice](#security-and-legal-notice)

---

## Features

- **Monitor Mode Control** — Enable and disable monitor mode on the selected wireless interface; release interfering processes only for that interface so other adapters stay connected.
- **Network Scanning** — Launch `airodump-ng` capture jobs, track running scans, and browse discovered access points and clients in a live-updating table.
- **Deauthentication** — Send targeted or broadcast deauth frames against a specific BSSID, with automatic channel tuning so frames reach the target on its operating frequency.
- **Handshake Capture** — Run a guided capture workflow that combines `airodump-ng` and `aireplay-ng` to acquire a WPA/WPA2 handshake; auto-deauth triggers and handshake detection are built in.
- **Password Cracking** — Submit captured handshake files to `aircrack-ng` with a wordlist, monitor cracking progress via live log streaming, and stop jobs at any time.
- **Capture Management** — Browse, download, and delete `.cap` and `.csv` files stored in the server-side capture directory.
- **Session Persistence** — Interface selection and target context (BSSID, channel) are stored in `localStorage` and restored across page reloads.
- **Loading States** — Every asynchronous action exposes a loading indicator; buttons are disabled during in-flight requests to prevent duplicate submissions.

---

## Architecture

```
AirmonGUI
├── backend/          Python 3.11+ — FastAPI / Uvicorn / Pydantic v2
│   └── app/
│       ├── routes/   One module per tool (interfaces, airodump, aireplay, aircrack, handshake, captures)
│       ├── models.py Pydantic request/response models with input validation
│       ├── state.py  In-process job state (scan jobs, crack jobs)
│       ├── utils.py  subprocess helpers, sudo prefix logic
│       └── config.py Environment-variable driven configuration
├── frontend/         Vue 3 / Vite 5 / Tailwind CSS 3 / lucide-vue-next
│   └── src/
│       ├── views/    One component per workflow (Monitor, Scan, Deauth, Handshake, Crack, Logs, Overview)
│       ├── composables/  Shared reactive logic (useInterfaces, useScan, useCrack)
│       ├── components/   AppSidebar, ToastContainer
│       └── api/      Fetch wrappers around every backend endpoint
└── website/          React 18 / TypeScript / Vite 5 / Tailwind CSS / shadcn-style components
    └── src/
        ├── pages/    Landing and not-found pages
        ├── components/  Website sections and shared UI
        ├── hooks/    React hooks
        └── lib/      Website utilities
```

The backend exposes a REST API on `http://127.0.0.1:8000/api`. The frontend Vite dev
server runs on `http://localhost:5173` and proxies API calls to the backend. In
production, run `npm run build` and serve `frontend/dist/` from a static file server
alongside the backend. The `website/` folder is a separate public project site that runs
on `http://localhost:8080` during development.

---

## Requirements

### System

| Requirement | Notes |
|---|---|
| Linux (kernel 4.x+) | Tested on Kali Linux and Ubuntu 22.04 |
| Wireless adapter with monitor-mode support | |
| `aircrack-ng` suite | `airmon-ng`, `airodump-ng`, `aireplay-ng`, `aircrack-ng` must be on `$PATH` |
| `iwconfig` | Part of `wireless-tools`; used for channel tuning |
| Root privileges | Required by all aircrack-ng tools |

Install the aircrack-ng suite on Debian/Ubuntu-based distributions:

```bash
sudo apt update && sudo apt install aircrack-ng wireless-tools
```

### Backend

- Python 3.11 or later
- pip

### Frontend

- Node.js 18 or later
- npm 9 or later

### Website

- Node.js 18 or later
- npm 9 or later

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ELHart05/AirmonGUI.git
cd AirmonGUI
```

### 2. Set up the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Set up the frontend

```bash
cd ../frontend
npm install
```

### 4. Set up the website

```bash
cd ../website
npm install
```

---

## Running the Application

Both the backend and frontend must be running simultaneously in separate terminals.

### Backend (requires root)

```bash
cd backend
source .venv/bin/activate
sudo .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Running as root is required because `airmon-ng`, `airodump-ng`, and `aireplay-ng` all
require raw socket access. Alternatively, configure passwordless `sudo` for the specific
binaries and adjust `utils.py` accordingly.

### Frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in a browser. The interface communicates exclusively with
`127.0.0.1:8000` — no external network connections are made.

### Production build

```bash
cd frontend
npm run build   # outputs to frontend/dist/
```

Serve `dist/` with any static file server, or configure your web server to proxy
`/api/*` to the Uvicorn process.

### Website

The website is independent from the local control app:

```bash
cd website
npm run dev
```

Open `http://localhost:8080`.

Build it with:

```bash
npm run lint
npm run build
```

---

## Configuration

All backend settings are controlled through environment variables. Defaults are shown below.
Copy `backend/.env.example` to `backend/.env` if you want a local reference file, then export
the variables before starting Uvicorn. The backend reads from the process environment.

| Variable | Default | Description |
|---|---|---|
| `AIRMON_GUI_CAPTURE_DIR` | `/tmp/airmongui` | Directory where `.cap` and `.csv` files are written |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list of allowed CORS origins |
| `API_HOST` | `127.0.0.1` | Host the Uvicorn server binds to |
| `API_PORT` | `8000` | Port the Uvicorn server listens on |

Example — change the capture directory:

```bash
export AIRMON_GUI_CAPTURE_DIR=/home/user/captures
sudo -E .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

---

## Project Structure

```
AirmonGUI/
├── CONTRIBUTING.md
├── README.md
├── backend/
│   ├── .env.example             Documented environment variable template
│   ├── README.md                Backend-specific setup and API notes
│   ├── main.py                  Application entry point; registers routers, CORS, and OpenAPI docs
│   ├── requirements.txt
│   └── app/
│       ├── config.py            Environment variable configuration
│       ├── models.py            Pydantic models for all request/response types
│       ├── state.py             In-memory job registry
│       ├── utils.py             subprocess execution, sudo prefix, command validation
│       └── routes/
│           ├── interfaces.py    GET /interfaces, POST /monitor, POST /checkkill
│           ├── airodump.py      POST /airodump/start|stop, GET /airodump/results/{job_id}
│           ├── aireplay.py      POST /aireplay/deauth
│           ├── aircrack.py      POST /aircrack/crack, GET /aircrack/{job_id}/status
│           ├── handshake.py     POST /handshake/start, GET /handshake/{job_id}/status
│           └── captures.py      GET /captures, DELETE /captures/{filename}
├── frontend/
│   ├── README.md                Frontend-specific setup and maintenance notes
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── main.js
│       ├── App.vue              Root layout: responsive sidebar + router outlet
│       ├── api/
│       │   └── index.js         Typed fetch wrappers for every API endpoint
│       ├── composables/
│       │   ├── useInterfaces.js  Interface list, monitor mode, check-kill
│       │   ├── useScan.js        Scan job lifecycle and result polling
│       │   └── useCrack.js       Crack job lifecycle and log polling
│       ├── components/
│       │   └── AppSidebar.vue    Navigation sidebar with interface selector
│       └── views/
│           ├── OverviewView.vue
│           ├── MonitorView.vue
│           ├── ScanView.vue
│           ├── DeauthView.vue
│           ├── HandshakeView.vue
│           ├── CrackView.vue
│           └── LogsView.vue
└── website/
    ├── README.md                Website-specific setup and content notes
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── pages/
        ├── components/
        ├── hooks/
        └── lib/
```

---

## API Reference

All REST endpoints are prefixed with `/api`. A full interactive schema is available at
`http://127.0.0.1:8000/docs` (Swagger UI), `http://127.0.0.1:8000/redoc` (ReDoc), and
`http://127.0.0.1:8000/openapi.json` when the backend is running.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Server health check |
| GET | `/api/toolcheck` | Check that required aircrack-ng tools are installed |
| GET | `/api/interfaces` | List wireless interfaces |
| POST | `/api/monitor` | Start or stop monitor mode with `{ "interface": "wlan0", "action": "start" }` or `"stop"` |
| POST | `/api/checkkill` | Release interfering services for one selected interface only |
| GET | `/api/airodump/jobs` | List running and known capture jobs |
| POST | `/api/airodump/start` | Start an `airodump-ng` scan job |
| POST | `/api/airodump/stop` | Stop a running scan job by `job_id` |
| GET | `/api/airodump/results/{job_id}` | Retrieve parsed CSV scan results for a job |
| POST | `/api/aireplay/deauth` | Send deauthentication frames |
| POST | `/api/handshake/start` | Start a handshake capture session |
| GET | `/api/handshake/{job_id}/status` | Poll handshake detection status |
| POST | `/api/handshake/{job_id}/stop` | Stop a handshake capture session |
| POST | `/api/aircrack/crack` | Start an `aircrack-ng` wordlist job |
| GET | `/api/aircrack/validate` | Validate whether a capture contains a handshake |
| GET | `/api/aircrack/{job_id}/status` | Poll crack job status and recent log output |
| POST | `/api/aircrack/{job_id}/stop` | Stop a running crack job |
| GET | `/api/captures` | List capture files |
| GET | `/api/captures/cap` | List crackable `.cap`, `.pcap`, and `.ivs` files |
| DELETE | `/api/captures/{filename}` | Delete a capture file |

The integrated terminal WebSocket is available at `/ws/terminal`.

---

## Folder Documentation

- [Backend README](backend/README.md) — backend setup, configuration, routes, and safety notes.
- [Frontend README](frontend/README.md) — Vue app setup, scripts, structure, and UI maintenance notes.
- [Website README](website/README.md) — public website setup, scripts, structure, and content guidelines.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, verification commands, safety rules, and
pull request expectations.

---

## Security and Legal Notice

This tool is intended exclusively for authorized wireless security testing, research, and
educational use on networks you own or have written permission to audit. Unauthorized
interception of network traffic and deauthentication attacks are illegal in most
jurisdictions.

The authors accept no liability for misuse. By using this software you confirm that you
have obtained all necessary permissions for every network you interact with.

**Run only on localhost.** The default configuration binds both the API and the Vite dev
server to loopback addresses. Do not expose either service on a public or shared network
interface.
