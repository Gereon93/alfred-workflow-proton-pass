#!/usr/bin/env python3
"""Tests for logged-out detection in the Alfred Proton Pass workflow.

Uses a stub pass-cli (no real vault access) so these never touch live data.
Run: python3 test_logout.py
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

STUB_LOGGED_OUT = """#!/bin/sh
case "$1" in
  --version) echo "pass-cli stub"; exit 0;;
  test) echo "not logged in" 1>&2; exit 1;;
  *) echo "not logged in" 1>&2; exit 1;;
esac
"""

STUB_LOGGED_IN = """#!/bin/sh
case "$1" in
  --version) echo "pass-cli stub"; exit 0;;
  test) exit 0;;
  *) exit 0;;
esac
"""


def _write_stub(dirpath, body):
    path = os.path.join(dirpath, "pass-cli")
    with open(path, "w") as f:
        f.write(body)
    os.chmod(path, 0o755)
    return path


def _run_search(cache_dir, stub_path, query=""):
    env = dict(os.environ)
    env["alfred_workflow_cache"] = cache_dir
    env["PASS_CLI_PATH"] = stub_path
    env["VAULT_NAME"] = ""  # exercise the no-configured-vault path
    cmd = [sys.executable, os.path.join(HERE, "search.py")]
    if query:
        cmd.append(query)  # Alfred passes the typed query as argv when it doesn't filter
    out = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
    assert out.returncode == 0, f"search.py crashed: {out.stderr}"
    return json.loads(out.stdout)


def _warm_cache(cache_dir):
    items = [{
        "title": "last.fm", "username": "me@example.com", "url": "https://last.fm",
        "totp_uri": "", "type": "login", "vaultName": "Personal", "itemTitle": "last.fm",
    }]
    with open(os.path.join(cache_dir, "items.json"), "w") as f:
        json.dump(items, f)


def test_logged_out_with_warm_cache_shows_login_banner():
    """The core bug: warm item cache must not mask a logged-out session."""
    with tempfile.TemporaryDirectory() as d:
        _warm_cache(d)
        stub = _write_stub(d, STUB_LOGGED_OUT)
        result = _run_search(d, stub)

        titles = [i.get("title", "") for i in result["items"]]
        joined = " ".join(titles).lower()
        assert "not logged in" in joined, f"expected login banner, got: {titles}"
        # Cached item titles must NOT leak through when logged out
        assert not any("last.fm" in t.lower() for t in titles), \
            f"cached items leaked while logged out: {titles}"
    print("PASS: logged-out + warm cache shows login banner")


def test_logged_out_banner_survives_a_typed_query():
    """Banner must stay visible even when a search term is typed (Alfred no longer filters)."""
    with tempfile.TemporaryDirectory() as d:
        _warm_cache(d)
        stub = _write_stub(d, STUB_LOGGED_OUT)
        result = _run_search(d, stub, query="last")

        titles = [i.get("title", "") for i in result["items"]]
        joined = " ".join(titles).lower()
        assert "not logged in" in joined, f"banner filtered out by query: {titles}"
        assert not any("last.fm" in t.lower() for t in titles), \
            f"cached items leaked while logged out: {titles}"
    print("PASS: logged-out banner survives a typed query")


def test_logged_in_query_filters_items():
    """When logged in, the script itself filters rows by the typed query."""
    with tempfile.TemporaryDirectory() as d:
        _warm_cache(d)
        stub = _write_stub(d, STUB_LOGGED_IN)
        result = _run_search(d, stub, query="last")
        titles = [i.get("title", "") for i in result["items"]]
        assert any("last.fm" in t.lower() for t in titles), \
            f"expected last.fm rows for query 'last', got: {titles}"

        # A query that matches nothing should drop the item rows
        none = _run_search(d, stub, query="zzzznomatch")
        ntitles = [i.get("title", "") for i in none["items"]]
        assert not any("last.fm" in t.lower() for t in ntitles), \
            f"non-matching query still returned items: {ntitles}"
    print("PASS: logged-in query filters items in-script")


def test_logged_in_with_warm_cache_shows_items():
    """Regression guard: when logged in, the warm cache still serves items fast."""
    with tempfile.TemporaryDirectory() as d:
        _warm_cache(d)
        stub = _write_stub(d, STUB_LOGGED_IN)
        result = _run_search(d, stub)

        titles = [i.get("title", "") for i in result["items"]]
        assert any("last.fm" in t.lower() for t in titles), \
            f"expected cached items when logged in, got: {titles}"
        assert not any("not logged in" in t.lower() for t in titles), \
            f"false login banner while logged in: {titles}"
    print("PASS: logged-in + warm cache shows items")


def test_action_auth_failure_marks_logged_out_and_notifies():
    """A failed copy must not be a silent no-op: flip the auth flag and notify."""
    with tempfile.TemporaryDirectory() as d:
        stub = _write_stub(d, STUB_LOGGED_OUT)  # 'item view' exits non-zero
        # Fake osascript on PATH so the test doesn't fire a real notification.
        notify_log = os.path.join(d, "notify.log")
        fake_bin = os.path.join(d, "bin")
        os.makedirs(fake_bin)
        osa = os.path.join(fake_bin, "osascript")
        with open(osa, "w") as f:
            f.write(f'#!/bin/sh\necho "$@" >> "{notify_log}"\n')
        os.chmod(osa, 0o755)

        env = dict(os.environ)
        env["alfred_workflow_cache"] = d
        env["PASS_CLI_PATH"] = stub
        env["PATH"] = fake_bin + os.pathsep + env["PATH"]
        env["action"] = "password"
        env["vaultName"] = "Personal"
        env["itemTitle"] = "last.fm"
        out = subprocess.run(
            [sys.executable, os.path.join(HERE, "action.py")],
            capture_output=True, text=True, env=env, timeout=30,
        )
        assert out.returncode == 0, f"action.py crashed: {out.stderr}"

        auth_path = os.path.join(d, "auth.json")
        assert os.path.exists(auth_path), "auth flag not written on failure"
        with open(auth_path) as f:
            assert json.load(f).get("logged_in") is False, "auth flag not set to False"
        assert os.path.exists(notify_log), "no notification fired on failure"
    print("PASS: action auth failure marks logged out and notifies")


if __name__ == "__main__":
    test_logged_out_with_warm_cache_shows_login_banner()
    test_logged_out_banner_survives_a_typed_query()
    test_logged_in_query_filters_items()
    test_logged_in_with_warm_cache_shows_items()
    test_action_auth_failure_marks_logged_out_and_notifies()
    print("\nAll tests passed.")
