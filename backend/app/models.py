"""
Pydantic request and response models for the AirmonGUI API.

Request models validate and document the JSON bodies clients send.
Response models document (and lightly shape) what each endpoint returns, so the
Swagger UI at `/docs` and the ReDoc page at `/redoc` show a full schema for
every operation. Models that wrap parsed tool output (interface lists,
airodump-ng tables) allow extra keys, because the exact columns depend on the
output of the underlying binary.
"""

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")


def _validate_mac(v: Optional[str]) -> Optional[str]:
    if v and not _MAC_RE.match(v):
        raise ValueError("Must be a valid MAC address (XX:XX:XX:XX:XX:XX)")
    return v


def _validate_channel_str(v: Optional[str]) -> Optional[str]:
    """Accept None, '', a single channel, or a comma-separated list, each in 1..165."""
    if not v:
        return v
    for part in str(v).strip().split(","):
        part = part.strip()
        if not part.isdigit() or not (1 <= int(part) <= 165):
            raise ValueError("Channel must be 1-165 (or a comma-separated list of channels)")
    return v


# ─────────────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────────────

class MonitorRequest(BaseModel):
    """Start or stop monitor mode on a single wireless interface."""

    interface: str = Field(
        ...,
        description="Wireless interface to act on, as shown by `GET /api/interfaces`.",
        examples=["wlan0"],
    )
    action: str = Field(
        ...,
        description="`start` to enable monitor mode, `stop` to return the interface to managed mode.",
        examples=["start"],
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"interface": "wlan0", "action": "start"}}
    )


class DeauthRequest(BaseModel):
    """Parameters for an `aireplay-ng --deauth` run."""

    interface: str = Field(
        ...,
        description="Monitor-mode interface used to transmit the deauth frames.",
        examples=["wlan1mon"],
    )
    bssid: str = Field(
        ...,
        description="Target access point MAC address.",
        examples=["A8:B2:34:90:12:CD"],
    )
    client: Optional[str] = Field(
        None,
        description="Optional client MAC to target. Leave empty to broadcast the deauth to every client on the AP.",
        examples=["6A:1B:9C:0D:2E:3F"],
    )
    count: int = Field(
        10,
        ge=0,
        le=65535,
        description="Number of deauth bursts to send. `0` means continuous until cancelled.",
        examples=[10],
    )
    channel: Optional[int] = Field(
        None,
        ge=1,
        le=165,
        description="AP channel. The interface is tuned to this channel before transmitting so the frames land.",
        examples=[36],
    )

    @field_validator("bssid")
    @classmethod
    def validate_bssid(cls, v: str) -> str:
        if not _MAC_RE.match(v):
            raise ValueError("BSSID must be a valid MAC address")
        return v

    @field_validator("client")
    @classmethod
    def validate_client(cls, v: Optional[str]) -> Optional[str]:
        return _validate_mac(v)

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: int) -> int:
        if v < 0 or v > 65535:
            raise ValueError("Count must be between 0 and 65535 (0 = continuous)")
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 165):
            raise ValueError("Channel must be between 1 and 165")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "interface": "wlan1mon",
                "bssid": "A8:B2:34:90:12:CD",
                "client": None,
                "count": 10,
                "channel": 36,
            }
        }
    )


class AirodumpStartRequest(BaseModel):
    """Parameters for starting an `airodump-ng` scan job."""

    interface: str = Field(
        ...,
        description="Monitor-mode interface to scan with.",
        examples=["wlan1mon"],
    )
    channel: Optional[str] = Field(
        None,
        description="Lock to a single channel (or comma list, e.g. `1,6,11`). Leave empty to hop all channels.",
        examples=["6"],
    )
    band: Optional[str] = Field(
        None,
        description="Band to scan: `a` (5 GHz), `g`/`bg` (2.4 GHz), or `ag` (both). Passed through to `--band`.",
        examples=["ag"],
    )
    bssid: Optional[str] = Field(
        None,
        description="Restrict the scan to a single access point MAC.",
        examples=["A8:B2:34:90:12:CD"],
    )
    output_prefix: Optional[str] = Field(
        None,
        description="File-name prefix for the capture files. Defaults to `capture_<timestamp>` if omitted.",
        examples=["campus_scan"],
    )

    @field_validator("bssid")
    @classmethod
    def validate_bssid(cls, v: Optional[str]) -> Optional[str]:
        return _validate_mac(v)

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: Optional[str]) -> Optional[str]:
        return _validate_channel_str(v)

    model_config = ConfigDict(
        json_schema_extra={"example": {"interface": "wlan1mon", "channel": "6", "band": "ag"}}
    )


