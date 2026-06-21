"""
Hardware-free API tests for the AirmonGUI backend.

These cover request validation, path-traversal containment, and the read-only
endpoints. None of them need the aircrack-ng suite, a wireless adapter, or root,
and none start a real airodump/aireplay/aircrack job, so they are safe in CI.
"""
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(scope="module")
def client():
    # The context manager runs the app lifespan (startup and shutdown).
    with TestClient(main.app) as test_client:
        yield test_client


# ── Liveness and schema ───────────────────────────────────────────────────────

def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"]


def test_openapi_schema_generates(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    # Building the schema exercises every route and response_model.
    assert len(paths) >= 20
    assert "/api/health" in paths


@pytest.mark.parametrize("docs_path", ["/docs", "/redoc", "/openapi.json"])
def test_interactive_docs_served(client, docs_path):
    assert client.get(docs_path).status_code == 200


def test_toolcheck_returns_structure(client):
    # `which <tool>` runs even when the tools are absent (as in CI), so this
    # stays 200 and reports installed=false rather than erroring.
    resp = client.get("/api/toolcheck")
    assert resp.status_code == 200
    tools = resp.json()["tools"]
    for tool in ("airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng"):
        assert tool in tools
        assert "installed" in tools[tool]


def test_captures_listing(client):
    resp = client.get("/api/captures")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["captures"], list)
    assert body["capture_dir"]


# ── Path-traversal containment (security regression tests) ────────────────────

@pytest.mark.parametrize(
    "bad_path",
    [
        "/etc/passwd",             # absolute, outside the capture dir
        "/etc/shadow",             # absolute, outside the capture dir
        "../../etc/passwd",        # relative traversal
        "../../../etc/shadow.cap", # traversal with a valid-looking extension
    ],
)
def test_validate_rejects_paths_outside_capture_dir(client, bad_path):
    resp = client.get("/api/aircrack/validate", params={"path": bad_path})
    assert resp.status_code == 400


def test_validate_rejects_non_capture_extension(client):
    # Contained but the wrong type — rejected before aircrack-ng is invoked.
    resp = client.get("/api/aircrack/validate", params={"path": "notes.txt"})
    assert resp.status_code == 400


def test_validate_missing_file_is_404(client):
    # Contained, correct extension, simply absent.
    resp = client.get("/api/aircrack/validate", params={"path": "does-not-exist.cap"})
    assert resp.status_code == 404


# ── Request-model validation (no subprocess runs on a 422) ────────────────────

def test_crack_rejects_invalid_bssid(client):
    resp = client.post(
        "/api/aircrack/crack",
        json={
            "capture_file": "h.cap",
            "wordlist": "/usr/share/wordlists/rockyou.txt",
            "bssid": "not-a-mac",
        },
    )
    assert resp.status_code == 422


def test_crack_rejects_out_of_range_channel(client):
    resp = client.post(
        "/api/aircrack/crack",
        json={
            "capture_file": "h.cap",
            "wordlist": "/usr/share/wordlists/rockyou.txt",
            "channel": "999",
        },
    )
    assert resp.status_code == 422


def test_airodump_rejects_out_of_range_channel(client):
    resp = client.post("/api/airodump/start", json={"interface": "wlan0mon", "channel": "999"})
    assert resp.status_code == 422


def test_airodump_rejects_invalid_bssid(client):
    resp = client.post("/api/airodump/start", json={"interface": "wlan0mon", "bssid": "ZZ:ZZ"})
    assert resp.status_code == 422


def test_monitor_rejects_unknown_action(client):
    # The handler validates the action before touching airmon-ng.
    resp = client.post("/api/monitor", json={"interface": "wlan0", "action": "frobnicate"})
    assert resp.status_code == 400
