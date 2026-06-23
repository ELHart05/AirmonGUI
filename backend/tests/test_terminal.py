"""
Tests for the WebSocket terminal gate (issue #1).

The terminal spawns a real shell, so these exercise the gate decision directly
instead of opening a socket. The gate is what runs before `accept()`, so proving
it rejects the unsafe cases is what matters.
"""
import os

import pytest
from fastapi.testclient import TestClient

import main
from app.routes import terminal

TOKEN = os.environ["AIRMON_GUI_AUTH_TOKEN"]
ORIGIN = "http://localhost:5173"


@pytest.fixture
def enabled(monkeypatch):
    # Turn the feature on and run as non-root for the "happy path" checks.
    monkeypatch.setattr(terminal, "TERMINAL_ENABLED", True)
    monkeypatch.setattr(terminal, "ALLOW_TERMINAL_AS_ROOT", False)
    monkeypatch.setattr(terminal, "ALLOWED_WS_ORIGINS", [ORIGIN])
    monkeypatch.setattr(terminal, "AUTH_TOKEN", TOKEN)
    monkeypatch.setattr(os, "geteuid", lambda: 1000)


def test_disabled_by_default():
    # With the default config the feature flag is off, regardless of token.
    assert terminal.terminal_gate(ORIGIN, TOKEN) is not None


def test_allows_valid_token_and_origin(enabled):
    assert terminal.terminal_gate(ORIGIN, TOKEN) is None


def test_allows_non_browser_client_without_origin(enabled):
    # No Origin header (curl/websocat): the token alone decides.
    assert terminal.terminal_gate(None, TOKEN) is None


def test_rejects_missing_token(enabled):
    assert terminal.terminal_gate(ORIGIN, None) is not None


def test_rejects_wrong_token(enabled):
    assert terminal.terminal_gate(ORIGIN, "nope") is not None


def test_rejects_foreign_origin(enabled):
    # A hostile page carries its own origin and is blocked (CSWSH defense).
    assert terminal.terminal_gate("https://evil.example", TOKEN) is not None


def test_rejects_root_without_breakglass(enabled, monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    assert terminal.terminal_gate(ORIGIN, TOKEN) is not None


def test_allows_root_with_breakglass(enabled, monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.setattr(terminal, "ALLOW_TERMINAL_AS_ROOT", True)
    assert terminal.terminal_gate(ORIGIN, TOKEN) is None


def test_route_absent_when_disabled():
    # The router is not even mounted by default, so a connect attempt fails before
    # any gate logic runs.
    with TestClient(main.app) as client:
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/terminal"):
                pass
