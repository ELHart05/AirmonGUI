import subprocess
import time

from fastapi import APIRouter, HTTPException, Path

from ..models import (
    AirodumpJobsResponse,
    AirodumpResultsResponse,
    AirodumpStartRequest,
    AirodumpStartResponse,
    AirodumpStopRequest,
    ErrorResponse,
    JobActionResponse,
)
from ..state import JOBS
from ..utils import (
    clean_terminal_output,
    command_prefix,
    latest_airodump_path,
    new_job_id,
    parse_airodump_csv,
    safe_capture_path,
    sanitize_name,
    set_interface_channel,
)

router = APIRouter(prefix="/airodump", tags=["airodump"])


@router.get(
    "/jobs",
    summary="List scan jobs",
    response_model=AirodumpJobsResponse,
    response_description="All known airodump-ng jobs, newest first",
)
def list_jobs() -> dict:
    """List every airodump-ng scan job this backend started, with live running state and output paths."""
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
    jobs.sort(key=lambda item: item.get("start_time") or 0, reverse=True)
    return {"jobs": jobs}


@router.post(
    "/start",
    summary="Start a scan job",
    response_model=AirodumpStartResponse,
    response_description="The created job id and the airodump-ng command that was launched",
    responses={
        400: {"model": ErrorResponse, "description": "Interface is required"},
        409: {
            "model": ErrorResponse,
            "description": "A scan is already running on this interface, or the channel could not be locked",
        },
    },
)
def start_airodump(request: AirodumpStartRequest) -> dict:
    """
    Launch a background `airodump-ng` capture. If a single channel is requested the
    interface is locked to it first; output is written to `.cap`/`.csv`/`.log` files
    in the capture directory. Poll `GET /api/airodump/results/{job_id}` for parsed data.
    """
    if not request.interface:
        raise HTTPException(status_code=400, detail="Interface is required")

    for job in JOBS.values():
        process = job.get("process")
        if (
            job.get("type") == "airodump"
            and job.get("interface") == request.interface
            and process
            and process.poll() is None
        ):
            raise HTTPException(
                status_code=409,
                detail=f"An airodump-ng scan is already running on {request.interface}",
            )

    prefix = request.output_prefix or f"capture_{int(time.time())}"
    prefix = sanitize_name(prefix)
    output_prefix = safe_capture_path(prefix)
    csv_path = f"{output_prefix}-01.csv"
    cap_path = f"{output_prefix}-01.cap"
    log_path = f"{output_prefix}.log"
    channel_result = None

    if request.channel and str(request.channel).strip().isdigit():
        channel_result = set_interface_channel(request.interface, request.channel)
        if not channel_result["success"]:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Could not lock {request.interface} to channel {channel_result['requested']} "
                    f"(current: {channel_result['current'] or 'unknown'}). "
                    f"{channel_result['stderr']}"
                ).strip(),
            )

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
    try:
        process = subprocess.Popen(command, stdout=log_handle, stderr=log_handle, text=True)
    except Exception:
        log_handle.close()
        raise

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
        "channel_result": channel_result,
    }

    return {
        "job_id": job_id,
        "output_prefix": output_prefix,
        "csv_path": csv_path,
        "cap_path": cap_path,
        "log_path": log_path,
        "channel_result": channel_result,
        "command": " ".join(command),
    }


@router.post(
    "/stop",
    summary="Stop a scan job",
    response_model=JobActionResponse,
    responses={404: {"model": ErrorResponse, "description": "Job not found"}},
)
def stop_airodump(request: AirodumpStopRequest) -> dict:
    """Terminate the airodump-ng process for the given job id and close its log file."""
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


@router.get(
    "/results/{job_id}",
    summary="Get parsed scan results",
    response_model=AirodumpResultsResponse,
    response_description="Parsed networks and clients plus a cleaned tail of the live log",
    responses={
        400: {"model": ErrorResponse, "description": "Job has no CSV output"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
def airodump_results(
    job_id: str = Path(..., description="Scan job id returned by POST /api/airodump/start"),
) -> dict:
    """Parse the job's CSV file into networks and clients and return it with the live running state."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Resolve the newest output file rather than trusting a hardcoded -01 path:
    # airodump-ng advances the suffix (-02, -03, ...) when a prefix is reused.
    output_prefix = job.get("output_prefix", "")
    start_time = job.get("start_time", 0)
    if output_prefix:
        job["csv_path"] = latest_airodump_path(output_prefix, "csv", start_time)
        job["cap_path"] = latest_airodump_path(output_prefix, "cap", start_time)

    csv_path = job.get("csv_path")
    if not csv_path:
        raise HTTPException(status_code=400, detail="No CSV path associated with this job")

    process = job.get("process")
    data = parse_airodump_csv(csv_path)
    log_tail = ""
    log_path = job.get("log_path")
    if log_path:
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as fh:
                log_tail = clean_terminal_output(fh.read(), max_lines=30)
        except OSError:
            pass
    return {
        "job_id": job_id,
        "csv_path": csv_path,
        "cap_path": job.get("cap_path"),
        "running": bool(process and process.poll() is None),
        "data": data,
        "log_tail": log_tail,
        "channel_result": job.get("channel_result"),
    }
