#!/bin/bash
set +e
tmux kill-session -t lucky_arrow_guardian 2>/dev/null
pkill -f '[l]ucky_arrow_escaper_guardian_bot.py' 2>/dev/null
rm -rf /tmp/lucky_arrow_escaper_guardian_bot.lock
echo "Bot Lucky Arrow Escaper sudah distop."
