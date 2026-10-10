#!/bin/bash
set -euo pipefail

# Rotasi pintar berdasarkan iklan:
# Magic buka iklan -> Woodland buka iklan -> Magic selesaikan+buka iklan baru -> Woodland selesaikan+buka iklan baru -> ulang.
# Usage: ./run_rotating_bots.sh [max_detik_per_giliran]
MAX_TURN_SECONDS="${1:-180}"
LOG_FILE="/Users/macbookair/game_rotator.log"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

exec > >(tee -a "$LOG_FILE") 2>&1

if ! [[ "$MAX_TURN_SECONDS" =~ ^[0-9]+$ ]] || [ "$MAX_TURN_SECONDS" -lt 60 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Max detik per giliran tidak valid: $MAX_TURN_SECONDS. Minimal 60 detik."
  exit 2
fi

cleanup() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rotator dihentikan, stop bot anak..."
  /Users/macbookair/android-game-bots/game-switcher/stop_all_switcher_bots.sh || true
}
trap cleanup EXIT INT TERM

cd "$SCRIPT_DIR"
exec caffeinate -dimsu python3 -u ./smart_ad_rotator.py --max-turn-seconds "$MAX_TURN_SECONDS"
