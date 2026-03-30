#!/usr/bin/env python3
"""Alfred Script Filter for Proton Pass — searches vault items.

pass-cli JSON structures (v1.8.0):

  vault list: {"vaults": [{"name": str, "vault_id": str, "share_id": str}]}

  item list:  {"items": [{
    "id": str, "share_id": str, "vault_id": str,
    "content": {
      "title": str, "note": str, "item_uuid": str,
      "content": {"Login": {"email": str, "username": str, "password": str,
                             "urls": [str], "totp_uri": str, "passkeys": []}},
      "extra_fields": [...]
    },
    "state": str, "flags": [], "create_time": str, "modify_time": str
  }]}
"""

import json
import os
import subprocess
import sys
import time

CACHE_TTL = 300  # 5 minutes
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


# -- CLI helpers --

def get_configured_vaults():
    raw = os.environ.get("VAULT_NAME", "").strip()
    if not raw:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


def fetch_vault_list():
    """Returns list of vault dicts or (None, error)."""
    try:
        result = subprocess.run(
            [PASS_CLI, "vault", "list", "--output", "json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None, result.stderr.strip()
        data = json.loads(result.stdout)
        # Structure: {"vaults": [...]}
        if isinstance(data, dict) and "vaults" in data:
            return data["vaults"], None
        if isinstance(data, list):
            return data, None
        return None, f"Unexpected vault format: {type(data).__name__}"
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        return None, str(e)


def fetch_items_for_vault(vault_name):
    """Fetch items for a specific vault. Returns flat list of normalized item dicts."""
    cmd = [PASS_CLI, "item", "list", "--output", "json", vault_name]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return None, result.stderr.strip()
    data = json.loads(result.stdout)

    # Structure: {"items": [...]} or just [...]
    raw_items = data
    if isinstance(data, dict) and "items" in data:
        raw_items = data["items"]
    if not isinstance(raw_items, list):
        return None, f"Unexpected items format: {type(raw_items).__name__}"

    items = [_normalize_item(i, vault_name) for i in raw_items if isinstance(i, dict)]
    return items, None


def _normalize_item(raw, vault_name=""):
    """Flatten pass-cli item into a simple dict for caching and searching.

    Input structure:
      {"id", "share_id", "vault_id",
       "content": {"title", "note", "content": {"Login": {"username", "email", "urls", "totp_uri"}}}}

    Output: flat dict with title, username, email, urls, type, vaultName, itemId, shareId
    """
    content = raw.get("content", {})
    inner = content.get("content", {})

    # inner is e.g. {"Login": {...}} or {"Note": {...}} etc.
    item_type = "login"
    login_data = {}
    if isinstance(inner, dict):
        for key in ("Login", "login"):
            if key in inner:
                login_data = inner[key] if isinstance(inner[key], dict) else {}
                item_type = "login"
                break
        else:
            # Check other types
            type_map = {"Note": "note", "CreditCard": "credit_card", "Alias": "alias",
                        "Identity": "identity", "SshKey": "ssh_key"}
            for key, t in type_map.items():
                if key in inner:
                    login_data = inner[key] if isinstance(inner[key], dict) else {}
                    item_type = t
                    break

    return {
        "title": content.get("title", ""),
        "note": content.get("note", ""),
        "username": login_data.get("username", ""),
        "email": login_data.get("email", ""),
        "urls": login_data.get("urls", []),
        "totp_uri": login_data.get("totp_uri", ""),
        "type": item_type,
        "itemId": raw.get("id", ""),
        "shareId": raw.get("share_id", ""),
        "vaultId": raw.get("vault_id", ""),
        "vaultName": vault_name,
        "state": raw.get("state", ""),
    }


def fetch_items():
    """Fetch all items. Returns (list, None) or (None, error)."""
    try:
        configured = get_configured_vaults()

        if configured:
            all_items = []
            last_error = None
            for vault in configured:
                items, error = fetch_items_for_vault(vault)
                if items:
                    all_items.extend(items)
                else:
                    last_error = error
            if all_items:
                save_cache(all_items)
                return all_items, None
            return None, last_error or "No items found in configured vaults"

        # Auto-discover all vaults
        vaults, error = fetch_vault_list()
        if not vaults:
            return None, error or "Could not list vaults"

        all_items = []
        for vault in vaults:
            vault_name = vault.get("name", "")
            if not vault_name:
                continue
            items, _ = fetch_items_for_vault(vault_name)
            if items:
                all_items.extend(items)

        if all_items:
            save_cache(all_items)
            return all_items, None
        return None, "No items found in any vault"

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
        result = subprocess.run(
            [PASS_CLI, "test"], capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# -- Item accessors (work on normalized items) --

def get_item_url(item):
    urls = item.get("urls", [])
    if urls:
        first = urls[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("url", "")
    return ""


def get_item_username(item):
    return item.get("username", "") or item.get("email", "")


def get_item_subtitle(item):
    parts = []
    username = get_item_username(item)
    if username:
        parts.append(username)
    vault = item.get("vaultName", "")
    if vault:
        parts.append(vault)
    return " · ".join(parts) if parts else ""


def item_matches(item, query):
    if not query:
        return True
    q = query.lower()
    fields = [
        item.get("title", "").lower(),
        get_item_username(item).lower(),
        get_item_url(item).lower(),
        item.get("vaultName", "").lower(),
    ]
    return any(q in f for f in fields)


def make_alfred_item(item):
    title = item.get("title", "Unknown")
    item_id = item.get("itemId", "")
    share_id = item.get("shareId", "")
    vault_name = item.get("vaultName", "")
    username = get_item_username(item)
    url = get_item_url(item)
    item_type = item.get("type", "login")

    arg_data = json.dumps({
        "itemId": item_id,
        "shareId": share_id,
        "vaultName": vault_name,
        "itemTitle": title,
        "username": username,
        "url": url,
        "type": item_type,
    })

    subtitle = get_item_subtitle(item)

    # match field lets Alfred filter on title, username, url, and vault
    match_parts = [title, username, url, vault_name]
    match_string = " ".join(p for p in match_parts if p)

    result = {
        "uid": f"{share_id}/{item_id}",
        "title": title,
        "subtitle": subtitle,
        "arg": arg_data,
        "autocomplete": title,
        "match": match_string,
        "icon": {"path": get_icon_for_type(item_type)},
        "variables": {"action": "url"},
        "mods": {
            "ctrl": {
                "subtitle": "⌃ Copy password",
                "arg": arg_data,
                "variables": {"action": "password"},
                "valid": True,
            },
            "alt": {
                "subtitle": f"⌥ Copy username: {username}" if username else "⌥ No username",
                "arg": arg_data,
                "variables": {"action": "username"},
                "valid": bool(username),
            },
            "shift": {
                "subtitle": "⇧ Copy TOTP code",
                "arg": arg_data,
                "variables": {"action": "totp"},
                "valid": True,
            },
            "cmd": {
                "subtitle": f"⌘ Copy URL: {url}" if url else "⌘ No URL",
                "arg": arg_data,
                "variables": {"action": "copy_url"},
                "valid": bool(url),
            },
        },
    }

    if url:
        result["subtitle"] = f"{subtitle}  ↩ Open URL" if subtitle else "↩ Open URL"
    else:
        result["variables"]["action"] = "password"
        result["subtitle"] = f"{subtitle}  ↩ Copy password" if subtitle else "↩ Copy password"

    return result


def get_icon_for_type(item_type):
    type_map = {
        "login": "icons/login.png",
        "note": "icons/note.png",
        "credit_card": "icons/card.png",
        "alias": "icons/alias.png",
        "identity": "icons/identity.png",
    }
    path = type_map.get(item_type, "icon.png")
    if os.path.exists(path):
        return path
    return "icon.png"


# -- Commands --

def handle_command(query):
    cmd = query.lstrip(":").strip().lower()

    if cmd == "refresh":
        cache_path = get_cache_path()
        if os.path.exists(cache_path):
            os.remove(cache_path)
        return {"items": [{"title": "Cache cleared", "subtitle": "Items will be refreshed on next search", "valid": False}]}

    if cmd.startswith("vault"):
        vaults, error = fetch_vault_list()
        if not vaults:
            return {"items": [{"title": "Could not list vaults", "subtitle": error or "Unknown error", "valid": False}]}
        configured = get_configured_vaults()
        items = []
        for v in vaults:
            name = v.get("name", "?")
            active = "✓ " if name in configured else ""
            items.append({
                "title": f"{active}{name}",
                "subtitle": "Set VAULT_NAME in workflow config to filter",
                "valid": False,
            })
        if not configured:
            items.insert(0, {
                "title": "All vaults active (no filter set)",
                "subtitle": "Set VAULT_NAME in workflow config to limit to specific vaults",
                "valid": False,
            })
        return {"items": items}

    if cmd.startswith("setup"):
        items = []
        cli_ok = check_cli_available()
        items.append({
            "title": f"pass-cli: {'✓ Installed' if cli_ok else '✗ Not found'}",
            "subtitle": f"Path: {PASS_CLI}" if cli_ok else "Install via: curl -fsSL https://proton.me/download/pass-cli/install.sh | bash",
            "valid": False,
        })
        if cli_ok:
            logged_in = check_logged_in()
            items.append({
                "title": f"Session: {'✓ Active' if logged_in else '✗ Not logged in'}",
                "subtitle": "Run 'pass-cli login' in Terminal" if not logged_in else "Authenticated",
                "valid": False,
            })
        return {"items": items}

    return None


# -- Main --

def main():
    query = sys.argv[1] if len(sys.argv) > 1 else ""

    # Debug: write argv to log file
    log_path = os.path.join(get_cache_dir(), "debug.log")
    with open(log_path, "a") as f:
        f.write(f"argv={sys.argv!r} query={query!r}\n")

    # Handle :commands
    if query.startswith(":"):
        result = handle_command(query)
        if result:
            print(json.dumps(result))
            return

    # Check CLI
    if not check_cli_available():
        print(json.dumps({"items": [{
            "title": "pass-cli not found",
            "subtitle": f"Looked in: {', '.join(_DEFAULT_CLI_PATHS)}",
            "valid": False,
        }]}))
        return

    # Load items (cache or fetch)
    items = load_cached_items()
    if items is None:
        items, error = fetch_items()
        if items is None:
            err_lower = (error or "").lower()
            if any(k in err_lower for k in ["not logged in", "unauthorized", "session", "unauthenticated"]):
                msg = "Not logged in to Proton Pass"
                sub = "Run 'pass-cli login' in Terminal first"
            else:
                msg = "Error fetching items"
                sub = error or "Unknown error"
            print(json.dumps({"items": [{"title": msg, "subtitle": sub, "valid": False}]}))
            return

    # Filter
    filtered = [i for i in items if item_matches(i, query)]

    if not filtered:
        print(json.dumps({"items": [{
            "title": f"No items matching '{query}'" if query else "No items in vault",
            "subtitle": "Try a different search term",
            "valid": False,
        }]}))
        return

    alfred_items = [make_alfred_item(i) for i in filtered]
    print(json.dumps({"items": alfred_items}))


if __name__ == "__main__":
    main()
