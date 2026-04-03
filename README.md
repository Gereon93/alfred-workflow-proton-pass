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

Type `ppass` followed by your search query. Each vault item expands into separate rows:

-   `Title — Copy Password` → press `↩ Enter` to copy the password
-   `Title — Copy Username` → press `↩ Enter` to copy the username
-   `Title — Open URL` → press `↩ Enter` to open the URL in your browser
-   `Title — Copy TOTP` → press `↩ Enter` to copy the current TOTP code (only shown when configured)

### Commands

-   `ppass :setup` — Check CLI status and login session
-   `ppass :refresh` — Clear cache and force reload from Proton
-   `ppass :vault` — Show available vaults

## Configuration

Set these environment variables in the Alfred Workflow configuration:

-   `VAULT_NAME`: (Optional) Comma-separated list of vault names to search (e.g., `Personal,Work`). If empty, all vaults are searched.
-   `PASS_CLI_PATH`: (Optional) Custom path to the `pass-cli` binary.
-   `CLIPBOARD_CLEAR_SECONDS`: (Default: 30) Seconds after which the clipboard is cleared.
