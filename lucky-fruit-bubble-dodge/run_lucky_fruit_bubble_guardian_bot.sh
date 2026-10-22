#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
LOCK_DIR="/tmp/lucky_fruit_bubble_guardian_bot.lock"
LOG_FILE="/Users/macbookair/lucky_fruit_bubble_guardian_bot.log"
if [ -d "$LOCK_DIR" ]; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Bot Lucky Fruit sudah berjalan pada PID $OLD_PID."
    exit 1
  fi
  rm -rf "$LOCK_DIR"
fi
mkdir "$LOCK_DIR"
echo $$ > "$LOCK_DIR/pid"
cleanup(){ rm -rf "$LOCK_DIR"; echo "Bot Lucky Fruit dihentikan."; }
trap cleanup EXIT INT TERM
exec > >(tee -a "$LOG_FILE") 2>&1
PYTHON_BIN="/opt/homebrew/bin/python3"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$(command -v python3)"
echo "=================================================="
echo "  LUCKY FRUIT BUBBLE DODGE GUARDIAN BOT"
echo "=================================================="
echo "Target package: com.newgameclick.luckyfruitbubbledodge"
echo "Log: $LOG_FILE"
echo ""
export LUCKY_FRUIT_NO_FILE_LOG=1
if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -dimsu "$PYTHON_BIN" -u ./lucky_fruit_bubble_guardian_bot.py "$@"
else
  exec "$PYTHON_BIN" -u ./lucky_fruit_bubble_guardian_bot.py "$@"
fi
