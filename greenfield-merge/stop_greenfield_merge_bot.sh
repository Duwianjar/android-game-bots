#!/bin/bash
set -euo pipefail

LOCK_DIR="/tmp/greenfield_merge_bot.lock"

pkill -f '[g]reenfield_merge_bot.py' 2>/dev/null || true
rm -f "$LOCK_DIR/pid" 2>/dev/null || true
rmdir "$LOCK_DIR" 2>/dev/null || true
echo "Bot Greenfield Merge sudah dihentikan."
