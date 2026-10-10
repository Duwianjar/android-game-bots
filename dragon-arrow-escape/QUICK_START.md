# 🚀 Quick Start - AdMob Monetization

## ⚠️ STATUS: TEST MODE (Tidak Menghasilkan Uang)

Aplikasi saat ini menggunakan **TEST AD IDs**. Iklan akan muncul, tapi **TIDAK menghasilkan pendapatan real**.

---

## ✅ Yang Sudah Dikonfigurasi

✓ Kode AdMob SDK terintegrasi (MainActivity.java, AdsManager.java)
✓ 3 jenis ads: Rewarded, Interstitial, Banner
✓ JavaScript bridge untuk komunikasi WebView ↔ Native
✓ Permissions di AndroidManifest.xml
✓ Network security config
✓ Auto-retry & error handling

---

## 🔥 Masalah yang Perlu Diperbaiki

### 1. **google-services.json TIDAK ADA** ❌

**Problem**: File ini WAJIB untuk AdMob, tapi belum dibuat.

**Solusi**:
1. Buka https://console.firebase.google.com
2. Create project baru: `dragon-arrow-escape`
3. Add Android App dengan package: `com.dragonarrowescape.game`
4. Download `google-services.json`
5. Copy ke: `android/app/google-services.json`

**Template tersedia**: `android/app/google-services.json.template` (ganti dengan file asli)

### 2. **Gradle Wrapper Hilang** ❌

**Problem**: `gradlew` tidak ada, tidak bisa build project.

**Solusi**:
```bash
cd android
gradle wrapper --gradle-version 8.1.2
chmod +x gradlew
```

### 3. **AdMob App ID Masih TEST** ⚠️

**Location**: `android/app/src/main/AndroidManifest.xml` (baris 41)

**Current (TEST)**:
```xml
android:value="ca-app-pub-3940256099942544~3347511713"
```

**Ganti dengan Production ID** dari https://admob.google.com setelah:
1. Daftar AdMob account
2. Create app "Dragon Arrow Escape"
3. Get App ID: `ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY`

### 4. **Ad Unit IDs Masih TEST** ⚠️

**Location**: `android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java`

**Baris 39-45**:
```java
// Ganti ketiga ID ini dengan Production Ad Unit IDs
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917"; // TEST
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712"; // TEST
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/6300978111"; // TEST
```

**Ganti dengan** Production Ad Unit IDs dari AdMob Console:
1. Create 3 ad units di AdMob (Rewarded, Interstitial, Banner)
2. Copy masing-masing Ad Unit ID
3. Paste ke AdsManager.java

---

## 📝 Langkah Singkat ke Production

### Step 1: Setup Firebase (5 menit)
```bash
# 1. Buat Firebase project
https://console.firebase.google.com

# 2. Add Android app: com.dragonarrowescape.game
# 3. Download google-services.json → android/app/
```

### Step 2: Setup AdMob (10 menit)
```bash
# 1. Daftar AdMob
https://admob.google.com

# 2. Create App "Dragon Arrow Escape"
#    Package: com.dragonarrowescape.game

# 3. Create 3 Ad Units:
#    - Rewarded Video
#    - Interstitial
#    - Banner

# 4. Catat semua IDs (App ID + 3 Ad Unit IDs)
```

### Step 3: Update Kode (5 menit)
```bash
# Edit AndroidManifest.xml → ganti App ID
# Edit AdsManager.java → ganti 3 Ad Unit IDs
```

### Step 4: Build & Test (10 menit)
```bash
cd android
gradle wrapper --gradle-version 8.1.2
./gradlew assembleDebug

# Install ke device/emulator
adb install app/build/outputs/apk/debug/app-debug.apk

# Test iklan muncul
```

### Step 5: Build Release & Publish (30 menit)
```bash
# Generate keystore
keytool -genkey -v -keystore release.keystore \
  -alias dragon-arrow-escape -keyalg RSA -keysize 2048 -validity 10000

# Build release APK
./gradlew assembleRelease

# Sign APK
jarsigner -keystore release.keystore \
  app/build/outputs/apk/release/app-release-unsigned.apk \
  dragon-arrow-escape

# Upload ke Play Console
https://play.google.com/console
```

