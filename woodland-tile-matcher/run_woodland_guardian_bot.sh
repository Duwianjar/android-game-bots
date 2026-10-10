#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
LOCK_DIR="/tmp/woodland_guardian_bot.lock"
LOG_FILE="/Users/macbookair/woodland_guardian_bot.log"
if [ -d "$LOCK_DIR" ]; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Bot Woodland sudah berjalan pada PID $OLD_PID."
    exit 1
  fi
  rm -rf "$LOCK_DIR"
fi
mkdir "$LOCK_DIR"
echo $$ > "$LOCK_DIR/pid"
cleanup(){ rm -rf "$LOCK_DIR"; echo "Bot Woodland dihentikan."; }
trap cleanup EXIT INT TERM
exec > >(tee -a "$LOG_FILE") 2>&1

PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi
echo "=================================================="
echo "  WOODLAND TILE MATCHER GUARDIAN BOT"
echo "=================================================="
echo "Target package: com.starlightgame.woodlandtilematcher"
echo "Log: $LOG_FILE"
echo ""
export WOODLAND_NO_FILE_LOG=1
if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -dimsu "$PYTHON_BIN" -u ./woodland_guardian_bot.py "$@"
else
  exec "$PYTHON_BIN" -u ./woodland_guardian_bot.py "$@"
fi
