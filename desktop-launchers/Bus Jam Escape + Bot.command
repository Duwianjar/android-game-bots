#!/bin/bash
tmux kill-session -t bus_jam_escape 2>/dev/null || true
pkill -9 -f "bus_jam_escape_bot" 2>/dev/null || true
tmux new-session -d -s bus_jam_escape 'cd /Users/macbookair/android-game-bots/bus-jam-escape && ./run_bus_jam_escape_bot.sh'
tail -f /Users/macbookair/bus_jam_escape_bot.log
