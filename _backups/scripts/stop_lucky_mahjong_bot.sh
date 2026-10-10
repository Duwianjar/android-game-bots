#!/bin/bash
echo "[+] Menghentikan Bot Lucky Mahjong..."
pkill -9 -f "lucky_mahjong_bot" 2>/dev/null
pkill -9 -f "multiprocessing.spawn" 2>/dev/null
for dev in $(adb devices | awk 'NR>1 && $2=="device" {print $1}'); do
  adb -s "$dev" shell "pkill -9 -f input; pkill -9 -f app_process" 2>/dev/null
done
echo "[✔] Bot Lucky Mahjong dihentikan."
