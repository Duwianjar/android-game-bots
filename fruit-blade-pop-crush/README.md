# Fruit Blade Pop Crush - Analisis Monetisasi & Panduan Bot

Panduan teknis dan catatan monetisasi untuk game **Fruit Blade Pop Crush**.

- **Nama Game**: Fruit Blade Pop Crush
- **Package ID**: `com.starlightgame.fruitbladepopcrush`
- **Developer / Perusahaan**: ACM PROJECTS & AUTOMATION LTD / Elias Galvin
- **Kategori**: Blade / Fruit Slice Puzzle
- **Skrip Bot**: `fruit-blade-pop-crush/fruit_blade_guardian_bot.py`

---

## 1. Catatan Penarikan & Analisis Monetisasi

| Parameter | Keterangan |
|---|---|
| **Instalasi Pertama** | Tersedia bot guardian otomatis; rawan terblokir. Belum ada catatan penarikan awal. |
| **Instalasi Kedua** | **Penarikan kedua perlu pakai OVO atau tidak bisa rekening yang sama.** |
| **Rekomendasi Instalasi** | **Semi rekomendasi.** Gunakan opsi OVO atau rekening berbeda saat melakukan penarikan di instalasi kedua. |
| **Metode Pencairan** | DANA / OVO / Rekening Baru. |

---

## 2. Fitur Bot Guardian (`fruit_blade_guardian_bot.py`)

- **Auto Foreground**: Membuka game otomatis jika tertutup atau teralihkan ke app lain.
- **Smart Ad Dismissal**: Deteksi & tutup iklan otomatis (UI dump, contour, arrow detection).
- **DOBEL & Bubble Handler**: Auto tap reward DOBEL / gelembung saldo.
- **Telegram Notification**: Monitoring saldo berkala dan kirim progres ke Telegram.

### Cara Menjalankan Bot:
```bash
cd /Users/macbookair/android-game-bots/fruit-blade-pop-crush
./run_fruit_blade_guardian_bot.sh
```
