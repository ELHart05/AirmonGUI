# AirmonGUI Backend

FastAPI backend for AirmonGUI. It exposes a local REST and WebSocket API that wraps
`airmon-ng`, `airodump-ng`, `aireplay-ng`, and `aircrack-ng`.

## Responsibilities

- List wireless interfaces and detect monitor-mode state.
- Start or stop monitor mode on a selected interface.
- Stop processes that interfere with monitor mode (global `airmon-ng check kill`).
- Run `airodump-ng`, handshake capture, deauth, and cracking jobs.
- Manage capture files in the configured capture directory.
- Serve Swagger UI at `/docs`, ReDoc at `/redoc`, and OpenAPI JSON at `/openapi.json`.

## Requirements

- Linux
- Python 3.11+
- `aircrack-ng` suite on `$PATH`
- `wireless-tools` for `iwconfig`
- Root privileges or passwordless sudo for the required wireless tooling

Install system tools on Debian/Ubuntu-based distributions:

```bash
sudo apt update
sudo apt install aircrack-ng wireless-tools
```

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Settings come from environment variables. On startup the backend also loads `backend/.env`
if present, so you can drop values there instead of exporting them; a variable already set in
the shell wins over the file. Copy `.env.example` to `.env` to get started, or point
`AIRMON_GUI_ENV_FILE` at another path (set it empty to skip the file entirely).

## Configuration

| Variable | Default | Description |
|---|---|---|
| `AIRMON_GUI_CAPTURE_DIR` | `/var/lib/airmongui/captures` | Directory for capture, CSV, and log output |
| `AIRMON_GUI_AUTH_ENABLED` | `true` | Set to `false` to drop the token requirement (loopback only) |
| `AIRMON_GUI_AUTH_TOKEN` | _(generated)_ | API token; generated and printed at startup if unset |
| `AIRMON_GUI_TERMINAL_ENABLED` | `1` | Token-gated `/ws/terminal` shell; set to `0` to remove the route and hide the tab |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated browser origins allowed by CORS |
| `API_HOST` | `127.0.0.1` | Uvicorn bind host |
| `API_PORT` | `8000` | Uvicorn bind port |

See `.env.example` for the full list, including the resource limits and wordlist directories.

## Running

```bash
cd backend
source .venv/bin/activate
sudo -E .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/api/health`

## API Overview

All REST endpoints are under `/api`.

While auth is enabled (the default), every endpoint except `/api/health` and `/api/auth/status`
needs the `X-Auth-Token` header. Swagger UI's Authorize button sends it for you.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Backend health and version (no token) |
| `GET /api/auth/status` | Whether auth and the terminal are enabled (no token) |
| `GET /api/auth/verify` | Confirm the supplied token is valid |
| `GET /api/toolcheck` | Check required aircrack-ng tools |
| `GET /api/interfaces` | List wireless interfaces |
| `POST /api/monitor` | Start or stop monitor mode |
| `POST /api/checkkill` | Run global `airmon-ng check kill` to stop interfering processes |
| `GET /api/airodump/jobs` | List capture jobs |
| `POST /api/airodump/start` | Start a scan job |
| `POST /api/airodump/stop` | Stop a scan job |
| `GET /api/airodump/results/{job_id}` | Poll parsed scan results |
| `POST /api/aireplay/deauth` | Send deauth frames |
| `POST /api/handshake/start` | Start targeted handshake capture |
| `GET /api/handshake/{job_id}/status` | Poll handshake state |
| `POST /api/handshake/{job_id}/stop` | Stop handshake capture |
| `POST /api/aircrack/crack` | Start cracking job |
| `GET /api/aircrack/validate` | Validate a capture file |
| `GET /api/aircrack/{job_id}/status` | Poll cracking job |
| `POST /api/aircrack/{job_id}/stop` | Stop cracking job |
| `GET /api/captures` | List capture files |
| `GET /api/captures/cap` | List crackable captures |
| `DELETE /api/captures/{filename}` | Delete a capture file |

The integrated terminal uses `WS /ws/terminal`.

## Project Structure

```text
backend/
├── .env.example
├── main.py
├── requirements.txt
└── app/
    ├── config.py
    ├── models.py
    ├── state.py
    ├── utils.py
    └── routes/
        ├── aircrack.py
        ├── aireplay.py
        ├── airodump.py
        ├── captures.py
        ├── handshake.py
        ├── interfaces.py
        └── terminal.py
```

## Verification

```bash
python -m compileall app main.py
```

For API schema checks, run the backend and open `/docs` or fetch `/openapi.json`.

## Safety Notes

Keep the API local-only unless you have a very explicit reason to do otherwise. Wireless
commands require elevated privileges and can disrupt connectivity. The check-kill endpoint
runs a global `airmon-ng check kill`, which stops NetworkManager and similar services
across the system, so use it only when those services are blocking monitor mode.
