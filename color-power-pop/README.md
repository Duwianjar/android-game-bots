# Color Power Pop - Analisis Monetisasi & Panduan Bot

Panduan teknis dan catatan analisis penarikan saldo untuk game **Color Power Pop**.

- **Nama Game**: Color Power Pop
- **Package ID**: `com.giraffeeapp.power`
- **Developer / Perusahaan**: Giraffee App / Muhammad Ahsan Saleem
- **Kategori**: Bubble Crush / Color Matching Puzzle
- **Skrip Bot**: `color-power-pop/color_power_pop_bot.py`

---

## 1. Catatan Penarikan & Analisis Monetisasi

| Parameter | Keterangan |
|---|---|
| **Instalasi Pertama** | **19 kali penarikan:** Rp1.000 sebanyak 4 kali dan Rp4.000 sekali (nominal lainnya bertahap). |
| **Instalasi Kedua** | **DANA aman tapi cuma sedikit karena kemungkinan instalnya di akhir.** |
| **Instalasi Ketiga** | DANA sudah tidak bisa lagi, harus pakai OVO; penarikan OVO masih aman (nominal Rp5.000 dan Rp2.000). |
| **Instalasi Keempat** | **Penarikan aman via OVO nomor baru:** tertinggi bisa mencapai Rp13.000, ada nominal Rp5.000 dan Rp3.000 (wajib pakai nomor OVO baru). |
| **Iklan Slot** | Lumayan (tersedia iklan slot untuk boost perolehan koin). |
| **Rekomendasi Instalasi** | **Prioritas 6 (tepat di bawah Magic Ocean).** Pasang target OVO nomor baru. |
| **Metode Pencairan** | DANA / Saldo e-wallet. |

---

## 2. Fitur Bot Otomatis (`color_power_pop_bot.py`)

Bot Color Power Pop berjalan dengan Python OpenCV + ADB:
1. **Multi-Device Engine**: Menjalankan bot secara paralel di seluruh HP yang terhubung via ADB.
2. **Color Matching Solver**: Mendeteksi warna kotak di board bawah (HSV terkalibrasi) dan mencocokkan kartu slot atas secara otomatis.
3. **Smart Ad Dismissal**: Menutup iklan secara berkala tanpa terjebak loop iklan.
4. **Auto-Detection & Launcher**: Otomatis mendeteksi keberadaan aplikasi dan membukanya di HP.

### Cara Menjalankan Bot:
```bash
cd /Users/macbookair/android-game-bots/color-power-pop
python3 color_power_pop_bot.py
```
