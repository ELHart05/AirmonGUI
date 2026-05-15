import os
import re
import subprocess
import time

from fastapi import APIRouter, HTTPException

from ..config import CAPTURE_DIR
from ..models import AircrackRequest
from ..state import JOBS
from ..utils import command_prefix, new_job_id, safe_capture_path

router = APIRouter(prefix="/aircrack", tags=["aircrack"])

# Strip ANSI escape sequences and other terminal control chars from log output
_ANSI = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def _read_log(log_path: str) -> str:
    """Read a log file produced by aircrack-ng, strip control chars, return last 50 lines."""
    try:
        raw = open(log_path, "rb").read()  # noqa: WPS515
    except OSError:
        return ""
    text = raw.decode("utf-8", errors="replace")
    text = _ANSI.sub("", text)
    # aircrack-ng uses \r to overwrite the progress line; split on \r or \n
    segments = [s for s in re.split(r"\r\n|\r|\n", text) if s.strip()]
    return "\n".join(segments[-50:])


@router.post("/crack")
def start_aircrack(request: AircrackRequest) -> dict:
    """Launch aircrack-ng as a background job and return job_id for polling."""
    capture_path = request.capture_file
    if not os.path.isabs(capture_path):
        capture_path = safe_capture_path(capture_path)
    if not os.path.exists(capture_path):
        raise HTTPException(status_code=404, detail="Capture file not found")

    if not os.path.isabs(request.wordlist):
        raise HTTPException(status_code=400, detail="Wordlist must be an absolute path")
    wordlist_path = os.path.normpath(request.wordlist)
    if not os.path.exists(wordlist_path):
        raise HTTPException(status_code=404, detail="Wordlist not found")

    job_id = new_job_id()
    log_path = os.path.join(CAPTURE_DIR, f"crack_{job_id}.log")

    command = command_prefix() + ["aircrack-ng", "-w", wordlist_path]
    if request.bssid:
        command += ["-b", request.bssid]
    if request.channel:
        command += ["-c", request.channel]
    command.append(capture_path)

    log_handle = open(log_path, "wb")  # noqa: WPS515
    process = subprocess.Popen(command, stdout=log_handle, stderr=log_handle)

    JOBS[job_id] = {
        "type": "crack",
        "process": process,
        "command": " ".join(command),
        "log_path": log_path,
        "log_handle": log_handle,
        "start_time": int(time.time()),
        "capture_file": capture_path,
        "wordlist": wordlist_path,
    }

    return {"job_id": job_id, "command": " ".join(command)}


@router.get("/validate")
def validate_cap_file(path: str) -> dict:
    """
    Dry-run aircrack-ng on a cap file (no wordlist) to check whether it
    contains a captured WPA 4-way handshake.
    Returns {has_handshake, handshake_count, networks, no_eapol, raw}.
    """
    cap_path = path if os.path.isabs(path) else os.path.join(CAPTURE_DIR, path)
    if not os.path.exists(cap_path):
        raise HTTPException(status_code=404, detail="Capture file not found")

    try:
        result = subprocess.run(
            command_prefix() + ["aircrack-ng", cap_path],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    combined = result.stdout + result.stderr

    # Parse table lines: "  1  AA:BB:CC…  ESSID  WPA (N handshake)"
    networks = []
    for line in combined.splitlines():
        m = re.search(
            r"\d+\s+([0-9A-Fa-f:]{17})\s+(.*?)\s+WPA.*?\((\d+)\s+handshake",
            line,
        )
        if m:
            networks.append({
                "bssid": m.group(1),
                "essid": m.group(2).strip(),
                "handshake_count": int(m.group(3)),
            })

    has_handshake = any(n["handshake_count"] > 0 for n in networks)
    no_eapol = (
        "no eapol data" in combined.lower()
        or "packets contained no eapol" in combined.lower()
    )

    return {
        "has_handshake": has_handshake,
        "handshake_count": sum(n["handshake_count"] for n in networks),
        "networks": networks,
        "no_eapol": no_eapol,
        "raw": combined[:3000],
    }


@router.get("/{job_id}/status")
def crack_status(job_id: str) -> dict:
    """Poll the status of a running aircrack-ng job."""
    job = JOBS.get(job_id)
    if not job or job.get("type") != "crack":
        raise HTTPException(status_code=404, detail="Job not found")

    process = job.get("process")
    running = bool(process and process.poll() is None)
    returncode = process.poll() if process else None

    log_tail = _read_log(job.get("log_path", ""))

    # Detect key
    key_found = False
    key = None
    m = re.search(r"KEY FOUND!\s*\[\s*(.*?)\s*\]", log_tail)
    if m:
        key_found = True
        key = m.group(1)

    # If key found announce it and close log handle
    if key_found or (not running and returncode is not None):
        log_handle = job.get("log_handle")
        if log_handle and not log_handle.closed:
            log_handle.close()

    return {
        "job_id": job_id,
        "running": running,
        "returncode": returncode,
        "key_found": key_found,
        "key": key,
        "log_tail": log_tail,
        "elapsed": int(time.time()) - job.get("start_time", int(time.time())),
        "capture_file": job.get("capture_file"),
        "command": job.get("command"),
    }


@router.post("/{job_id}/stop")
def stop_crack(job_id: str) -> dict:
    """Terminate a running aircrack-ng job."""
    job = JOBS.get(job_id)
    if not job or job.get("type") != "crack":
        raise HTTPException(status_code=404, detail="Job not found")

    process = job.get("process")
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    log_handle = job.get("log_handle")
    if log_handle and not log_handle.closed:
        log_handle.close()

    return {"success": True, "job_id": job_id}
