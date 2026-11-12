#!/bin/bash
set +e
tmux kill-session -t soda_jam_puzzle 2>/dev/null
pkill -f '[s]oda_jam_puzzle_bot.py' 2>/dev/null
rm -rf /tmp/soda_jam_puzzle_bot.lock
echo "Bot Soda Jam Puzzle sudah distop."
