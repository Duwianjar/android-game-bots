# Greenfield Merge Guardian & Auto-Ad Bot

Bot otomatisasi untuk game **Greenfield Merge** (`com.xteleremobilecompanyltd.GreenfieldMerge`).

## Fitur:
1. **Auto Click Papan Gambar (Merge)**: Melakukan ketukan bebas pada area papan untuk menghasilkan item dan memicu popup hadiah / iklan.
2. **Klaim Hadiah / Buka Iklan**: Mendeteksi tombol reward (`DAPATKAN`, `KLAIM`, `DOBEL`, `BUKA`, `GRATIS`, dll.) untuk memicu iklan berhadiah.
3. **Smart Ad Closer (Penyelesai Iklan)**:
   - Menghitung durasi tayang iklan (28-30s minimum).
   - Mendeteksi tombol `X`, `Tutup`, `Skip`, `Next` via UI tree uiautomator, OCR helper, dan OpenCV visual.
   - Fallback tombol BACK otomatis jika tombol tidak terdeteksi setelah durasi selesai.
4. **Anti-Redirect**: Menutup otomatis Chrome atau Play Store jika terbuka karena iklan, lalu kembali ke game.

## Cara Menjalankan:
```bash
# Dari mana saja di terminal:
greenfield-merge-bot

# Atau masuk folder:
cd /Users/macbookair/android-game-bots/greenfield-merge
./run_greenfield_merge_bot.sh

# Berhenti:
./stop_greenfield_merge_bot.sh  # atau Ctrl+C
```
