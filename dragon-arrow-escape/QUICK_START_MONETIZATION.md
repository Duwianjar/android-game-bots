# 🚀 QUICK START - MULAI MENGHASILKAN UANG

## Status Saat Ini: ✅ KODE LENGKAP, ❌ MASIH TEST MODE

### Kode Android: 100% Siap
- ✅ 3 jenis ads terintegrasi (Rewarded, Interstitial, Banner)
- ✅ Auto-show interstitial setiap 2 game
- ✅ Revenue tracking aktif
- ✅ JavaScript bridge berfungsi

### Masalah: TEST Ad IDs
- ❌ **Iklan TIDAK menghasilkan uang nyata**
- ❌ Pakai Google Test IDs untuk development

---

## 🎯 3 LANGKAH UNTUK GO LIVE

### STEP 1: Setup AdMob (15 menit)

1. **Buka AdMob:** https://admob.google.com
2. **Buat akun** dengan Google Account
3. **Add App:**
   - Platform: Android
   - Name: Dragon Arrow Escape  
   - Package: `com.dragonarrowescape.game`
4. **CATAT App ID** → Format: `ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY`

### STEP 2: Buat 3 Ad Units (10 menit)

Di AdMob dashboard, buat:

**A. Rewarded Video** (RPM tertinggi: $10-$30)
- Type: Rewarded
- Name: Dragon Arrow Rewarded
- **COPY Ad Unit ID #1**

**B. Interstitial** (RPM sedang: $3-$8)
- Type: Interstitial  
- Name: Dragon Arrow Interstitial
- **COPY Ad Unit ID #2**

**C. Banner** (RPM rendah: $0.5-$2)
- Type: Banner (320x50)
- Name: Dragon Arrow Banner
- **COPY Ad Unit ID #3**

### STEP 3: Update Kode (5 menit)

**File 1:** `android/app/src/main/AndroidManifest.xml`

Ganti line 40:
```xml
<!-- BEFORE -->
android:value="ca-app-pub-3940256099942544~3347511713"

<!-- AFTER -->
android:value="ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY"
```

**File 2:** `android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java`

Ganti line 42-50:
```java
// BEFORE (TEST)
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917";
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712";
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/6300978111";

// AFTER (PRODUCTION)
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/1111111111";
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/2222222222";
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/3333333333";
```

---

## 🏗️ BUILD & TEST

### Build Release APK
```bash
cd ~/android-game-bots/dragon-arrow-escape/android

# Clean
./gradlew clean

# Build
./gradlew assembleRelease

# Output: android/app/build/outputs/apk/release/app-release.apk
```

### Test di Device
```bash
# Install
adb install app/build/outputs/apk/release/app-release.apk

# Check logs
adb logcat | grep -E "AdsManager|DragonArrow"

# Verifikasi:
# ✅ Log: "Production Ad IDs detected"
# ✅ Tidak ada: "WARNING: USING TEST AD IDs"
```

---

## 💰 REVENUE EXPECTATIONS

### Dengan 1,000 Daily Active Users (DAU)

**Conservative estimate (Indonesia market):**

- **Rewarded Ads:** 
  - 30% user watch, 2x/day = 600 views
  - $15 RPM × 600/1000 = **$9/day**

- **Interstitial Ads:**
  - 80% user, 3 games/day, ad setiap 2 games = 1,200 views  
  - $5 RPM × 1,200/1000 = **$6/day**

- **Banner Ads:**
  - 50% see menu 2 min = 8,000 impressions
  - $1 RPM × 8,000/1000 = **$8/day**

**TOTAL: ~$23/day = $690/month** (1K DAU)

### Scaling:
- **5K DAU:** $3,450/month
- **10K DAU:** $6,900/month  
- **50K DAU:** $34,500/month
- **100K DAU:** $69,000/month

---

## 📊 MONITORING

### Cek Revenue (Daily)

**AdMob Console:** https://admob.google.com
- Revenue
- Impressions per ad type
- RPM (Revenue per 1000)
- Fill rate (target >90%)

### In-App Stats

```bash
# Real-time tracking
adb logcat | grep AdRevenueTracker

# Output example:
# 💎 Rewarded ad shown (session: 3)
# 📺 Interstitial ad shown (session: 5)
# 💰 Banner impression (session: 24)
```

---

## ⚠️ RULES - HINDARI BAN!

### JANGAN:
- ❌ Klik iklan sendiri
- ❌ Minta orang klik iklan
- ❌ Gunakan bot
- ❌ Show ads terlalu sering

### LAKUKAN:
- ✅ Test dengan test device IDs
- ✅ Monitor metrics
- ✅ Optimize berdasarkan data
- ✅ Balance UX & monetization

---

## 🎉 NEXT STEPS SETELAH LIVE

### Week 1-2: Monitor
- Daily revenue check
- User feedback
- Crash monitoring

### Month 1: Optimize  
- A/B test ad frequency
- Adjust based on retention
- Improve gameplay based on feedback

### Month 2+: Scale
- Marketing campaigns
- ASO (App Store Optimization)
- Content updates
- Consider ad mediation ($1k+/month revenue)

---

## 📞 HELP & SUPPORT

**Panduan Lengkap:**
```bash
cat ~/android-game-bots/dragon-arrow-escape/PRODUCTION_SETUP.md
```

**Official Docs:**
- AdMob: https://developers.google.com/admob
- Play Console: https://support.google.com/googleplay

**Troubleshooting:**
- "Ad failed to load" → Tunggu 1-2 jam setelah buat ad unit
- "No fill" → Normal di test mode, production biasanya 90%+
- "Low RPM" → Enable optimization di AdMob dashboard

---

## ✅ CHECKLIST GO LIVE

- [ ] AdMob account created
- [ ] App registered di AdMob
- [ ] 3 Ad Units created (Rewarded, Interstitial, Banner)
- [ ] App ID updated di AndroidManifest.xml
- [ ] 3 Ad Unit IDs updated di AdsManager.java
- [ ] Build release APK
- [ ] Test di physical device
- [ ] Verify: "Production Ad IDs detected" di log
- [ ] Ads muncul tanpa error
- [ ] Ready untuk publish Play Store!

**Total time: ~30 menit**  
**Mulai menghasilkan uang: Setelah publish & dapat users!** 💰

---

**Status Terakhir Update:** 11 Oktober 2026 - Kode lengkap, tinggal ganti IDs!
