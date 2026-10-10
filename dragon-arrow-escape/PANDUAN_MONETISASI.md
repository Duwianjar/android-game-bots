# 💰 Dragon Arrow Escape - Panduan Monetisasi Lengkap

## 📊 STATUS SAAT INI

✅ **SUDAH SIAP:**
- Kode AdMob SDK terintegrasi lengkap
- 3 jenis iklan: Rewarded, Interstitial, Banner
- JavaScript bridge untuk game HTML5
- Gradle wrapper untuk build APK
- Permissions lengkap di AndroidManifest

❌ **MASIH PERLU DIPERBAIKI:**
1. **google-services.json** - file konfigurasi Firebase/AdMob
2. **Production Ad IDs** - ganti TEST IDs dengan IDs asli dari AdMob

## 🚀 SETUP MONETISASI (30 MENIT)

### LANGKAH 1: Buat Akun AdMob (5 menit)

1. Buka https://admob.google.com
2. Klik **"Get Started"** atau **"Sign up"**
3. Login dengan Google Account
4. Isi informasi:
   - Negara tempat tinggal
   - Timezone
   - Currency (IDR untuk Indonesia)
5. **Penting**: Isi informasi pembayaran (untuk terima uang)
   - Nama lengkap sesuai KTP
   - Alamat lengkap
   - Nomor pajak (NPWP untuk Indonesia)
6. Tunggu verifikasi email (1-5 menit)

### LANGKAH 2: Daftarkan Aplikasi (5 menit)

1. Di AdMob Console, klik **"Apps"** → **"Add App"**
2. Pilih **"Android"**
3. Isi detail:
   - App name: **Dragon Arrow Escape**
   - Package name: **com.dragonarrowescape.game**
   - Category: **Games → Casual**
4. Klik **"Add"**
5. **CATAT APP ID** yang muncul (format: `ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY`)

   Contoh: `ca-app-pub-1234567890123456~9876543210`

### LANGKAH 3: Buat Ad Units (10 menit)

Buat 3 jenis ad unit untuk monetisasi maksimal:

#### 3.1. Rewarded Ad (Iklan Hadiah) - PRIORITAS TERTINGGI

1. Klik **"Ad Units"** → **"Add Ad Unit"** → **"Rewarded"**
2. Isi:
   - Ad unit name: `Dragon Arrow Reward`
   - Reward amount: `100` (coins)
   - Reward item: `coins`
3. Klik **"Create Ad Unit"**
4. **CATAT REWARDED AD UNIT ID**
   
   Format: `ca-app-pub-XXXXXXXXXXXXXXXX/1234567890`

**Kapan ditampilkan:**
- ✅ Game Over → Continue dengan nonton iklan
- ✅ Unlock item premium (skins, power-ups)
- ✅ Double coins setelah level
- ✅ Extra lives/continues

**Estimasi Revenue**: $10-$30 per 1000 impressions (CPM)

#### 3.2. Interstitial Ad (Iklan Fullscreen)

1. Klik **"Add Ad Unit"** → **"Interstitial"**
2. Isi:
   - Ad unit name: `Dragon Arrow Interstitial`
3. Klik **"Create Ad Unit"**
4. **CATAT INTERSTITIAL AD UNIT ID**

**Kapan ditampilkan:**
- ✅ Setelah complete level (setiap 2-3 level)
- ✅ Keluar ke menu utama
- ✅ Setelah session 3-5 menit
- ⚠️ **Cooldown 3 menit** (jangan terlalu sering!)

**Estimasi Revenue**: $3-$8 per 1000 impressions

#### 3.3. Banner Ad (Iklan Banner)

1. Klik **"Add Ad Unit"** → **"Banner"**
2. Isi:
   - Ad unit name: `Dragon Arrow Banner`
   - Banner size: **320x50** (Standard)
3. Klik **"Create Ad Unit"**
4. **CATAT BANNER AD UNIT ID**

**Kapan ditampilkan:**
- ✅ Di menu utama
- ✅ Di leaderboard/stats
- ✅ Di shop/upgrade screen
- ❌ **JANGAN** di gameplay aktif (mengganggu user)

**Estimasi Revenue**: $0.50-$2 per 1000 impressions

### LANGKAH 4: Download google-services.json (2 menit)

**Pilihan A: Dari Firebase Console (Recommended)**

