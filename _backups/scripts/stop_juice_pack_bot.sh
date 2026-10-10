#!/bin/bash
# Script untuk mematikan total Bot Juice Pack Frenzy

echo "[+] Menghentikan semua proses Bot Juice Pack Frenzy dan worker..."
pkill -9 -f "juice_pack_bot" 2>/dev/null
pkill -9 -f "multiprocessing.spawn" 2>/dev/null
pkill -9 -f "multiprocessing.resource_tracker" 2>/dev/null
pkill -9 -f "ocr_helper" 2>/dev/null

for dev in $(adb devices | awk 'NR>1 && $2=="device" {print $1}'); do
    echo "[+] Membersihkan proses shell pada HP ($dev)..."
    adb -s "$dev" shell "pkill -9 -f input; pkill -9 -f app_process" 2>/dev/null
done

echo "[✔] BOT JUICE PACK FRENZY TELAH BERHASIL DIMATIKAN TOTAL."
