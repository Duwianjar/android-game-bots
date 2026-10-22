#!/bin/bash
set -euo pipefail
pkill -f '[l]ucky_arrow_escaper_guardian_bot.py' 2>/dev/null || true
rm -rf /tmp/lucky_arrow_escaper_guardian_bot.lock
echo "Bot Lucky Arrow Escaper sudah distop."
