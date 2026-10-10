# 🎯 Setup AdMob untuk Monetisasi Game - PANDUAN LENGKAP

## ⚠️ STATUS SAAT INI: TESTING MODE (TIDAK MENGHASILKAN UANG!)

Aplikasi saat ini menggunakan **TEST AD UNIT IDs** dari Google. Ads akan muncul, tapi **TIDAK menghasilkan pendapatan**. Untuk mulai menghasilkan uang, ikuti langkah-langkah di bawah ini.

---

## 📋 LANGKAH 1: Buat Akun AdMob

1. **Kunjungi**: https://admob.google.com
2. **Sign in** dengan akun Google Anda
3. **Daftar** sebagai publisher AdMob (gratis)
4. **Verifikasi identitas** (diperlukan untuk pembayaran)
5. **Setup pembayaran**: 
   - Tambahkan rekening bank untuk menerima pembayaran
   - Threshold minimum pembayaran: $100 USD
   - Pilihan: Transfer bank / Wire transfer

---

## 📱 LANGKAH 2: Daftarkan Aplikasi di AdMob

### A. Buat Aplikasi Baru

1. Di dashboard AdMob, klik **"Apps"** > **"Add App"**
2. Pilih **"Android"**
3. **Nama aplikasi**: `Dragon Arrow Escape`
4. **Package name**: `com.dragonarrowescape.game`
   - ⚠️ **PENTING**: Harus sama persis dengan `applicationId` di `build.gradle`!
5. Klik **"Add"**

### B. Dapatkan AdMob App ID

Setelah membuat aplikasi, Anda akan mendapat:
```
AdMob App ID: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY
```

**Format**: `ca-app-pub-[16 digit]~[10 digit]`

📝 **CATAT ID INI** - Anda akan perlu mengganti di AndroidManifest.xml

---

## 🎯 LANGKAH 3: Buat Ad Units

Anda perlu membuat 3 jenis ad units:

### 3.1 Rewarded Ad (Prioritas Tertinggi - RPM $10-$30)

1. Pilih aplikasi > **"Ad units"** > **"Add ad unit"**
2. Pilih **"Rewarded"**
3. **Ad unit name**: `Rewarded Video - Bonus`
4. Klik **"Create ad unit"**
5. **CATAT Ad Unit ID**: `ca-app-pub-XXXXXXXXXXXXXXXX/ZZZZZZZZZZ`

**Penggunaan dalam game**:
- Bonus coins setelah game over
- Continue game (extra life)
- Unlock premium items
- Double rewards

### 3.2 Interstitial Ad (Prioritas Sedang - RPM $3-$8)

1. Pilih aplikasi > **"Ad units"** > **"Add ad unit"**
2. Pilih **"Interstitial"**
3. **Ad unit name**: `Interstitial - Level Transition`
4. Klik **"Create ad unit"**
5. **CATAT Ad Unit ID**: `ca-app-pub-XXXXXXXXXXXXXXXX/AAAAAAAAAA`

**Penggunaan dalam game**:
- Setiap 2-3 level
- Cooldown 3 menit (sudah di-handle di kode)
- Saat transisi menu

### 3.3 Banner Ad (Prioritas Rendah - RPM $0.5-$2)

1. Pilih aplikasi > **"Ad units"** > **"Add ad unit"**
2. Pilih **"Banner"**
3. **Ad unit name**: `Banner - Main Menu`
4. Klik **"Create ad unit"**
5. **CATAT Ad Unit ID**: `ca-app-pub-XXXXXXXXXXXXXXXX/BBBBBBBBBB`

**Penggunaan dalam game**:
- Di menu utama
- Saat pause
- Hidden saat gameplay

---

## 🔧 LANGKAH 4: Update Kode dengan Production IDs

### File 1: AndroidManifest.xml

**Lokasi**: `android/app/src/main/AndroidManifest.xml`

**GANTI BARIS 41**:
```xml
<!-- SEBELUM (TEST ID) -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-3940256099942544~3347511713" />

<!-- SESUDAH (Production ID dari Step 2B) -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY" />
```

