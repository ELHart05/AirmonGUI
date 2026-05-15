import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_HOST, API_PORT, CAPTURE_DIR, CORS_ORIGINS
from app.routes import airodump, aireplay, aircrack, captures, handshake, interfaces, terminal

os.makedirs(CAPTURE_DIR, exist_ok=True)

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
    description=(
        "REST + WebSocket API for the **aircrack-ng** wireless auditing suite.\n\n"
        "**Security note:** This API is intended to run on `127.0.0.1` only. "
        "All tool invocations require root privileges — run the backend as root "
        "or configure passwordless sudo for the specific binaries.\n\n"
        "Interactive Swagger UI: `/docs` · ReDoc: `/redoc` · OpenAPI JSON: `/openapi.json`"
    ),
    version="0.2.0",
    openapi_tags=_TAGS,
    contact={"name": "AirmonGUI", "url": "https://github.com/your-username/AirmonGUI"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    response_description="Returns version and status of the backend",
)
def health() -> dict:
    """Returns `{\"status\": \"ok\", \"version\": \"...\"}` — use this to verify the backend is reachable."""
    return {"status": "ok", "version": "0.2.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)
