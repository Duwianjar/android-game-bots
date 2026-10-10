# 🚀 PANDUAN: Mulai Menghasilkan Uang dari Game Android

**Dragon Arrow Escape - Monetization Setup**  
Tanggal: 11 Oktober 2026  
Status: **SIAP PRODUCTION** ✅

---

## 📊 STATUS IMPLEMENTASI

### ✅ SUDAH SELESAI (100%)

#### 1. **Kode Monetisasi Lengkap**
- ✅ AdsManager.java - Kelola Rewarded, Interstitial, Banner ads
- ✅ AdRevenueTracker.java - Tracking performa iklan
- ✅ AdMonetizationHelper.java - Verifikasi & troubleshooting
- ✅ MainActivity.java - JavaScript bridge untuk HTML5 game
- ✅ android-ads-bridge.js - Interface JavaScript
- ✅ Game HTML5 terintegrasi penuh dengan sistem iklan

#### 2. **Fitur Monetisasi Aktif**
- ✅ **Rewarded Ads** - Bonus coins, continue game, unlock items
  - RPM: $10-$30 per 1000 views
  - Auto-retry on failure
  - Reward callback ke game
  
- ✅ **Interstitial Ads** - Transisi level, menu
  - RPM: $3-$8 per 1000 views  
  - Cooldown otomatis 3 menit
  - Non-intrusive
  
- ✅ **Banner Ads** - Menu utama, shop, leaderboard
  - RPM: $0.5-$2 per 1000 impressions
  - Auto show/hide berdasarkan game state

#### 3. **Analytics & Tracking**
- ✅ Session tracking
- ✅ Impression counting
- ✅ Revenue estimation
- ✅ Performance metrics
- ✅ JSON export untuk analytics

---

## ❌ MASALAH KRITIS - HARUS DIPERBAIKI!

### 🚨 Masih Menggunakan TEST Ad IDs

**File:** `android/app/src/main/AndroidManifest.xml`
```xml
<!-- MASIH TEST ID ❌ -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-3940256099942544~3347511713" />
```

**File:** `AdsManager.java`
```java
// MASIH TEST IDs ❌
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917";
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712";
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/6300978111";
```

### ⚠️ DAMPAK:
- **TIDAK MENGHASILKAN UANG NYATA** 💰❌
- Iklan tetap muncul tapi AdMob tidak bayar
- Revenue reports akan $0.00
- Semua impressions tidak terhitung

---

## 🎯 LANGKAH-LANGKAH MULAI MENGHASILKAN UANG

### **STEP 1: Daftar AdMob Account** (15 menit)

1. **Buka:** https://admob.google.com
2. **Login** dengan Google Account
3. **Accept Terms & Conditions**
4. **Pilih negara & currency** (IDR untuk Indonesia)
5. **Verifikasi email** jika diminta

### **STEP 2: Daftarkan Aplikasi** (10 menit)

1. **Klik "Apps"** di menu kiri
2. **Klik "Add App"**
3. **Pilih "Android"**
4. **App name:** `Dragon Arrow Escape`
5. **Package name:** `com.dragonarrowescape.game`
6. **Submit**

📝 **Catat App ID** yang diberikan:
```
Format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY
```

### **STEP 3: Buat Ad Units** (15 menit)

Buat 3 jenis Ad Units:

#### 3.1. Rewarded Ad Unit
1. **Apps** > **Dragon Arrow Escape** > **Ad units**
2. **Create ad unit** > **Rewarded**
3. **Ad unit name:** `Rewarded - Bonus Coins`
4. **Create**
5. **Catat Rewarded Ad Unit ID**

#### 3.2. Interstitial Ad Unit
1. **Create ad unit** > **Interstitial**
2. **Ad unit name:** `Interstitial - Level Complete`
3. **Create**
4. **Catat Interstitial Ad Unit ID**

#### 3.3. Banner Ad Unit
1. **Create ad unit** > **Banner**
2. **Ad unit name:** `Banner - Menu`
3. **Banner size:** `320x50 (Standard)`
4. **Create**
5. **Catat Banner Ad Unit ID**

### **STEP 4: Setup Production IDs** (5 menit)

Jalankan script otomatis yang sudah saya buat:

```bash
cd /Users/macbookair/android-game-bots/dragon-arrow-escape
python3 setup_production_ids.py
```

Script akan:
- ✅ Minta input 4 Production IDs
- ✅ Validasi format IDs
- ✅ Backup file otomatis
- ✅ Update AndroidManifest.xml
- ✅ Update AdsManager.java
- ✅ Verifikasi tidak ada TEST IDs tersisa

**ATAU Manual Edit:**

1. Edit `android/app/src/main/AndroidManifest.xml`:
```xml
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="PASTE_APP_ID_DISINI" />
```

2. Edit `AdsManager.java`:
```java
private static final String REWARDED_AD_UNIT_ID = "PASTE_REWARDED_ID_DISINI";
private static final String INTERSTITIAL_AD_UNIT_ID = "PASTE_INTERSTITIAL_ID_DISINI";
private static final String BANNER_AD_UNIT_ID = "PASTE_BANNER_ID_DISINI";
```

### **STEP 5: Build Release APK** (10 menit)

```bash
cd android
./gradlew clean
./gradlew assembleRelease
```

APK output:
```
android/app/build/outputs/apk/release/app-release-unsigned.apk
```

### **STEP 6: Sign APK** (5 menit)

Gunakan Android Studio atau command line:

```bash
# Generate keystore (pertama kali)
keytool -genkey -v -keystore dragon-arrow-escape.keystore \
  -alias dragonarrow -keyalg RSA -keysize 2048 -validity 10000

# Sign APK
jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 \
  -keystore dragon-arrow-escape.keystore \
  app-release-unsigned.apk dragonarrow

# Zipalign
zipalign -v 4 app-release-unsigned.apk dragon-arrow-escape-release.apk
```

