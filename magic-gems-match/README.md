# Magical Gems Match 3 - Analisis Monetisasi & Panduan Guardian

Panduan teknis dan catatan monetisasi untuk game **Magical Gems Match 3**.

- **Nama Game**: Magical Gems Match 3
- **Package ID**: `com.glow.magical.match3`
- **Developer / Perusahaan**: DKSHUBDeveloper / Ghulam Yaseen
- **Kategori**: Match 3 Gems Puzzle
- **Skrip Guardian**: `magic-gems-match/magic_gems_guardian.py`

---

## 1. Catatan Penarikan & Analisis Monetisasi

| Parameter | Keterangan |
|---|---|
| **Instalasi Pertama** | **13 kali penarikan (Maks Rp1.050):** Rp20, Rp89, Rp51, Rp81, Rp210, Rp107, Rp182, Rp1.050, Rp354, Rp531, Rp206, Rp273, dan Rp290. Karakteristik: Susah, tetapi tetap cair. |
| **Instalasi Kedua** | **DANA normal tapi sedikit kemungkinan karena terakhir.** |
| **Iklan Slot** | Lumayan (tersedia reward slot/iklan). |
| **Rekomendasi Instalasi** | **Instal dengan target kecil.** Masuk dalam kelompok Rekomendasi Prioritas 7. |
| **Metode Pencairan** | DANA / Saldo e-wallet. |

---

## 2. Fitur Guardian Bot (`magic_gems_guardian.py`)

Skrip penjaga (*guardian*) memastikan game tetap aktif di layar tanpa teralihkan:
1. **Foreground Monitoring**: Memeriksa window aktif melalui `adb shell dumpsys window windows`.
2. **Auto Relaunch**: Jika game tertutup atau terpental ke aplikasi pengganggu/iklan (misal Google Chrome atau Google Play Store), skrip akan menghentikan paksa aplikasi blocker dan membuka kembali game.
3. **Multi-device Flag**: Mendukung flag `-s <serial>` untuk menargetkan perangkat tertentu.

### Cara Menjalankan Guardian:
```bash
cd /Users/macbookair/android-game-bots/magic-gems-match
./run_magic_gems_guardian.sh
# Atau langsung dengan python:
python3 magic_gems_guardian.py
```
