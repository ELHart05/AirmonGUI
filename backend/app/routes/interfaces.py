from fastapi import APIRouter, HTTPException

from ..models import (
    CommandResult,
    ErrorResponse,
    InterfacesResponse,
    MonitorRequest,
    MonitorResponse,
    ToolCheckResponse,
)
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


@router.get(
    "/interfaces",
    summary="List wireless interfaces",
    response_model=InterfacesResponse,
    response_description="Parsed interface list with monitor-mode status and MAC addresses",
    responses={500: {"model": ErrorResponse, "description": "`airmon-ng` could not be run"}},
)
def list_interfaces() -> dict:
    """
    Run `airmon-ng` and return every wireless interface with its driver, chipset,
    monitor-mode flag, and MAC address, alongside the raw tool output. This is the
    source of truth the UI uses to populate interface selectors.
    """
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


@router.post(
    "/monitor",
    summary="Start or stop monitor mode",
    response_model=MonitorResponse,
    response_description="Command output and the refreshed interface list",
    responses={400: {"model": ErrorResponse, "description": "Invalid action or interface name"}},
)
def monitor_action(request: MonitorRequest) -> dict:
    """
    Run `airmon-ng start|stop <interface>` to toggle monitor mode on one interface,
    then return the command output together with a freshly parsed interface list so
    the UI can update immediately.
    """
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
    summary="Kill global monitor-mode interfering processes",
    response_model=CommandResult,
    response_description="Output from `airmon-ng check kill`",
)
def check_kill() -> dict:
    """
    Run global `airmon-ng check kill` to stop processes that interfere with
    monitor mode across wireless interfaces.
    """
    return run_command(command_prefix() + ["airmon-ng", "check", "kill"], timeout=60)


@router.get(
    "/toolcheck",
    summary="Check aircrack-ng suite availability",
    response_model=ToolCheckResponse,
    response_description="Installation status and path for each required tool",
)
def tool_check() -> dict:
    """Check which aircrack-ng suite tools are installed."""
    tools = ["airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng"]
    results = {}
    for tool in tools:
        r = run_command(["which", tool], timeout=5)
        results[tool] = {"installed": r["success"], "path": r["stdout"]}
    return {"tools": results}
