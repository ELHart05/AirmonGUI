from typing import Dict

# In-memory store for background jobs (airodump-ng processes, etc.)
JOBS: Dict[str, dict] = {}
