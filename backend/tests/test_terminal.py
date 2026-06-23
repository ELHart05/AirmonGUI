"""
Tests for the WebSocket terminal gate (issue #1, revised).

The terminal spawns a real shell, so these exercise the gate decision directly
instead of opening a socket. Defaults changed: the terminal is on by default and,
when auth is enabled, the token is the gate (a root shell is allowed because the
token already grants the root-capable API). When auth is disabled, an
unauthenticated root shell is refused unless the break-glass flag is set.
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
    # Baseline: enabled, auth on, non-root, our origin allowed, real token.
    monkeypatch.setattr(terminal, "TERMINAL_ENABLED", True)
    monkeypatch.setattr(terminal, "AUTH_ENABLED", True)
    monkeypatch.setattr(terminal, "ALLOW_TERMINAL_AS_ROOT", False)
    monkeypatch.setattr(terminal, "ALLOWED_WS_ORIGINS", [ORIGIN])
    monkeypatch.setattr(terminal, "AUTH_TOKEN", TOKEN)
    monkeypatch.setattr(os, "geteuid", lambda: 1000)


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


def test_auth_on_allows_root(gate, monkeypatch):
    # With auth on, the token gates the shell, so root is fine.
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    assert terminal.terminal_gate(ORIGIN, TOKEN) is None


def test_auth_off_allows_non_root(gate, monkeypatch):
    monkeypatch.setattr(terminal, "AUTH_ENABLED", False)
    assert terminal.terminal_gate(ORIGIN, None) is None


def test_auth_off_rejects_root_without_breakglass(gate, monkeypatch):
    monkeypatch.setattr(terminal, "AUTH_ENABLED", False)
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    assert terminal.terminal_gate(ORIGIN, None) is not None


def test_auth_off_allows_root_with_breakglass(gate, monkeypatch):
    monkeypatch.setattr(terminal, "AUTH_ENABLED", False)
    monkeypatch.setattr(terminal, "ALLOW_TERMINAL_AS_ROOT", True)
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    assert terminal.terminal_gate(ORIGIN, None) is None


def test_mounted_route_rejects_tokenless_connect():
    # The route is mounted by default now; a connect with no token is closed by the
    # gate before any shell is spawned.
    with TestClient(main.app) as client:
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/terminal"):
                pass
