import os

from fastapi import APIRouter, HTTPException

from ..config import CAPTURE_DIR

router = APIRouter(prefix="/captures", tags=["captures"])


@router.get("", summary="List capture files",
            response_description="Files in the capture directory (.cap .pcap .csv .ivs .log)")
def list_captures() -> dict:
    items = []
    for name in sorted(os.listdir(CAPTURE_DIR)):
        if name.endswith((".cap", ".csv", ".pcap", ".ivs", ".log")):
            full = os.path.join(CAPTURE_DIR, name)
            stat = os.stat(full)
            items.append(
                {
                    "name": name,
                    "path": full,
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime),
                }
            )
    return {"captures": items, "capture_dir": CAPTURE_DIR}


@router.get("/cap", summary="List crackable capture files",
            response_description=".cap / .pcap / .ivs files suitable for aircrack-ng")
def list_cap_files() -> dict:
    """List only .cap / .pcap / .ivs files suitable for aircrack-ng."""
    items = []
    for name in sorted(os.listdir(CAPTURE_DIR)):
        if name.endswith((".cap", ".pcap", ".ivs")):
            full = os.path.join(CAPTURE_DIR, name)
            stat = os.stat(full)
            items.append(
                {
                    "name": name,
                    "path": full,
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime),
                }
            )
    return {"captures": items, "capture_dir": CAPTURE_DIR}


@router.delete("/{filename}", summary="Delete a capture file",
               response_description="Confirmation with the deleted filename")
def delete_capture(filename: str) -> dict:
    # Reject anything that looks like a path component
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")

    abs_dir = os.path.abspath(CAPTURE_DIR)
    abs_path = os.path.abspath(os.path.join(abs_dir, filename))
    if not abs_path.startswith(abs_dir + os.sep):
        raise HTTPException(status_code=400, detail="Path traversal detected")

    allowed_exts = (".cap", ".csv", ".pcap", ".ivs", ".log")
    if not any(filename.endswith(ext) for ext in allowed_exts):
        raise HTTPException(status_code=400, detail="File type not allowed")

    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="File not found")

    os.remove(abs_path)
    return {"success": True, "deleted": filename}
