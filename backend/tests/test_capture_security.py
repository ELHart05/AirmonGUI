"""
Tests for capture-directory hardening (issue #3).

Cover the symlink-clobber and world-readable risks: secure_open refuses a
symlink and writes private files, ensure_capture_dir refuses an unsafe directory,
safe_capture_path rejects traversal and symlinks, and the listing skips symlinks.
"""
import os
import stat

import pytest
from fastapi import HTTPException

from app.config import CAPTURE_DIR
from app.utils import ensure_capture_dir, safe_capture_path, secure_open


def test_secure_open_creates_private_file():
    path = os.path.join(CAPTURE_DIR, "mode_check.log")
    try:
        with secure_open(path, "w") as fh:
            fh.write("hello")
        mode = stat.S_IMODE(os.lstat(path).st_mode)
        assert mode == 0o600
    finally:
        os.remove(path)


def test_secure_open_refuses_symlink(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("important")
    link = tmp_path / "evil.log"
    link.symlink_to(target)
    # O_NOFOLLOW makes the open fail rather than clobber the symlink target.
    with pytest.raises(OSError):
        secure_open(str(link), "w")
    assert target.read_text() == "important"


def test_ensure_capture_dir_rejects_symlink(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(RuntimeError):
        ensure_capture_dir(str(link))


def test_ensure_capture_dir_rejects_non_directory(tmp_path):
    a_file = tmp_path / "afile"
    a_file.write_text("x")
    with pytest.raises(RuntimeError):
        ensure_capture_dir(str(a_file))


def test_ensure_capture_dir_rejects_wrong_owner(tmp_path, monkeypatch):
    d = tmp_path / "owned"
    d.mkdir()
    # Pretend we are a different user than the one who owns the directory.
    monkeypatch.setattr(os, "geteuid", lambda: os.lstat(str(d)).st_uid + 1)
    with pytest.raises(RuntimeError):
        ensure_capture_dir(str(d))


def test_ensure_capture_dir_forces_0700(tmp_path):
    d = tmp_path / "loose"
    d.mkdir(mode=0o755)
    os.chmod(str(d), 0o755)
    ensure_capture_dir(str(d))
    assert stat.S_IMODE(os.lstat(str(d)).st_mode) == 0o700


def test_safe_capture_path_rejects_traversal():
    with pytest.raises(HTTPException):
        safe_capture_path("../../etc/passwd")


def test_safe_capture_path_rejects_symlink():
    link = os.path.join(CAPTURE_DIR, "sneaky")
    os.symlink("/etc/passwd", link)
    try:
        with pytest.raises(HTTPException):
            safe_capture_path("sneaky")
    finally:
        os.remove(link)


def test_capture_listing_skips_symlinks(client):
    link = os.path.join(CAPTURE_DIR, "sneaky.cap")
    os.symlink("/etc/passwd", link)
    try:
        resp = client.get("/api/captures")
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["captures"]]
        assert "sneaky.cap" not in names
    finally:
        os.remove(link)
