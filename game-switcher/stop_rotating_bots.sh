#!/bin/bash
set +e
tmux kill-session -t game_rotator 2>/dev/null
/Users/macbookair/android-game-bots/game-switcher/stop_all_switcher_bots.sh || true
echo "Rotator dan semua bot anak sudah distop."
