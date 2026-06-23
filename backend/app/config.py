import os
import secrets


def _load_env_file(path: str) -> None:
    """Load KEY=VALUE lines from a .env file into the environment.

    A real exported variable always wins (we never overwrite one that is already
    set). Kept dependency-free and deliberately simple: blank lines and whole-line
    `#` comments are skipped, and a single matched pair of surrounding quotes is
    stripped. Inline trailing comments are not supported — keep comments on their
    own line, since a `#` can be a legitimate character inside a value.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip one matched pair of surrounding quotes, leaving any quote that is
        # part of the value itself intact.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("\"", "'"):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


# Auto-load backend/.env so the documented variables actually take effect without
# exporting them by hand. Set AIRMON_GUI_ENV_FILE to point elsewhere, or to an
# empty string to skip loading (the test suite does this to stay hermetic).
_DEFAULT_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
_ENV_FILE = os.environ.get("AIRMON_GUI_ENV_FILE", _DEFAULT_ENV_FILE)
if _ENV_FILE:
    _load_env_file(_ENV_FILE)


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Default off world-writable /tmp. /tmp/airmongui let a local user pre-create the
# directory (or plant symlinks) before the root backend started, and left captures
# world-readable. A private, root-owned state dir avoids both.
CAPTURE_DIR: str = os.environ.get("AIRMON_GUI_CAPTURE_DIR", "/var/lib/airmongui/captures")
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
API_HOST: str = os.environ.get("API_HOST", "127.0.0.1")
API_PORT: int = int(os.environ.get("API_PORT", "8000"))

# ── Authentication ────────────────────────────────────────────────────────────
# Auth is on by default. Set AIRMON_GUI_AUTH_ENABLED=false to drop the token
# requirement entirely (e.g. a single-user box on loopback where the prompt is
# just friction). With auth off, the privileged API is open to anything that can
# reach it, so the backend refuses to bind off loopback in that mode.
AUTH_ENABLED: bool = _is_truthy(os.environ.get("AIRMON_GUI_AUTH_ENABLED", "true"))

# The token that guards every privileged endpoint when auth is enabled. Set it
# explicitly with AIRMON_GUI_AUTH_TOKEN, otherwise the backend generates a random
# token at startup and prints it once to the console. Only the operator who can
# read the server console sees it, which is what stops a blind local process or a
# hostile web page from driving the privileged API.
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

# The interactive terminal is on by default. AIRMON_GUI_TERMINAL_ENABLED is the
# single switch: turn it off and the route is not mounted and the UI hides the
# tab. While auth is enabled the token (and Origin check) gate the socket, the
# same token that already guards the root-capable API.
TERMINAL_ENABLED: bool = _is_truthy(os.environ.get("AIRMON_GUI_TERMINAL_ENABLED", "true"))

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
