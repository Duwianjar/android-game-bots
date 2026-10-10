#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
LOCK_DIR="/tmp/juicy_slash_guardian_bot.lock"
LOG_FILE="/Users/macbookair/juicy_slash_guardian_bot.log"
if [ -d "$LOCK_DIR" ]; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Bot Juicy Slash Guardian sudah berjalan pada PID $OLD_PID."
    exit 1
  fi
  rm -rf "$LOCK_DIR"
fi
mkdir "$LOCK_DIR"
echo $$ > "$LOCK_DIR/pid"
cleanup() { rm -rf "$LOCK_DIR"; echo "Bot Juicy Slash Guardian dihentikan."; }
trap cleanup EXIT INT TERM
exec > >(tee -a "$LOG_FILE") 2>&1
PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then PYTHON_BIN="$(command -v python3)"; fi
echo "=================================================="
echo "  JUICY SLASH BLADE FRUIT GUARDIAN BOT"
echo "=================================================="
echo "Target package: com.dudufun.juicyslashbladefruit"
echo "Log: $LOG_FILE"
echo "Stop: Ctrl+C atau ./stop_juicy_slash_guardian_bot.sh"
echo ""
export JUICY_SLASH_NO_FILE_LOG=1
if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -dimsu "$PYTHON_BIN" -u ./juicy_slash_guardian_bot.py "$@"
else
  exec "$PYTHON_BIN" -u ./juicy_slash_guardian_bot.py "$@"
fi
