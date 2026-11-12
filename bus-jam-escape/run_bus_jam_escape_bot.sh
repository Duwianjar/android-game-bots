#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

LOCK_DIR="/tmp/bus_jam_escape_bot.lock"
LOG_FILE="/Users/macbookair/bus_jam_escape_bot.log"

if [ -d "$LOCK_DIR" ]; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Bot Bus Jam Escape sudah berjalan pada PID $OLD_PID."
    exit 1
  fi
  rm -rf "$LOCK_DIR"
fi

mkdir "$LOCK_DIR"
echo $$ > "$LOCK_DIR/pid"

cleanup() {
  rm -rf "$LOCK_DIR"
  echo "Bot Bus Jam Escape dihentikan."
}
trap cleanup EXIT INT TERM

exec > >(tee -a "$LOG_FILE") 2>&1

PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

echo "=================================================="
echo "  BUS JAM ESCAPE BOT"
echo "=================================================="
echo "Target package: com.busjam.escape.frenzy"
echo "Log: $LOG_FILE"
echo ""

if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -dimsu "$PYTHON_BIN" -u ./bus_jam_escape_bot.py "$@"
else
  exec "$PYTHON_BIN" -u ./bus_jam_escape_bot.py "$@"
fi
