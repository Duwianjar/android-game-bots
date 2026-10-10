#!/bin/bash
set -euo pipefail
LOCK_DIR="/tmp/juicy_slash_guardian_bot.lock"
pkill -f '[j]uicy_slash_guardian_bot.py' 2>/dev/null || true
rm -rf "$LOCK_DIR"
echo "Bot Juicy Slash Guardian sudah distop."
