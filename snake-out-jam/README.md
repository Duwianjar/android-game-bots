# Snake Out Jam - Panduan Instalasi & Analisis

Panduan teknis instalasi, bypass lisensi Google Play (PairIP Licensing), dan catatan analisis penarikan saldo untuk game **Snake Out Jam**.

- **Nama Game**: Snake Out Jam
- **Package ID**: `com.wiwvitsugeh.snack`
- **Versi**: `1.0.8` (versionCode: `108`)
- **Main Activity**: `com.wiwvitsugeh.snack/.u111.al1.Splash` -> `com.wiwvitsugeh.snack/.u111.al1.SnakeOutJam`
- **Format Paket Asli**: Split APK (Base + `config.armeabi_v7a` + `config.en` + `config.mdpi`)
- **Status Perangkat**: Teruji berhasil berjalan normal di Infinix X692 (Android 10).

---

## 1. Catatan Penarikan & Analisis Monetisasi

| Parameter | Keterangan |
|---|---|
| **Total Penarikan Tercatat** | 4 kali: Rp147, Rp9.237, Rp288, dan Rp51 |
| **Pencairan Terbesar** | Rp9.237 (Berhasil cair ke e-wallet) |
| **Karakteristik Game** | Setelah berhasil melakukan penarikan besar di kisaran **Rp9.000**, proses permainan dan pencairan terasa jauh lebih sulit atau dipersulit oleh server game. |
| **Instalasi Kedua** | **Susah iklan slotnya** (iklan reward/slot susah muncul/didapat saat instalasi kedua). |
| **Rekomendasi Instalasi** | **Instal dengan target kecil dulu.** Berada di bawah Color Power Pop. Jangan langsung memaksakan mengejar target Rp10.000+ dalam sekali sesi. |

---

## 2. Masalah Pada File Asli (Kenapa Tidak Bisa Dibuka Langsung)

Saat file APK/XAPK diunduh dari luar Google Play Store (misal APKPure):
1. **Google Play Licensing Protection (PairIP)**:
   - Aplikasi menggunakan proteksi `com.pairip.licensecheck.LicenseClient`.
   - Saat dijalankan pertama kali, aplikasi memeriksa lisensi pembelian ke Google Play Store.
   - Karena game diinstal manual via sideload/ADB dan listing game di Google Play telah dihapus/tidak ditemukan, pengecekan ini memicu redirect paksa membuka Google Play Store, lalu memanggil `System.exit(0)` sehingga game langsung tertutup (crash/exit).
2. **Struktur Split APK**:
   - Game tidak berupa single APK, melainkan bundle Split APK (Base + 3 config APK). Pemasangan harus memakai `adb install-multiple` dengan sertifikat penandatanganan (signature) yang seragam.
3. **Dependensi Kotlin Coroutines**:
   - Jika APK dibongkar dan disign ulang tanpa mempertahankan file konfigurasi internal `META-INF/services/kotlinx.coroutines.*`, aplikasi akan force-close saat inisialisasi coroutines (`NoSuchMethodError`).

---

## 3. Solusi & Prosedur Bypass Lisensi

Untuk membuat game dapat berjalan normal di HP tanpa lisensi Google Play:

### Langkah A: Ekstraksi XAPK
Ekstrak isi `Snake_Out_Jam.xapk`:
```bash
unzip ~/Downloads/Snake_Out_Jam.xapk -d /tmp/snack_raw
```

### Langkah B: Neutralisasi Proteksi PairIP di `classes2.dex`
Proteksi lisensi berada di `classes2.dex`. Kita menonaktifkan kode pemblokiran:
1. Decompile `classes2.dex` menggunakan JADX atau Baksmali.
2. Edit file `com/pairip/licensecheck/LicenseClient.java`:
   ```java
   package com.pairip.licensecheck;
   import android.content.Context;

   public class LicenseClient {
       public static void checkLicense(Context context) {
           // Dikosongkan agar tidak mengecek lisensi ke Play Store
       }
       public static LicenseClient getInstance(Context context) {
           return new LicenseClient();
       }
       public void initializeLicenseCheck() {
           // Dikosongkan
       }
   }
   ```
3. Edit `com/pairip/licensecheck/LicenseActivity.java` agar langsung menutup aktivitas lisensi tanpa memblokir game (`finish()` di `onCreate` dan `onStart`).
4. Kompilasi ulang kode Java ke class menggunakan `javac` dengan `android.jar`, lalu ubah menjadi `classes2.dex` menggunakan `d8`:
   ```bash
   d8 --output /tmp/dex_out /tmp/bin/com/pairip/licensecheck/*.class ...
   ```
5. Masukkan `classes2.dex` hasil patch kembali ke dalam APK utama:
   ```bash
   zip -u com.wiwvitsugeh.snack.apk classes2.dex
   ```

### Langkah C: Penandatanganan Ulang (Re-Signing & Zipalign)
1. Hapus tanda tangan lama dari semua split APK:
   ```bash
   zip -d *.apk "META-INF/*.SF" "META-INF/*.RSA" "META-INF/*.MF"
   ```
   *(Pastikan direktori `META-INF/services/` tetap utuh agar runtime Kotlin Coroutines tidak rusak).*
2. Align 4-byte menggunakan `zipalign`:
   ```bash
   zipalign -p -f 4 input.apk aligned.apk
   ```
3. Tandatangani semua split APK dengan keystore yang sama:
   ```bash
   apksigner sign --ks ~/.android/debug.keystore --ks-pass pass:android --key-pass pass:android *.apk
   ```

---

## 4. Cara Instalasi Cepat via Script

File APK yang telah dipatch dan siap pakai sudah tersimpan di:
`/Users/macbookair/Downloads/Snake_Out_Jam_Patched/`

Untuk memasang langsung ke perangkat HP yang terhubung via ADB, jalankan:
```bash
cd /Users/macbookair/android-game-bots/snake-out-jam
./install_snake_out_jam.sh
```

Skrip ini akan secara otomatis:
1. Mendeteksi HP yang terhubung via ADB.
2. Memasang semua split APK patched (`adb install-multiple`).
3. Membuka langsung game di layar HP.

---

## 5. Perintah Manual via ADB

Jika ingin memasang manual dari terminal:
```bash
cd /Users/macbookair/Downloads/Snake_Out_Jam_Patched
adb install-multiple -r -d \
    com.wiwvitsugeh.snack.apk \
    config.armeabi_v7a.apk \
    config.en.apk \
    config.mdpi.apk
```

Membuka aplikasi di layar:
```bash
adb shell monkey -p com.wiwvitsugeh.snack -c android.intent.category.LAUNCHER 1
```

Memeriksa apakah aplikasi sedang aktif di foreground:
```bash
adb shell dumpsys window | grep -E "mCurrentFocus|mFocusedApp"
```
