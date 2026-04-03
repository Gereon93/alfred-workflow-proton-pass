# Proton Pass for Alfred

Search and copy credentials from your Proton Pass vault directly from Alfred.

## Features

- Search across all vaults by title, username or URL
- Copy password, username, URL or TOTP code
- Each item expands into clearly labeled action rows — no modifier keys to remember
- Automatic clipboard clearing after configurable timeout
- 5-minute local cache for instant results
- Built-in commands for setup, cache refresh and vault overview

## Requirements

- [Alfred Powerpack](https://www.alfredapp.com/powerpack/)
- [Proton Pass CLI](https://proton.me/pass/download) (`pass-cli`) installed and logged in
- macOS 13 or later
- Python 3 (bundled with macOS)

## Installation

1. Download the latest `Proton Pass.alfredworkflow` from [Releases](https://github.com/Gereon93/alfred-workflow-proton-pass/releases)
2. Double-click to import into Alfred

## Setup

1. Install `pass-cli` if not already installed:
   ```bash
   curl -fsSL https://proton.me/download/pass-cli/install.sh | bash
   ```
2. Login to your Proton account:
   ```bash
   pass-cli login
   ```
3. Type `ppass :setup` in Alfred to verify everything works

*If Alfred reports that `pass-cli` is not found, set the path manually in the Workflow Configuration under `PASS_CLI_PATH`. Find the path by running `which pass-cli` in Terminal.*

## Usage

Type `ppass` and start typing to filter. Each vault item shows as separate action rows:

- **Title — Copy Password** → press `↩ Enter` to copy the password
- **Title — Copy Username** → press `↩ Enter` to copy the username
- **Title — Open URL** → press `↩ Enter` to open in browser
- **Title — Copy TOTP** → press `↩ Enter` to copy the TOTP code (only shown when configured)

### Commands

- `ppass :setup` — Check CLI status and login session
- `ppass :refresh` — Clear cache and force reload from Proton
- `ppass :vault` — Show available vaults

## Configuration

In Alfred's Workflow Configuration:

- **Vault Name(s)** — Comma-separated list of vault names to search (e.g., `Personal,Work`). Leave empty for all vaults.
- **pass-cli Path** — Custom path to the `pass-cli` binary. Leave empty for auto-detect.
- **Clipboard Clear Seconds** — Seconds after which the clipboard is cleared (default: 30).

## Disclaimer

This is an unofficial, community-maintained project and is not affiliated with, endorsed by, or associated with Proton AG. Proton and Proton Pass are trademarks of Proton AG.

*Developed with the assistance of Claude AI (Anthropic).*
