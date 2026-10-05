# Soda Pack Puzzle Bot

Bot otomatis untuk game Soda Pack Puzzle yang bisa farming saldo hingga auto withdraw ke DANA.

## ✨ Features

- ✅ **Auto Play Game** - Tap botol otomatis sesuai warna kotak
- ✅ **Auto Bubble Reward** - Deteksi dan klik Kado, Koin, Balon Iklan yang melayang
- ✅ **Anti Bot-Detect** - Tap random 5 detik saat iklan untuk hindari deteksi
- ✅ **Auto Handle Iklan** - BACK otomatis setelah 5 detik, tidak tunggu tombol X
- ✅ **Auto Withdraw** - Tarik saldo otomatis ke DANA saat >= Rp 500
- ✅ **Telegram Notification** - Update saldo real-time ke Telegram
- ✅ **Multi-Device** - Support multiple Android devices
- ✅ **Smart Detection** - Skip bubble yang sudah lewat, deteksi bottleneck
- ✅ **Speed Optimized** - Semua delay dikurangi 50%, gerakan super cepat

## 📊 Performa

- **Penghasilan:** Rp 100-200 per jam
- **Target minimal:** Rp 500
- **Metode penarikan:** DANA

## 🚀 Quick Start

```bash
# Install dependencies
pip3 install opencv-python pytesseract numpy Pillow requests

# Jalankan bot
./run_soda_pack_puzzle_bot.sh

# Monitor real-time
tmux attach -t soda_pack_bot

# Stop bot
./stop_soda_pack_puzzle_bot.sh
```

## 📱 Requirements

- Python 3.8+
- ADB & scrcpy
- HP Android dengan USB debugging
- Game Soda Pack Puzzle terinstall

## ⚙️ Konfigurasi

Edit `soda_pack_puzzle_bot.py`:

```python
MIN_WITHDRAW_RP = 500  # Minimal saldo untuk auto withdraw
AD_WAIT_SECONDS = 15   # Waktu tunggu iklan
PACKAGE_NAME = "com.soda.pack.puzzle"
```

### Telegram (Opsional)

Edit `soda_telegram_reporter.py`:

```python
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
```

## 🎯 Cara Kerja

1. **Scan Layar** - Ambil screenshot setiap 0.5 detik
2. **Deteksi Botol** - OCR warna kotak dan tap botol sesuai warna
3. **Track Bubble** - Deteksi bubble reward (Kado/Koin) yang melayang
4. **Handle Iklan** - 5 detik anti bot-detect → BACK → lanjut main
5. **Auto Withdraw** - Saldo >= Rp 500 → otomatis tarik ke DANA

## 🔧 Optimasi

### Anti Bot-Detect (5 detik)
```
Iklan Muncul
    ↓
[0-5s] Tap random di layar (3x, interval 2 detik)
    ↓
Auto BACK ke game
    ↓
Gagal? → BACK kedua → Gagal lagi? → Restart game
```

### Speed Boost
- Semua delay dikurangi 50%
- Skip verifikasi saldo pasca-iklan
- Tidak restart jika saldo tidak naik
- Deteksi cerdas bubble yang lewat

## 📝 Monitoring

```bash
# Cek saldo real-time
cat soda_telegram_reporter_state.json

# Lihat log
tail -f ~/soda_pack_puzzle_bot.log

# Monitor dalam tmux
tmux attach -t soda_pack_bot
# Keluar: Ctrl+B lalu D
```

## 🛡️ Anti-Ban

- Random tap timing
- Human-like movement
- 5 detik anti bot-detect saat iklan
- Variasi koordinat tap (±10px random)
- Sleep random delay

## 📁 File Structure

```
soda-pack-puzzle/
├── soda_pack_puzzle_bot.py       # Main bot
├── run_soda_pack_puzzle_bot.sh   # Start script
├── stop_soda_pack_puzzle_bot.sh  # Stop script
├── soda_telegram_reporter.py     # Telegram notifier
├── soda_event_logger.py          # Event logger
└── scrcpy_tap_marker.swift       # Visual tap marker
```

## 🐛 Troubleshooting

**Bot tidak deteksi HP:**
```bash
adb kill-server
adb start-server
adb devices
```

**Bot stuck:**
- Bot punya anti-stuck mechanism
- Auto refresh jika tidak ada aksi 15 detik

**Saldo tidak naik:**
- Fokus bot ada di bubble reward, bukan iklan
- Iklan kadang tidak kasih reward (normal)

## 📜 License

MIT License

## 👨‍💻 Author

Duwi Anjar - [@duwianjar](https://github.com/duwianjar)
