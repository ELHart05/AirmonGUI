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
        "start_time": int(time.time()),
        "log_handle": log_handle,
        "channel_result": channel_result,
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
        "elapsed": int(time.time()) - job.get("start_time", int(time.time())),
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

    return {
        "success": True,
        "job_id": job_id,
        "cap_path": job.get("cap_path"),
        "bssid": job.get("bssid"),
    }
