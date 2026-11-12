#!/bin/bash
# Jalankan bot penjaga Catch Cute Pets.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

exec "$PYTHON_BIN" -u ./catch_cute_pets_bot.py "$@"
