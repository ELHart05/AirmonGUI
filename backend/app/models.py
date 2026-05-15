import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")


def _validate_mac(v: Optional[str]) -> Optional[str]:
    if v and not _MAC_RE.match(v):
        raise ValueError("Must be a valid MAC address (XX:XX:XX:XX:XX:XX)")
    return v


class MonitorRequest(BaseModel):
    interface: str = Field(..., examples=["wlan0"])
    action: str = Field(..., examples=["start"])


class CheckKillRequest(BaseModel):
    interface: str = Field(
        ...,
        description="Wireless interface whose interfering processes should be released.",
        examples=["wlan0"],
    )


class DeauthRequest(BaseModel):
    interface: str
    bssid: str
    client: Optional[str] = None
    count: int = 10
    channel: Optional[int] = None

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


class AirodumpStartRequest(BaseModel):
    interface: str
    channel: Optional[str] = None
    band: Optional[str] = None
    bssid: Optional[str] = None
    output_prefix: Optional[str] = None


class AirodumpStopRequest(BaseModel):
    job_id: str


class AircrackRequest(BaseModel):
    capture_file: str
    wordlist: str
    bssid: Optional[str] = None
    channel: Optional[str] = None


class HandshakeCaptureRequest(BaseModel):
    interface: str
    bssid: str
    channel: str
    output_prefix: Optional[str] = None

    @field_validator("bssid")
    @classmethod
    def validate_bssid(cls, v: str) -> str:
        if not _MAC_RE.match(v):
            raise ValueError("BSSID must be a valid MAC address")
        return v
