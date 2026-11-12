#!/bin/bash
# Script untuk menghentikan Crazy Fruit Blade Winner Recent Apps Watcher

LOCK_DIR="/tmp/crazy_fruit_recents_watcher.lock"

if [ -f "$LOCK_DIR/pid" ]; then
  PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "[*] Menghentikan bot pada PID $PID..."
    kill "$PID" 2>/dev/null || true
    sleep 0.5
    kill -9 "$PID" 2>/dev/null || true
  fi
  rm -rf "$LOCK_DIR"
fi

# Pastikan proses python crazy_fruit_recents_watcher dihentikan
pkill -f "crazy_fruit_recents_watcher.py" 2>/dev/null || true
echo "[OK] Bot Recent Apps Watcher berhasil dihentikan."
