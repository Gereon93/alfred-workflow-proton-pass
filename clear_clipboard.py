#!/usr/bin/env python3
"""Background script to clear clipboard after N seconds."""

import subprocess
import sys
import time


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    # Remember what we copied so we only clear if it's still the same
    result = subprocess.run(["pbpaste"], capture_output=True)
    original = result.stdout
    time.sleep(seconds)
    # Only clear if clipboard still contains what we put there
    result = subprocess.run(["pbpaste"], capture_output=True)
    if result.stdout == original:
        subprocess.run(["pbcopy"], input=b"")


if __name__ == "__main__":
    main()
