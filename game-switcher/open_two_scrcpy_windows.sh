#!/bin/bash
set -euo pipefail
SERIAL="062322513B000705"
# Buka dua mirror window dari HP yang sama. Ini BUKAN dua device, hanya dua tampilan.
nohup scrcpy --serial "$SERIAL" --window-title 'HP Mirror 1 - Infinix X692' >/tmp/scrcpy_mirror_1.log 2>&1 &
sleep 1
nohup scrcpy --serial "$SERIAL" --window-title 'HP Mirror 2 - Infinix X692' >/tmp/scrcpy_mirror_2.log 2>&1 &
echo "Dua window scrcpy diminta dibuka."
