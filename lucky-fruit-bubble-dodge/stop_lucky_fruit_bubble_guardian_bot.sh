#!/bin/bash
set -euo pipefail
pkill -f '[l]ucky_fruit_bubble_guardian_bot.py' 2>/dev/null || true
rm -rf /tmp/lucky_fruit_bubble_guardian_bot.lock
echo "Bot Lucky Fruit sudah distop."
