#!/bin/bash
# Runner untuk Crazy Fruit Blade Winner - Recent Apps Watcher Bot
# Lokasi: /Users/macbookair/android-game-bots/crazy-fruit-blade-winner/run_recents_watcher.sh

cd "$(dirname "$0")"

LOCK_DIR="/tmp/crazy_fruit_recents_watcher.lock"
LOG_FILE="$HOME/crazy_fruit_recents_watcher.log"

if [ -f "$LOCK_DIR/pid" ]; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[!] Bot Recent Apps Watcher sudah berjalan pada PID $OLD_PID."
    echo "    Untuk menghentikan: ./stop_recents_watcher.sh"
    exit 1
  fi
  rm "$LOCK_DIR/pid" 2>/dev/null || true
  rmdir "$LOCK_DIR" 2>/dev/null || true
fi

mkdir -p "$LOCK_DIR"

PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

echo "=========================================================="
echo "  CRAZY FRUIT BLADE WINNER - RECENT APPS WATCHER"
echo "=========================================================="
echo "Target: com.starlightgame.crazyfruitbladewinner"
echo "Log   : $LOG_FILE"
echo "Stop  : Tekan Ctrl+C atau jalankan stop_recents_watcher.sh"
echo "=========================================================="
echo ""

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu "$PYTHON_BIN" -u ./crazy_fruit_recents_watcher.py "$@" &
  BOT_PID=$!
else
  "$PYTHON_BIN" -u ./crazy_fruit_recents_watcher.py "$@" &
  BOT_PID=$!
fi

echo $BOT_PID > "$LOCK_DIR/pid"
echo "[OK] Bot berjalan di background dengan PID $BOT_PID"
wait $BOT_PID
