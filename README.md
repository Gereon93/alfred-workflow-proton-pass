# Proton Pass for Alfred

Search and copy passwords from your Proton Pass vault directly from Alfred.

**Note:** This project was vibe-coded.

## Prerequisites

1.  **Install `pass-cli`**:
    Run this command in your Terminal:
    ```bash
    curl -fsSL https://proton.me/download/pass-cli/install.sh | bash
    ```
    *Note: If Alfred still reports that `pass-cli` is not found after installation, you can manually set the path in the Workflow Configuration under `PASS_CLI_PATH`. You can find the path by running `where pass-cli` in your Terminal.*

2.  **Login**:
    Run `pass-cli login` in your Terminal and follow the instructions.

## Installation

1.  Download the latest `Proton Pass.alfredworkflow` from the [Releases](https://github.com/Gereon93/alfred-workflow-proton-pass/releases) page.
2.  Double-click to install.

## Usage

-   Type `pp` followed by your search query.
-   `↩ Enter` — Open URL (or copy password if no URL)
-   `⌃ Ctrl+Enter` — Copy password
-   `⌥ Opt+Enter` — Copy username
-   `⇧ Shift+Enter` — Copy TOTP code
-   `⌘ Cmd+Enter` — Copy URL

### Commands

-   `pp :setup` — Check CLI status and login session
-   `pp :refresh` — Clear cache and force reload from Proton
-   `pp :vault` — Show available vaults

## Configuration

Set these environment variables in the Alfred Workflow configuration:

-   `VAULT_NAME`: (Optional) Comma-separated list of vault names to search (e.g., `Personal,Work`). If empty, all vaults are searched.
-   `PASS_CLI_PATH`: (Optional) Custom path to the `pass-cli` binary.
-   `CLIPBOARD_CLEAR_SECONDS`: (Default: 30) Seconds after which the clipboard is cleared.
