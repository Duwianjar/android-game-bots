#!/bin/bash
set -euo pipefail

LOCK_DIR="/tmp/magic_ocean_guardian_bot.lock"

pkill -f '[m]agic_ocean_guardian_bot.py' 2>/dev/null || true
rm -rf "$LOCK_DIR"
echo "Bot Magic Ocean Guardian sudah distop."
