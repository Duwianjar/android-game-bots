#!/bin/bash
set +e
tmux kill-session -t color_power_pop 2>/dev/null
pkill -f 'color_power_pop_bot' 2>/dev/null
rm -rf /tmp/color_power_pop_bot.lock
echo "Bot Color Power Pop sudah distop."
