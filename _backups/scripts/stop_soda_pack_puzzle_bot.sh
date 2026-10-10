#!/bin/bash
# Script untuk mematikan total Bot Soda Pack Puzzle & Reporter Telegram

echo "[+] Menghentikan semua proses Bot Soda Pack Puzzle, worker, dan Telegram reporter..."
pkill -9 -f "soda_pack_puzzle_bot" 2>/dev/null
pkill -9 -f "soda_telegram_reporter" 2>/dev/null
pkill -9 -f "multiprocessing.spawn" 2>/dev/null
pkill -9 -f "multiprocessing.resource_tracker" 2>/dev/null
pkill -9 -f "ocr_helper" 2>/dev/null

for dev in $(adb devices | awk 'NR>1 && $2=="device" {print $1}'); do
    echo "[+] Membersihkan proses shell pada HP ($dev)..."
    adb -s "$dev" shell "pkill -9 -f input; pkill -9 -f app_process" 2>/dev/null
done

WAKTU_STOP=$(date "+%Y-%m-%d %H:%M:%S WIB")
python3 /Users/macbookair/telegram_sender.py "🛑 <b>BOT SODA PACK PUZZLE TELAH DIMATIKAN TOTAL</b>
🕐 <b>Waktu:</b> ${WAKTU_STOP}
⚙️ <i>Semua worker dan reporter telah dihentikan.</i>" >/dev/null 2>&1

echo "[✔] BOT SODA PACK PUZZLE TELAH BERHASIL DIMATIKAN TOTAL."
