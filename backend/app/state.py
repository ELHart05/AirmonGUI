import threading
from typing import Dict

# In-memory store for background jobs (airodump-ng processes, etc.)
JOBS: Dict[str, dict] = {}

# Serializes read-modify-write on JOBS entries. FastAPI serves the sync route
# handlers on a threadpool, so concurrent status polls can otherwise race the
# deauth auto-restart guard and spawn orphaned processes.
JOBS_LOCK = threading.Lock()
