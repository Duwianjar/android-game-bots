#!/bin/bash
# Launcher Zoo Tile Guardian Bot.
# Usage:
#   ./run_zoo_tile_guardian_bot.sh
#   ./run_zoo_tile_guardian_bot.sh --serial SERIAL --interval 0.5

set -euo pipefail
cd "$(dirname "$0")"

LOCK_DIR="/tmp/zoo_tile_guardian_bot.lock"
LOG_FILE="/Users/macbookair/zoo_tile_guardian_bot.log"

if [ -d "$LOCK_DIR" ]; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Bot Zoo Tile sudah berjalan pada PID $OLD_PID."
    exit 1
  fi
  rm -f "$LOCK_DIR/pid" 2>/dev/null || true
  rmdir "$LOCK_DIR" 2>/dev/null || true
fi

mkdir -p "$LOCK_DIR"
echo $$ > "$LOCK_DIR/pid"

cleanup() {
  rm -f "$LOCK_DIR/pid" 2>/dev/null || true
  rmdir "$LOCK_DIR" 2>/dev/null || true
  echo "Bot Zoo Tile dihentikan."
}
trap cleanup EXIT INT TERM

PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

echo "=================================================="
echo "  ZOO TILE GUARDIAN BOT (AUTO REOPEN)"
echo "=================================================="
echo "Target package: com.zoo.tile.cute.animal.elephant.mouse.fox"
echo "Log: $LOG_FILE"
echo "Stop: Ctrl+C atau ./stop_zoo_tile_guardian_bot.sh"
echo ""

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu "$PYTHON_BIN" -u ./zoo_tile_guardian_bot.py "$@"
else
  "$PYTHON_BIN" -u ./zoo_tile_guardian_bot.py "$@"
fi
