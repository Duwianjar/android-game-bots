# 🚀 CARA MENGHASILKAN UANG DARI IKLAN - LANGKAH LENGKAP

## ❌ MASALAH SAAT INI
Game sudah jadi dan bisa menampilkan iklan, TAPI masih pakai **TEST IDs** dari Google.

**TEST IDs = $0 revenue** (tidak menghasilkan uang sama sekali!)

```
REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917"  ← TEST ID
INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712"  ← TEST ID  
BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/6300978111"  ← TEST ID
```

---

## ✅ SOLUSI: GANTI DENGAN PRODUCTION IDs

### STEP 1: Buat Akun AdMob (5 menit)

1. **Buka:** https://admob.google.com
2. **Login** dengan akun Google kamu
3. **Klik:** "Get Started" atau "Mulai"
4. **Isi data pembayaran** (agar bisa terima uang):
   - Nama lengkap
   - Alamat lengkap
   - Nomor rekening bank atau PayPal
   - Informasi pajak (sesuai negara)

💰 **Minimal payout:** $100 USD  
💰 **Waktu bayar:** Setiap bulan tanggal 21

---

### STEP 2: Daftarkan Aplikasi (3 menit)

1. Di dashboard AdMob, klik **"Apps"** → **"Add App"**
2. Pilih platform: **Android**
3. App sudah di Play Store? **Pilih "No"**
4. Nama app: **Dragon Arrow Escape**
5. Klik **"Add"**

**CATAT App ID yang muncul:**
```
ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY
```

Contoh nyata:
```
ca-app-pub-1234567890123456~0987654321
```

---

### STEP 3: Buat 3 Ad Units (5 menit)

#### A. REWARDED AD (Revenue tertinggi: $10-$30 per 1000 views)

1. Klik **"Add Ad Unit"**
2. Pilih **"Rewarded"**
3. Nama: **Dragon Arrow Rewarded**
4. Klik **"Create Ad Unit"**
5. **CATAT ID:**
   ```
   ca-app-pub-XXXXXXXXXXXXXXXX/1111111111
   ```

**Kegunaan:** User tonton iklan dapat bonus coins, continue game

---

#### B. INTERSTITIAL AD (Revenue sedang: $3-$8 per 1000 views)

1. Klik **"Add Ad Unit"** lagi
2. Pilih **"Interstitial"**
3. Nama: **Dragon Arrow Interstitial**
4. Klik **"Create Ad Unit"**
5. **CATAT ID:**
   ```
   ca-app-pub-XXXXXXXXXXXXXXXX/2222222222
   ```

**Kegunaan:** Muncul otomatis setiap 2-3 level (cooldown 3 menit)

---

#### C. BANNER AD (Revenue rendah: $0.5-$2 per 1000 views, tapi always on)

1. Klik **"Add Ad Unit"** lagi
2. Pilih **"Banner"**
3. Nama: **Dragon Arrow Banner**
4. Klik **"Create Ad Unit"**
5. **CATAT ID:**
   ```
   ca-app-pub-XXXXXXXXXXXXXXXX/3333333333
   ```

**Kegunaan:** Tampil di menu utama (hidden saat gameplay)

---

### STEP 4: Update Kode (OTOMATIS dengan script!)

Setelah dapat **4 IDs** (1 App ID + 3 Ad Unit IDs), jalankan script ini:

```bash
cd ~/android-game-bots/dragon-arrow-escape
./setup_production_admob.sh
```

Script akan tanya:
1. **App ID** (yang dari Step 2)
2. **Rewarded Ad Unit ID** (yang dari Step 3A)
3. **Interstitial Ad Unit ID** (yang dari Step 3B)
4. **Banner Ad Unit ID** (yang dari Step 3C)

Script otomatis update:
- ✅ AndroidManifest.xml
- ✅ AdsManager.java
- ✅ Backup file lama

---

### STEP 5: Build Release APK (5 menit)

```bash
cd ~/android-game-bots/dragon-arrow-escape/android
./gradlew assembleRelease
```

APK siap ada di:
```
android/app/build/outputs/apk/release/app-release.apk
```

