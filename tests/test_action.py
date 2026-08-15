"""Unit tests for action.py and clear_clipboard.py — imported in-process for coverage."""

import json
import subprocess
from types import SimpleNamespace

import pytest

import action
import clear_clipboard


def _completed(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("alfred_workflow_cache", str(tmp_path))
    return tmp_path


@pytest.fixture
def spy_run(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return _completed()

    monkeypatch.setattr(action.subprocess, "run", fake_run)
    return calls


def test_find_pass_cli_prefers_explicit_path(monkeypatch):
    monkeypatch.setenv("PASS_CLI_PATH", "/custom/pass-cli")
    assert action._find_pass_cli() == "/custom/pass-cli"


def test_find_pass_cli_falls_back_to_bare_name(monkeypatch):
    monkeypatch.setenv("PASS_CLI_PATH", "")
    monkeypatch.setattr(action.os.path, "exists", lambda _p: False)
    assert action._find_pass_cli() == "pass-cli"


def test_find_pass_cli_takes_first_existing_default(monkeypatch):
    monkeypatch.setenv("PASS_CLI_PATH", "")
    expected = action._DEFAULT_CLI_PATHS[2]
    monkeypatch.setattr(action.os.path, "exists", lambda p: p == expected)
    assert action._find_pass_cli() == expected


def test_cache_dir_defaults_to_home(tmp_path, monkeypatch):
    monkeypatch.delenv("alfred_workflow_cache", raising=False)
    monkeypatch.setattr(action.os.path, "expanduser", lambda _p: str(tmp_path))
    assert action.get_cache_dir() == str(tmp_path / ".cache" / "alfred-proton-pass")


def test_mark_logged_out_writes_the_shared_flag(cache_dir):
    action.mark_logged_out()
    with open(cache_dir / "auth.json") as f:
        assert json.load(f) == {"logged_in": False}


def test_mark_logged_out_swallows_write_errors(monkeypatch, cache_dir):
    def boom(*_a, **_k):
        raise OSError("read-only")

    monkeypatch.setattr("builtins.open", boom)
    action.mark_logged_out()


def test_notify_passes_message_as_argv(spy_run):
    action.notify("copy failed")
    cmd = spy_run[0][0]
    assert cmd[0] == "osascript"
    assert cmd[-2:] == ["copy failed", "Proton Pass"]


def test_notify_flattens_newlines_and_defaults(spy_run):
    action.notify("line one\nline two")
    assert spy_run[0][0][-2] == "line one line two"
    action.notify("   ")
    assert spy_run[1][0][-2] == "Action failed"


def test_notify_survives_a_missing_osascript(monkeypatch):
    def boom(*_a, **_k):
        raise FileNotFoundError

    monkeypatch.setattr(action.subprocess, "run", boom)
    action.notify("whatever")


def test_notify_survives_a_hung_osascript(monkeypatch):
    def boom(*_a, **_k):
        raise subprocess.TimeoutExpired("osascript", 5)

    monkeypatch.setattr(action.subprocess, "run", boom)
    action.notify("whatever")


@pytest.mark.parametrize("error", [
    "Error: not logged in",
    "401 Unauthorized",
    "session expired",
    "please login first",
    "auth required",
])
def test_handle_failure_flags_auth_errors(monkeypatch, error):
    flagged, messages = [], []
    monkeypatch.setattr(action, "mark_logged_out", lambda: flagged.append(True))
    monkeypatch.setattr(action, "notify", messages.append)
    action.handle_failure(error)
    assert flagged == [True]
    assert "pass-cli login" in messages[0]


def test_handle_failure_passes_other_errors_through(monkeypatch):
    monkeypatch.setattr(action, "mark_logged_out", lambda: pytest.fail("not an auth error"))
    messages = []
    monkeypatch.setattr(action, "notify", messages.append)
    action.handle_failure("disk on fire")
    assert messages == ["disk on fire"]


def test_handle_failure_without_message(monkeypatch):
    messages = []
    monkeypatch.setattr(action, "notify", messages.append)
    action.handle_failure(None)
    assert messages == ["Action failed"]


def test_get_password_returns_trimmed_secret(monkeypatch):
    monkeypatch.setattr(action.subprocess, "run", lambda *a, **k: _completed(stdout="s3cret\n"))
    assert action.get_password("Personal", "last.fm") == ("s3cret", None)


def test_get_password_reports_stderr(monkeypatch):
    monkeypatch.setattr(
        action.subprocess, "run", lambda *a, **k: _completed(returncode=1, stderr=" nope \n")
    )
    assert action.get_password("Personal", "last.fm") == (None, "nope")


@pytest.mark.parametrize("stdout,expected", [
    ('{"totp": "123456"}', "123456"),
    ('{"code": "654321"}', "654321"),
    ("123456\n", "123456"),
    ('["123456"]', '["123456"]'),
    ("not json at all", "not json at all"),
])
def test_get_totp_extracts_the_code(monkeypatch, stdout, expected):
    monkeypatch.setattr(action.subprocess, "run", lambda *a, **k: _completed(stdout=stdout))
    assert action.get_totp("Personal", "last.fm") == (expected, None)


def test_get_totp_reports_stderr(monkeypatch):
    monkeypatch.setattr(
        action.subprocess, "run", lambda *a, **k: _completed(returncode=1, stderr="no totp")
    )
    assert action.get_totp("Personal", "last.fm") == (None, "no totp")


def test_copy_to_clipboard_feeds_pbcopy(spy_run):
    action.copy_to_clipboard("s3cret")
    cmd, kwargs = spy_run[0]
    assert cmd == ["pbcopy"] and kwargs["input"] == b"s3cret"


def test_clear_clipboard_later_detaches(monkeypatch):
    calls = []
    monkeypatch.setattr(action.subprocess, "Popen", lambda cmd, **kw: calls.append((cmd, kw)))
    action.clear_clipboard_later(30)
    cmd, kwargs = calls[0]
    assert cmd[1].endswith("clear_clipboard.py") and cmd[2] == "30"
    assert kwargs["start_new_session"] is True


def test_copy_secret_copies_and_schedules_a_wipe(monkeypatch):
    copied, scheduled = [], []
    monkeypatch.setattr(action, "copy_to_clipboard", copied.append)
    monkeypatch.setattr(action, "clear_clipboard_later", scheduled.append)
    action.copy_secret(lambda _v, _t: ("s3cret", None), "Personal", "last.fm")
    assert copied == ["s3cret"]
    assert scheduled == [action.CLIPBOARD_CLEAR_SECONDS]


def test_copy_secret_reports_failures_instead_of_copying(monkeypatch):
    monkeypatch.setattr(action, "copy_to_clipboard", lambda _t: pytest.fail("nothing to copy"))
    failures = []
    monkeypatch.setattr(action, "handle_failure", failures.append)
    action.copy_secret(lambda _v, _t: (None, "not logged in"), "Personal", "last.fm")
    assert failures == ["not logged in"]


@pytest.mark.parametrize("url,expected", [
    ("https://last.fm", "https://last.fm"),
    ("http://last.fm", "http://last.fm"),
    ("last.fm", "https://last.fm"),
    ("last.fm/login?a=b", "https://last.fm/login?a=b"),
])
def test_open_url_opens_web_targets(spy_run, url, expected):
    action.open_url(url)
    cmd, kwargs = spy_run[0]
    assert cmd == ["open", expected]
    assert kwargs["timeout"] == 10


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://example.com/x",
    "x-malicious-handler://run",
    "/Applications/Calculator.app",
])
def test_open_url_refuses_non_web_targets(monkeypatch, url):
    monkeypatch.setattr(action.subprocess, "run", lambda *a, **k: pytest.fail("must not open"))
    messages = []
    monkeypatch.setattr(action, "notify", messages.append)
    action.open_url(url)
    assert "Refused" in messages[0]


