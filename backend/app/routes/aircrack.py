import os
import re
import signal
import subprocess
import time

from fastapi import APIRouter, HTTPException, Path, Query

from ..config import CAPTURE_DIR
from ..models import (
    AircrackRequest,
    CrackJobsResponse,
    CrackStartResponse,
    CrackStatusResponse,
    ErrorResponse,
    JobActionResponse,
    ValidateResponse,
)
from ..state import JOBS
from ..utils import command_prefix, new_job_id, safe_capture_path

router = APIRouter(prefix="/aircrack", tags=["aircrack"])

# Strip ANSI escape sequences and other terminal control chars from log output
_ANSI = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def _start_process(command: list[str], log_handle) -> subprocess.Popen:
    return subprocess.Popen(command, stdout=log_handle, stderr=log_handle, preexec_fn=os.setsid)


def _stop_process(process: subprocess.Popen, timeout: int = 10) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=timeout)


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


@router.get(
    "/jobs",
    summary="List crack jobs",
    response_model=CrackJobsResponse,
    response_description="All known aircrack-ng jobs, newest first",
)
def list_crack_jobs() -> dict:
    jobs = []
    for job_id, job in JOBS.items():
        if job.get("type") != "crack":
            continue
        process = job.get("process")
        running = bool(process and process.poll() is None)
        jobs.append({
            "job_id": job_id,
            "running": running,
            "returncode": process.poll() if process else None,
            "command": job.get("command"),
            "log_path": job.get("log_path"),
            "start_time": job.get("start_time"),
            "capture_file": job.get("capture_file"),
            "wordlist": job.get("wordlist"),
        })
    jobs.sort(key=lambda item: item.get("start_time") or 0, reverse=True)
    return {"jobs": jobs}


@router.post(
    "/crack",
    summary="Start a dictionary attack",
    response_model=CrackStartResponse,
    response_description="The job id and the aircrack-ng command that was launched",
    responses={
        400: {"model": ErrorResponse, "description": "Wordlist must be an absolute path"},
        404: {"model": ErrorResponse, "description": "Capture file or wordlist not found"},
        409: {"model": ErrorResponse, "description": "An aircrack-ng job is already running"},
    },
)
def start_aircrack(request: AircrackRequest) -> dict:
    """
    Launch `aircrack-ng` against a capture and wordlist as a background job. Only one
    crack job runs at a time. Poll `GET /api/aircrack/{job_id}/status` for progress and
    the recovered key.
    """
    for job in JOBS.values():
        process = job.get("process")
        if job.get("type") == "crack" and process and process.poll() is None:
            raise HTTPException(status_code=409, detail="An aircrack-ng job is already running")

    # Always confine the capture file to CAPTURE_DIR (safe_capture_path rejects
    # absolute paths and traversal that resolve outside the directory).
    capture_path = safe_capture_path(request.capture_file)
    if not capture_path.lower().endswith((".cap", ".pcap", ".pcapng", ".ivs")):
        raise HTTPException(status_code=400, detail="Capture must be a .cap/.pcap/.pcapng/.ivs file")
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
    try:
        process = _start_process(command, log_handle)
    except Exception:
        log_handle.close()
        raise

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


@router.get(
    "/validate",
    summary="Check a capture for a handshake",
    response_model=ValidateResponse,
    response_description="Whether the capture holds a WPA handshake, with per-network counts",
    responses={
        404: {"model": ErrorResponse, "description": "Capture file not found"},
        500: {"model": ErrorResponse, "description": "aircrack-ng could not be run"},
    },
)
def validate_cap_file(
    path: str = Query(
        ...,
        description="Absolute path, or a file name inside the capture directory, to inspect.",
        examples=["handshake-OfficeNet-01.cap"],
    ),
) -> dict:
    """
    Dry-run `aircrack-ng` on a capture (no wordlist) to report whether it contains a
    WPA 4-way handshake, without starting a crack job.
    """
    # Confine to CAPTURE_DIR — same containment as start_aircrack.
    cap_path = safe_capture_path(path)
    if not cap_path.lower().endswith((".cap", ".pcap", ".pcapng", ".ivs")):
        raise HTTPException(status_code=400, detail="Capture must be a .cap/.pcap/.pcapng/.ivs file")
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


@router.get(
    "/{job_id}/status",
    summary="Poll a crack job",
    response_model=CrackStatusResponse,
    response_description="Live state, elapsed time, log tail, and the recovered key when found",
    responses={404: {"model": ErrorResponse, "description": "Job not found"}},
)
def crack_status(
    job_id: str = Path(..., description="Crack job id from POST /api/aircrack/crack"),
) -> dict:
    """Poll a running aircrack-ng job. `key_found` flips to true and `key` is populated once recovered."""
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


@router.post(
    "/{job_id}/stop",
    summary="Stop a crack job",
    response_model=JobActionResponse,
    responses={404: {"model": ErrorResponse, "description": "Job not found"}},
)
def stop_crack(
    job_id: str = Path(..., description="Crack job id to stop"),
) -> dict:
    """Terminate a running aircrack-ng job and close its log file."""
    job = JOBS.get(job_id)
    if not job or job.get("type") != "crack":
        raise HTTPException(status_code=404, detail="Job not found")

    process = job.get("process")
    if process:
        _stop_process(process)

    log_handle = job.get("log_handle")
    if log_handle and not log_handle.closed:
        log_handle.close()

    return {"success": True, "job_id": job_id}
