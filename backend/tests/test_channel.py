"""
Tests for interface-mode detection and the channel-lock behaviour reported on
Reddit: a managed interface gives a clear error, and a failed channel pre-lock no
longer aborts a scan (airodump-ng tunes the channel itself via -c).
"""
import subprocess
import types

import pytest

from app import utils
from app.routes import airodump
from app.state import JOBS

IW_MONITOR = "Interface wlan0mon\n\ttype monitor\n\tchannel 6 (2437 MHz)\n"
IW_MANAGED = "Interface wlan0\n\ttype managed\n"


def _fake_run(output):
    def run(*_args, **_kwargs):
        return types.SimpleNamespace(stdout=output, stderr="", returncode=0)
    return run


def test_interface_mode_monitor(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run(IW_MONITOR))
    assert utils.interface_mode("wlan0mon") == "monitor"


def test_interface_mode_managed(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run(IW_MANAGED))
    assert utils.interface_mode("wlan0") == "managed"


def test_interface_mode_unknown_when_iw_missing(monkeypatch):
    def boom(*_args, **_kwargs):
        raise FileNotFoundError("iw")
    monkeypatch.setattr(subprocess, "run", boom)
    assert utils.interface_mode("wlan0") == ""


def test_scan_rejects_managed_interface(client, monkeypatch):
    monkeypatch.setattr(airodump, "interface_mode", lambda _iface: "managed")
    resp = client.post("/api/airodump/start", json={"interface": "wlan0"})
    assert resp.status_code == 400
    assert "monitor mode" in resp.json()["detail"]


def test_scan_starts_despite_failed_channel_lock(client, monkeypatch):
    # Monitor interface, but the channel readback fails to verify. The scan should
    # still start (airodump-ng tunes with -c) rather than 409.
    monkeypatch.setattr(airodump, "interface_mode", lambda _iface: "monitor")
    monkeypatch.setattr(
        airodump,
        "set_interface_channel",
        lambda _iface, _ch: {"success": False, "requested": "1", "current": "", "verified": False, "stderr": "unverified"},
    )

    class FakeProc:
        def poll(self):
            return None

    monkeypatch.setattr(airodump.subprocess, "Popen", lambda *a, **k: FakeProc())

    class FakeHandle:
        closed = False
        def close(self):
            self.closed = True

    monkeypatch.setattr(airodump, "secure_open", lambda *a, **k: FakeHandle())

    resp = client.post("/api/airodump/start", json={"interface": "wlan0mon", "channel": "1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"]
    # The unverified lock is surfaced, not fatal.
    assert body["channel_result"]["success"] is False
    # Don't leak the fake job into the shared store other tests share.
    JOBS.pop(body["job_id"], None)
