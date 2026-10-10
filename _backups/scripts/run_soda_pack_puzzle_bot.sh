#!/bin/bash
# Launcher tunggal untuk Bot Soda Pack Puzzle + Telegram reporter.
# Fitur: anti-duplikat, Telegram 5 menit, log tee, auto-restart kalau bot keluar.

cd /Users/macbookair || exit 1

LOCK_DIR="/tmp/soda_pack_puzzle_bot.lock"
LOG_FILE="/Users/macbookair/soda_pack_puzzle_bot.log"
REPORTER_PID=""
STOP_REQUESTED=0

# Simpan semua output ke terminal dan log agar gampang dicek.
exec > >(tee -a "$LOG_FILE") 2>&1

if [ -d "$LOCK_DIR" ]; then
    OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[!] Bot Soda Pack Puzzle sudah berjalan pada launcher PID $OLD_PID. Tidak membuat instance duplikat."
        exit 1
    fi
    echo "[!] Lock lama ditemukan tapi prosesnya tidak aktif. Membersihkan lock stale..."
    rm -rf "$LOCK_DIR"
fi

mkdir "$LOCK_DIR" || exit 1
echo $$ > "$LOCK_DIR/pid"

cleanup() {
    STOP_REQUESTED=1
    echo -e "
[+] Menghentikan bot & reporter..."
    if [ -n "$REPORTER_PID" ] && kill -0 "$REPORTER_PID" 2>/dev/null; then
        kill "$REPORTER_PID" 2>/dev/null
    fi
    pkill -f "soda_telegram_reporter.py" 2>/dev/null
    rm -rf "$LOCK_DIR"

    WAKTU_STOP=$(date "+%Y-%m-%d %H:%M:%S WIB")
    python3 /Users/macbookair/telegram_sender.py "🛑 <b>BOT SODA PACK PUZZLE DIHENTIKAN</b>
🕐 <b>Waktu:</b> ${WAKTU_STOP}
⚠️ <i>Bot dan reporter telah berhenti.</i>" >/dev/null 2>&1
}

trap cleanup EXIT INT TERM

WAKTU_START=$(date "+%Y-%m-%d %H:%M:%S WIB")
DEVICES=$(adb devices 2>/dev/null | awk 'NR>1 && $2=="device" {print $1}' | tr '
' ' ')
[ -z "$DEVICES" ] && DEVICES="Tidak terdeteksi"

export SODA_TG_INTERVAL=60

echo "=================================================="
echo "  MEMULAI BOT SODA PACK PUZZLE + TELEGRAM         "
echo "=================================================="
echo "[+] Telegram reporter interval: ${SODA_TG_INTERVAL}s, kirim hanya saat saldo berubah / 7 menit tidak naik"
echo "[+] Log: $LOG_FILE"

python3 /Users/macbookair/telegram_sender.py "🚀 <b>BOT SODA PACK PUZZLE DIMULAI</b>
🕐 <b>Waktu:</b> ${WAKTU_START}
📱 <b>Device:</b> <code>${DEVICES}</code>
⚙️ <i>Reporter kirim hanya saat saldo berubah; warning jika 7 menit tidak naik.</i>" >/dev/null 2>&1

# Reporter cukup satu proses, pakai interval 5 menit dari env.
SODA_TG_INTERVAL=60 python3 /Users/macbookair/soda_telegram_reporter.py >/dev/null 2>&1 &
REPORTER_PID=$!
echo "[+] Reporter Telegram aktif PID $REPORTER_PID"

# Watchdog: kalau bot utama keluar/crash, restart otomatis.
while true; do
    echo "[+] Menjalankan bot utama..."
    python3 -u /Users/macbookair/soda_pack_puzzle_bot.py
    STATUS=$?

    if [ "$STOP_REQUESTED" = "1" ]; then
        break
    fi

    WAKTU_RESTART=$(date "+%Y-%m-%d %H:%M:%S WIB")
    echo "[!] Bot utama keluar dengan status $STATUS pada $WAKTU_RESTART. Restart dalam 5 detik..."
    python3 /Users/macbookair/telegram_sender.py "⚠️ <b>BOT SODA PACK PUZZLE RESTART OTOMATIS</b>
🕐 <b>Waktu:</b> ${WAKTU_RESTART}
📌 <b>Status keluar:</b> <code>${STATUS}</code>
🔁 <i>Watchdog menjalankan ulang bot.</i>" >/dev/null 2>&1
    sleep 5
done
