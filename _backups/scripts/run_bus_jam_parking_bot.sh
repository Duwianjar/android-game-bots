#!/bin/bash
# Launcher untuk menjalankan Bot Bus Jam Parking otomatis + Notifikasi Telegram

cd /Users/macbookair

echo "=================================================="
echo "  🚀 MEMULAI BOT BUS JAM PARKING + TELEGRAM       "
echo "=================================================="

# Jalankan Bot Utama (Terintegrasi Realtime OCR & Telegram 3-menit)
exec python3 -u /Users/macbookair/bus_jam_parking_bot.py
