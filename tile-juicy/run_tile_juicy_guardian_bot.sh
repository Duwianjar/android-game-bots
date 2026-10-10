#!/bin/bash
# Jalankan Tile Juicy Guardian Bot
cd "$(dirname "$0")"
exec python3 tile_juicy_guardian_bot.py --serial 062322513B000705 --interval 2 "$@"
