import os

CAPTURE_DIR: str = os.environ.get("AIRMON_GUI_CAPTURE_DIR", "/tmp/airmongui")
CORS_ORIGINS: list[str] = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173"
).split(",")
API_HOST: str = os.environ.get("API_HOST", "127.0.0.1")
API_PORT: int = int(os.environ.get("API_PORT", "8000"))
