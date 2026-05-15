import os
import re
import signal
import subprocess
import time

from fastapi import APIRouter, HTTPException

from ..config import CAPTURE_DIR
from ..models import DeauthRequest
from ..state import JOBS
from ..utils import (
    clean_terminal_output,
    command_prefix,
    new_job_id,
    run_command,
    set_interface_channel,
    stop_conflicting_airodump_jobs,
)

router = APIRouter(prefix="/aireplay", tags=["aireplay"])

_AP_CHANNEL_RE = re.compile(r"AP uses channel\s+(\d+)", re.IGNORECASE)


def _start_process(command: list[str], log_handle) -> subprocess.Popen:
    return subprocess.Popen(
        command,
        stdout=log_handle,
        stderr=log_handle,
        text=True,
        preexec_fn=os.setsid,
    )


def _stop_process(process: subprocess.Popen, timeout: int = 3) -> None:
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


def _build_deauth_command(request: DeauthRequest) -> tuple[list[str], str, dict | None, list[str]]:
    iface = request.interface.strip()
    if not iface or "/" in iface or ".." in iface:
        raise HTTPException(status_code=400, detail="Invalid interface name")

    stopped_scan_jobs = stop_conflicting_airodump_jobs(iface)

    # Set interface channel before attacking so frames land on the right frequency
    channel_result = None
    if request.channel is not None:
        channel_result = set_interface_channel(iface, request.channel)
        if not channel_result["success"]:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Could not lock {iface} to channel {channel_result['requested']} "
                    f"(current: {channel_result['current'] or 'unknown'}). "
                    f"{channel_result['stderr']}"
                ).strip(),
            )

    command = command_prefix() + [
        "aireplay-ng",
        "--deauth",
        str(request.count),
        "-a",
        request.bssid,
    ]
    if request.client:
        command += ["-c", request.client]
    command.append(iface)
    return command, iface, channel_result, stopped_scan_jobs


def _detect_ap_channel(output: str) -> str:
    match = _AP_CHANNEL_RE.search(output or "")
    return match.group(1) if match else ""


def _retry_request_on_ap_channel(request: DeauthRequest, output: str) -> DeauthRequest | None:
    ap_channel = _detect_ap_channel(output)
    if not ap_channel or str(request.channel or "") == ap_channel:
        return None
    return request.model_copy(update={"channel": int(ap_channel)})


@router.post("/deauth", summary="Send deauthentication frames",
             response_description="stdout/stderr from aireplay-ng")
def deauth(request: DeauthRequest) -> dict:
    command, _iface, channel_result, stopped_scan_jobs = _build_deauth_command(request)

    result = run_command(command, timeout=120)
    retry_request = _retry_request_on_ap_channel(request, f"{result.get('stdout', '')}\n{result.get('stderr', '')}")
    if retry_request:
        retry_command, _iface, retry_channel, retry_stopped_scan_jobs = _build_deauth_command(retry_request)
        retry_result = run_command(retry_command, timeout=120)
        retry_result["stdout"] = "\n".join(
            part for part in [
                result.get("stdout", ""),
                f"Detected AP channel {retry_request.channel}; retried deauth on that channel.",
                retry_result.get("stdout", ""),
            ] if part
        )
        retry_result["stderr"] = "\n".join(
            part for part in [result.get("stderr", ""), retry_result.get("stderr", "")] if part
        )
        retry_result["channel"] = retry_channel
        retry_result["retried_channel"] = retry_request.channel
        retry_result["stopped_scan_jobs"] = list(dict.fromkeys(stopped_scan_jobs + retry_stopped_scan_jobs))
        return retry_result
    if channel_result:
        result["channel"] = channel_result
    result["stopped_scan_jobs"] = stopped_scan_jobs
    return result


@router.get("/deauth/jobs", summary="List deauth jobs")
def list_deauth_jobs() -> dict:
    jobs = []
    for job_id, job in JOBS.items():
        if job.get("type") != "deauth":
            continue
        process = job.get("process")
        running = bool(process and process.poll() is None)
        jobs.append({
            "job_id": job_id,
            "running": running,
            "stopped": bool(job.get("stopped")),
            "interface": job.get("interface"),
            "bssid": job.get("bssid"),
            "client": job.get("client"),
            "count": job.get("count"),
            "channel": job.get("channel"),
            "channel_result": job.get("channel_result"),
            "command": job.get("command"),
            "start_time": job.get("start_time"),
        })
    jobs.sort(key=lambda item: item.get("start_time") or 0, reverse=True)
    return {"jobs": jobs}


