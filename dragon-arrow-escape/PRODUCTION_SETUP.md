# 🚀 PRODUCTION SETUP - Dragon Arrow Escape

## ⚠️ PENTING: Agar Game MENGHASILKAN UANG

Saat ini aplikasi masih menggunakan **TEST AD IDs** yang **TIDAK menghasilkan uang nyata!**

Untuk mendapatkan revenue dari iklan, Anda HARUS:
1. ✅ Daftar akun AdMob
2. ✅ Daftarkan aplikasi ke AdMob
3. ✅ Dapatkan Production Ad Unit IDs
4. ✅ Ganti semua TEST IDs dengan Production IDs
5. ✅ Build dan publish ke Google Play Store

---

## 📋 CHECKLIST PRODUCTION

### Step 1: Daftar AdMob (15 menit)

1. **Buka AdMob Console**
   - URL: https://admob.google.com
   - Login dengan akun Google Anda
   - Setujui Terms of Service

2. **Buat Akun AdMob**
   - Pilih negara: Indonesia
   - Timezone: GMT+7 (Jakarta)
   - Currency: USD (recommended) atau IDR
   - Isi informasi pajak (akan diminta saat withdrawal pertama)

### Step 2: Daftarkan Aplikasi (10 menit)

1. **Klik "Apps" → "Add App"**
   - Pilih: "No" (aplikasi belum di Play Store)
   - Platform: **Android**
   - App name: **Dragon Arrow Escape**
   - Pilih kategori: **Games - Arcade**

2. **Dapatkan App ID**
   - Format: `ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY`
   - **COPY ID ini untuk Step 3**

### Step 3: Buat Ad Units (15 menit)

Buat 3 Ad Units untuk monetisasi optimal:

#### 3.1 Rewarded Ad (RPM tertinggi: $10-$30)

1. Klik "Ad units" → "Add ad unit" → **Rewarded**
2. Settings:
   - Name: `Dragon Arrow Rewarded`
   - Reward amount: `1`
   - Reward item: `coin`
3. **COPY Rewarded Ad Unit ID** → Format: `ca-app-pub-XXXXXXXXXXXXXXXX/1234567890`

**Gunakan untuk:**
- Continue game setelah game over
- Bonus coins (2x coins)
- Unlock premium items/skins
- Hints atau power-ups

#### 3.2 Interstitial Ad (RPM sedang: $3-$8)

1. Klik "Ad units" → "Add ad unit" → **Interstitial**
2. Settings:
   - Name: `Dragon Arrow Interstitial`
   - Type: `Full-screen`
3. **COPY Interstitial Ad Unit ID**

**Gunakan untuk:**
- Setelah complete level (setiap 2-3 level)
- Transisi menu → gameplay
- Cooldown otomatis: 3 menit (sudah di kode)

#### 3.3 Banner Ad (RPM rendah: $0.5-$2)

1. Klik "Ad units" → "Add ad unit" → **Banner**
2. Settings:
   - Name: `Dragon Arrow Banner`
   - Size: `320x50` (Standard Banner)
3. **COPY Banner Ad Unit ID**

**Gunakan untuk:**
- Menu utama
- Leaderboard
- Shop/Store
- **JANGAN tampilkan saat gameplay** (sudah dihandle di kode)

---

## 🔧 Step 4: Ganti TEST IDs dengan PRODUCTION IDs

### File 1: `AndroidManifest.xml`

Lokasi: `android/app/src/main/AndroidManifest.xml`

```xml
<!-- GANTI BARIS INI (line 40-41): -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-3940256099942544~3347511713" /> <!-- TEST ID -->

<!-- DENGAN App ID yang Anda dapatkan dari Step 2: -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY" /> <!-- PRODUCTION ID -->
```

### File 2: `AdsManager.java`

Lokasi: `android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java`

```java
// GANTI BARIS 39-45:

// BEFORE (TEST IDs):
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917";
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712";
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/6300978111";

// AFTER (PRODUCTION IDs dari Step 3):
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/1111111111";
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/2222222222";
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/3333333333";
```

---

## 🏗️ Step 5: Build Production APK

### 5.1 Generate Signing Key (SATU KALI SAJA)

```bash
cd /Users/macbookair/android-game-bots/dragon-arrow-escape/android

# Buat keystore (SIMPAN PASSWORD dengan AMAN!)
keytool -genkey -v -keystore dragon-arrow-release.keystore \
  -alias dragon-arrow -keyalg RSA -keysize 2048 -validity 10000

# Isi informasi:
# - Password: [pilih password kuat dan CATAT!]
# - First and last name: [nama Anda]
# - Organization: [nama perusahaan/pribadi]
# - Country code: ID
```