### File 2: AdsManager.java

**Lokasi**: `android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java`

**GANTI BARIS 39, 42, 45**:

```java
// SEBELUM (TEST IDs)
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917";
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712";
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/6300978111";

// SESUDAH (Production IDs dari Step 3)
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/ZZZZZZZZZZ"; // Rewarded
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/AAAAAAAAAA"; // Interstitial
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/BBBBBBBBBB"; // Banner
```

---

## 🔐 LANGKAH 5: Setup Firebase (Diperlukan)

AdMob memerlukan file `google-services.json` dari Firebase.

### A. Buat/Link Firebase Project

1. Kunjungi: https://console.firebase.google.com
2. Klik **"Add project"** atau gunakan existing project
3. Nama project: `dragon-arrow-escape` (atau sesuai keinginan)
4. Enable Google Analytics (recommended)

### B. Tambahkan Android App

1. Di Firebase Console > **Project Settings** > **"Add app"** > **Android**
2. **Android package name**: `com.dragonarrowescape.game`
   - ⚠️ **HARUS SAMA** dengan applicationId!
3. **App nickname**: `Dragon Arrow Escape`
4. **Debug SHA-1**: (optional untuk sekarang)
5. Klik **"Register app"**

### C. Download google-services.json

1. Download file `google-services.json`
2. Copy ke: `android/app/google-services.json`
3. **⚠️ PENTING**: File ini berisi API keys - **JANGAN commit ke public repo!**

**Struktur file**:
```
android/
├── app/
│   ├── google-services.json  ← LETAKKAN DI SINI
│   ├── build.gradle
│   └── src/
```

### D. Link AdMob ke Firebase

1. Di Firebase Console: **Project Settings** > **Integrations**
2. Cari **"AdMob"** > Klik **"Link"**
3. Pilih AdMob app yang sudah dibuat di Step 2
4. Confirm link

---

## 🏗️ LANGKAH 6: Build Production APK

### A. Build Release APK

```bash
cd android
./gradlew assembleRelease
```

APK ada di: `android/app/build/outputs/apk/release/app-release-unsigned.apk`

### B. Sign APK (Untuk Upload ke Play Store)

1. **Generate Keystore** (sekali saja):
```bash
keytool -genkey -v -keystore dragon-arrow-escape.keystore \
  -alias dragon-arrow-escape \
  -keyalg RSA -keysize 2048 -validity 10000
```

**⚠️ SIMPAN PASSWORD**: Anda akan perlu ini setiap build!

2. **Sign APK**:
```bash
cd android/app/build/outputs/apk/release
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore /path/to/dragon-arrow-escape.keystore \
  app-release-unsigned.apk dragon-arrow-escape
```

3. **Zipalign**:
```bash
zipalign -v 4 app-release-unsigned.apk dragon-arrow-escape.apk
```

---

## 📤 LANGKAH 7: Upload ke Google Play Store

### A. Buat Google Play Console Account

1. Kunjungi: https://play.google.com/console
2. **Biaya pendaftaran**: $25 USD (sekali seumur hidup)
3. Lengkapi profil developer

### B. Buat Aplikasi Baru

1. Klik **"Create app"**
2. **App name**: `Dragon Arrow Escape`
3. **Default language**: Indonesian
4. **App type**: Game
5. **Category**: Action
6. **Free/Paid**: Free (dengan ads)

### C. Upload APK/AAB

1. **Production** > **Create new release**
2. Upload `dragon-arrow-escape.apk` atau build AAB:
```bash
./gradlew bundleRelease
```
3. **Version**: 1.0.0
4. Release notes (Bahasa Indonesia):
```
🎮 Dragon Arrow Escape - Versi Pertama!

✨ Fitur:
• Game arcade seru dengan dragon dan panah magis
• Kontrol joystick smooth
• Sistem scoring
• Bonus rewards dari menonton iklan
• Grafis modern dan colorful

Selamat bermain! 🚀
```

