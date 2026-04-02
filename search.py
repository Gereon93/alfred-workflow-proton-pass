#!/usr/bin/env python3
"""Alfred Script Filter for Proton Pass.

Each vault item becomes 3 rows: Copy Password, Copy Username, Copy/Open URL.
Alfred filters results as the user types (alfredfiltersresults=true).
"""

import json
import os
import subprocess
import sys
import time

CACHE_TTL = 300
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


# -- Cache --

def get_cache_dir():
    d = os.environ.get("alfred_workflow_cache", "")
    if not d:
        d = os.path.join(os.path.expanduser("~"), ".cache", "alfred-proton-pass")
    os.makedirs(d, exist_ok=True)
    return d


def get_cache_path():
    return os.path.join(get_cache_dir(), "items.json")


def load_cached_items():
    path = get_cache_path()
    if not os.path.exists(path):
        return None
    if time.time() - os.path.getmtime(path) > CACHE_TTL:
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_cache(items):
    with open(get_cache_path(), "w") as f:
        json.dump(items, f)


# -- CLI --

def get_configured_vaults():
    raw = os.environ.get("VAULT_NAME", "").strip()
    if not raw:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


def fetch_vault_list():
    try:
        result = subprocess.run(
            [PASS_CLI, "vault", "list", "--output", "json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None, result.stderr.strip()
        data = json.loads(result.stdout)
        if isinstance(data, dict) and "vaults" in data:
            return data["vaults"], None
        if isinstance(data, list):
            return data, None
        return None, "Unexpected format"
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        return None, str(e)


def fetch_items_for_vault(vault_name):
    cmd = [PASS_CLI, "item", "list", "--output", "json", vault_name]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return None, result.stderr.strip()
    data = json.loads(result.stdout)
    raw_items = data.get("items", data) if isinstance(data, dict) else data
    if not isinstance(raw_items, list):
        return None, "Unexpected format"
    return [_normalize_item(i, vault_name) for i in raw_items if isinstance(i, dict)], None


def _normalize_item(raw, vault_name=""):
    content = raw.get("content", {})
    inner = content.get("content", {})
    login_data = {}
    item_type = "login"
    if isinstance(inner, dict):
        for key in ("Login", "login"):
            if key in inner and isinstance(inner[key], dict):
                login_data = inner[key]
                break
        else:
            for key, t in {"Note": "note", "CreditCard": "credit_card",
                           "Alias": "alias", "Identity": "identity"}.items():
                if key in inner:
                    item_type = t
                    break
    urls = login_data.get("urls", [])
    return {
        "title": content.get("title", ""),
        "username": login_data.get("username", "") or login_data.get("email", ""),
        "url": urls[0] if urls and isinstance(urls[0], str) else "",
        "totp_uri": login_data.get("totp_uri", ""),
        "type": item_type,
        "vaultName": vault_name,
        "itemTitle": content.get("title", ""),
    }


def fetch_items():
    try:
        configured = get_configured_vaults()
        vault_names = configured
        if not vault_names:
            vaults, error = fetch_vault_list()
            if not vaults:
                return None, error or "Could not list vaults"
            vault_names = [v.get("name", "") for v in vaults if v.get("name")]

        all_items = []
        last_error = None
        for vault in vault_names:
            items, error = fetch_items_for_vault(vault)
            if items:
                all_items.extend(items)
            else:
                last_error = error
        if all_items:
            save_cache(all_items)
            return all_items, None
        return None, last_error or "No items found"
    except FileNotFoundError:
        return None, "pass-cli not found"
    except subprocess.TimeoutExpired:
        return None, "pass-cli timed out"
    except json.JSONDecodeError:
        return None, "Invalid JSON from pass-cli"


def check_cli_available():
    try:
        subprocess.run([PASS_CLI, "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_logged_in():
    try:
        r = subprocess.run([PASS_CLI, "test"], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# -- Build Alfred rows: one item → up to 4 rows --

def make_rows_for_item(item):
    title = item.get("title", "Unknown")
    vault = item.get("vaultName", "")
    username = item.get("username", "")
    url = item.get("url", "")
    totp = item.get("totp_uri", "")

    match_parts = [title, username, url, vault]
    match_str = " ".join(p for p in match_parts if p)

    # All data goes via variables (env vars), not via arg/{query} which is unreliable
    base_vars = {"vaultName": vault, "itemTitle": title}
    rows = []

    # 1. Copy Password
    rows.append({
        "uid": f"{title}/pw",
        "title": f"{title} — Copy Password",
        "subtitle": f"{username} · {vault}" if username else vault,
        "arg": title,
        "match": match_str,
        "icon": {"path": "icons/login.png"},
        "variables": {**base_vars, "action": "password"},
    })

    # 2. Copy Username
    if username:
        rows.append({
            "uid": f"{title}/user",
            "title": f"{title} — Copy Username",
            "subtitle": username,
            "arg": title,
            "match": match_str,
            "icon": {"path": "icons/identity.png"},
            "variables": {**base_vars, "action": "username", "username": username},
        })

    # 3. Open URL
    if url:
        rows.append({
            "uid": f"{title}/url",
            "title": f"{title} — Open URL",
            "subtitle": url,
            "arg": title,
            "match": match_str,
            "icon": {"path": "icons/url.png"},
            "variables": {**base_vars, "action": "url", "url": url},
        })

    # 4. Copy TOTP (only if configured)
    if totp:
        rows.append({
            "uid": f"{title}/totp",
            "title": f"{title} — Copy TOTP",
            "subtitle": vault,
            "arg": title,
            "match": match_str,
            "icon": {"path": "icons/note.png"},
            "variables": {**base_vars, "action": "totp"},
        })

    return rows


# -- Commands --

def handle_command(query):
    cmd = query.lstrip(":").strip().lower()

    if cmd == "refresh":
        path = get_cache_path()
        if os.path.exists(path):
            os.remove(path)
        return {"items": [{"title": "Cache cleared", "subtitle": "Refreshing on next search", "valid": False}]}

    if cmd.startswith("vault"):
        vaults, error = fetch_vault_list()
        if not vaults:
            return {"items": [{"title": "Could not list vaults", "subtitle": error or "", "valid": False}]}
        configured = get_configured_vaults()
        items = []
        if not configured:
            items.append({"title": "All vaults (no filter)", "subtitle": "Set VAULT_NAME to limit", "valid": False})
        for v in vaults:
            name = v.get("name", "?")
            pfx = "✓ " if name in configured else ""
            items.append({"title": f"{pfx}{name}", "subtitle": "Set VAULT_NAME to filter", "valid": False})
        return {"items": items}

    if cmd.startswith("setup"):
        items = []
        cli_ok = check_cli_available()
        items.append({
            "title": f"pass-cli: {'✓ Installed' if cli_ok else '✗ Not found'}",
            "subtitle": f"Path: {PASS_CLI}" if cli_ok else "Install: curl -fsSL https://proton.me/download/pass-cli/install.sh | bash",
            "valid": False,
        })
        if cli_ok:
            ok = check_logged_in()
            items.append({
                "title": f"Session: {'✓ Active' if ok else '✗ Not logged in'}",
                "subtitle": "Run 'pass-cli login' in Terminal" if not ok else "Authenticated",
                "valid": False,
            })
        return {"items": items}

    return None


# -- Main --

def main():
    query = sys.argv[1] if len(sys.argv) > 1 else ""

    if query.startswith(":"):
        result = handle_command(query)
        if result:
            print(json.dumps(result))
            return

    if not check_cli_available():
        print(json.dumps({"items": [{"title": "pass-cli not found", "valid": False}]}))
        return

    items = load_cached_items()
    if items is None:
        items, error = fetch_items()
        if items is None:
            err = (error or "").lower()
            if any(k in err for k in ["not logged in", "unauthorized", "session"]):
                print(json.dumps({"items": [{"title": "Not logged in", "subtitle": "Run 'pass-cli login' in Terminal", "valid": False}]}))
            else:
                print(json.dumps({"items": [{"title": "Error", "subtitle": error or "Unknown", "valid": False}]}))
            return

    if not items:
        print(json.dumps({"items": [{"title": "No items in vault", "valid": False}]}))
        return

    # Each item → multiple rows (password, username, url, totp)
    # Alfred filters these with alfredfiltersresults=true
    all_rows = []
    for item in items:
        all_rows.extend(make_rows_for_item(item))

    print(json.dumps({"items": all_rows}))


if __name__ == "__main__":
    main()