def test_open_url_reports_a_hung_open(monkeypatch):
    def boom(*_a, **_k):
        raise subprocess.TimeoutExpired("open", 10)

    monkeypatch.setattr(action.subprocess, "run", boom)
    messages = []
    monkeypatch.setattr(action, "notify", messages.append)
    action.open_url("https://last.fm")
    assert messages == ["Could not open URL"]


def test_clear_item_cache_removes_the_file(cache_dir):
    cache_file = cache_dir / "items.json"
    cache_file.write_text("[]")
    action.clear_item_cache()
    assert not cache_file.exists()


def test_clear_item_cache_is_a_noop_without_a_cache(cache_dir):
    action.clear_item_cache()
    assert not (cache_dir / "items.json").exists()


@pytest.fixture
def dispatch(monkeypatch):
    """Records what main() did, with every side effect stubbed out."""
    log = {"copied": [], "scheduled": [], "failed": [], "opened": [], "cleared": []}
    monkeypatch.setattr(action, "copy_to_clipboard", log["copied"].append)
    monkeypatch.setattr(action, "clear_clipboard_later", log["scheduled"].append)
    monkeypatch.setattr(action, "handle_failure", log["failed"].append)
    monkeypatch.setattr(action, "clear_item_cache", lambda: log["cleared"].append(True))
    monkeypatch.setattr(action.subprocess, "run", lambda cmd, **k: log["opened"].append(cmd))
    for var in ("action", "vaultName", "itemTitle", "username", "url"):
        monkeypatch.delenv(var, raising=False)
    return log


