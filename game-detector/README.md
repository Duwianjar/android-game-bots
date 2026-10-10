# Game Detector Bot

Bot untuk mendeteksi game Android yang sedang aktif/terbuka di HP Anda.

## 🎯 Fitur

- ✅ Deteksi package name aplikasi yang aktif
- ✅ Convert package name ke nama yang user-friendly
- ✅ Support monitoring continuous
- ✅ Simpan state ke JSON file
- ✅ Log semua deteksi
- ✅ Filter system apps
- ✅ Known games database

## 📋 Requirements

- Python 3.8+
- ADB (Android Debug Bridge)
- HP Android dengan USB debugging enabled

## 🚀 Cara Pakai

### 1. Single Check (Cek Sekali)

```bash
./run_detector.sh check
```

Output:
```
🎮 Game yang terdeteksi:
   Nama: Soda Pack Puzzle
   Package: com.soda.pack.puzzle
   Waktu: 2026-10-07 19:30:45
```

### 2. Monitoring Mode (Terus-Menerus)

```bash
./run_detector.sh monitor
```

Bot akan terus monitoring setiap 5 detik dan log setiap kali game berubah.

### 3. JSON Output

```bash
./run_detector.sh json
```

Output dalam format JSON untuk integrasi dengan bot lain.

## 📊 Output

### State File

Bot menyimpan state di `~/game_detector_state.json`:

```json
{
  "package_name": "com.soda.pack.puzzle",
  "app_name": "Soda Pack Puzzle",
  "detected_at": "2026-10-07 19:30:45"
}
```

### Log File

Log lengkap disimpan di `~/game_detector.log`

## 🔧 Advanced Usage

### Monitoring dengan Custom Interval

```bash
./detect_current_game.py --monitor --interval 10
```

### JSON Output

```bash
./detect_current_game.py --json
```

## 🎮 Known Games Database

Bot sudah mengenali game-game berikut:

- Soda Pack Puzzle
- Lucky Mahjong
- Juice Pack
- Bus Jam Parking
- Bus Parking Dash
- Can Sort
- Coin Dash Shot
- Color Power Pop
- Soda Jam Puzzle
- Jungle Animal Eliminate
- Dragon Arrow Escape

Game lain akan di-parse otomatis dari package name.

## 📝 Integrasi dengan Bot Lain

Bot lain bisa membaca state file untuk mengetahui game yang aktif:

```python
import json

# Load state
with open(os.path.expanduser("~/game_detector_state.json"), 'r') as f:
    game_info = json.load(f)

print(f"Current game: {game_info['app_name']}")
print(f"Package: {game_info['package_name']}")
```

## 🛠️ Troubleshooting

### Device Tidak Terdeteksi

```bash
# Cek device terhubung
adb devices

# Restart ADB server
adb kill-server
adb start-server
```

### Permission Denied

```bash
chmod +x detect_current_game.py
chmod +x run_detector.sh
```

## 💡 Tips

1. **Monitoring Background**: Jalankan di tmux/screen untuk monitoring 24/7
2. **Auto-detect Bot**: Gunakan bersama bot launcher otomatis
3. **Log Analysis**: Analisa log untuk tracking usage pattern

## 📜 License

MIT License - bebas digunakan dan dimodifikasi.

## 👨‍💻 Author

**Duwi Anjar**
- GitHub: [@duwianjar](https://github.com/duwianjar)
