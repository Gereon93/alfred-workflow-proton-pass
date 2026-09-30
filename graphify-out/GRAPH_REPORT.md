# Graph Report - alfred-workflow-proton-pass  (2026-10-01)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 198 nodes · 418 edges · 18 communities
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.85)
- Token cost: 77,838 input · 239 output

## Graph Freshness
- Built from commit: `6dad268d`
- Run `git diff 6dad268d --stat -- ':!graphify-out' ':!.graphify*' ':!CLAUDE.md'` to check if indexed source files have changed since the build.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Clipboard Clear Script
- Secret Fetch and Dispatch
- Login Probe and Filtering
- Action Dispatch Tests
- Search Helpers Tests
- Logout Flag Notifications
- CLI and Vault Commands
- Vault Item Fetching
- Auth Cache Status
- Search Main Flow
- Open URL Handling
- Item Cache Storage
- Clipboard Actions
- Copy Secret Handling
- Item Normalization
- Cache Clearing
- Multi-Vault Fetch
- Pass CLI Discovery

## God Nodes (most connected - your core abstractions)
1. `main()` - 17 edges
2. `main()` - 15 edges
3. `fetch_items()` - 12 edges
4. `get_login_status()` - 12 edges
5. `_completed()` - 10 edges
6. `get_auth_cache_path()` - 9 edges
7. `write_auth_flag()` - 9 edges
8. `_completed()` - 8 edges
9. `load_cached_items()` - 8 edges
10. `_write_stub()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `test_cache_missing_returns_none()` --calls--> `load_cached_items()`  [EXTRACTED]
  tests/test_search.py → search.py
- `test_handle_failure_flags_auth_errors()` --calls--> `handle_failure()`  [EXTRACTED]
  tests/test_action.py → action.py
- `test_cache_dir_defaults_to_home()` --calls--> `get_cache_dir()`  [EXTRACTED]
  tests/test_search.py → search.py
- `test_fetch_items_uses_configured_vaults()` --calls--> `load_cached_items()`  [EXTRACTED]
  tests/test_search.py → search.py
- `test_copy_secret_copies_and_schedules_a_wipe()` --calls--> `copy_secret()`  [EXTRACTED]
  tests/test_action.py → action.py

## Import Cycles
- None detected.

## Communities (18 total, 0 thin omitted)

### Community 0 - "Clipboard Clear Script"
Cohesion: 0.13
Nodes (24): Background script to clear clipboard after N seconds., json, os, subprocess, sys, tempfile, Makes the workflow scripts importable from tests/ without installing them., After re-login, a cached logged-out flag must not keep showing the banner. (+16 more)

### Community 1 - "Secret Fetch and Dispatch"
Cohesion: 0.14
Nodes (18): get_password(), get_totp(), main(), cache_dir(), _completed(), dispatch(), fixture, Records what main() did, with every side effect stubbed out. (+10 more)

### Community 2 - "Login Probe and Filtering"
Cohesion: 0.12
Nodes (14): filter_rows(), probe_login(), True=logged in, False=logged out, None=could not determine (timeout/missing).…, Filter rows by the typed query (alfredfiltersresults is off, so we filter).…, parametrize, test_classify_content(), test_fetch_items_maps_cli_failures(), test_fetch_vault_list_reports_missing_cli() (+6 more)

### Community 3 - "Action Dispatch Tests"
Cohesion: 0.21
Nodes (14): main(), Dispatch the Alfred action; every input arrives as an environment variable., pytest, Unit tests for action.py and clear_clipboard.py — imported in-process for…, test_main_ignores_an_unknown_action(), test_main_password_action(), test_main_password_failure_is_not_silent(), test_main_refresh_action() (+6 more)

### Community 4 - "Search Helpers Tests"
Cohesion: 0.19
Nodes (13): _find_pass_cli(), make_rows_for_item(), cache_dir(), fixture, Unit tests for search.py — imported in-process so coverage sees the lines., test_cache_dir_defaults_to_home(), test_cache_missing_returns_none(), test_find_pass_cli_falls_back_to_bare_name() (+5 more)

### Community 5 - "Logout Flag Notifications"
Cohesion: 0.18
Nodes (10): mark_logged_out(), notify(), Flip the shared auth flag so the next search surfaces the login banner., test_mark_logged_out_swallows_write_errors(), boom(), test_mark_logged_out_writes_the_shared_flag(), test_notify_flattens_newlines_and_defaults(), test_notify_passes_message_as_argv() (+2 more)

### Community 6 - "CLI and Vault Commands"
Cohesion: 0.18
Nodes (10): check_cli_available(), check_logged_in(), get_configured_vaults(), make_command_rows(), test_check_cli_available(), test_check_cli_available_false_when_missing(), test_check_logged_in_maps_unknown_to_false(), test_get_configured_vaults() (+2 more)

### Community 7 - "Vault Item Fetching"
Cohesion: 0.31
Nodes (10): fetch_items_for_vault(), fetch_vault_list(), _completed(), test_fetch_items_for_vault_normalizes(), test_fetch_items_for_vault_rejects_unexpected_shape(), test_fetch_items_for_vault_reports_stderr(), test_fetch_vault_list_accepts_bare_list(), test_fetch_vault_list_rejects_unexpected_shape() (+2 more)

### Community 8 - "Auth Cache Status"
Cohesion: 0.40
Nodes (10): get_auth_cache_path(), get_login_status(), Return True (logged in), False (logged out), or None (could not determine).…, write_auth_flag(), test_login_status_reprobes_a_cached_logout(), test_login_status_reprobes_an_expired_cache(), test_login_status_survives_a_corrupt_auth_cache(), test_login_status_unknown_is_not_cached() (+2 more)

### Community 9 - "Search Main Flow"
Cohesion: 0.31
Nodes (10): login_banner(), main(), _stdout_json(), test_login_banner_is_not_actionable(), test_main_fetches_on_cold_cache_and_filters(), test_main_maps_auth_error_from_fetch(), test_main_reports_missing_cli(), test_main_serves_cached_items() (+2 more)

### Community 10 - "Open URL Handling"
Cohesion: 0.28
Nodes (8): open_url(), Return the http(s) URL to hand to `open`, or None if it isn't a web URL. The…, web_target(), parametrize, test_handle_failure_flags_auth_errors(), test_open_url_opens_web_targets(), test_open_url_refuses_non_web_targets(), test_open_url_reports_a_failed_open()

### Community 11 - "Item Cache Storage"
Cohesion: 0.42
Nodes (8): get_cache_dir(), get_cache_path(), load_cached_items(), Alfred Script Filter for Proton Pass. Each vault item becomes 3 rows: Copy…, save_cache(), test_cache_corrupt_returns_none(), test_cache_ignored_when_older_than_ttl(), test_cache_roundtrip()

### Community 12 - "Clipboard Actions"
Cohesion: 0.32
Nodes (7): clear_clipboard_later(), copy_to_clipboard(), copy_with_clear(), Executes actions: copy password, username, open URL, copy TOTP. All data comes…, test_clear_clipboard_later_detaches(), test_copy_to_clipboard_feeds_pbcopy(), urllib_parse

### Community 13 - "Copy Secret Handling"
Cohesion: 0.29
Nodes (7): copy_secret(), handle_failure(), Copy a secret fetched via pass-cli, or surface why the fetch failed., test_copy_secret_copies_and_schedules_a_wipe(), test_copy_secret_reports_failures_instead_of_copying(), test_handle_failure_passes_other_errors_through(), test_handle_failure_without_message()

### Community 14 - "Item Normalization"
Cohesion: 0.29
Nodes (7): _classify_content(), _normalize_item(), Return (login_data, item_type) for an item's inner content block., test_normalize_item_falls_back_to_email(), test_normalize_item_ignores_non_string_url(), test_normalize_item_maps_login_fields(), test_normalize_item_tolerates_empty_payload()

### Community 15 - "Cache Clearing"
Cohesion: 0.40
Nodes (5): clear_item_cache(), get_cache_dir(), test_cache_dir_defaults_to_home(), test_clear_item_cache_is_a_noop_without_a_cache(), test_clear_item_cache_removes_the_file()

### Community 16 - "Multi-Vault Fetch"
Cohesion: 0.40
Nodes (5): fetch_items(), test_fetch_items_discovers_vaults_when_unconfigured(), test_fetch_items_keeps_last_error_when_all_vaults_fail(), test_fetch_items_uses_configured_vaults(), test_fetch_items_without_vaults_returns_error()

### Community 17 - "Pass CLI Discovery"
Cohesion: 0.50
Nodes (4): _find_pass_cli(), test_find_pass_cli_falls_back_to_bare_name(), test_find_pass_cli_prefers_explicit_path(), test_find_pass_cli_takes_first_existing_default()

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Action Dispatch Tests` to `Secret Fetch and Dispatch`, `Open URL Handling`, `Clipboard Actions`, `Copy Secret Handling`, `Cache Clearing`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `test_open_url_reports_a_failed_open()` connect `Open URL Handling` to `Action Dispatch Tests`, `Logout Flag Notifications`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `test_fetch_items_maps_cli_failures()` connect `Login Probe and Filtering` to `Multi-Vault Fetch`, `Search Helpers Tests`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `main()` (e.g. with `get_password()` and `get_totp()`) actually correct?**
  _`main()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `Clipboard Clear Script` be split into smaller, more focused modules?**
  _Cohesion score 0.12535612535612536 - nodes in this community are weakly interconnected._
- **Should `Secret Fetch and Dispatch` be split into smaller, more focused modules?**
  _Cohesion score 0.1437908496732026 - nodes in this community are weakly interconnected._
- **Should `Login Probe and Filtering` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._