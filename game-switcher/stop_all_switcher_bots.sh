#!/bin/bash
set +e
tmux kill-session -t magic_ocean_guardian 2>/dev/null
tmux kill-session -t woodland_guardian 2>/dev/null
pkill -f '[m]agic_ocean_guardian_bot.py' 2>/dev/null
pkill -f '[w]oodland_guardian_bot.py' 2>/dev/null
rm -rf /tmp/magic_ocean_guardian_bot.lock
rm -rf /tmp/woodland_guardian_bot.lock
echo "Semua bot switcher distop."