class AirodumpStopRequest(BaseModel):
    """Identify the scan job to stop."""

    job_id: str = Field(
        ...,
        description="Job id returned by `POST /api/airodump/start`.",
        examples=["a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"],
    )


class AircrackRequest(BaseModel):
    """Parameters for an `aircrack-ng` dictionary attack."""

    capture_file: str = Field(
        ...,
        description="Capture file to crack. Either an absolute path or a name inside the capture directory.",
        examples=["handshake-OfficeNet-01.cap"],
    )
    wordlist: str = Field(
        ...,
        description="Absolute path to the wordlist file.",
        examples=["/usr/share/wordlists/rockyou.txt"],
    )
    bssid: Optional[str] = Field(
        None,
        description="Restrict cracking to a single BSSID when the capture holds more than one network.",
        examples=["A8:B2:34:90:12:CD"],
    )
    channel: Optional[str] = Field(
        None,
        description="Optional channel hint passed to `aircrack-ng`.",
        examples=["36"],
    )

    @field_validator("bssid")
    @classmethod
    def validate_bssid(cls, v: Optional[str]) -> Optional[str]:
        return _validate_mac(v)

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: Optional[str]) -> Optional[str]:
        return _validate_channel_str(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "capture_file": "handshake-OfficeNet-01.cap",
                "wordlist": "/usr/share/wordlists/rockyou.txt",
                "bssid": "A8:B2:34:90:12:CD",
            }
        }
    )


class HandshakeCaptureRequest(BaseModel):
    """Parameters for a targeted WPA handshake capture."""

    interface: str = Field(
        ...,
        description="Monitor-mode interface to capture with.",
        examples=["wlan1mon"],
    )
    bssid: str = Field(
        ...,
        description="Target access point MAC. The capture is locked to this BSSID.",
        examples=["A8:B2:34:90:12:CD"],
    )
    channel: str = Field(
        ...,
        description="Target channel. The backend re-resolves and locks the interface to it before capturing.",
        examples=["36"],
    )
    output_prefix: Optional[str] = Field(
        None,
        description="File-name prefix for the capture. Defaults to `hs_<bssid>` if omitted.",
        examples=["handshake-OfficeNet"],
    )

    @field_validator("bssid")
    @classmethod
    def validate_bssid(cls, v: str) -> str:
        if not _MAC_RE.match(v):
            raise ValueError("BSSID must be a valid MAC address")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"interface": "wlan1mon", "bssid": "A8:B2:34:90:12:CD", "channel": "36"}
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shared response building blocks
# ─────────────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """FastAPI's standard error body."""

    detail: str = Field(..., description="Human-readable error message.", examples=["Job not found"])


class CommandResult(BaseModel):
    """Result of a one-shot command run through the subprocess helper."""

    success: bool = Field(..., description="True when the command exited with status 0.")
    stdout: str = Field("", description="Captured standard output, trimmed.")
    stderr: str = Field("", description="Captured standard error, trimmed.")
    returncode: int = Field(..., description="Process exit code (`-1` on timeout).")


class ChannelResult(BaseModel):
    """Outcome of setting and verifying a wireless interface channel."""

    success: bool = Field(..., description="True when the interface was locked to the requested channel.")
    requested: str = Field(..., description="Channel that was requested.", examples=["36"])
    current: str = Field("", description="Channel read back from the interface, if available.", examples=["36"])
    verified: bool = Field(..., description="True when the readback matched the requested channel.")
    method: str = Field("direct", description="How the channel was set.", examples=["direct"])
    stderr: str = Field("", description="Any errors collected while setting the channel.")


class ToolInfo(BaseModel):
    """Installation status of a single aircrack-ng binary."""

    installed: bool = Field(..., description="True when the binary is on `$PATH`.")
    path: str = Field("", description="Resolved path from `which`, empty if not found.", examples=["/usr/sbin/airmon-ng"])


class InterfaceInfo(BaseModel):
    """
    A wireless interface parsed from `airmon-ng`. Columns depend on the tool's
    output, so extra keys are preserved.
    """

    model_config = ConfigDict(extra="allow")

    interface: Optional[str] = Field(None, description="Interface name.", examples=["wlan0"])
    phy: Optional[str] = Field(None, description="PHY identifier.", examples=["phy0"])
    driver: Optional[str] = Field(None, description="Kernel driver.", examples=["iwlwifi"])
    chipset: Optional[str] = Field(None, description="Reported chipset.", examples=["Intel Wi-Fi 6 AX200"])
    monitor_mode: Optional[bool] = Field(None, description="True when the interface is in monitor mode.")
    mac: Optional[str] = Field(None, description="Interface MAC address.", examples=["3C:7C:3F:AA:BB:CC"])