def test_main_password_action(monkeypatch, dispatch):
    monkeypatch.setenv("action", "password")
    monkeypatch.setattr(action, "get_password", lambda _v, _t: ("s3cret", None))
    action.main()
    assert dispatch["copied"] == ["s3cret"] and dispatch["scheduled"]


def test_main_password_failure_is_not_silent(monkeypatch, dispatch):
    monkeypatch.setenv("action", "password")
    monkeypatch.setattr(action, "get_password", lambda _v, _t: (None, "not logged in"))
    action.main()
    assert dispatch["copied"] == [] and dispatch["failed"] == ["not logged in"]


def test_main_totp_action(monkeypatch, dispatch):
    monkeypatch.setenv("action", "totp")
    monkeypatch.setattr(action, "get_totp", lambda _v, _t: ("123456", None))
    action.main()
    assert dispatch["copied"] == ["123456"]


def test_main_username_action(monkeypatch, dispatch):
    monkeypatch.setenv("action", "username")
    monkeypatch.setenv("username", "me@example.com")
    action.main()
    assert dispatch["copied"] == ["me@example.com"]


def test_main_username_action_without_a_username(monkeypatch, dispatch):
    monkeypatch.setenv("action", "username")
    action.main()
    assert dispatch["copied"] == []


def test_main_url_action(monkeypatch, dispatch):
    monkeypatch.setenv("action", "url")
    monkeypatch.setenv("url", "https://last.fm")
    action.main()
    assert dispatch["opened"] == [["open", "https://last.fm"]]


def test_main_url_action_without_a_url(monkeypatch, dispatch):
    monkeypatch.setenv("action", "url")
    action.main()
    assert dispatch["opened"] == []


def test_main_refresh_action(monkeypatch, dispatch):
    monkeypatch.setenv("action", "refresh")
    action.main()
    assert dispatch["cleared"] == [True]


def test_main_ignores_an_unknown_action(monkeypatch, dispatch):
    monkeypatch.setenv("action", "nonsense")
    action.main()
    assert dispatch == {"copied": [], "scheduled": [], "failed": [],
                        "opened": [], "cleared": []}


def test_clear_clipboard_wipes_unchanged_clipboard(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return _completed(stdout=b"s3cret")

    monkeypatch.setattr(clear_clipboard.subprocess, "run", fake_run)
    monkeypatch.setattr(clear_clipboard.time, "sleep", lambda _s: None)
    monkeypatch.setattr(clear_clipboard.sys, "argv", ["clear_clipboard.py", "5"])
    clear_clipboard.main()
    assert calls[-1][0] == ["pbcopy"] and calls[-1][1]["input"] == b""


def test_clear_clipboard_leaves_a_changed_clipboard_alone(monkeypatch):
    outputs = [b"s3cret", b"something the user copied since"]
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _completed(stdout=outputs[len(calls) - 1])

    monkeypatch.setattr(clear_clipboard.subprocess, "run", fake_run)
    monkeypatch.setattr(clear_clipboard.time, "sleep", lambda _s: None)
    monkeypatch.setattr(clear_clipboard.sys, "argv", ["clear_clipboard.py"])
    clear_clipboard.main()
    assert calls == [["pbpaste"], ["pbpaste"]]
