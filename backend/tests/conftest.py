"""
Shared test setup.

These env vars must be set before `import main`, which imports `app.config` at
module load. Tests run as an unprivileged user with no wireless hardware, so we
pin a known token and point the capture directory at a private temp dir.
"""
import os
import tempfile

os.environ.setdefault("AIRMON_GUI_AUTH_TOKEN", "test-token-please-change")

_CAPTURE_DIR = os.path.join(tempfile.gettempdir(), "airmongui_test_captures")
os.makedirs(_CAPTURE_DIR, mode=0o700, exist_ok=True)
os.chmod(_CAPTURE_DIR, 0o700)
os.environ.setdefault("AIRMON_GUI_CAPTURE_DIR", _CAPTURE_DIR)
