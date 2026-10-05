# Android Game Bots Collection

Koleksi bot otomatis untuk berbagai game Android yang menghasilkan saldo real money.

## 🎮 Daftar Bot

### 1. Soda Pack Puzzle Bot
Bot otomatis untuk game Soda Pack Puzzle dengan fitur:
- ✅ Auto play game (tap botol sesuai warna)
- ✅ Auto klik bubble reward (Kado, Koin, Balon Iklan)
- ✅ Anti bot-detect (5 detik tap random saat iklan)
- ✅ Auto handle iklan dengan BACK otomatis
- ✅ Auto tarik saldo ke DANA (minimal Rp 500)
- ✅ Telegram notification
- ✅ Multi-device support

**Performa:** ~Rp 100-200 per jam

### 2. Lucky Mahjong Bot
Bot otomatis untuk game Lucky Mahjong.

### 3. Juice Pack Bot
Bot otomatis untuk game Juice Pack.

### 4. Bus Jam Parking Bot
Bot otomatis untuk game Bus Jam Parking.

### 5. Can Sort Bot
Bot otomatis untuk game Can Sort.

## 📋 Requirements

- macOS / Linux
- Python 3.8+
- ADB (Android Debug Bridge)
- scrcpy
- Android device dengan USB debugging enabled

## 🚀 Instalasi

```bash
# Clone repository
git clone git@github.com:duwianjar/android-game-bots.git
cd android-game-bots

# Install dependencies
pip3 install opencv-python pytesseract numpy Pillow requests

# Install ADB & scrcpy (macOS)
brew install android-platform-tools scrcpy

# Sambungkan HP Android via USB
adb devices
```

## 📱 Setup HP Android

1. Enable Developer Options
2. Enable USB Debugging
3. Sambungkan ke Mac/PC via USB
4. Izinkan USB debugging saat prompt muncul

## 🎯 Cara Pakai

### Soda Pack Puzzle Bot

```bash
cd soda-pack-puzzle
./run_soda_pack_puzzle_bot.sh
```

Bot akan otomatis:
1. Buka game Soda Pack Puzzle
2. Main game (tap botol)
3. Klik bubble reward
4. Handle iklan (5 detik anti bot-detect + auto BACK)
5. Tarik saldo ke DANA saat >= Rp 500

### Monitoring

```bash
# Lihat bot real-time
tmux attach -t soda_pack_bot

# Keluar: Ctrl+B lalu D

# Cek saldo
cat soda_telegram_reporter_state.json

# Stop bot
./stop_soda_pack_puzzle_bot.sh
```

## ⚙️ Konfigurasi

Edit file `soda_pack_puzzle_bot.py`:

```python
# Minimum saldo untuk auto tarik
MIN_WITHDRAW_RP = 500

# Waktu tunggu iklan (detik)
AD_WAIT_SECONDS = 15

# Telegram bot token (opsional)
TELEGRAM_BOT_TOKEN = "your_token"
TELEGRAM_CHAT_ID = "your_chat_id"
```

## 🔧 Optimasi Yang Sudah Diterapkan

1. **Anti Bot-Detect:** Tap random 5 detik saat iklan untuk hindari deteksi
2. **Auto BACK:** Tidak tunggu tombol X, langsung BACK setelah 5 detik
3. **Skip Verification:** Skip verifikasi saldo, fokus ke gameplay
4. **Speed Boost:** Semua delay dikurangi 50%
5. **Smart Detection:** Deteksi bubble yang sudah lewat/statis
6. **No Restart Loop:** Tidak restart jika saldo tidak naik (karena iklan bukan sumber utama)

## 📊 Performa

| Game | Penghasilan/Jam | Target Minimal | Metode Penarikan |
|------|----------------|----------------|------------------|
| Soda Pack Puzzle | Rp 100-200 | Rp 500 | DANA |
| Lucky Mahjong | Rp 50-100 | Rp 300 | DANA |
| Juice Pack | Rp 80-150 | Rp 500 | DANA |

## 🛡️ Anti-Ban Features

- ✅ Random tap timing (tidak fix interval)
- ✅ Human-like movement simulation
- ✅ Anti bot-detect saat iklan (5 detik tap random)
- ✅ Variasi koordinat tap (±10px random offset)
- ✅ Sleep random delay antara aksi

## 📝 Log & Debugging

```bash
# Lihat log lengkap
tail -f ~/soda_pack_puzzle_bot.log

# Cek error
grep ERROR ~/soda_pack_puzzle_bot.log

# Monitor saldo real-time
watch -n 5 'cat ~/soda_telegram_reporter_state.json'
```

## 🤝 Contributing

Pull requests welcome! Untuk perubahan besar, buka issue dulu untuk diskusi.

## ⚠️ Disclaimer

Bot ini untuk educational purposes. Gunakan dengan bijak dan ikuti terms of service dari masing-masing game.

## 📜 License

MIT License - bebas digunakan dan dimodifikasi.

## 👨‍💻 Author

**Duwi Anjar**
- GitHub: [@duwianjar](https://github.com/duwianjar)

---

**⭐ Star repo ini jika berguna!**
