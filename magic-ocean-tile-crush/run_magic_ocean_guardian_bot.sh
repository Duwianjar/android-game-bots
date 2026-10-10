#!/bin/bash
# Launcher Magic Ocean Tile Crush Guardian Bot.
# Usage:
#   ./run_magic_ocean_guardian_bot.sh
#   ./run_magic_ocean_guardian_bot.sh --serial SERIAL

set -euo pipefail
cd "$(dirname "$0")"

LOCK_DIR="/tmp/magic_ocean_guardian_bot.lock"
LOG_FILE="/Users/macbookair/magic_ocean_guardian_bot.log"

if [ -d "$LOCK_DIR" ]; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Bot Magic Ocean Guardian sudah berjalan pada PID $OLD_PID."
    exit 1
  fi
  rm -rf "$LOCK_DIR"
fi

mkdir "$LOCK_DIR"
echo $$ > "$LOCK_DIR/pid"

cleanup() {
  rm -rf "$LOCK_DIR"
  echo "Bot Magic Ocean Guardian dihentikan."
}
trap cleanup EXIT INT TERM

exec > >(tee -a "$LOG_FILE") 2>&1

PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

echo "=================================================="
echo "  MAGIC OCEAN TILE CRUSH GUARDIAN BOT"
echo "=================================================="
echo "Target package: com.starlightgame.magicoceantilecrush"
echo "Log: $LOG_FILE"
echo "Stop: Ctrl+C atau ./stop_magic_ocean_guardian_bot.sh"
echo ""

export MAGIC_OCEAN_NO_FILE_LOG=1
# caffeinate menjaga Mac tidak idle sleep selama bot berjalan.
# Catatan: agar tetap jalan saat lid/layar MacBook ditutup, aktifkan juga script:
#   /Users/macbookair/enable_bot_awake_lid_closed.sh
if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -dimsu "$PYTHON_BIN" -u ./magic_ocean_guardian_bot.py "$@"
else
  exec "$PYTHON_BIN" -u ./magic_ocean_guardian_bot.py "$@"
fi