### **STEP 7: Upload ke Google Play** (30 menit)

1. **Buka:** https://play.google.com/console
2. **Create app** > **Dragon Arrow Escape**
3. **Upload APK** ke Internal Testing atau Production
4. **Isi Store Listing:**
   - Title: Dragon Arrow Escape
   - Short description: Endless runner game dengan naga
   - Full description: (lihat template di bawah)
   - Screenshots: gunakan yang sudah ada di folder project
   - Icon: buat 512x512 icon
5. **Content rating questionnaire**
6. **Pricing:** Free
7. **Submit for review**

### **STEP 8: Wait & Monitor** (1-3 hari)

1. **Google Play Review:** biasanya 1-3 hari
2. **AdMob Verification:** otomatis setelah app live
3. **Monitor Dashboard:** https://admob.google.com

---

## 💰 ESTIMASI REVENUE

### Perhitungan Konservatif

**Asumsi:**
- 100 daily active users (DAU)
- 5 game sessions per user per day
- 50% user nonton rewarded ads
- 80% completion rate interstitial ads

**Per Day:**
- Rewarded: 250 views × $10 CPM = **$2.50/day**
- Interstitial: 400 views × $3 CPM = **$1.20/day**
- Banner: 500 impressions × $0.50 CPM = **$0.25/day**

**Total:** **~$4/day** atau **$120/bulan**

### Optimistic Scenario (1000 DAU)
- **$40/day** atau **$1,200/bulan**

### Growth Potential (10,000 DAU)
- **$400/day** atau **$12,000/bulan**

---

## 📱 CARA TESTING SEBELUM PRODUCTION

### Test dengan Test IDs (Current)
```bash
cd android
./gradlew installDebug
adb logcat | grep -i "admob\|ads\|revenue"
```

Cek log untuk:
- ✅ "Rewarded Ad Loaded Successfully"
- ✅ "Interstitial Ad Loaded Successfully"  
- ✅ "Banner ad loaded"
- ✅ "User earned reward"

### Test Production IDs (Setelah Setup)

⚠️ **JANGAN terlalu sering klik iklan sendiri!**
- AdMob bisa ban account
- Gunakan **Test Devices** untuk development

**Enable Test Device:**
1. Run app, cek logcat untuk device ID
2. Tambahkan di AdsManager.java:
```java
AdRequest adRequest = new AdRequest.Builder()
    .addTestDevice("YOUR_DEVICE_ID_HERE")
    .build();
```

---

## 🎮 GAME MECHANICS - MONETIZATION INTEGRATION

### Sudah Terintegrasi:

#### 1. **Game Over Screen**
```javascript
// User bisa nonton iklan untuk continue
if (AndroidAds.isRewardedAdReady()) {
  showButton("Continue - Tonton Iklan");
}
```

#### 2. **Level Complete**
```javascript
// Interstitial setiap 3 level
if (level % 3 === 0) {
  AndroidAds.showInterstitialAd();
}
```

#### 3. **Bonus Coins**
```javascript
// Double coins dengan nonton iklan
AndroidAds.showRewardedAd((type, amount) => {
  coins += amount;
});
```

---

## 🔧 TROUBLESHOOTING

### Iklan Tidak Muncul

**1. Check Logcat:**
```bash
adb logcat | grep -E "AdsManager|AdMob"
```

**2. Common Issues:**
- ❌ App ID salah → check AndroidManifest.xml
- ❌ Ad Unit ID salah → check AdsManager.java
- ❌ Internet off → enable WiFi/data
- ❌ Cooldown aktif → wait 3 menit untuk interstitial

### Revenue Masih $0

**1. Verifikasi Production IDs:**
```bash
grep -r "3940256099942544" android/
```
Jika ada hasil, berarti masih TEST IDs!

**2. Check AdMob Dashboard:**
- Requests > 0? ✅ Ads loading
- Impressions > 0? ✅ Ads showing
- Estimated earnings > 0? ✅ Revenue aktif

**3. Timing:**
- Revenue update: **setiap 24 jam**
- Payment: **setiap bulan** (min $100)

---

## 📞 SUPPORT & NEXT STEPS

### Dokumentasi Lengkap:
- `PRODUCTION_SETUP.md` - Setup detail
- `CARA_PRODUCTION_ADMOB.md` - AdMob configuration
- `STATUS_MONETIZATION_READY.md` - Status teknis

### Build Scripts:
- `setup_production_ids.py` - Setup IDs otomatis ✅
- `verify_production.sh` - Verifikasi configuration
- `build-release.sh` - Build APK

### Monitoring:
- AdMob Dashboard: https://admob.google.com
- Play Console: https://play.google.com/console

---

## ✅ CHECKLIST FINAL

**Sebelum Submit:**
- [ ] Production IDs sudah disetup
- [ ] No TEST IDs found (verify dengan grep)
- [ ] APK signed dengan production keystore
- [ ] Test di real device
- [ ] Screenshots & icon ready
- [ ] Store listing complete

**Setelah Submit:**
- [ ] Monitor review status
- [ ] Check AdMob verification
- [ ] Set up payment info di AdMob
- [ ] Monitor revenue daily
- [ ] Optimize based on metrics

---

## 🎉 SELAMAT!

Kode monetisasi sudah **100% SIAP**.  
Tinggal **ganti IDs ke Production** dan **upload ke Play Store**.

**Estimasi waktu total: 2 jam**  
**Potential revenue: $4-40/day** tergantung user base

**Good luck! 🚀💰**
