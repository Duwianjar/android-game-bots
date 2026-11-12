#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
LOCK_DIR="/tmp/lucky_arrow_escaper_guardian_bot.lock"
LOG_FILE="/Users/macbookair/lucky_arrow_escaper_guardian_bot.log"

if [ -d "$LOCK_DIR" ]; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Bot Lucky Arrow Escaper sudah berjalan pada PID $OLD_PID."
    exit 1
  fi
  rm -rf "$LOCK_DIR"
fi
mkdir -p "$LOCK_DIR"
echo $$ > "$LOCK_DIR/pid"

cleanup(){
  rm -rf "$LOCK_DIR"
  echo "Bot Lucky Arrow Escaper dihentikan."
}
trap cleanup EXIT INT TERM

exec > >(tee -a "$LOG_FILE") 2>&1

PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

echo "=================================================="
echo "  LUCKY ARROW ESCAPER GUARDIAN BOT (PERSISTENT)"
echo "=================================================="
echo "Target package: com.starlightgame.luckyarrowescaper"
echo "Log: $LOG_FILE"
echo "Auto-restart: AKTIF"
echo ""

export LUCKY_ARROW_NO_FILE_LOG=1

while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Menjalankan bot (Supervisor PID $$)..."
  if command -v caffeinate >/dev/null 2>&1; then
    caffeinate -dimsu "$PYTHON_BIN" -u ./lucky_arrow_escaper_guardian_bot.py "$@" || true
  else
    "$PYTHON_BIN" -u ./lucky_arrow_escaper_guardian_bot.py "$@" || true
  fi
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Bot berhenti tak terduga, auto-restart dalam 3 detik..."
  sleep 3
done
