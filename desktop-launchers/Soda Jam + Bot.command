#!/bin/bash
tmux kill-session -t soda_jam_puzzle 2>/dev/null || true
pkill -9 -f "soda_jam_puzzle_bot" 2>/dev/null || true
tmux new-session -d -s soda_jam_puzzle 'cd /Users/macbookair/android-game-bots/soda-jam-puzzle && ./run_soda_jam_puzzle_bot.sh'
tail -f /Users/macbookair/soda_jam_puzzle_bot.log
