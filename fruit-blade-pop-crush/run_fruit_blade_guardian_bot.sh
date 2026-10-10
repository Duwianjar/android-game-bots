#!/bin/bash
# Launcher Fruit Blade Pop Crush Guardian Bot.
# Usage:
#   ./run_fruit_blade_guardian_bot.sh
#   ./run_fruit_blade_guardian_bot.sh --serial SERIAL

set -euo pipefail
cd "$(dirname "$0")"

LOCK_DIR="/tmp/fruit_blade_guardian_bot.lock"
LOG_FILE="/Users/macbookair/fruit_blade_guardian_bot.log"

if [ -d "$LOCK_DIR" ]; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Bot Fruit Blade Guardian sudah berjalan pada PID $OLD_PID."
    exit 1
  fi
  rm -rf "$LOCK_DIR"
fi

mkdir "$LOCK_DIR"
echo $$ > "$LOCK_DIR/pid"

cleanup() {
  rm -rf "$LOCK_DIR"
  echo "Bot Fruit Blade Guardian dihentikan."
}
trap cleanup EXIT INT TERM

exec > >(tee -a "$LOG_FILE") 2>&1

PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

echo "=================================================="
echo "  FRUIT BLADE POP CRUSH GUARDIAN BOT"
echo "=================================================="
echo "Target package: com.starlightgame.fruitbladepopcrush"
echo "Log: $LOG_FILE"
echo "Stop: Ctrl+C atau ./stop_fruit_blade_guardian_bot.sh"
echo ""

export FRUIT_BLADE_NO_FILE_LOG=1
if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -dimsu "$PYTHON_BIN" -u ./fruit_blade_guardian_bot.py "$@"
else
  exec "$PYTHON_BIN" -u ./fruit_blade_guardian_bot.py "$@"
fi