class AirodumpData(BaseModel):
    """Networks and clients parsed from an airodump-ng CSV file."""

    networks: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Access point rows. Keys mirror the airodump-ng CSV columns (BSSID, ESSID, channel, Power, Privacy, ...).",
    )
    clients: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Client/station rows (Station MAC, BSSID, Power, # packets, Probed ESSIDs, ...).",
    )


class CaptureFile(BaseModel):
    """A single file in the capture directory."""

    name: str = Field(..., description="File name.", examples=["handshake-OfficeNet-01.cap"])
    path: str = Field(..., description="Absolute path on the server.", examples=["/tmp/airmongui/handshake-OfficeNet-01.cap"])
    size: int = Field(..., description="Size in bytes.", examples=[245678])
    modified: int = Field(..., description="Last-modified time as a Unix timestamp.", examples=[1718881200])


# ─────────────────────────────────────────────────────────────────────────────
# interfaces
# ─────────────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    version: str = Field(..., examples=["0.2.0"])


class InterfacesResponse(BaseModel):
    raw: str = Field(..., description="Raw `airmon-ng` output, as text.")
    interfaces: List[InterfaceInfo] = Field(..., description="Parsed interface list.")


class MonitorResponse(BaseModel):
    success: bool = Field(..., description="True when `airmon-ng` exited cleanly.")
    stdout: str = Field("", description="Command output.")
    stderr: str = Field("", description="Command errors.")
    returncode: int = Field(..., description="Exit code.")
    interfaces: List[InterfaceInfo] = Field(
        default_factory=list, description="Refreshed interface list after the action."
    )


class ToolCheckResponse(BaseModel):
    tools: Dict[str, ToolInfo] = Field(
        ..., description="Installation status keyed by binary name."
    )


# ─────────────────────────────────────────────────────────────────────────────
# airodump
# ─────────────────────────────────────────────────────────────────────────────

class AirodumpJob(BaseModel):
    job_id: str
    type: Optional[str] = Field(None, examples=["airodump"])
    interface: Optional[str] = None
    command: Optional[str] = None
    output_prefix: Optional[str] = None
    csv_path: Optional[str] = None
    cap_path: Optional[str] = None
    log_path: Optional[str] = None
    running: bool = Field(..., description="True while the airodump-ng process is alive.")
    start_time: Optional[int] = Field(None, description="Job start time (Unix timestamp).")


class AirodumpJobsResponse(BaseModel):
    jobs: List[AirodumpJob]


class AirodumpStartResponse(BaseModel):
    job_id: str = Field(..., description="Use this to poll results and stop the job.")
    output_prefix: str
    csv_path: str
    cap_path: str
    log_path: str
    channel_result: Optional[ChannelResult] = Field(
        None, description="Set when a single channel was locked, otherwise null."
    )
    command: str = Field(..., description="The exact airodump-ng command that was launched.")


class JobActionResponse(BaseModel):
    """Generic success acknowledgement for stop/delete style actions."""

    success: bool = True
    job_id: str


class AirodumpResultsResponse(BaseModel):
    job_id: str
    csv_path: Optional[str] = None
    cap_path: Optional[str] = None
    running: bool
    data: AirodumpData
    log_tail: str = Field("", description="Cleaned tail of the airodump-ng log.")
    channel_result: Optional[ChannelResult] = None


# ─────────────────────────────────────────────────────────────────────────────
# aireplay (deauth)
# ─────────────────────────────────────────────────────────────────────────────

