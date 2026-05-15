import glob
import os
import re
import subprocess
import time

from fastapi import APIRouter, HTTPException

from ..models import HandshakeCaptureRequest
from ..state import JOBS
from ..utils import (
    clean_terminal_output,
    command_prefix,
    new_job_id,
    parse_airodump_csv,
    safe_capture_path,
    sanitize_name,
    set_interface_channel,
)

router = APIRouter(prefix="/handshake", tags=["handshake"])


def _stop_conflicting_airodump_jobs(interface: str) -> list[str]:
    """Stop scan jobs that would keep channel-hopping the target interface."""
    stopped: list[str] = []
    for job_id, job in JOBS.items():
        if job.get("type") != "airodump" or job.get("interface") != interface:
            continue
        process = job.get("process")
        if not process or process.poll() is not None:
            continue
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        log_handle = job.get("log_handle")
        if log_handle and not log_handle.closed:
            log_handle.close()
        stopped.append(job_id)
    return stopped


def _latest_airodump_path(output_prefix: str, extension: str, start_time: int) -> str:
    pattern = re.compile(rf"^{re.escape(output_prefix)}-\d+\.{re.escape(extension)}$")
    paths = [path for path in glob.glob(f"{output_prefix}-*.{extension}") if pattern.match(path)]
    recent_paths = [path for path in paths if os.path.getmtime(path) >= start_time - 1]
    if not recent_paths:
        return f"{output_prefix}-01.{extension}"
    return max(recent_paths, key=os.path.getmtime)


def _resolve_bssid_channel(interface: str, bssid: str) -> str:
    """Briefly hop channels with airodump-ng to refresh the AP channel before locked capture."""
    prefix = safe_capture_path(f"resolve_{sanitize_name(bssid.replace(':', ''))}_{int(time.time())}")
    csv_path = f"{prefix}-01.csv"
    command = command_prefix() + [
        "airodump-ng",
        "--bssid", bssid,
        "--output-format", "csv",
        "--write", prefix,
        interface,
    ]
    try:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        time.sleep(6)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
        data = parse_airodump_csv(csv_path)
        for network in data.get("networks", []):
            if network.get("BSSID", "").upper() == bssid.upper():
                channel = str(network.get("channel", "")).strip()
                if channel.isdigit():
                    return channel
    except (OSError, subprocess.SubprocessError):
        return ""
    finally:
        for suffix in ("-01.csv", "-01.kismet.csv", "-01.kismet.netxml", "-01.log.csv"):
            try:
                os.remove(f"{prefix}{suffix}")
            except OSError:
                pass
    return ""


def _handshake_job_summary(job_id: str, job: dict) -> dict:
    process = job.get("process")
    running = bool(process and process.poll() is None)
    start_time = job.get("start_time", int(time.time()))
    output_prefix = job.get("output_prefix", "")
    if output_prefix:
        job["cap_path"] = _latest_airodump_path(output_prefix, "cap", start_time)
        job["csv_path"] = _latest_airodump_path(output_prefix, "csv", start_time)
    return {
        "job_id": job_id,
        "running": running,
        "interface": job.get("interface"),
        "bssid": job.get("bssid"),
        "channel": job.get("channel"),
        "requested_channel": job.get("requested_channel"),
        "resolved_channel": job.get("resolved_channel"),
        "command": job.get("command"),
        "output_prefix": output_prefix,
        "cap_path": job.get("cap_path"),
        "csv_path": job.get("csv_path"),
        "log_path": job.get("log_path"),
        "start_time": start_time,
        "channel_result": job.get("channel_result"),
    }


@router.get("/jobs")
def list_handshake_jobs() -> dict:
    jobs = [
        _handshake_job_summary(job_id, job)
        for job_id, job in JOBS.items()
        if job.get("type") == "handshake"
    ]
    jobs.sort(key=lambda item: item.get("start_time") or 0, reverse=True)
    return {"jobs": jobs}