---

### STEP 6: Upload ke Google Play Store

1. **Buka:** https://play.google.com/console
2. **Buat aplikasi baru**
3. **Upload APK** yang sudah di-build
4. **Isi store listing:** (screenshot, deskripsi, dll)
5. **Submit untuk review**

⏰ **Review time:** 1-7 hari

---

## 💰 ESTIMASI REVENUE

### Skenario Konservatif (1000 daily active users):

**Per Hari:**
- Rewarded Ads: 500 views × $0.015 = $7.50
- Interstitial Ads: 800 views × $0.005 = $4.00
- Banner Ads: 3000 impressions × $0.001 = $3.00
- **TOTAL: $14.50/hari**

**Per Bulan:** $14.50 × 30 = **$435**  
**Per Tahun:** $435 × 12 = **$5,220**

---

### Skenario Optimis (10,000 daily active users):

**Per Hari:**
- Rewarded Ads: 5,000 views × $0.015 = $75
- Interstitial Ads: 8,000 views × $0.005 = $40
- Banner Ads: 30,000 impressions × $0.001 = $30
- **TOTAL: $145/hari**

**Per Bulan:** $145 × 30 = **$4,350**  
**Per Tahun:** $4,350 × 12 = **$52,200**

---

## 🔍 CARA CEK REVENUE

1. Buka https://admob.google.com
2. Dashboard → **Reports**
3. Lihat:
   - **Impressions** (berapa kali iklan tampil)
   - **Estimated earnings** (estimasi pendapatan)
   - **eCPM** (earnings per 1000 impressions)

**Update:** Real-time (dengan delay 1-2 jam)

---

## ⚠️ PENTING!

### Jangan Klik Iklan Sendiri!
- ❌ Jangan test dengan klik iklan sendiri berulang kali
- ❌ Google detect fraud → akun bisa di-banned permanent
- ✅ Pakai TEST IDs untuk development
- ✅ Ganti PRODUCTION IDs hanya saat mau publish

### Tips Aman Testing:
```bash
# Test mode (pakai TEST IDs)
./verify_monetization.sh

# Production mode (setelah dapat real IDs dari AdMob)
./setup_production_admob.sh
```

---

## 📊 MONITORING PERFORMANCE

Script built-in untuk cek performa iklan:

```bash
# Cek status monetisasi
./verify_monetization.sh

# Estimasi revenue
python3 estimate_revenue.py

# Build APK release
./build-release.sh
```

---

## 🆘 TROUBLESHOOTING

### "Iklan tidak muncul di production"
1. Tunggu 24-48 jam setelah publish (AdMob butuh waktu setup)
2. Pastikan app sudah approved di Play Store
3. Cek AdMob dashboard: app status harus "Ready to serve ads"

### "Revenue masih $0"
1. Pastikan sudah ganti TEST IDs dengan PRODUCTION IDs
2. Cek AdMob dashboard: pastikan ad units aktif
3. Tunggu 24-48 jam untuk data muncul

### "Ad request failed"
1. Cek internet connection
2. Pastikan google-services.json sudah download dari Firebase
3. Cek logcat: `adb logcat | grep AdMob`

---

## 📞 KONTAK & SUPPORT

- **AdMob Help:** https://support.google.com/admob
- **Play Console:** https://support.google.com/googleplay
- **Dokumentasi lengkap:** Baca semua file .md di folder project

---

## ✅ CHECKLIST BEFORE PRODUCTION

- [ ] Sudah dapat 4 Production IDs dari AdMob
- [ ] Sudah jalankan `./setup_production_admob.sh`
- [ ] Sudah build release APK
- [ ] Sudah test APK di device fisik (bukan emulator)
- [ ] Iklan tampil dengan benar (Rewarded, Interstitial, Banner)
- [ ] google-services.json sudah download dari Firebase
- [ ] App sudah upload ke Play Store (Internal Testing dulu)
- [ ] Tunggu 24-48 jam setelah publish untuk ads aktif

**SETELAH SEMUA CHECKLIST ✅ → GAME SIAP MENGHASILKAN UANG! 💰**
