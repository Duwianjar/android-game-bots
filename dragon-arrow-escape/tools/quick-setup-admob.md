# 🚀 QUICK SETUP ADMOB (15 MENIT)

## Panduan singkat untuk mulai menghasilkan uang dari iklan

---

## 📱 STEP 1: Buat AdMob Account (5 menit)

### A. Sign Up
1. Buka: https://admob.google.com
2. Klik "**Get Started**"
3. Login dengan **Google Account** kamu
4. Setuju dengan Terms & Conditions
5. Isi informasi bisnis (boleh isi basic dulu)

### B. Add Your First App
1. Di dashboard, klik "**Apps**" → "**ADD APP**"
2. Pilih:
   - ☑️ **Is your app published?** → NO (kalau belum di Play Store)
   - **App name**: `Dragon Arrow Escape`
   - **Platform**: Android
3. Klik "**ADD**"

### C. Simpan App ID
```
Setelah dibuat, kamu akan dapat App ID:

Format: ca-app-pub-1234567890123456~9876543210
              ^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^
              Publisher ID       App ID

⚠️ SIMPAN INI! Kamu butuh untuk step berikutnya!
```

---

## 🎯 STEP 2: Buat Ad Units (8 menit)

Kamu perlu 3 jenis iklan:

### A. Rewarded Ad (💰 Revenue tertinggi)
```
1. Klik app "Dragon Arrow Escape"
2. Klik "Ad units" → "ADD AD UNIT"
3. Pilih "Rewarded"
4. Settings:
   - Ad unit name: Dragon Rewarded Bonus
   - Advanced settings: (biarkan default)
5. Klik "CREATE AD UNIT"
6. SIMPAN Ad Unit ID yang muncul!
   Format: ca-app-pub-1234567890123456/1111111111
```

### B. Interstitial Ad (💰 Revenue sedang)
```
1. Klik "ADD AD UNIT" lagi
2. Pilih "Interstitial"
3. Settings:
   - Ad unit name: Dragon Interstitial Level
4. Klik "CREATE AD UNIT"
5. SIMPAN Ad Unit ID!
   Format: ca-app-pub-1234567890123456/2222222222
```

### C. Banner Ad (💰 Revenue konsisten)
```
1. Klik "ADD AD UNIT" lagi
2. Pilih "Banner"
3. Settings:
   - Ad unit name: Dragon Banner Menu
4. Klik "CREATE AD UNIT"
5. SIMPAN Ad Unit ID!
   Format: ca-app-pub-1234567890123456/3333333333
```

---

## 📝 STEP 3: Update Kode (2 menit)

### A. Update AndroidManifest.xml

**File:** `android/app/src/main/AndroidManifest.xml`  
**Line:** ~40

```xml
<!-- GANTI INI -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-3940256099942544~3347511713" />

<!-- DENGAN App ID dari Step 1 -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-1234567890123456~9876543210" />
    <!--            ^^^^^^^^^^^^^^^^^^^^ GANTI INI! -->
```

### B. Update AdsManager.java

**File:** `android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java`

**Line 42 - Rewarded Ad:**
```java
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-1234567890123456/1111111111";
//                                                 ^^^^^^^^^^^^^^^^^^^^ GANTI INI!
```

**Line 46 - Interstitial Ad:**
```java
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-1234567890123456/2222222222";
//                                                      ^^^^^^^^^^^^^^^^^^^^ GANTI INI!
```

**Line 50 - Banner Ad:**
```java
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-1234567890123456/3333333333";
//                                               ^^^^^^^^^^^^^^^^^^^^ GANTI INI!
```

---

## ✅ STEP 4: Verify & Build

### A. Verify Configuration
```bash
cd /Users/macbookair/android-game-bots/dragon-arrow-escape
./tools/verify-ads-config.sh
```

Harus semua ✅ (tidak ada ❌ ERROR)

### B. Build APK
```bash
./tools/build-production.sh
```

### C. Test di Device
```bash
cd android
adb install -r app/build/outputs/apk/release/app-release-unsigned.apk
```

---

## 🔍 VERIFY IKLAN BERFUNGSI

### Di Device:
1. Buka app
2. Main game sampai Game Over
3. Klik "Tonton Iklan & Dapatkan Bonus"
4. **Iklan HARUS muncul!**

### Di Logcat:
```bash
adb logcat | grep -i "ads\|admob"
```

Harus muncul:
```
✅ Google Mobile Ads SDK initialized
✅ Rewarded Ad Loaded Successfully
✅ Interstitial Ad Loaded Successfully
✅ Banner ad loaded
```

Jika muncul ini = **MASIH TEST ID:**
```
⚠️ WARNING: USING TEST AD IDs - NO REAL REVENUE!
```

---

## 💰 KAPAN MULAI DAPAT UANG?

### Timeline:
- **Day 0**: Setup AdMob + ganti IDs → Build APK
- **Day 1**: Upload ke Play Store (Internal Testing)
- **Day 3-7**: Google review app
- **Day 7**: App approved → Mulai dapat impressions
- **Day 8**: Revenue pertama muncul di dashboard!
- **Day 30+**: Dapat payment pertama (min $100)

### First Month Estimate:
```
Conservative (100 active users):
- 50 rewarded ads/day × $0.015 = $0.75/day
- 80 interstitial ads/day × $0.005 = $0.40/day
- 200 banner impressions/day × $0.001 = $0.20/day
----------------------------------------
Total: ~$1.35/day = $40/month

Optimistic (1000 active users):
- 500 rewarded ads/day × $0.020 = $10/day
- 800 interstitial ads/day × $0.006 = $4.80/day
- 2000 banner impressions/day × $0.0015 = $3/day
----------------------------------------
Total: ~$18/day = $540/month
```

---

## 🚨 COMMON ISSUES

### "Iklan tidak muncul"
```
Cause: Test IDs masih terpakai
Fix: Ganti semua 4 IDs (1 App ID + 3 Ad Unit IDs)

Cause: Internet connection
Fix: Check WiFi/Data

Cause: AdMob belum approve app
Fix: Tunggu 24-48 jam setelah setup
```

### "Revenue masih $0"
```
Cause: Baru setup
Fix: Tunggu 24-48 jam untuk data processing

Cause: Impressions rendah
Fix: Promote app, increase user count

Cause: Fill rate rendah
Fix: Add mediation networks (Facebook, Unity Ads)
```

---

## 📊 MONITOR REVENUE

### Daily Check:
1. AdMob Dashboard: https://admob.google.com
2. Check metrics:
   - Impressions (berapa kali iklan muncul)
   - Clicks (berapa kali user klik)
   - Revenue (total earning)
   - Fill Rate (% request yang diisi ads)

### Weekly Optimization:
- Jika fill rate < 90% → add mediation
- Jika CTR < 1% → improve ad placement
- Jika eCPM < $5 → test different ad formats

---

## 🎯 CHECKLIST

Sebelum publish:
```
☐ AdMob account created
☐ 3 Ad Units created (Rewarded, Interstitial, Banner)
☐ AndroidManifest.xml updated (App ID)
☐ AdsManager.java updated (3 Ad Unit IDs)
☐ Verification script passed (no ❌ errors)
☐ APK built successfully
☐ Tested on real device
☐ Ads loading and showing
☐ No TEST ID warnings in logcat
☐ Ready to upload Play Store!
```

---

**🚀 KAMU SIAP MULAI MENGHASILKAN UANG!**

Next: Upload ke Google Play Console dan tunggu approval!
