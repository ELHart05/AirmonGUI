"""
Tests for the dependency-free .env loader in app.config.

The loader runs at import as root, so its rules matter: an already-exported
variable must win over the file, and comments/blanks/quotes are handled without
pulling in a third-party parser. monkeypatch restores the environment after each
test, so these stay hermetic.
"""
import os

from app import config


def test_load_env_file_sets_unset_keys(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# a comment\n"
        "\n"
        "AIRMON_GUI_FAKE_ONE=hello\n"
        'AIRMON_GUI_FAKE_TWO="quoted value"\n'
    )
    monkeypatch.delenv("AIRMON_GUI_FAKE_ONE", raising=False)
    monkeypatch.delenv("AIRMON_GUI_FAKE_TWO", raising=False)

    config._load_env_file(str(env_path))

    assert os.environ["AIRMON_GUI_FAKE_ONE"] == "hello"
    assert os.environ["AIRMON_GUI_FAKE_TWO"] == "quoted value"


def test_load_env_file_keeps_inner_and_unmatched_quotes(tmp_path, monkeypatch):
    # Only a single matched surrounding pair is stripped; a quote that is part of
    # the value (interior, or an unmatched edge quote) survives intact.
    env_path = tmp_path / ".env"
    env_path.write_text(
        "AIRMON_GUI_FAKE_ONE=tok\"en\n"
        "AIRMON_GUI_FAKE_TWO=trailing\"\n"
    )
    monkeypatch.delenv("AIRMON_GUI_FAKE_ONE", raising=False)
    monkeypatch.delenv("AIRMON_GUI_FAKE_TWO", raising=False)

    config._load_env_file(str(env_path))

    assert os.environ["AIRMON_GUI_FAKE_ONE"] == 'tok"en'
    assert os.environ["AIRMON_GUI_FAKE_TWO"] == 'trailing"'


def test_load_env_file_does_not_override_exported(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("AIRMON_GUI_FAKE_THREE=from_file\n")
    monkeypatch.setenv("AIRMON_GUI_FAKE_THREE", "from_shell")

    config._load_env_file(str(env_path))

    assert os.environ["AIRMON_GUI_FAKE_THREE"] == "from_shell"


def test_load_env_file_missing_is_silent(tmp_path):
    # A missing file is not an error; the backend just falls back to defaults.
    config._load_env_file(str(tmp_path / "does-not-exist.env"))
