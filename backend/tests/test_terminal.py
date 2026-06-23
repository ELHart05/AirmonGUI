"""
Tests for the WebSocket terminal gate (issue #1, revised).

The terminal spawns a real shell, so these exercise the gate decision directly
instead of opening a socket. AIRMON_GUI_TERMINAL_ENABLED is the single switch.
Beyond it the gate is silent plumbing: a foreign Origin is always rejected, and
while auth is enabled the API token is required. With auth off (loopback only) the
flag and Origin are the gate.
"""
import os

import pytest
from fastapi.testclient import TestClient

import main
from app.routes import terminal

TOKEN = os.environ["AIRMON_GUI_AUTH_TOKEN"]
ORIGIN = "http://localhost:5173"


@pytest.fixture
def gate(monkeypatch):
    # Baseline: enabled, auth on, our origin allowed, real token.
    monkeypatch.setattr(terminal, "TERMINAL_ENABLED", True)
    monkeypatch.setattr(terminal, "AUTH_ENABLED", True)
    monkeypatch.setattr(terminal, "ALLOWED_WS_ORIGINS", [ORIGIN])
    monkeypatch.setattr(terminal, "AUTH_TOKEN", TOKEN)


def test_disabled_blocks(gate, monkeypatch):
    monkeypatch.setattr(terminal, "TERMINAL_ENABLED", False)
    assert terminal.terminal_gate(ORIGIN, TOKEN) is not None


def test_allows_valid_token_and_origin(gate):
    assert terminal.terminal_gate(ORIGIN, TOKEN) is None


def test_allows_non_browser_client_without_origin(gate):
    assert terminal.terminal_gate(None, TOKEN) is None


def test_rejects_missing_token(gate):
    assert terminal.terminal_gate(ORIGIN, None) is not None


def test_rejects_wrong_token(gate):
    assert terminal.terminal_gate(ORIGIN, "nope") is not None


def test_rejects_foreign_origin(gate):
    assert terminal.terminal_gate("https://evil.example", TOKEN) is not None


def test_auth_off_allows_without_token(gate, monkeypatch):
    # With auth off the flag and Origin are the gate; no token needed.
    monkeypatch.setattr(terminal, "AUTH_ENABLED", False)
    assert terminal.terminal_gate(ORIGIN, None) is None


def test_auth_off_still_rejects_foreign_origin(gate, monkeypatch):
    # Origin is checked regardless of auth, so a hostile page is still blocked.
    monkeypatch.setattr(terminal, "AUTH_ENABLED", False)
    assert terminal.terminal_gate("https://evil.example", None) is not None


def test_mounted_route_rejects_tokenless_connect():
    # The route is mounted by default now; a connect with no token is closed by the
    # gate before any shell is spawned.
    with TestClient(main.app) as client:
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/terminal"):
                pass