1. Buka https://console.firebase.google.com
2. Klik **"Add Project"** atau pilih project existing
3. Nama project: `dragon-arrow-escape` (atau sama dengan yang di AdMob)
4. Enable Google Analytics (optional)
5. Klik **"Continue"**
6. Setelah project dibuat, klik **"Add app"** → **Android**
7. Package name: `com.dragonarrowescape.game`
8. App nickname: `Dragon Arrow Escape`
9. Klik **"Register app"**
10. **Download google-services.json**
11. Letakkan file di: `android/app/google-services.json`

**Pilihan B: Dari AdMob Console**

1. Di AdMob Console, klik **"App Settings"**
2. Scroll ke bawah, cari **"Link to Firebase"**
3. Klik **"Link"** → ikuti instruksi
4. Download `google-services.json` dari Firebase Console

### LANGKAH 5: Update Production Ad IDs (3 menit)

Jalankan script setup dengan Ad IDs yang sudah dicatat:

```bash
cd ~/android-game-bots/dragon-arrow-escape

python3 setup_admob.py \
  --app-id "ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY" \
  --rewarded "ca-app-pub-XXXXXXXXXXXXXXXX/1111111111" \
  --interstitial "ca-app-pub-XXXXXXXXXXXXXXXX/2222222222" \
  --banner "ca-app-pub-XXXXXXXXXXXXXXXX/3333333333"
```

**GANTI** XXXXXXXXXXXXXXXX dan angka-angka dengan IDs asli dari AdMob!

Script akan:
- ✅ Validasi format Ad IDs
- ✅ Backup file lama
- ✅ Update AndroidManifest.xml dengan App ID
- ✅ Update AdsManager.java dengan Ad Unit IDs
- ✅ Check google-services.json ada

### LANGKAH 6: Build & Test (5 menit)

```bash
cd ~/android-game-bots/dragon-arrow-escape/android

# Build debug APK
./gradlew assembleDebug

# Install ke device
adb install app/build/outputs/apk/debug/app-debug.apk

# Monitor logs
adb logcat | grep -i "DragonArrowEscape\|AdsManager\|Ads"
```

**Yang harus muncul di log:**
- ✅ `Google Mobile Ads SDK initialized`
- ✅ `Rewarded Ad Loaded Successfully`
- ✅ `Interstitial Ad Loaded Successfully`
- ✅ `Banner ad loaded`

## 💰 ESTIMASI PENDAPATAN

### Skenario Konservatif

**Asumsi:**
- 1,000 active users per hari
- Setiap user main 10 menit/hari
- Rewarded ads: 2x per session (user triggered)
- Interstitial: 1x per session (auto)
- Banner: 50 impressions per session (menu saja)

**Perhitungan:**
```
Rewarded:     2,000 impressions × $15 CPM = $30/hari
Interstitial: 1,000 impressions × $5 CPM  = $5/hari
Banner:      50,000 impressions × $1 CPM  = $50/hari
------------------------------------------------
TOTAL: $85/hari = $2,550/bulan = Rp 40 juta/bulan
```

### Skenario Optimis (10K Users)

**Dengan 10,000 active users per hari:**
```
Rewarded:     20,000 impressions × $15 CPM = $300/hari
Interstitial: 10,000 impressions × $5 CPM  = $50/hari
Banner:      500,000 impressions × $1 CPM  = $500/hari
-------------------------------------------------
TOTAL: $850/hari = $25,500/bulan = Rp 400 juta/bulan
```

### Faktor yang Meningkatkan Revenue:

1. **Geography** - US/UK/Australia CPM lebih tinggi 3-5x
2. **User Engagement** - Lebih lama main = lebih banyak ads
3. **Ad Fill Rate** - Biasanya 80-95% (tidak semua request dapat ads)
4. **Click-Through Rate** - Banner ads yang diklik = bonus revenue

## 📊 MONITORING REVENUE

### AdMob Dashboard

1. Login ke https://admob.google.com
2. Klik **"Reports"** atau **"Laporan"**
3. Lihat metrics:
   - **Estimated earnings** (Pendapatan estimasi)
   - **Ad requests** (Request iklan)
   - **Impressions** (Tayangan iklan)
   - **Match rate** (% request yang dapat ads)
   - **eCPM** (Earnings per 1000 impressions)

### Update Realtime (setelah 24 jam):
- Impressions update setiap 1-2 jam
- Revenue update setiap 4-6 jam
- Final numbers update setiap 24 jam

### Payout (Pencairan Uang):
- **Minimum payout**: $100 USD
- **Waktu payout**: Setiap tanggal 21 bulan berikutnya
- **Metode**: Bank transfer, Western Union, Wire Transfer

