import os
import signal
import subprocess
from contextlib import asynccontextmanager

import sys

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    API_HOST,
    API_PORT,
    AUTH_ENABLED,
    AUTH_TOKEN,
    AUTH_TOKEN_FROM_ENV,
    CAPTURE_DIR,
    CORS_ORIGINS,
    TERMINAL_ENABLED,
    is_loopback_host,
)
from app.models import HealthResponse
from app.routes import airodump, aireplay, aircrack, captures, handshake, interfaces, terminal
from app.security import require_token
from app.state import JOBS
from app.utils import ensure_capture_dir

# Captures and logs can hold handshakes, client MACs, and recovered passphrases.
# Default new files to owner-only (child tools like airodump-ng inherit this), and
# refuse to start on an unsafe capture directory.
os.umask(0o077)
ensure_capture_dir(CAPTURE_DIR)

# Fail closed when binding off loopback. With auth disabled the API is wide open,
# so that combination is refused outright. With auth enabled, require an explicit
# token rather than the auto-generated console-only one.
if not is_loopback_host(API_HOST):
    if not AUTH_ENABLED:
        raise RuntimeError(
            f"API_HOST={API_HOST!r} is not loopback and auth is disabled. Enable auth "
            "(AIRMON_GUI_AUTH_ENABLED=true) or bind to 127.0.0.1."
        )
    if not AUTH_TOKEN_FROM_ENV:
        raise RuntimeError(
            f"API_HOST={API_HOST!r} is not loopback. Set AIRMON_GUI_AUTH_TOKEN to an "
            "explicit secret before exposing the backend off 127.0.0.1, or bind to "
            "127.0.0.1."
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Print the generated token on startup; clean up tool processes on shutdown.

    aireplay-ng and aircrack-ng run in their own session (os.setsid), so they do not
    receive a terminal Ctrl-C and would otherwise keep running headless after the
    server stops or reloads.
    """
    if AUTH_ENABLED and not AUTH_TOKEN_FROM_ENV:
        print(
            "\n" + "=" * 70 + "\n"
            "AirmonGUI API token (generated for this run):\n\n"
            f"    {AUTH_TOKEN}\n\n"
            "Paste it into the AirmonGUI web UI when prompted. Set "
            "AIRMON_GUI_AUTH_TOKEN to pin a token across restarts.\n"
            + "=" * 70 + "\n",
            file=sys.stderr,
            flush=True,
        )
    yield
    for job in list(JOBS.values()):
        process = job.get("process")
        if process and process.poll() is None:
            try:
                if job.get("type") in ("deauth", "crack"):
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except (ProcessLookupError, OSError):
                    pass
            except (ProcessLookupError, OSError):
                pass
        log_handle = job.get("log_handle")
        if log_handle and not log_handle.closed:
            try:
                log_handle.close()
            except OSError:
                pass

_TAGS = [
    {
        "name": "interfaces",
        "description": (
            "Wireless interface enumeration and monitor-mode control. "
            "Wraps `airmon-ng` and optionally `nmcli`/`wpa_cli` for targeted process management."
        ),
    },
    {
        "name": "airodump",
        "description": (
            "Long-running `airodump-ng` scan jobs. Start a job, poll results, stop the job. "
            "Results are parsed from the live CSV file written by airodump-ng."
        ),
    },
    {
        "name": "aireplay",
        "description": (
            "Send deauthentication frames via `aireplay-ng --deauth`. "
            "The interface is tuned to the requested channel before the attack."
        ),
    },
    {
        "name": "handshake",
        "description": (
            "Targeted `airodump-ng` session locked to a BSSID/channel for WPA 4-way handshake capture. "
            "Poll the status endpoint to detect the handshake in the live cap file."
        ),
    },
    {
        "name": "aircrack",
        "description": (
            "Background `aircrack-ng` dictionary-attack jobs. "
            "Stream live log output and poll for a found/not-found result."
        ),
    },
    {
        "name": "captures",
        "description": (
            "Browse and delete files in the capture directory "
            f"(default: `{CAPTURE_DIR}`). Supports `.cap`, `.pcap`, `.csv`, `.ivs`, `.log`."
        ),
    },
]

app = FastAPI(
    title="AirmonGUI API",
    summary="REST and WebSocket API for the aircrack-ng wireless auditing suite.",
    description=(
        "Backend that drives the **aircrack-ng** suite (`airmon-ng`, `airodump-ng`, "
        "`aireplay-ng`, `aircrack-ng`) for the AirmonGUI front-end.\n\n"
        "### Typical workflow\n"
        "1. `GET /api/interfaces`, then `POST /api/monitor` to enable monitor mode.\n"
        "2. `POST /api/airodump/start` and poll `GET /api/airodump/results/{job_id}` to scan.\n"
        "3. `POST /api/handshake/start` and poll its status to capture a WPA handshake.\n"
        "4. `POST /api/aircrack/crack` and poll its status to recover the key.\n\n"
        "### Jobs\n"
        "The long-running tools run as background **jobs**. A start call returns a `job_id`; "
        "poll the matching status or results endpoint, then stop the job when you are done. "
        "Job state is kept in memory and is lost when the server restarts.\n\n"
        "### Authorization and security\n"
        "This API is meant to run on `127.0.0.1` only. Every tool needs root, so run the "
        "backend as root or grant passwordless sudo for the specific binaries. Use it only on "
        "networks you own or are explicitly authorized to test.\n\n"
        "### Interactive docs\n"
        "Swagger UI at `/docs`, ReDoc at `/redoc`, raw schema at `/openapi.json`. An interactive "
        "terminal over a WebSocket at `/ws/terminal` is on by default, gated by the API token and "
        "an allowed Origin; turn it off with `AIRMON_GUI_TERMINAL_ENABLED=0` (the token is not part "
        "of the HTTP schema)."
    ),
    version="0.2.0",
    openapi_tags=_TAGS,
    contact={"name": "AirmonGUI on GitHub", "url": "https://github.com/ELHart05/AirmonGUI"},
    license_info={
        "name": "MIT",
        "url": "https://github.com/ELHart05/AirmonGUI/blob/master/LICENSE",
    },
    servers=[{"url": "http://127.0.0.1:8000", "description": "Local backend (default)"}],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Auth-Token"],
)

# Every privileged router requires a valid token. The health check and the
# interactive docs stay open so the UI can confirm the backend is reachable.
_auth = [Depends(require_token)]
app.include_router(interfaces.router, prefix="/api", dependencies=_auth)
app.include_router(airodump.router, prefix="/api", dependencies=_auth)
app.include_router(aireplay.router, prefix="/api", dependencies=_auth)
app.include_router(aircrack.router, prefix="/api", dependencies=_auth)
app.include_router(captures.router, prefix="/api", dependencies=_auth)
app.include_router(handshake.router, prefix="/api", dependencies=_auth)

# The terminal is an arbitrary-command shell. Register it only when explicitly
# enabled; the route itself still checks the token, Origin, and root state.
if TERMINAL_ENABLED:
    app.include_router(terminal.router)  # WebSocket route — no /api prefix needed


@app.get(
    "/api/health",
    summary="Health check",
    tags=["interfaces"],
    response_model=HealthResponse,
    response_description="Returns version and status of the backend",
)
def health() -> dict:
    """Returns `{\"status\": \"ok\", \"version\": \"...\"}` — use this to verify the backend is reachable."""
    return {"status": "ok", "version": "0.2.0"}


@app.get(
    "/api/auth/status",
    summary="UI bootstrap flags",
    tags=["interfaces"],
    response_description=(
        "`{\"auth_required\": ..., \"terminal_enabled\": ...}` so the UI knows whether to "
        "prompt for a token and whether to show the terminal tab"
    ),
)
def auth_status() -> dict:
    """Open endpoint: tells the UI whether to show the unlock screen and the terminal tab."""
    return {"auth_required": AUTH_ENABLED, "terminal_enabled": TERMINAL_ENABLED}


@app.get(
    "/api/auth/verify",
    summary="Verify the API token",
    tags=["interfaces"],
    response_description="`{\"ok\": true}` when the supplied X-Auth-Token is valid",
)
def auth_verify(_: None = Depends(require_token)) -> dict:
    """Cheap endpoint the UI calls to confirm a pasted token before unlocking."""
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)
