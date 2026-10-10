#!/bin/bash
set -euo pipefail

LOCK_DIR="/tmp/fruit_blade_guardian_bot.lock"

pkill -f '[f]ruit_blade_guardian_bot.py' 2>/dev/null || true
rm -rf "$LOCK_DIR"
echo "Bot Fruit Blade Guardian sudah distop."