Contoh: Revenue Oktober = $150 → Dibayar tanggal 21 November

## ⚠️ ATURAN PENTING (WAJIB BACA!)

### DO ✅

1. **Tawarkan value untuk rewarded ads**
   - Continue game setelah game over
   - 2x coins/rewards
   - Unlock premium items
   - Extra lives
   
2. **Timing interstitial ads yang baik**
   - Setelah complete level
   - Natural breaks dalam gameplay
   - Cooldown minimum 3 menit
   
3. **Hide banner saat gameplay aktif**
   - Show di menu, shop, leaderboard
   - Hide saat user sedang main
   
4. **Test di real device**
   - Emulator ads tidak akurat
   - Test di Android fisik
   
5. **Monitor AdMob dashboard**
   - Check revenue harian
   - Optimize ad placement
   - A/B test frekuensi ads

### DON'T ❌

1. **JANGAN KLIK ADS SENDIRI**
   - Instant ban permanently!
   - Google detect invalid clicks
   - Akun bisa ditutup selamanya
   
2. **JANGAN SPAM ADS**
   - User akan uninstall
   - Bad reviews di Play Store
   - Lower retention rate
   
3. **JANGAN MISLEADING**
   - Jangan bilang "Loading" padahal ads
   - Jangan fake button di rewarded ads
   - Jangan force ads tanpa value
   
4. **JANGAN LUPA GANTI TEST IDs**
   - Test IDs TIDAK menghasilkan uang
   - Harus ganti ke production IDs
   
5. **JANGAN PUBLISH TANPA TESTING**
   - Test ads muncul
   - Test no crashes
   - Test user experience

## 🔍 VALIDASI SEBELUM PUBLISH

Jalankan checker script:

```bash
cd ~/android-game-bots/dragon-arrow-escape
python3 check_monetization.py
```

**Harus semua ✅ PASSED:**
- [x] Gradle wrapper exists
- [x] google-services.json configured
- [x] Production Ad IDs (bukan test)
- [x] AdMob SDK dependencies
- [x] Required permissions
- [x] Ad implementation complete

## 🐛 TROUBLESHOOTING

### Problem: "Ads failed to load"

**Solution:**
1. Check internet connection
2. Tunggu 24-48 jam setelah setup (AdMob butuh waktu)
3. Check logcat: `adb logcat | grep -i ads`
4. Verify Ad Unit IDs benar
5. Check AdMob dashboard - app approved?

### Problem: "No fill" atau "Match rate rendah"

**Normal di awal!**
- New apps butuh 2-7 hari untuk build ad inventory
- Match rate akan improve seiring waktu
- Target: 80-95% match rate

**Action:**
- Aktifkan "Optimize ad serving" di AdMob
- Enable "Mediation" untuk backup ads
- Enable "Open Bidding" untuk higher CPM

### Problem: Revenue tidak masuk rekening

**Check:**
1. Minimum $100 belum tercapai?
2. Payment info sudah lengkap?
3. Tunggu sampai tanggal 21 bulan berikutnya
4. Check email dari Google untuk verification

### Problem: Account suspended

**Penyebab:**
- Invalid traffic (klik sendiri, bots)
- Misleading implementation
- Policy violations

**Prevention:**
- JANGAN klik ads sendiri
- Follow Ad Placement Policies
- Transparent dengan user

## 📞 SUPPORT & RESOURCES

- **AdMob Support**: https://support.google.com/admob
- **AdMob Policies**: https://support.google.com/admob/answer/6128543
- **Quick Start Guide**: https://developers.google.com/admob/android/quick-start
- **Best Practices**: https://support.google.com/admob/answer/6128877

## 🎯 RINGKASAN QUICK START

```bash
# 1. Setup monetization
cd ~/android-game-bots/dragon-arrow-escape

# 2. Get IDs dari https://admob.google.com
# 3. Download google-services.json dari Firebase
# 4. Run setup
python3 setup_admob.py --app-id YOUR_APP_ID --rewarded ... --interstitial ... --banner ...

# 5. Validate
python3 check_monetization.py

# 6. Build
cd android && ./gradlew assembleRelease

# 7. Test
adb install app/build/outputs/apk/release/app-release.apk

# 8. Publish ke Play Store
# 9. Monitor di https://admob.google.com
```

---

**🎉 Selamat menghasilkan uang dari game! 💰**

Target realistis: **$1,000-$5,000/bulan** dengan 5,000-10,000 active users.