---

## 💰 Proyeksi Pendapatan

### Asumsi: 1000 Daily Active Users

| Metric | Value | Earnings |
|--------|-------|----------|
| **Rewarded Ads** | 2/user/day | $30/day |
| **Interstitial Ads** | 1/user/day | $5/day |
| **Banner Ads** | 5 impressions/user | $5/day |
| **TOTAL** | - | **$40/day** |

**Per bulan**: $1,200 (~ Rp 18 juta)  
**Per tahun**: $14,400 (~ Rp 216 juta)

### Strategi Optimasi

**Maximize Rewarded Ads** (highest RPM: $10-30):
- Tawari bonus poin jelas: "+500 poin"
- Tawari continue game setelah game over
- Unlock premium items/skins
- Target: 2-3 rewarded ads per session

**Smart Interstitial Timing**:
- Cooldown 3 menit (sudah di-set)
- Hanya di natural break (selesai level)
- JANGAN spam atau interrupt gameplay
- Target: 1-2 interstitial per session

**Banner Placement**:
- Hanya di menu/pause screen
- Hide saat gameplay
- Bottom atau top screen
- Auto-refresh by AdMob

---

## 🔍 Troubleshooting

### Ads tidak muncul?
```
1. Cek google-services.json sudah di android/app/
2. Cek AndroidManifest.xml sudah update App ID
3. Cek AdsManager.java sudah update Ad Unit IDs
4. Cek internet connection
5. Cek logcat: adb logcat | grep -i "admob\|ads"
```

### Build error?
```
1. Cek gradlew ada: gradle wrapper
2. Cek google-services.json ada
3. Clean build: ./gradlew clean
4. Sync dependencies: ./gradlew build --refresh-dependencies
```

### Ads error di runtime?
```
1. Cek logcat untuk error messages
2. Verify App ID match di AdMob & manifest
3. Verify Ad Unit IDs match di AdMob & AdsManager.java
4. Pastikan AdMob account active (tidak suspended)
```

### Revenue rendah?
```
1. Wait 1-2 minggu untuk ad inventory build up
2. Enable AdMob Mediation untuk fill rate
3. Target high-value countries (US, EU)
4. Optimize ad placement (A/B testing)
5. Increase DAU dengan marketing
```

---

## 📚 Resources

**Essential Links**:
- AdMob Console: https://admob.google.com
- Firebase Console: https://console.firebase.google.com
- Play Console: https://play.google.com/console
- AdMob Policies: https://support.google.com/admob/answer/6128543

**Documentation**:
- Full Setup Guide: `SETUP_ADMOB.md` (detail lengkap)
- Monetization Docs: `android/MONETIZATION_SETUP.md`

**Support**:
- Stack Overflow: [google-mobile-ads] tag
- AdMob Help: https://support.google.com/admob

---

## ✅ Pre-Launch Checklist

**Configuration**:
- [ ] `google-services.json` ada di `android/app/`
- [ ] AdMob App ID updated di `AndroidManifest.xml`
- [ ] 3 Ad Unit IDs updated di `AdsManager.java`
- [ ] Gradle wrapper installed (`gradlew` exists)

**Testing**:
- [ ] Build debug APK berhasil
- [ ] Install di device berhasil
- [ ] Rewarded ad muncul saat "Tonton Iklan"
- [ ] Interstitial ad muncul setelah game over
- [ ] Banner ad muncul di menu (optional)

**Production**:
- [ ] Keystore generated dan disimpan aman
- [ ] Release APK signed
- [ ] Play Store listing lengkap (screenshots, description)
- [ ] Content rating completed
- [ ] Privacy policy URL (jika perlu)

**Monetization**:
- [ ] AdMob account verified
- [ ] Payment info added di AdMob
- [ ] Firebase ↔ AdMob linked
- [ ] Ad units created dan active

---

## 🚀 Ready to Launch!

Setelah semua checklist ✅, aplikasi siap:
1. Generate revenue dari ads
2. Scale dengan marketing
3. Monitor di AdMob dashboard
4. Optimize berdasarkan data

**Target**: $100/day dengan 2500 DAU → $36K/year! 💰

Good luck! 🎮🔥
