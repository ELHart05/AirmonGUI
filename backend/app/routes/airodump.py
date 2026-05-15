import subprocess
import time

from fastapi import APIRouter, HTTPException

from ..models import AirodumpStartRequest, AirodumpStopRequest
from ..state import JOBS
from ..utils import (
    command_prefix,
    new_job_id,
    parse_airodump_csv,
    safe_capture_path,
    sanitize_name,
)

router = APIRouter(prefix="/airodump", tags=["airodump"])


@router.get("/jobs")
def list_jobs() -> dict:
    jobs = []
    for job_id, job in JOBS.items():
        process = job.get("process")
        running = bool(process and process.poll() is None)
        jobs.append(
            {
                "job_id": job_id,
                "type": job.get("type"),
                "interface": job.get("interface"),
                "command": job.get("command"),
                "output_prefix": job.get("output_prefix"),
                "csv_path": job.get("csv_path"),
                "cap_path": job.get("cap_path"),
                "log_path": job.get("log_path"),
                "running": running,
                "start_time": job.get("start_time"),
            }
        )
    return {"jobs": jobs}


@router.post("/start")
def start_airodump(request: AirodumpStartRequest) -> dict:
    if not request.interface:
        raise HTTPException(status_code=400, detail="Interface is required")

    prefix = request.output_prefix or f"capture_{int(time.time())}"
    prefix = sanitize_name(prefix)
    output_prefix = safe_capture_path(prefix)
    csv_path = f"{output_prefix}-01.csv"
    cap_path = f"{output_prefix}-01.cap"
    log_path = f"{output_prefix}.log"

    command = command_prefix() + [
        "airodump-ng",
        request.interface,
        "--output-format",
        "pcap,csv",
        "--write",
        output_prefix,
    ]
    if request.channel:
        command += ["-c", request.channel]
    if request.band:
        command += ["--band", request.band]
    if request.bssid:
        command += ["--bssid", request.bssid]

    log_handle = open(log_path, "w", encoding="utf-8")  # noqa: WPS515
    process = subprocess.Popen(command, stdout=log_handle, stderr=log_handle, text=True)

    job_id = new_job_id()
    JOBS[job_id] = {
        "type": "airodump",
        "interface": request.interface,
        "process": process,
        "command": " ".join(command),
        "output_prefix": output_prefix,
        "csv_path": csv_path,
        "cap_path": cap_path,
        "log_path": log_path,
        "start_time": int(time.time()),
        "log_handle": log_handle,
    }

    return {
        "job_id": job_id,
        "output_prefix": output_prefix,
        "csv_path": csv_path,
        "cap_path": cap_path,
        "log_path": log_path,
        "command": " ".join(command),
    }


@router.post("/stop")
def stop_airodump(request: AirodumpStopRequest) -> dict:
    job = JOBS.get(request.job_id)
    if not job:
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

    return {"success": True, "job_id": request.job_id}


@router.get("/results/{job_id}")
def airodump_results(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    csv_path = job.get("csv_path")
    if not csv_path:
        raise HTTPException(status_code=400, detail="No CSV path associated with this job")

    process = job.get("process")
    data = parse_airodump_csv(csv_path)
    return {
        "job_id": job_id,
        "csv_path": csv_path,
        "cap_path": job.get("cap_path"),
        "running": bool(process and process.poll() is None),
        "data": data,
    }
