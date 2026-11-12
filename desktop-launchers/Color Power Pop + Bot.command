#!/bin/bash
tmux kill-session -t color_power_pop 2>/dev/null || true
pkill -9 -f "color_power_pop_bot" 2>/dev/null || true
tmux new-session -d -s color_power_pop 'cd /Users/macbookair/android-game-bots/color-power-pop && ./run_color_power_pop_bot.sh'
tail -f /Users/macbookair/android-game-bots/color-power-pop/bot.log
