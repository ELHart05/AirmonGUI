import os
import secrets

# Default off world-writable /tmp. /tmp/airmongui let a local user pre-create the
# directory (or plant symlinks) before the root backend started, and left captures
# world-readable. A private, root-owned state dir avoids both.
CAPTURE_DIR: str = os.environ.get("AIRMON_GUI_CAPTURE_DIR", "/var/lib/airmongui/captures")
CORS_ORIGINS: list[str] = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173"
).split(",")
API_HOST: str = os.environ.get("API_HOST", "127.0.0.1")
API_PORT: int = int(os.environ.get("API_PORT", "8000"))

# ── Authentication ────────────────────────────────────────────────────────────
# Every privileged endpoint requires this token in the `X-Auth-Token` header.
# Set it explicitly with AIRMON_GUI_AUTH_TOKEN, otherwise the backend generates a
# random token at startup and prints it once to the console. Only the operator
# who can read the server console (the person who launched the root process) sees
# it, which is what stops a blind local process or a hostile web page from driving
# the privileged API.
AUTH_TOKEN: str = os.environ.get("AIRMON_GUI_AUTH_TOKEN", "").strip()
AUTH_TOKEN_FROM_ENV: bool = bool(AUTH_TOKEN)
if not AUTH_TOKEN:
    AUTH_TOKEN = secrets.token_urlsafe(32)

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def is_loopback_host(host: str) -> bool:
    return host.strip().lower() in _LOOPBACK_HOSTS


# Origins allowed to open the WebSocket terminal. Defaults to the HTTP CORS list.
ALLOWED_WS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_WS_ORIGINS", ",".join(CORS_ORIGINS)).split(",")
    if origin.strip()
]


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


# The interactive terminal is an arbitrary-command shell, so it is off unless the
# operator opts in. Even then it stays closed while the backend runs as root,
# unless the break-glass flag is also set.
TERMINAL_ENABLED: bool = _is_truthy(os.environ.get("AIRMON_GUI_TERMINAL_ENABLED", ""))
ALLOW_TERMINAL_AS_ROOT: bool = _is_truthy(
    os.environ.get("AIRMON_GUI_ALLOW_TERMINAL_AS_ROOT", "")
)

# ── Resource limits ─────────────────────────────────────────────────────────--
# Cap the number of concurrently running tool processes so an authenticated
# caller cannot exhaust the host with scan/deauth/handshake/crack jobs.
MAX_ACTIVE_JOBS: int = int(os.environ.get("AIRMON_GUI_MAX_ACTIVE_JOBS", "8"))

# Directories a cracking wordlist may live in. A caller-supplied wordlist path
# must resolve inside one of these (or the capture directory). This blocks the
# arbitrary-file existence oracle the crack endpoint otherwise exposes.
WORDLIST_DIRS: list[str] = [
    os.path.abspath(path)
    for path in os.environ.get(
        "AIRMON_GUI_WORDLIST_DIRS", "/usr/share/wordlists:/usr/share/seclists"
    ).split(":")
    if path.strip()
]
