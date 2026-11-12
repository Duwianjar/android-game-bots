#!/bin/bash
set -euo pipefail

LOCK_DIR="/tmp/zoo_tile_guardian_bot.lock"

pkill -9 -f 'zoo_tile' 2>/dev/null || true
rm -rf "$LOCK_DIR" 2>/dev/null || true
echo "Bot Zoo Tile sudah dihentikan."
