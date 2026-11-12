#!/bin/bash
# Launcher Greenfield Merge Bot.
# Usage:
#   ./run_greenfield_merge_bot.sh
#   ./run_greenfield_merge_bot.sh --serial SERIAL

set -euo pipefail
cd "$(dirname "$0")"

LOCK_DIR="/tmp/greenfield_merge_bot.lock"
LOG_FILE="/Users/macbookair/greenfield_merge_bot.log"

if [ -d "$LOCK_DIR" ]; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Bot Greenfield Merge sudah berjalan pada PID $OLD_PID."
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
  echo "Bot Greenfield Merge dihentikan."
}
trap cleanup EXIT INT TERM

PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

echo "=================================================="
echo "  GREENFIELD MERGE GUARDIAN & AUTO-AD BOT"
echo "=================================================="
echo "Target package: com.xteleremobilecompanyltd.GreenfieldMerge"
echo "Log: $LOG_FILE"
echo "Stop: Ctrl+C atau ./stop_greenfield_merge_bot.sh"
echo ""

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu "$PYTHON_BIN" -u ./greenfield_merge_bot.py "$@"
else
  "$PYTHON_BIN" -u ./greenfield_merge_bot.py "$@"
fi
