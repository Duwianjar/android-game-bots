#!/bin/bash
# Rotator pintar: 1 buka iklan -> 2 buka iklan -> balik 1 selesaikan+buka iklan -> balik 2 selesaikan+buka iklan -> ulang.
# Angka 180 = batas maksimal 3 menit per giliran jika macet.
tmux kill-session -t game_rotator 2>/dev/null
/Users/macbookair/android-game-bots/game-switcher/stop_all_switcher_bots.sh || true
tmux new-session -d -s game_rotator 'cd /Users/macbookair/android-game-bots/game-switcher && ./run_rotating_bots.sh 180'
echo "Bot bergantian pintar Magic-Woodland sudah jalan. Log: /Users/macbookair/game_rotator.log"