⚠️ **PENTING:** Simpan file `.keystore` dan password di tempat AMAN! 
Jika hilang, Anda TIDAK bisa update aplikasi di Play Store!

### 5.2 Configure Gradle Signing

Edit `android/app/build.gradle`:

```gradle
android {
    // ... existing config ...
    
    signingConfigs {
        release {
            storeFile file('../dragon-arrow-release.keystore')
            storePassword 'YOUR_KEYSTORE_PASSWORD'
            keyAlias 'dragon-arrow'
            keyPassword 'YOUR_KEY_PASSWORD'
        }
    }
    
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```

### 5.3 Build APK

```bash
cd /Users/macbookair/android-game-bots/dragon-arrow-escape/android

# Clean build
./gradlew clean

# Build release APK
./gradlew assembleRelease

# APK akan ada di:
# app/build/outputs/apk/release/app-release.apk
```

---

## 📱 Step 6: Test di Device Real

⚠️ **JANGAN test production ads dengan sering!** Bisa kena ban dari AdMob!

### Test Mode untuk Development:

Tambahkan test device ID di `AdsManager.java`:

```java
// Di method loadRewardedAd(), line 86:
AdRequest adRequest = new AdRequest.Builder()
    .addTestDevice("YOUR_DEVICE_ID_HERE")  // Tambahkan ini
    .build();
```

Cara dapatkan device ID:
```bash
adb logcat | grep "Test device ID"
```

### Test Checklist:

- [ ] Rewarded ad muncul saat klik "Watch Ad"
- [ ] Reward diterima setelah nonton ad selesai
- [ ] Interstitial ad muncul setiap 2-3 level
- [ ] Interstitial ada cooldown 3 menit
- [ ] Banner muncul di menu, hidden saat gameplay
- [ ] Tidak ada crash saat show/close ads
- [ ] Game lancar setelah ads ditutup

---

## 🚀 Step 7: Publish ke Google Play Store

### 7.1 Persiapan Asset

Siapkan:
- **App Icon** (512x512 PNG)
- **Feature Graphic** (1024x500 PNG)
- **Screenshots** (minimal 2, maksimal 8)
  - Phone: 1080x1920 atau 1080x2340
- **Short Description** (max 80 karakter)
- **Full Description** (max 4000 karakter)
- **Privacy Policy URL** (WAJIB jika ada ads!)

### 7.2 Buat Akun Play Console

1. URL: https://play.google.com/console
2. One-time fee: $25 USD
3. Isi profil developer

### 7.3 Create App

1. Klik "Create app"
2. Pilih:
   - App name: **Dragon Arrow Escape**
   - Default language: Indonesian
   - Type: **Game**
   - Category: **Arcade**
   - Free or paid: **Free**

### 7.4 Upload APK

1. Go to: **Production** → **Create new release**
2. Upload: `app-release.apk`
3. Version code akan auto-increment
4. Release notes: "Initial release"

### 7.5 Content Rating

1. Questionnaire:
   - Violence: None
   - Sexual content: None
   - Profanity: None
   - Drugs/tobacco: None
   - Result: **PEGI 3 / Everyone**

### 7.6 Target Audience

- Age range: **All ages**
- Ads present: **Yes** ✓
- Made for kids: **No** (karena ada ads)

### 7.7 Privacy Policy

Minimal privacy policy:

```
Dragon Arrow Escape - Privacy Policy

We use Google AdMob to display advertisements.
AdMob may collect device identifiers and location data for ad personalization.

For more info: https://policies.google.com/privacy
```

Host di: GitHub Pages / Google Sites / website Anda

### 7.8 Review & Publish

1. Complete all sections (marked with ✓)
2. Submit for review
3. Review time: **1-7 hari**
4. Anda akan dapat email saat approved

---

## 💰 Step 8: Monetization Strategy

### Optimal Ad Frequency:

#### Rewarded Ads (User-Triggered)
- ✅ **Tidak ada limit** - user yang minta
- ✅ Best revenue per view
- Placement:
  - Continue after game over
  - 2x coins reward
  - Unlock premium items
  - Bonus lives/power-ups

#### Interstitial Ads (Auto)
- ⚠️ **Cooldown 3 menit** (sudah di kode)
- ⚠️ Jangan terlalu sering = user uninstall
- Placement:
  - Every 2-3 levels (sudah optimal)
  - Menu → Gameplay transition
  - After 5 minutes gameplay

#### Banner Ads (Always-On di Menu)
- ✅ Low revenue per view
- ✅ Cumulative revenue tinggi
- Show:
  - Main menu
  - Leaderboard
  - Shop
- Hide:
  - During gameplay (PENTING!)

### Revenue Estimation (Indonesia):

