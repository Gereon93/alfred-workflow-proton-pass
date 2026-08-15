"""Unit tests for search.py — imported in-process so coverage sees the lines."""

import json
import os
import subprocess
import time
from types import SimpleNamespace

import pytest

import search


def _completed(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("alfred_workflow_cache", str(tmp_path))
    return tmp_path


def test_find_pass_cli_prefers_explicit_path(monkeypatch):
    monkeypatch.setenv("PASS_CLI_PATH", "/custom/pass-cli")
    assert search._find_pass_cli() == "/custom/pass-cli"


def test_find_pass_cli_falls_back_to_bare_name(monkeypatch):
    monkeypatch.setenv("PASS_CLI_PATH", "")
    monkeypatch.setattr(search.os.path, "exists", lambda _p: False)
    assert search._find_pass_cli() == "pass-cli"


def test_find_pass_cli_takes_first_existing_default(monkeypatch):
    monkeypatch.setenv("PASS_CLI_PATH", "")
    expected = search._DEFAULT_CLI_PATHS[1]
    monkeypatch.setattr(search.os.path, "exists", lambda p: p == expected)
    assert search._find_pass_cli() == expected


def test_cache_roundtrip(cache_dir):
    search.save_cache([{"title": "a"}])
    assert search.load_cached_items() == [{"title": "a"}]


def test_cache_ignored_when_older_than_ttl(cache_dir):
    search.save_cache([{"title": "a"}])
    stale = time.time() - search.CACHE_TTL - 1
    os.utime(search.get_cache_path(), (stale, stale))
    assert search.load_cached_items() is None


def test_cache_missing_returns_none(cache_dir):
    assert search.load_cached_items() is None


def test_cache_corrupt_returns_none(cache_dir):
    with open(search.get_cache_path(), "w") as f:
        f.write("{not json")
    assert search.load_cached_items() is None


def test_cache_dir_defaults_to_home(tmp_path, monkeypatch):
    monkeypatch.delenv("alfred_workflow_cache", raising=False)
    monkeypatch.setattr(search.os.path, "expanduser", lambda _p: str(tmp_path))
    assert search.get_cache_dir() == str(tmp_path / ".cache" / "alfred-proton-pass")


def test_write_auth_flag_persists_bool(cache_dir):
    search.write_auth_flag(True)
    with open(search.get_auth_cache_path()) as f:
        assert json.load(f) == {"logged_in": True}


def test_write_auth_flag_swallows_write_errors(monkeypatch, cache_dir):
    def boom(*_a, **_k):
        raise OSError("read-only")

    monkeypatch.setattr("builtins.open", boom)
    search.write_auth_flag(True)


def test_login_status_uses_fresh_logged_in_cache(monkeypatch, cache_dir):
    search.write_auth_flag(True)
    monkeypatch.setattr(search, "probe_login", lambda: pytest.fail("must not re-probe"))
    assert search.get_login_status() is True


def test_login_status_reprobes_a_cached_logout(monkeypatch, cache_dir):
    search.write_auth_flag(False)
    monkeypatch.setattr(search, "probe_login", lambda: True)
    assert search.get_login_status() is True
    with open(search.get_auth_cache_path()) as f:
        assert json.load(f)["logged_in"] is True


def test_login_status_reprobes_an_expired_cache(monkeypatch, cache_dir):
    search.write_auth_flag(True)
    stale = time.time() - search.AUTH_TTL - 1
    os.utime(search.get_auth_cache_path(), (stale, stale))
    monkeypatch.setattr(search, "probe_login", lambda: False)
    assert search.get_login_status() is False


def test_login_status_unknown_is_not_cached(monkeypatch, cache_dir):
    monkeypatch.setattr(search, "probe_login", lambda: None)
    assert search.get_login_status() is None
    assert not os.path.exists(search.get_auth_cache_path())


def test_login_status_survives_a_corrupt_auth_cache(monkeypatch, cache_dir):
    with open(search.get_auth_cache_path(), "w") as f:
        f.write("{not json")
    monkeypatch.setattr(search, "probe_login", lambda: True)
    assert search.get_login_status() is True


def test_check_logged_in_maps_unknown_to_false(monkeypatch):
    monkeypatch.setattr(search, "get_login_status", lambda: None)
    assert search.check_logged_in() is False


@pytest.mark.parametrize("raw,expected", [
    ("", []),
    ("   ", []),
    ("Personal", ["Personal"]),
    (" Personal , Work ,, ", ["Personal", "Work"]),
])
def test_get_configured_vaults(monkeypatch, raw, expected):
    monkeypatch.setenv("VAULT_NAME", raw)
    assert search.get_configured_vaults() == expected


def test_fetch_vault_list_unwraps_dict(monkeypatch):
    payload = json.dumps({"vaults": [{"name": "Personal"}]})
    monkeypatch.setattr(search.subprocess, "run", lambda *a, **k: _completed(stdout=payload))
    assert search.fetch_vault_list() == ([{"name": "Personal"}], None)


def test_fetch_vault_list_accepts_bare_list(monkeypatch):
    payload = json.dumps([{"name": "Work"}])
    monkeypatch.setattr(search.subprocess, "run", lambda *a, **k: _completed(stdout=payload))
    assert search.fetch_vault_list() == ([{"name": "Work"}], None)


def test_fetch_vault_list_rejects_unexpected_shape(monkeypatch):
    monkeypatch.setattr(search.subprocess, "run", lambda *a, **k: _completed(stdout='"nope"'))
    assert search.fetch_vault_list() == (None, "Unexpected format")


def test_fetch_vault_list_reports_stderr(monkeypatch):
    monkeypatch.setattr(
        search.subprocess, "run", lambda *a, **k: _completed(returncode=1, stderr=" boom \n")
    )
    assert search.fetch_vault_list() == (None, "boom")


def test_fetch_vault_list_reports_missing_cli(monkeypatch):
    def boom(*_a, **_k):
        raise FileNotFoundError("pass-cli")

    monkeypatch.setattr(search.subprocess, "run", boom)
    items, error = search.fetch_vault_list()
    assert items is None and "pass-cli" in error


def test_fetch_items_for_vault_normalizes(monkeypatch):
    payload = json.dumps({"items": [
        {"content": {"title": "last.fm", "content": {"Login": {"username": "me"}}}},
        "not-a-dict",
    ]})
    monkeypatch.setattr(search.subprocess, "run", lambda *a, **k: _completed(stdout=payload))
    items, error = search.fetch_items_for_vault("Personal")
    assert error is None
    assert items == [{
        "title": "last.fm", "username": "me", "url": "", "totp_uri": "",
        "type": "login", "vaultName": "Personal", "itemTitle": "last.fm",
    }]


def test_fetch_items_for_vault_reports_stderr(monkeypatch):
    monkeypatch.setattr(
        search.subprocess, "run", lambda *a, **k: _completed(returncode=1, stderr="denied")
    )
    assert search.fetch_items_for_vault("Personal") == (None, "denied")


def test_fetch_items_for_vault_rejects_unexpected_shape(monkeypatch):
    monkeypatch.setattr(search.subprocess, "run", lambda *a, **k: _completed(stdout='"nope"'))
    assert search.fetch_items_for_vault("Personal") == (None, "Unexpected format")


def test_fetch_items_uses_configured_vaults(monkeypatch, cache_dir):
    monkeypatch.setenv("VAULT_NAME", "Personal")
    monkeypatch.setattr(
        search, "fetch_vault_list", lambda: pytest.fail("configured vaults must win")
    )
    monkeypatch.setattr(
        search, "fetch_items_for_vault", lambda v: ([{"title": "a", "vaultName": v}], None)
    )
    items, error = search.fetch_items()
    assert error is None and items == [{"title": "a", "vaultName": "Personal"}]
    assert search.load_cached_items() == items


def test_fetch_items_discovers_vaults_when_unconfigured(monkeypatch, cache_dir):
    monkeypatch.setenv("VAULT_NAME", "")
    monkeypatch.setattr(search, "fetch_vault_list", lambda: ([{"name": "Work"}], None))
    monkeypatch.setattr(search, "fetch_items_for_vault", lambda v: ([{"vaultName": v}], None))
    items, _ = search.fetch_items()
    assert items == [{"vaultName": "Work"}]


def test_fetch_items_without_vaults_returns_error(monkeypatch, cache_dir):
    monkeypatch.setenv("VAULT_NAME", "")
    monkeypatch.setattr(search, "fetch_vault_list", lambda: (None, "no session"))
    assert search.fetch_items() == (None, "no session")


def test_fetch_items_keeps_last_error_when_all_vaults_fail(monkeypatch, cache_dir):
    monkeypatch.setenv("VAULT_NAME", "Personal")
    monkeypatch.setattr(search, "fetch_items_for_vault", lambda _v: (None, "not logged in"))
    assert search.fetch_items() == (None, "not logged in")


@pytest.mark.parametrize("exc,expected", [
    (FileNotFoundError("x"), "pass-cli not found"),
    (subprocess.TimeoutExpired("pass-cli", 1), "pass-cli timed out"),
    (json.JSONDecodeError("x", "y", 0), "Invalid JSON from pass-cli"),
])
def test_fetch_items_maps_cli_failures(monkeypatch, cache_dir, exc, expected):
    monkeypatch.setenv("VAULT_NAME", "Personal")

    def boom(_v):
        raise exc

    monkeypatch.setattr(search, "fetch_items_for_vault", boom)
    assert search.fetch_items() == (None, expected)


def test_check_cli_available(monkeypatch):
    monkeypatch.setattr(search.subprocess, "run", lambda *a, **k: _completed())
    assert search.check_cli_available() is True


def test_check_cli_available_false_when_missing(monkeypatch):
    def boom(*_a, **_k):
        raise FileNotFoundError

    monkeypatch.setattr(search.subprocess, "run", boom)
    assert search.check_cli_available() is False


@pytest.mark.parametrize("returncode,expected", [(0, True), (1, False)])
def test_probe_login_maps_exit_code(monkeypatch, returncode, expected):
    monkeypatch.setattr(
        search.subprocess, "run", lambda *a, **k: _completed(returncode=returncode)
    )
    assert search.probe_login() is expected


def test_probe_login_timeout_is_unknown_not_logged_out(monkeypatch):
    def boom(*_a, **_k):
        raise subprocess.TimeoutExpired("pass-cli", 10)

    monkeypatch.setattr(search.subprocess, "run", boom)
    assert search.probe_login() is None


@pytest.mark.parametrize("inner,expected_type", [
    ({"Login": {}}, "login"),
    ({"login": {}}, "login"),
    ({"Note": {}}, "note"),
    ({"CreditCard": {}}, "credit_card"),
    ({"Alias": {}}, "alias"),
    ({"Identity": {}}, "identity"),
    ({}, "login"),
    ("garbage", "login"),
])
def test_classify_content(inner, expected_type):
    login_data, item_type = search._classify_content(inner)
    assert item_type == expected_type
    assert isinstance(login_data, dict)


def test_normalize_item_maps_login_fields():
    raw = {"content": {"title": "last.fm", "content": {"Login": {
        "username": "me", "urls": ["https://last.fm"], "totp_uri": "otpauth://x",
    }}}}
    assert search._normalize_item(raw, "Personal") == {
        "title": "last.fm", "username": "me", "url": "https://last.fm",
        "totp_uri": "otpauth://x", "type": "login",
        "vaultName": "Personal", "itemTitle": "last.fm",
    }


def test_normalize_item_falls_back_to_email():
    raw = {"content": {"content": {"Login": {"email": "me@example.com"}}}}
    assert search._normalize_item(raw)["username"] == "me@example.com"


def test_normalize_item_ignores_non_string_url():
    raw = {"content": {"content": {"Login": {"urls": [{"href": "x"}]}}}}
    assert search._normalize_item(raw)["url"] == ""


def test_normalize_item_tolerates_empty_payload():
    assert search._normalize_item({})["title"] == ""


def test_make_rows_for_item_builds_all_four_rows():
    item = {"title": "last.fm", "vaultName": "Personal", "username": "me",
            "url": "https://last.fm", "totp_uri": "otpauth://x"}
    rows = search.make_rows_for_item(item)
    assert [r["variables"]["action"] for r in rows] == ["password", "username", "url", "totp"]
    assert all("last.fm" in r["match"] for r in rows)
    assert rows[1]["variables"]["username"] == "me"
    assert rows[2]["variables"]["url"] == "https://last.fm"


def test_make_rows_for_item_password_only_when_bare():
    rows = search.make_rows_for_item({"title": "bare"})
    assert len(rows) == 1
    assert rows[0]["subtitle"] == ""


def test_make_rows_for_item_defaults_missing_title():
    assert search.make_rows_for_item({})[0]["title"].startswith("Unknown")


def test_make_command_rows_marks_active_vault(monkeypatch):
    monkeypatch.setenv("VAULT_NAME", "Personal")
    monkeypatch.setattr(search, "check_cli_available", lambda: True)
    monkeypatch.setattr(search, "check_logged_in", lambda: True)
    rows = search.make_command_rows(["Personal", "Work"])
    by_uid = {r["uid"]: r for r in rows}
    assert by_uid["cmd/refresh"]["variables"]["action"] == "refresh"
    assert by_uid["cmd/setup-session"]["title"] == "Session: Active"
    assert by_uid["cmd/vault/Personal"]["title"] == "Active: Personal"
    assert by_uid["cmd/vault/Work"]["title"] == "Work"
    assert "cmd/vault-all" not in by_uid


def test_make_command_rows_without_cli_hides_session_row(monkeypatch):
    monkeypatch.setenv("VAULT_NAME", "")
    monkeypatch.setattr(search, "check_cli_available", lambda: False)
    rows = search.make_command_rows([])
    uids = [r["uid"] for r in rows]
    assert "cmd/setup-session" not in uids
    assert "cmd/vault-all" in uids


@pytest.mark.parametrize("query,expected", [
    ("", ["a", "b"]),
    ("   ", ["a", "b"]),
    ("LAST", ["a"]),
    ("last fm", ["a"]),
    ("nomatch", []),
])
def test_filter_rows(query, expected):
    rows = [{"uid": "a", "match": "last.fm me@example.com"}, {"uid": "b", "title": "Other"}]
    assert [r["uid"] for r in search.filter_rows(rows, query)] == expected


def test_filter_rows_falls_back_to_title():
    rows = [{"uid": "b", "title": "Other"}]
    assert search.filter_rows(rows, "other") == rows


def test_login_banner_is_not_actionable():
    item = search.login_banner()["items"][0]
    assert item["valid"] is False
    assert item["icon"]["path"] == search.DEFAULT_ICON


def _stdout_json(capsys):
    return json.loads(capsys.readouterr().out)


def test_main_reports_missing_cli(monkeypatch, capsys):
    monkeypatch.setattr(search, "check_cli_available", lambda: False)
    search.main()
    assert _stdout_json(capsys)["items"][0]["title"] == "pass-cli not found"


def test_main_shows_banner_when_logged_out(monkeypatch, capsys):
    monkeypatch.setattr(search, "check_cli_available", lambda: True)
    monkeypatch.setattr(search, "get_login_status", lambda: False)
    monkeypatch.setattr(search, "load_cached_items", lambda: pytest.fail("cache must not win"))
    search.main()
    assert "Not logged in" in _stdout_json(capsys)["items"][0]["title"]


def test_main_serves_cached_items(monkeypatch, capsys):
    monkeypatch.setattr(search, "check_cli_available", lambda: True)
    monkeypatch.setattr(search, "get_login_status", lambda: True)
    monkeypatch.setattr(search, "load_cached_items", lambda: [
        {"title": "last.fm", "vaultName": "Personal"}])
    monkeypatch.setattr(search, "make_command_rows", lambda _v: [])
    monkeypatch.setattr(search.sys, "argv", ["search.py"])
    search.main()
    assert _stdout_json(capsys)["items"][0]["title"] == "last.fm — Copy Password"


def test_main_fetches_on_cold_cache_and_filters(monkeypatch, capsys):
    monkeypatch.setattr(search, "check_cli_available", lambda: True)
    monkeypatch.setattr(search, "get_login_status", lambda: None)
    monkeypatch.setattr(search, "load_cached_items", lambda: None)
    monkeypatch.setattr(search, "fetch_items", lambda: (
        [{"title": "last.fm", "vaultName": "Personal"}, {"title": "github"}], None))
    monkeypatch.setattr(search, "make_command_rows", lambda _v: [])
    monkeypatch.setattr(search.sys, "argv", ["search.py", " github "])
    search.main()
    titles = [i["title"] for i in _stdout_json(capsys)["items"]]
    assert titles == ["github — Copy Password"]


def test_main_maps_auth_error_from_fetch(monkeypatch, capsys):
    monkeypatch.setattr(search, "check_cli_available", lambda: True)
    monkeypatch.setattr(search, "get_login_status", lambda: None)
    monkeypatch.setattr(search, "load_cached_items", lambda: None)
    monkeypatch.setattr(search, "fetch_items", lambda: (None, "Session expired"))
    search.main()
    assert _stdout_json(capsys)["items"][0]["title"] == "Not logged in"


def test_main_surfaces_generic_error(monkeypatch, capsys):
    monkeypatch.setattr(search, "check_cli_available", lambda: True)
    monkeypatch.setattr(search, "get_login_status", lambda: None)
    monkeypatch.setattr(search, "load_cached_items", lambda: None)
    monkeypatch.setattr(search, "fetch_items", lambda: (None, "disk on fire"))
    search.main()
    item = _stdout_json(capsys)["items"][0]
    assert item["title"] == "Error" and item["subtitle"] == "disk on fire"
