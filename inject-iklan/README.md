# Inject Iklan

Bot mandiri untuk siklus injeksi persona & profiling iklan Google slot/judi tanpa gameplay.

## Alur Kerja (5 Langkah):
1. **Membuka Chrome**: Membuka browser Google Chrome via intent ADB.
2. **Pencarian Google**: Melakukan pencarian Google dengan kata kunci acak terkait slot / judi (toto, gacor, maxwin, zeus, pragmatic, deposit dana, dll.).
3. **Buka Hasil Pencarian & Deteksi DAFTAR**: Scroll hasil Google, klik link situs, scroll konten halaman web, lalu mendeteksi tombol `DAFTAR` / `REGISTER` menggunakan OCR (`ocr_helper`).
4. **Isi Formulir Pendaftaran**: Membaca kolom form (via accessibility tree / OCR label) dan mengisikan data tersimpan (`username`, `password`, `email`, `phone`, `bank: OVO`, `rek`, `nama_rek`) tanpa menekan submit.
5. **Aplikasi Slot Acak & Kembali ke Magic Ocean**: Membuka salah satu aplikasi slot secara acak (RR33, K68, FJ99, atau app slot terinstal), swipe interaksi, menutup aplikasi (`force-stop`), lalu kembali ke game **Magic Ocean Tile Crush** (`com.starlightgame.magicoceantilecrush`).

## Cara Menjalankan:

### Langsung dari Terminal mana saja:
```bash
inject-iklan
```

### 1 Kali Siklus (Default):
```bash
cd /Users/macbookair/android-game-bots/inject-iklan
./inject-iklan
```

### Loop Berkala (misal tiap 5 menit):
```bash
inject-iklan --loop --interval 300
```

### Opsi Lainnya:
- `--count N` atau `-n N`: Jalankan N siklus berturut-turut.
- `--serial SERIAL` atau `-s SERIAL`: Tentukan ID perangkat jika terhubung lebih dari 1 HP.
- `--dry-run`: Mode simulasi (tanpa tap fisik).
- `--no-marker`: Nonaktifkan efek visual tap marker di layar scrcpy.
