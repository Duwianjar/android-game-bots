# Magic Ocean Tile Crush Guardian Bot

Bot penjaga foreground untuk game **Magic Ocean Tile Crush**.

Target:
- Nama game: `Magic Ocean Tile Crush`
- Package: `com.starlightgame.magicoceantilecrush`

Fitur versi pertama:
- Jika game tidak terbuka/foreground, bot membuka game otomatis.
- Jika foreground pindah ke Chrome, bot force-stop Chrome lalu kembali ke game.
- Jika foreground pindah ke Play Store, bot force-stop Play Store lalu kembali ke game.
- Log durasi iklan saat activity iklan di dalam game sedang terbuka.
- OCR layar untuk deteksi tombol bertuliskan `Dobel`, lalu log `MENEMUKAN TOMBOL DOBEL`.
- Saat iklan terbuka, deteksi tombol selesai iklan (`X`, `Close`, panah kanan/next), log, lalu tap tombolnya.
- Mendukung satu device otomatis, atau pilih device dengan `--serial`.

## Jalankan

```bash
cd /Users/macbookair/android-game-bots/magic-ocean-tile-crush
./run_magic_ocean_guardian_bot.sh
```

Jika ada lebih dari satu device:

```bash
./run_magic_ocean_guardian_bot.sh --serial 062322513B000705
```

## Cek sekali saja

```bash
python3 magic_ocean_guardian_bot.py --once
```

## Stop

```bash
./stop_magic_ocean_guardian_bot.sh
```

## Log

```bash
tail -f /Users/macbookair/magic_ocean_guardian_bot.log
```

Contoh log iklan:

```text
IKLAN TERBUKA: com.unity3d.ads.adplayer.FullScreenWebViewDisplay | durasi 0 detik
IKLAN MASIH TERBUKA: com.unity3d.ads.adplayer.FullScreenWebViewDisplay | durasi 10 detik
IKLAN SELESAI: com.unity3d.ads.adplayer.FullScreenWebViewDisplay | total durasi 32 detik
MENEMUKAN TOMBOL DOBEL: 'Dobel' | bbox=0.40,0.20,0.20,0.05
MENEMUKAN TOMBOL SELESAI IKLAN: X 'Close' di (203,1248) via ui | durasi 6 detik
KLIK TOMBOL SELESAI IKLAN: X di (203,1248)
```
