#!/usr/bin/env python3
"""Handles actions triggered by modifier keys in Alfred."""

import json
import os
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


def copy_to_clipboard(text):
    """Copy text to clipboard using pbcopy."""
    subprocess.run(["pbcopy"], input=text.encode(), check=True)


def clear_clipboard_later(seconds):
    """Spawn a background process to clear clipboard after N seconds."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clear_clipboard.py")
    subprocess.Popen(
        [sys.executable, script, str(seconds)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def get_password(vault_name, item_title):
    """Fetch password via pass-cli."""
    cmd = [PASS_CLI, "item", "view", "--vault-name", vault_name, "--item-title", item_title, "--field", "password"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        return None, result.stderr.strip()
    return result.stdout.strip(), None


def get_totp(vault_name, item_title):
    """Fetch TOTP code via pass-cli."""
    cmd = [PASS_CLI, "item", "totp", "--vault-name", vault_name, "--item-title", item_title]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        return None, result.stderr.strip()
    # Output may be JSON or plain text
    output = result.stdout.strip()
    try:
        data = json.loads(output)
        # TOTP JSON: {"totp": "123456"} or {"TOTP 1": "123456", ...}
        if isinstance(data, dict):
            return data.get("totp") or next(iter(data.values()), None), None
    except json.JSONDecodeError:
        pass
    # Plain text: just the code
    return output, None


def open_url(url):
    """Open URL in default browser."""
    if url:
        subprocess.run(["open", url])


def main():
    action = os.environ.get("action", "url")
    raw_arg = sys.argv[1] if len(sys.argv) > 1 else ""

    try:
        item_data = json.loads(raw_arg)
    except json.JSONDecodeError:
        print("Error: Invalid item data", file=sys.stderr)
        sys.exit(1)

    vault_name = item_data.get("vaultName", "")
    item_title = item_data.get("itemTitle", "")
    username = item_data.get("username", "")
    url = item_data.get("url", "")

    if action == "url":
        if url:
            open_url(url)
        else:
            # Fallback: copy password if no URL
            action = "password"

    if action == "password":
        pw, error = get_password(vault_name, item_title)
        if pw:
            copy_to_clipboard(pw)
            clear_clipboard_later(CLIPBOARD_CLEAR_SECONDS)
        else:
            # Output error for Alfred notification
            print(f"Error: {error or 'Could not get password'}", file=sys.stderr)
            sys.exit(1)

    elif action == "username":
        if username:
            copy_to_clipboard(username)
            clear_clipboard_later(CLIPBOARD_CLEAR_SECONDS)
        else:
            print("No username available", file=sys.stderr)
            sys.exit(1)

    elif action == "totp":
        code, error = get_totp(vault_name, item_title)
        if code:
            copy_to_clipboard(code)
            clear_clipboard_later(CLIPBOARD_CLEAR_SECONDS)
        else:
            print(f"Error: {error or 'No TOTP configured'}", file=sys.stderr)
            sys.exit(1)

    elif action == "copy_url":
        if url:
            copy_to_clipboard(url)
            clear_clipboard_later(CLIPBOARD_CLEAR_SECONDS)
        else:
            print("No URL available", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
