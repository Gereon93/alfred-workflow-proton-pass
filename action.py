#!/usr/bin/env python3
"""Executes actions: copy password, username, open URL, copy TOTP.

All data comes via environment variables set by Alfred (from Script Filter variables).
"""

import os
import json
import subprocess
import sys

_DEFAULT_CLI_PATHS = [
    os.path.expanduser("~/.local/bin/pass-cli"),
    "/usr/local/bin/pass-cli",
    "/opt/homebrew/bin/pass-cli",
    "pass-cli",
]


def _find_pass_cli():
    explicit = os.environ.get("PASS_CLI_PATH", "")
    if explicit:
        return explicit
    for p in _DEFAULT_CLI_PATHS:
        if os.path.exists(p):
            return p
    return "pass-cli"


PASS_CLI = _find_pass_cli()
CLIPBOARD_CLEAR_SECONDS = int(os.environ.get("CLIPBOARD_CLEAR_SECONDS", "30"))


def get_cache_dir():
    d = os.environ.get("alfred_workflow_cache", "")
    if not d:
        d = os.path.join(os.path.expanduser("~"), ".cache", "alfred-proton-pass")
    os.makedirs(d, exist_ok=True)
    return d


def mark_logged_out():
    """Flip the shared auth flag so the next search surfaces the login banner."""
    try:
        with open(os.path.join(get_cache_dir(), "auth.json"), "w") as f:
            json.dump({"logged_in": False}, f)
    except OSError:
        pass


def notify(message):
    # Pass text as argv so untrusted error text can't break out of the
    # AppleScript string or inject code; bounded by a timeout so a hung
    # osascript can't stall the action.
    message = " ".join(str(message).splitlines()).strip() or "Action failed"
    try:
        subprocess.run(
            ["osascript",
             "-e", "on run argv",
             "-e", "display notification (item 1 of argv) with title (item 2 of argv)",
             "-e", "end run",
             message, "Proton Pass"],
            capture_output=True, timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass


def handle_failure(error):
    err = (error or "").lower()
    if any(k in err for k in ["not logged in", "unauthorized", "session", "login", "auth"]):
        mark_logged_out()
        notify("Not logged in — run 'pass-cli login' in Terminal")
    else:
        notify(error or "Action failed")


def copy_to_clipboard(text):
    subprocess.run(["pbcopy"], input=text.encode(), check=True)


def clear_clipboard_later(seconds):
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clear_clipboard.py")
    subprocess.Popen(
        [sys.executable, script, str(seconds)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def get_password(vault_name, item_title):
    cmd = [PASS_CLI, "item", "view", "--vault-name", vault_name,
           "--item-title", item_title, "--field", "password"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        return None, result.stderr.strip()
    return result.stdout.strip(), None


def get_totp(vault_name, item_title):
    cmd = [PASS_CLI, "item", "totp", "--vault-name", vault_name,
           "--item-title", item_title]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        return None, result.stderr.strip()
    output = result.stdout.strip()
    try:
        data = json.loads(output)
        if isinstance(data, dict):
            return data.get("totp") or next(iter(data.values()), None), None
    except json.JSONDecodeError:
        pass
    return output, None


def main():
    # All data from Alfred environment variables
    action = os.environ.get("action", "")
    vault_name = os.environ.get("vaultName", "")
    item_title = os.environ.get("itemTitle", "")
    username = os.environ.get("username", "")
    url = os.environ.get("url", "")

    if action == "password":
        pw, error = get_password(vault_name, item_title)
        if pw:
            copy_to_clipboard(pw)
            clear_clipboard_later(CLIPBOARD_CLEAR_SECONDS)
        else:
            handle_failure(error)

    elif action == "username":
        if username:
            copy_to_clipboard(username)
            clear_clipboard_later(CLIPBOARD_CLEAR_SECONDS)

    elif action == "url":
        if url:
            subprocess.run(["open", url])

    elif action == "totp":
        code, error = get_totp(vault_name, item_title)
        if code:
            copy_to_clipboard(code)
            clear_clipboard_later(CLIPBOARD_CLEAR_SECONDS)
        else:
            handle_failure(error)

    elif action == "refresh":
        cache_dir = os.environ.get("alfred_workflow_cache", "")
        if not cache_dir:
            cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "alfred-proton-pass")
        cache_file = os.path.join(cache_dir, "items.json")
        if os.path.exists(cache_file):
            os.remove(cache_file)


if __name__ == "__main__":
    main()
