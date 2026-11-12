#!/bin/bash
set +e
tmux kill-session -t bus_jam_parking 2>/dev/null
pkill -f '[b]us_jam_parking_bot.py' 2>/dev/null
rm -rf /tmp/bus_jam_parking_bot.lock
echo "Bot Bus Jam Parking sudah distop."
