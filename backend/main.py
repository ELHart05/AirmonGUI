import os
import signal
import subprocess
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_HOST, API_PORT, CAPTURE_DIR, CORS_ORIGINS
from app.models import HealthResponse
from app.routes import airodump, aireplay, aircrack, captures, handshake, interfaces, terminal
from app.state import JOBS

os.makedirs(CAPTURE_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """On shutdown, terminate any still-running tool processes and close their logs.

    aireplay-ng and aircrack-ng run in their own session (os.setsid), so they do not
    receive a terminal Ctrl-C and would otherwise keep running headless after the
    server stops or reloads.
    """
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
        "terminal is available over a WebSocket at `/ws/terminal` (not part of the HTTP schema)."
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
    allow_headers=["Content-Type"],
)

# Mount all route modules under /api
app.include_router(interfaces.router, prefix="/api")
app.include_router(airodump.router, prefix="/api")
app.include_router(aireplay.router, prefix="/api")
app.include_router(aircrack.router, prefix="/api")
app.include_router(captures.router, prefix="/api")
app.include_router(handshake.router, prefix="/api")
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


if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)
