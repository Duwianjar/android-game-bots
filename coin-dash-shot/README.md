# Coin Sort Dash - Analisis Monetisasi & Panduan Bot

Panduan teknis dan catatan monetisasi untuk game **Coin Sort Dash**.

- **Nama Game**: Coin Sort Dash
- **Package ID**: `com.coin.sortdash.remove`
- **Developer / Perusahaan**: أحمد البكري خميس موسي (developer sama dengan Bus Jam Parking Master)
- **Kategori**: Sorting & Puzzle
- **Skrip Bot**: `coin-dash-shot/coin_dash_shot_bot.py`

---

## 1. Catatan Penarikan & Analisis Monetisasi

| Parameter | Keterangan |
|---|---|
| **Instalasi Pertama** | **3 kali penarikan:** Rp1.017, Rp627, dan Rp20 (Maks Rp1.017). Lumayan, tetapi rawan terblokir iklan. |
| **Instalasi Kedua** | **DANA normal tapi sedikit kemungkinan karena terakhir.** |
| **Iklan Slot** | Lumayan, tetapi rawan pemblokiran iklan. |
| **Rekomendasi Instalasi** | **Instal setelah prioritas utama.** Prioritas 9 dalam daftar rekomendasi. |
| **Metode Pencairan** | DANA / Saldo e-wallet. |

---

## 2. Fitur Bot Otomatis (`coin_dash_shot_bot.py`)

- **Auto Play & Sorting**: Menjalankan aksi gameplay otomatis.
- **Smart Ad Timer**: Menunggu iklan 6 detik lalu melakukan pemulihan aplikasi jika diperlukan.
- **OCR Saldo & Auto Withdraw**: Deteksi nilai saldo dengan bantuan `ocr_helper` dan memicu penarikan saat mencapai ambang batas (default Rp200 - Rp500).
- **Telegram Notification**: Mengirim notifikasi saldo dan progres penarikan ke bot Telegram.

### Cara Menjalankan Bot:
```bash
cd /Users/macbookair/android-game-bots/coin-dash-shot
python3 coin_dash_shot_bot.py
```
