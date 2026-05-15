import subprocess

from fastapi import APIRouter, HTTPException

from ..models import CheckKillRequest, MonitorRequest
from ..utils import command_prefix, parse_airmon_interfaces, run_command

router = APIRouter(tags=["interfaces"])


def _get_mac(iface: str) -> str:
    """Read interface MAC address from sysfs."""
    try:
        with open(f"/sys/class/net/{iface}/address") as f:
            return f.read().strip().upper()
    except OSError:
        return ""


def _enrich_with_macs(interfaces: list) -> list:
    for entry in interfaces:
        name = entry.get("interface", "")
        if name:
            entry["mac"] = _get_mac(name)
    return interfaces


@router.get("/interfaces", summary="List wireless interfaces",
            response_description="Parsed interface list with monitor-mode status and MAC addresses")
def list_interfaces() -> dict:
    result = run_command(command_prefix() + ["airmon-ng"])
    if not result["success"] and not result["stdout"]:
        raise HTTPException(
            status_code=500, detail=result["stderr"] or "Failed to run airmon-ng"
        )
    ifaces = _enrich_with_macs(parse_airmon_interfaces(result["stdout"]))
    return {
        "raw": result["stdout"],
        "interfaces": ifaces,
    }


@router.post("/monitor", summary="Start or stop monitor mode",
             response_description="Command output and refreshed interface list")
def monitor_action(request: MonitorRequest) -> dict:
    if request.action not in {"start", "stop"}:
        raise HTTPException(status_code=400, detail="Action must be 'start' or 'stop'")
    iface = request.interface.strip()
    if not iface or "/" in iface or ".." in iface:
        raise HTTPException(status_code=400, detail="Invalid interface name")
    result = run_command(command_prefix() + ["airmon-ng", request.action, iface], timeout=120)
    # Return refreshed interface list so UI can update immediately
    iface_data = run_command(command_prefix() + ["airmon-ng"])
    result["interfaces"] = _enrich_with_macs(parse_airmon_interfaces(iface_data["stdout"]))
    return result


@router.post(
    "/checkkill",
    summary="Release processes for one interface",
    response_description="Targeted process-release result for the selected interface",
)
def check_kill(request: CheckKillRequest) -> dict:
    """
    Release only the selected interface from services that can interfere with
    monitor mode. This intentionally does not run global `airmon-ng check kill`.
    """
    iface = request.interface.strip()
    if not iface or "/" in iface or ".." in iface:
        raise HTTPException(status_code=400, detail="Invalid interface name")
    return _targeted_kill(iface)


def _find_pids_for(pattern: str) -> list[str]:
    """Return PIDs whose full command line contains *pattern*."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True, text=True, timeout=5,
        )
        return [p.strip() for p in result.stdout.splitlines() if p.strip().isdigit()]
    except Exception:
        return []


def _targeted_kill(iface: str) -> dict:
    """Release a single interface from NetworkManager / wpa_supplicant / dhclient."""
    lines: list[str] = []
    errors: list[str] = []

    # 1. Ask NetworkManager to stop managing this specific interface (non-destructive).
    nm = subprocess.run(
        command_prefix() + ["nmcli", "device", "set", iface, "managed", "no"],
        capture_output=True, text=True, timeout=5,
    )
    if nm.returncode == 0:
        lines.append(f"NetworkManager: unmanaged {iface}")
    elif nm.stderr.strip():
        # nmcli not available or NM isn't running — not a hard error.
        errors.append(f"nmcli: {nm.stderr.strip()}")

    # 2. Kill any wpa_supplicant process that references this interface.
    for pid in _find_pids_for(f"wpa_supplicant.*{iface}"):
        r = subprocess.run(
            command_prefix() + ["kill", "-15", pid],
            capture_output=True,
            timeout=3,
        )
        if r.returncode == 0:
            lines.append(f"Killed wpa_supplicant (PID {pid}) for {iface}")
        else:
            errors.append(f"Could not kill PID {pid}")

    # 3. Kill any dhclient / dhcpcd process referencing this interface.
    for daemon in ("dhclient", "dhcpcd"):
        for pid in _find_pids_for(f"{daemon}.*{iface}"):
            r = subprocess.run(
                command_prefix() + ["kill", "-15", pid],
                capture_output=True,
                timeout=3,
            )
            if r.returncode == 0:
                lines.append(f"Killed {daemon} (PID {pid}) for {iface}")
            else:
                errors.append(f"Could not kill {daemon} PID {pid}")

    stdout = "\n".join(lines) if lines else f"No active interfering processes found for {iface}."
    return {
        "success": True,
        "stdout": stdout,
        "stderr": "\n".join(errors),
        "returncode": 0,
    }


@router.get("/toolcheck", summary="Check aircrack-ng suite availability",
            response_description="Installation status and path for each required tool")
def tool_check() -> dict:
    """Check which aircrack-ng suite tools are installed."""
    tools = ["airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng"]
    results = {}
    for tool in tools:
        r = run_command(["which", tool], timeout=5)
        results[tool] = {"installed": r["success"], "path": r["stdout"]}
    return {"tools": results}
