from fastapi import APIRouter, HTTPException

from ..models import DeauthRequest
from ..utils import command_prefix, run_command, set_interface_channel

router = APIRouter(prefix="/aireplay", tags=["aireplay"])


@router.post("/deauth", summary="Send deauthentication frames",
             response_description="stdout/stderr from aireplay-ng")
def deauth(request: DeauthRequest) -> dict:
    iface = request.interface.strip()
    if not iface or "/" in iface or ".." in iface:
        raise HTTPException(status_code=400, detail="Invalid interface name")

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

    result = run_command(command, timeout=120)
    if channel_result:
        result["channel"] = channel_result
    return result
