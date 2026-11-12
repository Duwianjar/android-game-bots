# Zoo Tile Guardian & Match-3 Auto Player Bot

Bot penjaga, auto-reopen, dan auto-player match-3 untuk game **Tangkap Hewan Lucu: Permainan Tile** *(Zoo Tile: Win Mega Rewards!)*.

- **Package**: `com.zoo.tile.cute.animal.elephant.mouse.fox`
- **Activity Utama**: `com.google.firebase.MessagingUnityPlayerActivity`
- **Device Target**: Infinix X692 (720x1640)

## Fitur Utama

1. **Auto Match-3 Gameplay**:
   - Memindai ubin hewan di area bermain ($y \in [350, 1250]$) dan status nampan bawah ($y \in [1300, 1420]$).
   - Mengelompokkan ikon hewan yang sama secara otomatis via template matching OpenCV.
   - Mengetuk 3 ubin hewan identik secara berurutan agar langsung cocok (*match-3*) dan hilang tanpa memenuhi nampan.
   - Otomatis mendeteksi dan mengetuk tombol **Klaim / Lanjut** saat menyelesaikan level.
2. **Smart Ad Handling**:
   - Mengenali activity iklan reward (Vungle, MBridge, Pangle/Bytedance, AppLovin, AdMob).
   - Mendeteksi tombol tutup/skip (X, >>, Close, Tutup) secara dinamis via UIAutomator, OCR helper, dan Computer Vision tanpa salah klik banner/web redirect.
3. **Auto Reopen Game (Guardian)**:
   - Jika HP keluar dari game (ke Launcher, browser Chrome, Google Play Store, atau aplikasi redirect lain), bot otomatis menutup aplikasi redirect (`force-stop`) dan membuka kembali Zoo Tile secara instan.
4. **Screen Wake**:
   - Jika layar HP mati/asleep saat bot berjalan, bot otomatis mengirim sinyal bangun layar (`KEYCODE_WAKEUP`).

## Cara Menjalankan

### Melalui Terminal
```bash
cd /Users/macbookair/android-game-bots/zoo-tile
./run_zoo_tile_guardian_bot.sh
```

Atau langsung dengan Python:
```bash
python3 zoo_tile_guardian_bot.py
```

Opsi argumen:
- `--serial <SERIAL>` : Menentukan serial ADB device jika terhubung lebih dari 1 HP.
- `--interval <DETIK>` : Mengatur interval pengecekan (default: `0.5`).
- `--no-gameplay` : Mode penjaga saja (tanpa auto klik match-3).
- `--dry-run` : Mode simulasi pengecekan tanpa eksekusi tap / force-stop.

### Menghentikan Bot
Tekan `Ctrl+C` di terminal atau jalankan:
```bash
./stop_zoo_tile_guardian_bot.sh
```

### Melalui Launcher Desktop
Klik dua kali file:
`/Users/macbookair/android-game-bots/desktop-launchers/Zoo Tile + Bot.command`

## Log File
Aktivitas bot dicatat secara real-time pada:
`~/zoo_tile_guardian_bot.log`
