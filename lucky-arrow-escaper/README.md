# Lucky Arrow Escape - Analisis Monetisasi & Panduan Bot

Panduan teknis dan catatan monetisasi untuk game **Lucky Arrow Escape**.

- **Nama Game**: Lucky Arrow Escape
- **Package ID**: `com.starlightgame.luckyarrowescaper`
- **Developer / Perusahaan**: ACM PROJECTS & AUTOMATION LTD / Elias Galvin
- **Kategori**: Arrow Unblock / Puzzle
- **Skrip Bot**: `lucky-arrow-escaper/lucky_arrow_escaper_guardian_bot.py`

---

## 1. Catatan Penarikan & Analisis Monetisasi

| Parameter | Keterangan |
|---|---|
| **Instalasi Pertama** | Tersedia bot guardian otomatis (deteksi DOBEL, bubble reward, auto-close iklan, anti-stuck). |
| **Instalasi Kedua** | **Penarikan 25 dan 27 aman DANA.** |
| **Rekomendasi Instalasi** | **Prioritas 1 (paling pertama).** Coba tunggu gede dulu atau 25k baru tarik. |
| **Metode Pencairan** | DANA / Saldo e-wallet. |

---

## 2. Fitur Bot Guardian (`lucky_arrow_escaper_guardian_bot.py`)

- **Auto Foreground**: Membuka game otomatis jika tertutup atau teralihkan ke app lain.
- **Smart Ad Dismissal**: Deteksi & tutup iklan dengan circle arrow / contour detection / UI dump.
- **DOBEL & Bubble Handler**: Auto tap reward DOBEL / gelembung saldo.
- **Telegram Notification & OCR Saldo**: Monitoring saldo berkala dan kirim progres ke Telegram.

### Cara Menjalankan Bot:
```bash
cd /Users/macbookair/android-game-bots/lucky-arrow-escaper
./run_lucky_arrow_escaper_guardian_bot.sh
```
