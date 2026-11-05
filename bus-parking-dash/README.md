# Bus Parking Dash - Analisis Monetisasi & Panduan Bot

Panduan teknis dan catatan monetisasi untuk game **Bus Parking Dash**.

- **Nama Game**: Bus Parking Dash
- **Package ID**: `com.bus.parking.dash`
- **Developer / Perusahaan**: Freelancer Jibon
- **Kategori**: Bus Jam / Parking Puzzle
- **Skrip Bot**: `bus-parking-dash/bus_parking_dash_bot.py`

---

## 1. Catatan Penarikan & Analisis Monetisasi

| Parameter | Keterangan |
|---|---|
| **Instalasi Pertama** | Tersedia bot otomatis dengan path optimization dan auto-withdrawal. |
| **Instalasi Kedua** | **Cuma bisa selain rekening yang sudah (seperti Bus Jam Parking), atau bisa OVO.** |
| **Rekomendasi Instalasi** | **Semi rekomendasi.** Gunakan opsi dompet digital OVO atau beda nomor/rekening baru saat instalasi kedua. |
| **Metode Pencairan** | DANA / OVO / Rekening Baru. |

---

## 2. Fitur Bot Otomatis (`bus_parking_dash_bot.py`)

- **Multi-Device Parallel Engine**: Menjalankan bot paralel di semua HP via ADB.
- **Precision Floor-Masked Bus Detection**: Deteksi warna bus & penumpang dengan HSV presisi.
- **Smart Ad Timer**: Menunggu iklan selama waktu yang ditentukan dan pemulihan otomatis jika stuck.
- **Auto Fail Recovery**: Deteksi dialog gagal/habis ruang dan klik 'Main lagi' otomatis.

### Cara Menjalankan Bot:
```bash
cd /Users/macbookair/android-game-bots/bus-parking-dash
python3 bus_parking_dash_bot.py
```
