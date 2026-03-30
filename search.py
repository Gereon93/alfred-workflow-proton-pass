#!/usr/bin/env python3
"""Alfred Script Filter for Proton Pass — searches vault items."""

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
    path = get_cache_path()
    with open(path, "w") as f:
        json.dump(items, f)


def get_configured_vaults():
    """Return list of vault names from VAULT_NAME env var (comma-separated), or empty list for all."""
    raw = os.environ.get("VAULT_NAME", "").strip()
    if not raw:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


def fetch_vault_list():
    """Fetch available vaults from pass-cli."""
    try:
        result = subprocess.run(
            [PASS_CLI, "vault", "list", "--output", "json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None, result.stderr.strip()
        return json.loads(result.stdout), None
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        return None, str(e)


def fetch_items_for_vault(vault_name):
    """Fetch items for a specific vault."""
    cmd = [PASS_CLI, "item", "list", "--output", "json", vault_name]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return None, result.stderr.strip()
    return json.loads(result.stdout), None


def fetch_items():
    """Fetch items from pass-cli. Returns list of items or None on error."""
    try:
        configured = get_configured_vaults()

        if configured:
            # Fetch from configured vaults
            all_items = []
            for vault in configured:
                items, error = fetch_items_for_vault(vault)
                if items:
                    all_items.extend(items)
            if all_items:
                save_cache(all_items)
                return all_items, None
            return None, error or "No items found in configured vaults"

        # No vault configured — discover all vaults and fetch from each
        vaults, error = fetch_vault_list()
        if not vaults:
            return None, error or "Could not list vaults"

        all_items = []
        for vault in vaults:
            vault_name = vault.get("vaultName") or vault.get("name", "")
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


def get_item_subtitle(item):
    """Build subtitle from item fields."""
    parts = []
    # Try to get username/email from content
    content = item.get("content", {})
    if isinstance(content, dict):
        username = content.get("username") or content.get("email", "")
        if username:
            parts.append(username)
    # Vault name
    vault = item.get("vaultName", "")
    if vault:
        parts.append(vault)
    return " · ".join(parts) if parts else ""


def get_item_url(item):
    content = item.get("content", {})
    if isinstance(content, dict):
        urls = content.get("urls", [])
        if urls:
            return urls[0] if isinstance(urls[0], str) else urls[0].get("url", "")
    return ""


def get_item_username(item):
    content = item.get("content", {})
    if isinstance(content, dict):
        return content.get("username") or content.get("email", "")
    return ""


def item_matches(item, query):
    """Check if item matches search query (case-insensitive)."""
    if not query:
        return True
    q = query.lower()
    title = (item.get("title") or item.get("data", {}).get("metadata", {}).get("name", "")).lower()
    username = get_item_username(item).lower()
    url = get_item_url(item).lower()
    vault = item.get("vaultName", "").lower()
    return any(q in field for field in [title, username, url, vault])


def make_alfred_item(item):
    """Convert a pass-cli item to Alfred Script Filter JSON format."""
    title = item.get("title") or item.get("data", {}).get("metadata", {}).get("name", "Unknown")
    item_id = item.get("itemId", "")
    share_id = item.get("shareId", "")
    vault_name = item.get("vaultName", "")
    item_title = title
    username = get_item_username(item)
    url = get_item_url(item)
    item_type = item.get("type", "login")

    # Arg carries all info needed for actions
    arg_data = json.dumps({
        "itemId": item_id,
        "shareId": share_id,
        "vaultName": vault_name,
        "itemTitle": item_title,
        "username": username,
        "url": url,
        "type": item_type,
    })

    subtitle = get_item_subtitle(item)

    result = {
        "uid": f"{share_id}/{item_id}",
        "title": title,
        "subtitle": subtitle,
        "arg": arg_data,
        "autocomplete": title,
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
                "subtitle": "⌘ Copy URL" if url else "⌘ No URL",
                "arg": arg_data,
                "variables": {"action": "copy_url"},
                "valid": bool(url),
            },
        },
    }

    # Default Enter action: open URL if available, otherwise copy password
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


def handle_command(query):
    """Handle special :commands."""
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
            name = v.get("vaultName") or v.get("name", "?")
            active = "✓ " if name in configured else ""
            items.append({
                "title": f"{active}{name}",
                "subtitle": "Set VAULT_NAME in workflow config to filter vaults (comma-separated)",
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
            "subtitle": f"Path: {PASS_CLI}" if cli_ok else "Install: curl -fsSL https://proton.me/download/pass-cli/install.sh | bash",
            "valid": False,
        })
        if cli_ok:
            logged_in = check_logged_in()
            items.append({
                "title": f"Session: {'✓ Active' if logged_in else '✗ Not logged in'}",
                "subtitle": "Run 'pass-cli login' in Terminal to log in" if not logged_in else "Authenticated",
                "valid": False,
            })
        return {"items": items}

    return None


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else ""

    # Handle :commands
    if query.startswith(":"):
        result = handle_command(query)
        if result:
            print(json.dumps(result))
            return

    # Check CLI availability
    if not check_cli_available():
        print(json.dumps({"items": [{
            "title": "pass-cli not found",
            "subtitle": "Install: curl -fsSL https://proton.me/download/pass-cli/install.sh | bash",
            "valid": False,
        }]}))
        return

    # Try cache first, then fetch
    items = load_cached_items()
    if items is None:
        items, error = fetch_items()
        if items is None:
            if error and ("not logged in" in error.lower() or "unauthorized" in error.lower() or "session" in error.lower()):
                print(json.dumps({"items": [{
                    "title": "Not logged in to Proton Pass",
                    "subtitle": "Run 'pass-cli login' in Terminal first",
                    "valid": False,
                }]}))
            else:
                print(json.dumps({"items": [{
                    "title": "Error fetching items",
                    "subtitle": error or "Unknown error",
                    "valid": False,
                }]}))
            return

    # Filter items
    filtered = [i for i in items if item_matches(i, query)]

    if not filtered:
        print(json.dumps({"items": [{
            "title": f"No items matching '{query}'" if query else "No items in vault",
            "subtitle": "Try a different search term",
            "valid": False,
        }]}))
        return

    # Convert to Alfred format
    alfred_items = [make_alfred_item(i) for i in filtered]
    print(json.dumps({"items": alfred_items}))


if __name__ == "__main__":
    main()