Asumsi:
- 1000 Daily Active Users (DAU)
- 5 minutes average session
- 3 sessions per day per user

**Conservative estimate:**
- Rewarded: 1000 users × 2 views/day × $0.015 = **$30/day**
- Interstitial: 1000 × 3 views/day × $0.008 = **$24/day**
- Banner: 1000 × 15 impressions/day × $0.0015 = **$22.5/day**

**Total: ~$76.5/day = $2,295/month** dengan 1000 DAU

Untuk 10,000 DAU: **~$22,950/month**

### Tips Meningkatkan Revenue:

1. **Optimize ad placement**
   - A/B test kapan show interstitial
   - Tambah rewarded ad opportunities

2. **Tingkatkan retention**
   - Daily rewards
   - Achievement system
   - Leaderboards

3. **Viral growth**
   - Share score ke social media
   - Referral rewards
   - Challenge friends

4. **Mediation** (advanced)
   - Tambahkan: Meta Audience Network, Unity Ads
   - AdMob mediation untuk CPM tertinggi

---

## 🔍 Step 9: Monitoring & Optimization

### AdMob Console (Daily Check)

URL: https://admob.google.com

**Key Metrics:**
- **RPM** (Revenue per 1000 impressions)
  - Target: Rewarded >$10, Interstitial >$3, Banner >$0.5
- **Fill Rate** (% ad request yang terisi)
  - Target: >95%
- **Impression Rate** (% ad yang benar-benar ditampilkan)
  - Target: >80%
- **Click-through Rate (CTR)**
  - Rewarded: 2-5%
  - Interstitial: 1-3%
  - Banner: 0.5-2%

### Google Play Console (Weekly Check)

**Key Metrics:**
- Installs (trending up?)
- Uninstalls (< 5% = good)
- Retention:
  - Day 1: target >40%
  - Day 7: target >20%
  - Day 30: target >10%
- Crash rate (< 1% = good)
- ANR rate (< 0.5% = good)

### Optimization Actions:

**Jika RPM rendah:**
- Cek fill rate (< 90% = masalah inventory)
- Enable "Optimize" di AdMob
- Tambah ad networks via mediation

**Jika retention rendah:**
- Tambah daily rewards
- Bikin tutorial lebih jelas
- Fix bugs/crashes ASAP

**Jika uninstall tinggi:**
- Kurangi frequency interstitial ads
- Fix performance issues
- Tambah konten baru

---

## ⚠️ ATURAN PENTING (Hindari Ban!)

### JANGAN:
❌ Klik ads sendiri (auto-ban!)
❌ Minta orang lain klik ads (ban!)
❌ Show ads terlalu sering (user complain)
❌ Show rewarded ad tanpa user consent
❌ Fake ad impressions (ban permanent!)
❌ Gunakan bot untuk download/klik ads

### LAKUKAN:
✅ Test dengan test devices
✅ Follow AdMob policies
✅ Buat UX yang baik
✅ Transparent tentang ads
✅ Respect user choice
✅ Monitor metrics regularly

---

## 📞 Support & Resources

### Official Docs:
- AdMob: https://developers.google.com/admob
- Play Console: https://support.google.com/googleplay/android-developer

### Troubleshooting:

**"Ad failed to load"**
- Cek internet connection
- Pastikan Ad Unit IDs benar
- Tunggu 1-2 jam setelah buat ad unit (propagation time)

**"No fill"**
- Normal untuk test mode
- Production: enable "Optimize" di AdMob
- Consider mediation

**"App rejected dari Play Store"**
- Baca rejection reason
- Fix issues
- Resubmit

**"Revenue tidak masuk"**
- Minimum payment: $100
- Payment cycle: monthly
- Setup payment method di AdMob

---

## ✅ PRODUCTION CHECKLIST FINAL

Sebelum publish, pastikan:

- [ ] Semua TEST IDs diganti dengan PRODUCTION IDs
- [ ] App ID di AndroidManifest.xml sudah production
- [ ] Build release APK dengan signing key
- [ ] Test di real device (bukan emulator)
- [ ] All ads working (rewarded, interstitial, banner)
- [ ] Privacy policy URL sudah ada
- [ ] Screenshots dan asset Play Store siap
- [ ] Content rating completed
- [ ] Target audience configured
- [ ] App reviewed dan tidak ada crash
- [ ] Version code dan version name benar
- [ ] AdMob ads.txt verified (untuk website traffic)

---

**🎉 Selamat! Game Anda siap menghasilkan uang dari iklan!**

Next steps:
1. Marketing & user acquisition
2. Regular content updates
3. Monitor metrics & optimize
4. Scale to 10k, 100k, 1M+ users

Good luck! 🚀💰
