import os
from stat import S_ISREG

from fastapi import APIRouter, HTTPException, Path

from ..config import CAPTURE_DIR
from ..models import CapturesResponse, DeleteCaptureResponse, ErrorResponse

router = APIRouter(prefix="/captures", tags=["captures"])


@router.get(
    "",
    summary="List capture files",
    response_model=CapturesResponse,
    response_description="Files in the capture directory (.cap .pcap .csv .ivs .log)",
)
def list_captures() -> dict:
    """List every capture-related file in the capture directory with size and modified time."""
    items = []
    for name in sorted(os.listdir(CAPTURE_DIR)):
        if name.endswith((".cap", ".csv", ".pcap", ".ivs", ".log")):
            full = os.path.join(CAPTURE_DIR, name)
            try:
                stat = os.lstat(full)
            except OSError:
                continue  # file vanished between listdir and lstat
            if not S_ISREG(stat.st_mode):
                continue  # skip symlinks and anything that is not a regular file
            items.append(
                {
                    "name": name,
                    "path": full,
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime),
                }
            )
    return {"captures": items, "capture_dir": CAPTURE_DIR}


@router.get(
    "/cap",
    summary="List crackable capture files",
    response_model=CapturesResponse,
    response_description=".cap / .pcap / .ivs files suitable for aircrack-ng",
)
def list_cap_files() -> dict:
    """List only .cap / .pcap / .ivs files suitable for aircrack-ng."""
    items = []
    for name in sorted(os.listdir(CAPTURE_DIR)):
        if name.endswith((".cap", ".pcap", ".ivs")):
            full = os.path.join(CAPTURE_DIR, name)
            try:
                stat = os.lstat(full)
            except OSError:
                continue  # file vanished between listdir and lstat
            if not S_ISREG(stat.st_mode):
                continue  # skip symlinks and anything that is not a regular file
            items.append(
                {
                    "name": name,
                    "path": full,
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime),
                }
            )
    return {"captures": items, "capture_dir": CAPTURE_DIR}


@router.delete(
    "/{filename}",
    summary="Delete a capture file",
    response_model=DeleteCaptureResponse,
    response_description="Confirmation with the deleted filename",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid filename, path traversal, or disallowed type"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
)
def delete_capture(
    filename: str = Path(
        ...,
        description="Name of the file to delete. Must be a bare file name with no path components.",
        examples=["handshake-OfficeNet-01.cap"],
    ),
) -> dict:
    """Delete one file from the capture directory after validating the name and extension."""
    # Reject anything that looks like a path component
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")

    abs_dir = os.path.realpath(CAPTURE_DIR)
    joined = os.path.join(abs_dir, filename)
    # Reject a symlink outright so deletion cannot be redirected through one.
    if os.path.islink(joined):
        raise HTTPException(status_code=400, detail="Path traversal detected")
    abs_path = os.path.realpath(joined)
    if not abs_path.startswith(abs_dir + os.sep):
        raise HTTPException(status_code=400, detail="Path traversal detected")

    allowed_exts = (".cap", ".csv", ".pcap", ".ivs", ".log")
    if not any(filename.endswith(ext) for ext in allowed_exts):
        raise HTTPException(status_code=400, detail="File type not allowed")

    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")

    os.remove(abs_path)
    return {"success": True, "deleted": filename}