class DeauthResponse(BaseModel):
    """Result of the one-shot blocking deauth endpoint."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    returncode: Optional[int] = None
    channel: Optional[ChannelResult] = Field(None, description="Channel-lock result, if a channel was set.")
    retried_channel: Optional[int] = Field(
        None, description="Set when the AP's real channel was detected and the deauth was retried there."
    )
    stopped_scan_jobs: List[str] = Field(
        default_factory=list, description="Scan job ids that were stopped to free the interface."
    )


class DeauthJob(BaseModel):
    job_id: str
    running: bool
    stopped: bool = False
    interface: Optional[str] = None
    bssid: Optional[str] = None
    client: Optional[str] = None
    count: Optional[int] = None
    channel: Optional[str] = None
    channel_result: Optional[ChannelResult] = None
    command: Optional[str] = None
    start_time: Optional[int] = None


class DeauthJobsResponse(BaseModel):
    jobs: List[DeauthJob]


class DeauthStartResponse(BaseModel):
    job_id: str
    running: bool = True
    command: str
    channel: Optional[ChannelResult] = None
    stopped_scan_jobs: List[str] = Field(default_factory=list)


class DeauthStatusResponse(BaseModel):
    job_id: str
    running: bool
    success: bool = Field(..., description="True while running, or exit code 0 after a clean finish.")
    stopped: bool = Field(False, description="True if the job was cancelled by the user.")
    returncode: Optional[int] = None
    stdout: str = Field("", description="Cleaned tail of the aireplay-ng log.")
    stderr: str = ""
    channel: Optional[ChannelResult] = None
    retried_channel: Optional[str] = None
    stopped_scan_jobs: List[str] = Field(default_factory=list)
    command: Optional[str] = None
    elapsed: int = Field(..., description="Seconds since the job started.")


# ─────────────────────────────────────────────────────────────────────────────
# aircrack
# ─────────────────────────────────────────────────────────────────────────────

class CrackJob(BaseModel):
    job_id: str
    running: bool
    returncode: Optional[int] = None
    command: Optional[str] = None
    log_path: Optional[str] = None
    start_time: Optional[int] = None
    capture_file: Optional[str] = None
    wordlist: Optional[str] = None


class CrackJobsResponse(BaseModel):
    jobs: List[CrackJob]


class CrackStartResponse(BaseModel):
    job_id: str = Field(..., description="Poll `GET /api/aircrack/{job_id}/status` with this id.")
    command: str


class ValidateNetwork(BaseModel):
    bssid: str = Field(..., examples=["A8:B2:34:90:12:CD"])
    essid: str = Field(..., examples=["OfficeNet"])
    handshake_count: int = Field(..., examples=[1])


class ValidateResponse(BaseModel):
    has_handshake: bool = Field(..., description="True when the capture holds at least one WPA handshake.")
    handshake_count: int = Field(..., description="Total handshakes across all networks in the capture.")
    networks: List[ValidateNetwork] = Field(default_factory=list)
    no_eapol: bool = Field(..., description="True when aircrack-ng reported no EAPOL data at all.")
    raw: str = Field("", description="First 3000 characters of the aircrack-ng output.")


class CrackStatusResponse(BaseModel):
    job_id: str
    running: bool
    returncode: Optional[int] = None
    key_found: bool = Field(..., description="True once the passphrase is recovered.")
    key: Optional[str] = Field(None, description="The recovered key, or null.", examples=["Summer2024!"])
    log_tail: str = Field("", description="Cleaned tail of the aircrack-ng output.")
    elapsed: int = Field(..., description="Seconds since the job started.")
    capture_file: Optional[str] = None
    command: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# handshake
# ─────────────────────────────────────────────────────────────────────────────

class HandshakeJob(BaseModel):
    job_id: str
    running: bool
    interface: Optional[str] = None
    bssid: Optional[str] = None
    channel: Optional[str] = None
    requested_channel: Optional[str] = None
    resolved_channel: Optional[str] = None
    command: Optional[str] = None
    output_prefix: Optional[str] = None
    cap_path: Optional[str] = None
    csv_path: Optional[str] = None
    log_path: Optional[str] = None
    start_time: Optional[int] = None
    channel_result: Optional[ChannelResult] = None


class HandshakeJobsResponse(BaseModel):
    jobs: List[HandshakeJob]


class HandshakeStartResponse(BaseModel):
    job_id: str
    interface: str
    cap_path: str
    csv_path: str
    bssid: str
    channel: str = Field(..., description="Channel the capture was locked to.")
    requested_channel: Optional[str] = Field(None, description="Channel the client asked for.")
    resolved_channel: Optional[str] = Field(None, description="Channel re-detected from a brief scan, if found.")
    channel_result: Optional[ChannelResult] = None
    stopped_scan_jobs: List[str] = Field(default_factory=list)
    command: str


class HandshakeStatusResponse(BaseModel):
    job_id: str
    running: bool
    handshake_detected: bool = Field(..., description="True once a WPA 4-way handshake is captured.")
    cap_path: str = ""
    cap_size: int = Field(0, description="Size of the cap file in bytes.")
    bssid: Optional[str] = None
    channel: Optional[str] = None
    requested_channel: Optional[str] = None
    resolved_channel: Optional[str] = None
    channel_result: Optional[ChannelResult] = None
    elapsed: int = Field(..., description="Seconds since the capture started.")
    log_tail: str = ""
    data: AirodumpData


class HandshakeStopResponse(BaseModel):
    success: bool = True
    job_id: str
    cap_path: Optional[str] = None
    bssid: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# captures
# ─────────────────────────────────────────────────────────────────────────────

class CapturesResponse(BaseModel):
    captures: List[CaptureFile]
    capture_dir: str = Field(..., description="Directory the files were listed from.", examples=["/tmp/airmongui"])


class DeleteCaptureResponse(BaseModel):
    success: bool = True
    deleted: str = Field(..., description="Name of the deleted file.", examples=["handshake-OfficeNet-01.cap"])
