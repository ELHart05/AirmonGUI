from fastapi import APIRouter, HTTPException
import subprocess

from ..models import DeauthRequest
from ..utils import command_prefix, run_command

router = APIRouter(prefix="/aireplay", tags=["aireplay"])


@router.post("/deauth", summary="Send deauthentication frames",
             response_description="stdout/stderr from aireplay-ng")
def deauth(request: DeauthRequest) -> dict:
    iface = request.interface.strip()
    if not iface or "/" in iface or ".." in iface:
        raise HTTPException(status_code=400, detail="Invalid interface name")

    # Set interface channel before attacking so frames land on the right frequency
    if request.channel is not None:
        subprocess.run(
            command_prefix() + ["iwconfig", iface, "channel", str(request.channel)],
            capture_output=True,
            timeout=5,
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

    return run_command(command, timeout=120)