@router.post("/deauth/start", summary="Start cancellable deauth job")
def start_deauth(request: DeauthRequest) -> dict:
    command, iface, channel_result, stopped_scan_jobs = _build_deauth_command(request)
    job_id = new_job_id()
    log_path = os.path.join(CAPTURE_DIR, f"deauth_{job_id}.log")
    log_handle = open(log_path, "w", encoding="utf-8")  # noqa: WPS515
    process = _start_process(command, log_handle)

    JOBS[job_id] = {
        "type": "deauth",
        "interface": iface,
        "bssid": request.bssid,
        "client": request.client,
        "count": request.count,
        "channel": str(request.channel) if request.channel is not None else "",
        "channel_result": channel_result,
        "process": process,
        "command": " ".join(command),
        "log_path": log_path,
        "log_handle": log_handle,
        "start_time": int(time.time()),
        "stopped": False,
        "stopped_scan_jobs": stopped_scan_jobs,
    }
    return {
        "job_id": job_id,
        "running": True,
        "command": " ".join(command),
        "channel": channel_result,
        "stopped_scan_jobs": stopped_scan_jobs,
    }


def _restart_deauth_on_detected_channel(job: dict, log_tail: str) -> bool:
    if job.get("retried_channel"):
        return False
    ap_channel = _detect_ap_channel(log_tail)
    if not ap_channel or job.get("channel") == ap_channel:
        return False

    request = DeauthRequest(
        interface=job["interface"],
        bssid=job["bssid"],
        client=job.get("client"),
        count=job["count"],
        channel=int(ap_channel),
    )
    command, _iface, channel_result = _build_deauth_command(request)
    log_handle = job.get("log_handle")
    if log_handle and not log_handle.closed:
        log_handle.close()
    log_handle = open(job["log_path"], "a", encoding="utf-8")  # noqa: WPS515
    log_handle.write(f"\nDetected AP channel {ap_channel}; retrying deauth on that channel.\n")
    log_handle.flush()
    process = _start_process(command, log_handle)
    job.update({
        "process": process,
        "command": " ".join(command),
        "channel": ap_channel,
        "channel_result": channel_result,
        "log_handle": log_handle,
        "retried_channel": ap_channel,
        "start_time": int(time.time()),
    })
    return True


@router.get("/deauth/{job_id}/status", summary="Poll deauth job")
def deauth_status(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job or job.get("type") != "deauth":
        raise HTTPException(status_code=404, detail="Job not found")

    process = job.get("process")
    running = bool(process and process.poll() is None)
    returncode = process.poll() if process else None

    if not running:
        log_handle = job.get("log_handle")
        if log_handle and not log_handle.closed:
            log_handle.close()

    log_tail = ""
    try:
        with open(job.get("log_path", ""), "r", encoding="utf-8", errors="ignore") as fh:
            log_tail = clean_terminal_output(fh.read(), max_lines=40)
    except OSError:
        pass

    if not running and not job.get("stopped") and _restart_deauth_on_detected_channel(job, log_tail):
        return deauth_status(job_id)

    return {
        "job_id": job_id,
        "running": running,
        "success": True if running else returncode == 0 and not job.get("stopped"),
        "stopped": bool(job.get("stopped")),
        "returncode": returncode,
        "stdout": log_tail,
        "stderr": "",
        "channel": job.get("channel_result"),
        "retried_channel": job.get("retried_channel"),
        "stopped_scan_jobs": job.get("stopped_scan_jobs", []),
        "command": job.get("command"),
        "elapsed": int(time.time()) - job.get("start_time", int(time.time())),
    }


@router.post("/deauth/{job_id}/stop", summary="Cancel deauth job")
def stop_deauth(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job or job.get("type") != "deauth":
        raise HTTPException(status_code=404, detail="Job not found")

    process = job.get("process")
    job["stopped"] = True
    if process:
        _stop_process(process)

    log_handle = job.get("log_handle")
    if log_handle and not log_handle.closed:
        log_handle.close()

    return deauth_status(job_id)
