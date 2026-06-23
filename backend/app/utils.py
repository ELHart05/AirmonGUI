import csv
import glob
import os
import re
import subprocess
import time
import uuid
from typing import List

from fastapi import HTTPException

from .config import CAPTURE_DIR, MAX_ACTIVE_JOBS
from .state import JOBS

_ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def command_prefix() -> List[str]:
    """Return sudo prefix when not running as root."""
    if os.geteuid() == 0:
        return []
    return ["sudo"]


def new_job_id() -> str:
    return uuid.uuid4().hex


def count_active_jobs() -> int:
    """Number of tool processes currently alive across all job types."""
    return sum(
        1
        for job in JOBS.values()
        if (process := job.get("process")) and process.poll() is None
    )


def enforce_job_quota() -> None:
    """Reject a new job once the concurrent-process limit is reached."""
    if count_active_jobs() >= MAX_ACTIVE_JOBS:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Too many active jobs (limit {MAX_ACTIVE_JOBS}). "
                "Stop a running job before starting another."
            ),
        )


def run_command(command: List[str], timeout: int = 60) -> dict:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "success": completed.returncode == 0,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "returncode": completed.returncode,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "stdout": exc.stdout or "",
            "stderr": f"Command timed out after {timeout}s",
            "returncode": -1,
        }


def clean_terminal_output(value: str, max_lines: int = 80) -> str:
    """Convert terminal-style output with ANSI cursor controls into readable lines."""
    if not value:
        return ""
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = _ANSI_RE.sub("", text)
    text = _CTRL_RE.sub("", text)
    lines = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip():
            lines.append(line)
    return "\n".join(lines[-max_lines:])


def _read_interface_channel(iface: str) -> str:
    """Best-effort channel readback using iw first, iwconfig second."""
    try:
        iw = subprocess.run(
            command_prefix() + ["iw", "dev", iface, "info"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        match = re.search(r"\bchannel\s+(\d+)\b", iw.stdout + iw.stderr, re.IGNORECASE)
        if match:
            return match.group(1)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        iwconfig = subprocess.run(
            command_prefix() + ["iwconfig", iface],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        match = re.search(r"\bChannel[:=](\d+)\b", iwconfig.stdout + iwconfig.stderr, re.IGNORECASE)
        if match:
            return match.group(1)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


def set_interface_channel(iface: str, channel: str | int, attempts: int = 3) -> dict:
    """Set and verify a wireless interface channel before targeted capture/deauth."""
    target = str(channel).strip()
    if not target.isdigit() or not (1 <= int(target) <= 165):
        raise HTTPException(status_code=400, detail="Channel must be between 1 and 165")

    commands = [
        command_prefix() + ["iw", "dev", iface, "set", "channel", target],
        command_prefix() + ["iwconfig", iface, "channel", target],
    ]
    errors: list[str] = []
    current = ""

    for _ in range(attempts):
        for command in commands:
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
                if result.returncode != 0 and result.stderr.strip():
                    errors.append(f"{' '.join(command)}: {result.stderr.strip()}")
            except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
                errors.append(f"{' '.join(command)}: {exc}")
        time.sleep(0.25)
        current = _read_interface_channel(iface)
        if current == target:
            return {
                "success": True,
                "requested": target,
                "current": current,
                "verified": True,
                "method": "direct",
                "stderr": "\n".join(dict.fromkeys(errors)),
            }

    if current and current != target:
        errors.append(f"Requested channel {target}; readback currently reports channel {current}.")
    elif not current:
        errors.append("Requested channel set could not be verified by iw or iwconfig.")

    return {
        "success": False,
        "requested": target,
        "current": current,
        "verified": False,
        "method": "direct",
        "stderr": "\n".join(dict.fromkeys(errors)),
    }


def stop_conflicting_airodump_jobs(interface: str) -> list[str]:
    """Stop active scan jobs on the same interface before a channel-locked action."""
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


def sanitize_name(value: str) -> str:
    """Strip unsafe characters from user-supplied file name components."""
    return re.sub(r"[^a-zA-Z0-9._-]", "_", value.strip())


def safe_capture_path(name: str) -> str:
    """Resolve a capture name to an absolute path, preventing directory traversal."""
    base = os.path.abspath(CAPTURE_DIR)
    candidate = os.path.abspath(os.path.join(base, name))
    if not candidate.startswith(base + os.sep):
        raise HTTPException(status_code=400, detail="Invalid capture path")
    return candidate


def latest_airodump_path(output_prefix: str, extension: str, start_time: int) -> str:
    """Return the newest <prefix>-NN.<ext> written for a job, falling back to -01.

    airodump-ng never overwrites an existing capture: a reused prefix advances the
    numeric suffix (-02, -03, ...). Resolving the newest file at read time avoids
    returning stale or empty data from a hardcoded -01 path.
    """
    pattern = re.compile(rf"^{re.escape(output_prefix)}-\d+\.{re.escape(extension)}$")
    paths = [p for p in glob.glob(f"{output_prefix}-*.{extension}") if pattern.match(p)]
    recent = [p for p in paths if os.path.getmtime(p) >= start_time - 1]
    if not recent:
        return f"{output_prefix}-01.{extension}"
    return max(recent, key=os.path.getmtime)


def parse_airmon_interfaces(output: str) -> List[dict]:
    lines = [line for line in output.splitlines() if line.strip()]
    if not lines:
        return []

    header_index = None
    for i, line in enumerate(lines):
        lower = line.strip().lower()
        if lower.startswith("interface") or lower.startswith("phy"):
            header_index = i
            break

    if header_index is None or header_index + 1 >= len(lines):
        return []

    header_line = lines[header_index].strip()
    headers = re.split(r"\s{2,}|\t", header_line)
    headers = [h.strip().lower() for h in headers]

    parsed = []
    for row in lines[header_index + 1 :]:
        columns = re.split(r"\s{2,}|\t", row.strip())
        if len(columns) < 2:
            continue
        entry = {headers[i]: columns[i] for i in range(min(len(headers), len(columns)))}
        # Detect monitor mode heuristically
        iface_name = entry.get("interface", "")
        entry["monitor_mode"] = iface_name.endswith("mon")
        parsed.append(entry)

    return parsed


def parse_airodump_csv(path: str) -> dict:
    if not os.path.exists(path):
        return {"networks": [], "clients": []}

    networks: List[dict] = []
    clients: List[dict] = []
    section = "networks"
    headers: List[str] = []

    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                section = "separator"
                headers = []
                continue
            if row[0].strip().lower() == "station mac":
                section = "clients"
                headers = [col.strip() for col in row]
                continue
            if section == "separator":
                headers = [col.strip() for col in row]
                section = "networks"
                continue
            if not headers:
                headers = [col.strip() for col in row]
                continue

            entry = {headers[i]: row[i].strip() for i in range(min(len(headers), len(row)))}
            if section == "clients":
                clients.append(entry)
            else:
                networks.append(entry)

    return {"networks": networks, "clients": clients}