### D. Lengkapi Store Listing

**Required**:
- **App icon** (512x512 PNG)
- **Feature graphic** (1024x500 PNG)
- **Screenshots** (minimal 2):
  - Phone: 1080x1920 atau 720x1280
  - Ambil dari gameplay
- **Short description** (80 chars):
  ```
  Petualangan dragon yang menembakkan panah magis! Hindari rintangan & raih skor!
  ```
- **Full description** (4000 chars):
  ```
  🐉 Dragon Arrow Escape - Petualangan Seru Penuh Aksi!

  Kendalikan dragon pemberani yang menembakkan panah magis untuk bertahan hidup! 
  Hindari rintangan berbahaya, kumpulkan poin, dan raih high score tertinggi!

  🎮 GAMEPLAY:
  • Kontrol intuitif dengan virtual joystick
  • Tembakkan panah magis dengan tap button
  • Hindari rintangan yang semakin cepat
  • Sistem scoring yang adiktif

  ✨ FITUR:
  • Grafis modern dan colorful
  • Gameplay smooth dan responsive
  • Tonton iklan untuk bonus poin
  • Cocok untuk semua umur
  • Offline-friendly

  🎯 CARA BERMAIN:
  1. Gunakan joystick untuk menggerakkan dragon
  2. Tekan tombol panah untuk menembak
  3. Hindari rintangan merah
  4. Kumpulkan poin sebanyak mungkin
  5. Tonton iklan untuk bonus rewards!

  Ayo download sekarang dan buktikan skill-mu! 🚀
  ```
- **Category**: Action
- **Content rating**: Complete questionnaire (PEGI 3/Everyone)
- **Contact details**: Email Anda

### E. Submit for Review

1. Review semua informasi
2. Klik **"Save"** untuk semua halaman
3. **"Submit for review"**
4. **Waktu review**: 1-7 hari (biasanya 24-48 jam)

---

## 💰 LANGKAH 8: Verifikasi Ads Berjalan

### A. Testing Setelah Publish

⚠️ **JANGAN test dengan akun AdMob sendiri** - bisa banned!

**Test dengan**:
- Device orang lain
- Akun Google berbeda
- Atau gunakan test mode dulu

### B. Monitor di AdMob Dashboard

1. **Home** > **Dashboard**
2. Lihat metrics:
   - **Impressions**: Berapa kali ads tampil
   - **Clicks**: Berapa kali ads diklik
   - **Estimated earnings**: Perkiraan penghasilan
   - **eCPM**: Earnings per 1000 impressions

### C. Optimasi Monetisasi

**Rewarded Ads** (Best Practice):
- Tampilkan setelah game over dengan benefit jelas
- "Tonton iklan untuk +500 poin bonus"
- "Tonton iklan untuk continue game"
- Target: 1-3 rewarded ads per session

**Interstitial Ads** (Best Practice):
- Cooldown 3 menit (sudah di-set di kode)
- Tampilkan di natural break (selesai level, bukan tengah gameplay)
- Target: 1-2 interstitial per session
- ⚠️ Jangan spam - user akan uninstall!

**Banner Ads** (Best Practice):
- Hanya di menu, tidak saat gameplay
- Bottom atau top screen
- Auto-refresh setiap 30-60 detik (handled by AdMob)

---

## 📊 ESTIMASI PENGHASILAN

### Revenue Per Mille (RPM) - Indonesia Market

| Ad Type | eCPM | Per 1000 Impressions |
|---------|------|----------------------|
| **Rewarded** | $10-30 | Rp 150,000 - 450,000 |
| **Interstitial** | $3-8 | Rp 45,000 - 120,000 |
| **Banner** | $0.5-2 | Rp 7,500 - 30,000 |

### Contoh Perhitungan

**Skenario**: 1000 daily active users (DAU)

**Asumsi per user per day**:
- 2 rewarded ads
- 1 interstitial ad
- 5 banner impressions

