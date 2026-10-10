#!/bin/bash
# Script untuk menghentikan total seluruh bot Can Sort & proses latar belakang

echo "[+] Menghentikan semua proses Bot Can Sort dan worker..."
pkill -9 -f "can_sort_bot" 2>/dev/null
pkill -9 -f "multiprocessing.spawn" 2>/dev/null
pkill -9 -f "multiprocessing.resource_tracker" 2>/dev/null
pkill -9 -f "ocr_helper" 2>/dev/null
pkill -9 -f "runtime_player" 2>/dev/null

# Hentikan proses input / shell yang menggantung di perangkat Android
for dev in $(adb devices | awk 'NR>1 && $2=="device" {print $1}'); do
    echo "[+] Membersihkan proses shell pada HP ($dev)..."
    adb -s "$dev" shell "pkill -9 -f input; pkill -9 -f app_process" 2>/dev/null
done

echo "[✔] SEMUA BOT & PROSES KLIK OTOMATIS TELAH BERHASIL DIMATIKAN TOTAL."
