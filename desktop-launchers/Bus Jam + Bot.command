#!/bin/bash
tmux kill-session -t bus_jam_parking 2>/dev/null || true
pkill -9 -f "bus_jam_parking_bot" 2>/dev/null || true
tmux new-session -d -s bus_jam_parking 'cd /Users/macbookair/android-game-bots/bus-jam-parking && ./run_bus_jam_parking_bot.sh'
tail -f /Users/macbookair/bus_jam_parking_bot.log
