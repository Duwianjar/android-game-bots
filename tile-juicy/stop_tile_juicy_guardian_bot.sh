#!/bin/bash
# Stop Tile Juicy Guardian Bot
pkill -f "tile_juicy_guardian_bot.py" 2>/dev/null && echo "Bot dihentikan." || echo "Bot tidak sedang jalan."