@router.post("/start")
def start_handshake_capture(request: HandshakeCaptureRequest) -> dict:
    """
    Start a targeted airodump-ng session aimed at a specific BSSID + channel
    to capture a WPA 4-way handshake.
    """
    prefix = request.output_prefix or f"hs_{sanitize_name(request.bssid.replace(':', ''))}"
    output_prefix = safe_capture_path(prefix)
    cap_path = f"{output_prefix}-01.cap"
    csv_path = f"{output_prefix}-01.csv"
    log_path = f"{output_prefix}.log"
    start_time = int(time.time())

    for job in JOBS.values():
        process = job.get("process")
        if (
            job.get("type") == "handshake"
            and job.get("interface") == request.interface
            and process
            and process.poll() is None
        ):
            raise HTTPException(
                status_code=409,
                detail=f"A handshake capture is already running on {request.interface}",
            )

    stopped_scan_jobs = _stop_conflicting_airodump_jobs(request.interface)
    resolved_channel = _resolve_bssid_channel(request.interface, request.bssid)
    target_channel = resolved_channel or request.channel

    channel_result = set_interface_channel(request.interface, target_channel)
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
        "-c", target_channel,
        "--bssid", request.bssid,
        "--output-format", "pcap,csv",
        "--write", output_prefix,
        request.interface,
    ]

    log_handle = open(log_path, "w", encoding="utf-8")  # noqa: WPS515
    process = subprocess.Popen(command, stdout=log_handle, stderr=log_handle, text=True)

    job_id = new_job_id()
    JOBS[job_id] = {
        "type": "handshake",
        "interface": request.interface,
        "bssid": request.bssid,
        "channel": target_channel,
        "requested_channel": request.channel,
        "resolved_channel": resolved_channel,
        "process": process,
        "command": " ".join(command),
        "output_prefix": output_prefix,
        "cap_path": cap_path,
        "csv_path": csv_path,
        "log_path": log_path,
        "start_time": start_time,
        "log_handle": log_handle,
        "channel_result": channel_result,
        "stopped_scan_jobs": stopped_scan_jobs,
    }

    return {
        "job_id": job_id,
        "interface": request.interface,
        "cap_path": cap_path,
        "csv_path": csv_path,
        "bssid": request.bssid,
        "channel": target_channel,
        "requested_channel": request.channel,
        "resolved_channel": resolved_channel,
        "channel_result": channel_result,
        "stopped_scan_jobs": stopped_scan_jobs,
        "command": " ".join(command),
    }


@router.get("/{job_id}/status")
def handshake_status(job_id: str) -> dict:
    """
    Poll the status of a handshake capture job.
    Returns handshake_detected=True when the WPA 4-way handshake is captured,
    detected either from the airodump log or by running aircrack-ng on the cap file.
    """
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    process = job.get("process")
    running = bool(process and process.poll() is None)
    start_time = job.get("start_time", int(time.time()))
    output_prefix = job.get("output_prefix", "")
    if output_prefix:
        job["cap_path"] = _latest_airodump_path(output_prefix, "cap", start_time)
        job["csv_path"] = _latest_airodump_path(output_prefix, "csv", start_time)
    cap_path = job.get("cap_path", "")
    csv_path = job.get("csv_path", "")
    log_path = job.get("log_path", "")

    # Primary: look for "WPA handshake: XX:XX..." line in airodump log
    handshake_in_log = False
    log_tail = ""
    if log_path and os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as fh:
                raw_log = fh.read()
            log_tail = clean_terminal_output(raw_log, max_lines=30)
            handshake_in_log = "WPA handshake" in log_tail
        except OSError:
            pass

    handshake_detected = handshake_in_log

    # Secondary: run aircrack-ng on the cap file if it exists.
    # Must match a positive count: "(N handshake)" with N >= 1 to avoid the
    # false-positive triggered by "WPA (0 handshake)" containing the word.
    if not handshake_detected and cap_path and os.path.exists(cap_path):
        try:
            result = subprocess.run(
                command_prefix() + ["aircrack-ng", cap_path],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            combined = result.stdout + result.stderr
            hs_match = re.search(r"\((\d+)\s+handshake", combined)
            has_positive_hs = bool(hs_match and int(hs_match.group(1)) > 0)
            has_pmkid = "pmkid" in combined.lower() and "0 pmkid" not in combined.lower()
            handshake_detected = has_positive_hs or has_pmkid
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    cap_size = 0
    if cap_path and os.path.exists(cap_path):
        cap_size = os.path.getsize(cap_path)
    data = parse_airodump_csv(csv_path) if csv_path else {"networks": [], "clients": []}

    return {
        "job_id": job_id,
        "running": running,
        "handshake_detected": handshake_detected,
        "cap_path": cap_path,
        "cap_size": cap_size,
        "bssid": job.get("bssid"),
        "channel": job.get("channel"),
        "requested_channel": job.get("requested_channel"),
        "resolved_channel": job.get("resolved_channel"),
        "channel_result": job.get("channel_result"),
        "elapsed": int(time.time()) - start_time,
        "log_tail": log_tail,
        "data": data,
    }


@router.post("/{job_id}/stop")
def stop_handshake_capture(job_id: str) -> dict:
    job = JOBS.get(job_id)
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

    output_prefix = job.get("output_prefix", "")
    start_time = job.get("start_time", int(time.time()))
    if output_prefix:
        job["cap_path"] = _latest_airodump_path(output_prefix, "cap", start_time)
        job["csv_path"] = _latest_airodump_path(output_prefix, "csv", start_time)

    return {
        "success": True,
        "job_id": job_id,
        "cap_path": job.get("cap_path"),
        "bssid": job.get("bssid"),
    }
