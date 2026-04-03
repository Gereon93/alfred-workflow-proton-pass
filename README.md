# Proton Pass for Alfred

## Setup

[Install the Proton Pass CLI](https://proton.me/pass/download) and log in:

```bash
curl -fsSL https://proton.me/download/pass-cli/install.sh | bash
pass-cli login
```

If `pass-cli` is not found by the workflow, set the path manually in the Workflow's Configuration under `pass-cli Path`. Find it by running `which pass-cli` in Terminal.

## Usage

Search and copy credentials from your Proton Pass vault via the `ppass` keyword.

Each vault item expands into separate action rows:

* <kbd>↩</kbd> **Copy Password**
* <kbd>↩</kbd> **Copy Username**
* <kbd>↩</kbd> **Open URL** in browser
* <kbd>↩</kbd> **Copy TOTP** code (only shown when configured)

Type `ppass :setup` to check CLI status and login session. Type `ppass :refresh` to clear the cache and reload from Proton. Type `ppass :vault` to show available vaults.

Copied passwords and usernames are automatically cleared from the clipboard after the time configured in the Workflow's Configuration.

## Disclaimer

This is an unofficial, community-maintained project and is not affiliated with, endorsed by, or associated with Proton AG. Proton and Proton Pass are trademarks of Proton AG.

*Developed with the assistance of Claude AI (Anthropic).*