**Revenue per day**:
```
Rewarded:    1000 users x 2 ads x $0.015 = $30/day
Interstitial: 1000 users x 1 ad  x $0.005 = $5/day
Banner:       1000 users x 5 imp x $0.001 = $5/day
--------------------------------------------------
TOTAL:                                      $40/day
```

**Per bulan**: $40 x 30 = **$1,200/month** (≈ Rp 18,000,000)

**Per tahun**: $1,200 x 12 = **$14,400/year** (≈ Rp 216,000,000)

⚠️ **Note**: Angka ini adalah estimasi. Actual revenue tergantung:
- Geography (negara pengguna)
- Ad fill rate (ketersediaan ads)
- CTR (click-through rate)
- User engagement
- Seasonal trends

---

## 🔍 TROUBLESHOOTING

### Ads Tidak Muncul?

**1. Masih menggunakan Test IDs?**
- Periksa `AndroidManifest.xml` dan `AdsManager.java`
- Ganti dengan Production IDs

**2. google-services.json tidak ada?**
- Download dari Firebase Console
- Letakkan di `android/app/google-services.json`
- Rebuild project

**3. AdMob App belum disetup?**
- Pastikan app sudah didaftarkan di admob.google.com
- Link dengan Firebase project
- App ID sudah benar di manifest

**4. Permissions kurang?**
- Periksa `AndroidManifest.xml` ada INTERNET permission
- Periksa device terkoneksi internet

**5. App belum di-publish?**
- Production ads hanya muncul setelah app di Play Store
- Gunakan test IDs untuk development

### Penghasilan Rendah?

**1. Fill Rate Rendah (<50%)**
- Enable more ad networks via AdMob Mediation
- Check geographic targeting
- Wait for ad inventory to build up (1-2 minggu)

**2. CTR Rendah**
- Improve ad placement (natural breaks)
- Jangan spam ads
- Optimize reward messaging

**3. eCPM Rendah**
- Most users dari low-value countries?
- Optimize ad formats mix
- Try AdMob Bidding

### Account Disabled?

⚠️ **Policy Violations** - Jangan:
- Klik ads sendiri
- Minta user klik ads
- Tampilkan ads saat app di background
- Generate invalid traffic

**Jika disabled**:
1. Read email dari Google
2. Appeal via AdMob Console
3. Fix issues
4. Wait for review (bisa 1-4 minggu)

---

## 📚 RESOURCES

### Documentation
- **AdMob Guide**: https://support.google.com/admob
- **AdMob Android SDK**: https://developers.google.com/admob/android/quick-start
- **AdMob Policies**: https://support.google.com/admob/answer/6128543

### Community
- **Stack Overflow**: [google-mobile-ads] tag
- **Reddit**: r/androiddev, r/admob
- **Discord**: Google Developer Community

### Tools
- **AdMob Dashboard**: https://admob.google.com
- **Firebase Console**: https://console.firebase.google.com
- **Play Console**: https://play.google.com/console

---

## ✅ CHECKLIST BEFORE PRODUCTION

- [ ] AdMob account created and verified
- [ ] App registered in AdMob with correct package name
- [ ] 3 Ad Units created (Rewarded, Interstitial, Banner)
- [ ] Production Ad Unit IDs replaced in `AndroidManifest.xml`
- [ ] Production Ad Unit IDs replaced in `AdsManager.java`
- [ ] Firebase project created
- [ ] `google-services.json` downloaded and placed in `android/app/`
- [ ] AdMob linked to Firebase
- [ ] Release APK signed with keystore
- [ ] Play Store listing completed (screenshots, description, etc.)
- [ ] App submitted to Play Store
- [ ] Payment info added to AdMob for receiving money

---

## 🎉 SELAMAT!

Setelah semua langkah di atas, aplikasi Anda siap menghasilkan uang dari iklan!

**Next Steps**:
1. Monitor AdMob dashboard daily
2. Analyze user behavior
3. A/B test ad placements
4. Add more game features
5. Marketing untuk increase DAU

**Good luck! 🚀💰**
