#!/bin/bash
# Launcher Inject Iklan (Siklus Seeding Slot & Kembali ke Game)
# Usage:
#   ./run_inject_iklan.sh
#   ./run_inject_iklan.sh --serial SERIAL
#   ./run_inject_iklan.sh --loop --interval 300

set -euo pipefail
cd "$(dirname "$0")"

LOCK_DIR="/tmp/inject_iklan_bot.lock"
LOG_FILE="/Users/macbookair/inject_iklan.log"

if [ -d "$LOCK_DIR" ]; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Bot Inject Iklan sudah berjalan pada PID $OLD_PID."
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
  echo "Bot Inject Iklan selesai/dihentikan."
}
trap cleanup EXIT INT TERM

exec > >(tee -a "$LOG_FILE") 2>&1

PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

echo "=================================================="
echo "  INJECT IKLAN (SLOT SEARCH & REGISTRATION BOT)"
echo "=================================================="
echo "Log: $LOG_FILE"
echo "Stop: Ctrl+C"
echo ""

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu "$PYTHON_BIN" -u ./inject_iklan.py "$@"
else
  "$PYTHON_BIN" -u ./inject_iklan.py "$@"
fi
