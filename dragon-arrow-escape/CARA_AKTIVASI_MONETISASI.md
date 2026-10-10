# 💰 CARA AKTIVASI MONETISASI - Dragon Arrow Escape

**Status:** Kode 100% siap, tinggal aktivasi AdMob!  
**Waktu dibutuhkan:** 30 menit setup + 1-7 hari approval Play Store  
**Target revenue:** Rp 6.8M - 340M per bulan (tergantung jumlah user)

---

## 🎯 QUICK START (3 Langkah)

### ⚡ LANGKAH 1: Buat Akun AdMob (15 menit)

```
1. Buka: https://admob.google.com
2. Sign in dengan Google Account
3. Klik "Get Started"
4. Isi informasi payment:
   - Nama lengkap
   - Alamat
   - Nomor rekening bank
   - Tax information
```

**Output:** Akun AdMob aktif

---

### ⚡ LANGKAH 2: Buat App & Ad Units (10 menit)

#### A. Buat App di AdMob

```
1. Di AdMob Dashboard → "Apps" → "Add App"
2. Is your app listed on a supported app store? → NO (belum publish)
3. App name: Dragon Arrow Escape
4. Platform: Android
5. Klik "Add"
```

**✅ Catat App ID yang muncul:**
```
Format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY
Contoh: ca-app-pub-1234567890123456~0987654321
```

#### B. Buat 3 Ad Units

**B.1. Rewarded Ad (Revenue tertinggi)**
```
1. Pilih app "Dragon Arrow Escape"
2. Ad Units → "Add Ad Unit" → "Rewarded"
3. Ad unit name: Dragon Arrow Rewarded
4. Klik "Create ad unit"
```
**✅ Catat Rewarded Ad Unit ID:**
```
Format: ca-app-pub-XXXXXXXXXXXXXXXX/1111111111
```

**B.2. Interstitial Ad**
```
1. Ad Units → "Add Ad Unit" → "Interstitial"
2. Ad unit name: Dragon Arrow Interstitial
3. Klik "Create ad unit"
```
**✅ Catat Interstitial Ad Unit ID:**
```
Format: ca-app-pub-XXXXXXXXXXXXXXXX/2222222222
```

**B.3. Banner Ad**
```
1. Ad Units → "Add Ad Unit" → "Banner"
2. Ad unit name: Dragon Arrow Banner
3. Klik "Create ad unit"
```
**✅ Catat Banner Ad Unit ID:**
```
Format: ca-app-pub-XXXXXXXXXXXXXXXX/3333333333
```

**Total IDs yang harus dicatat: 4 IDs**
- 1 App ID
- 3 Ad Unit IDs

---

### ⚡ LANGKAH 3: Setup & Build (5 menit)

```bash
cd ~/android-game-bots/dragon-arrow-escape

# Jalankan script setup otomatis
python3 setup_production_ads.py

# Script akan tanya 4 IDs, input satu per satu
# Format akan divalidasi otomatis

# Build Release APK
./build_release.sh
```

**Output:**
```
✅ Production IDs ter-install
✅ APK siap di: android/app/build/outputs/apk/release/
```

---

## 📱 LANGKAH 4: Upload ke Play Store

### A. Buat Play Console Account

```
1. Buka: https://play.google.com/console
2. Sign in dengan Google Account yang sama
3. Bayar one-time fee: $25 (sekali bayar selamanya)
```

### B. Create App Listing

```
1. Klik "Create app"
2. App name: Dragon Arrow Escape
3. Default language: English / Indonesian
4. App or game: Game
5. Free or paid: Free
6. Klik "Create app"
```

### C. Upload APK

```
1. Dashboard → "Release" → "Production"
2. Klik "Create new release"
3. Upload APK: android/app/build/outputs/apk/release/app-release.apk
4. Release name: 1.0.1
5. Release notes: "Initial release with ad monetization"
6. Klik "Save"
```

### D. Complete Store Listing

**Required fields:**

1. **App details**
   - Short description (80 char)
   - Full description (4000 char)
   - App icon (512x512 PNG)
   
2. **Graphics**
   - Screenshots (minimal 2)
   - Feature graphic (1024x500)
   
3. **Categorization**
   - App category: Games → Arcade
   - Content rating: Complete questionnaire
   
4. **Contact details**
   - Email address
   - Privacy policy URL (optional tapi recommended)

5. **Pricing & distribution**
   - Countries: Pilih semua atau specific
   - Content rating: E for Everyone

### E. Submit for Review

```
1. Review → "Start rollout to Production"
2. Klik "Confirm"
```

**⏰ Waiting time:** 1-7 hari untuk approval

---

## 💰 REVENUE EXPECTATIONS

### Skenario Konservatif (1,000 DAU)

**Assumptions:**
- 50% watch rewarded ads = 500 views/day
- 80% see interstitial = 800 views/day
- 100% see banner = 3,000 impressions/day

**Revenue per hari:**
```
Rewarded:     500 × $0.015 = $7.50
Interstitial: 800 × $0.005 = $4.00
Banner:      3000 × $0.001 = $3.00
────────────────────────────────
TOTAL:                   $14.50/hari
```

**Monthly:** $14.50 × 30 = **$435** ≈ **Rp 6.8 juta**

### Skenario Realistis (5,000 DAU)

**Revenue per hari:**
```
Rewarded:    2,500 × $0.015 = $37.50
Interstitial: 4,000 × $0.005 = $20.00
Banner:      15,000 × $0.001 = $15.00
─────────────────────────────────
TOTAL:                    $72.50/hari
```

**Monthly:** $72.50 × 30 = **$2,175** ≈ **Rp 34 juta**

### Scaling Table

| Daily Users | Daily Revenue | Monthly Revenue | Annual Revenue |
|-------------|---------------|-----------------|----------------|
| 1,000       | $14.50        | $435            | $5,220         |
| 5,000       | $72.50        | $2,175          | $26,100        |
| 10,000      | $145          | $4,350          | $52,200        |
| 50,000      | $725          | $21,750         | $261,000       |
| 100,000     | $1,450        | $43,500         | $522,000       |

---

## ⚠️ CRITICAL WARNINGS

### DO ✅

1. **Test dulu dengan TEST IDs** sebelum ganti Production
2. **Monitor AdMob dashboard** setiap hari
3. **Test di real device** (emulator tidak akurat)
4. **Follow AdMob policies** ketat
5. **Backup semua files** sebelum update

### DON'T ❌

1. **JANGAN klik iklan sendiri** → Instant permanent ban!
2. **JANGAN spam ads** → Max 1 interstitial per 3 menit (sudah di-implement)
3. **JANGAN misleading ads** → Policy violation
4. **JANGAN lupa ganti TEST IDs** → Tidak dapat uang sama sekali
5. **JANGAN publish tanpa test** → Bisa crash di user device

---

## 🔍 TROUBLESHOOTING

### Problem: Ads tidak muncul setelah publish

**Solution:**
```
1. Check AdMob dashboard → ads status harus "Serving"
2. Wait 24-48 jam setelah app approved (fill rate meningkat bertahap)
3. Check logcat: adb logcat | grep -i "admob\|ads"
4. Verify Production IDs sudah benar di kode
```

### Problem: Revenue masih $0 setelah 1 minggu

**Possible causes:**
```
1. Masih pakai TEST IDs → Check AndroidManifest.xml
2. App belum approved Play Store → Check Play Console
3. Fill rate rendah → Normal untuk new app, wait 1-2 minggu
4. Tidak ada user → Check Play Store installs
```

### Problem: Build gagal

**Solution:**
```bash
cd ~/android-game-bots/dragon-arrow-escape/android

# Clean build
./gradlew clean

# Check gradle version
./gradlew --version

# Rebuild
./gradlew assembleDebug --stacktrace
```

---

## 📊 MONITORING REVENUE

### AdMob Dashboard

```
URL: https://admob.google.com
Login → Reports
```

**Key metrics:**
- **Impressions:** Jumlah iklan ditampilkan
- **Estimated earnings:** Revenue estimasi (update real-time)
- **eCPM:** Earnings per 1000 impressions
- **Fill rate:** % request yang dapat iklan
- **Match rate:** % impressions yang match dengan advertiser

**Timeline:**
- **Real-time:** Impressions visible
- **24 hours:** Estimated earnings visible
- **48 hours:** Accurate earnings data
- **Monthly:** Final earnings confirmed
- **30 days after $100:** Payout ke bank

### Play Console Analytics

```
URL: https://play.google.com/console
Dashboard → Statistics
```

**Key metrics:**
- **Installs:** Total downloads
- **Active devices:** Current DAU/MAU
- **Retention:** D1, D7, D30 retention rates
- **Crashes:** App stability

---

## 🚀 TIPS MAKSIMALKAN REVENUE

### 1. Optimize Rewarded Ads (Highest RPM)

**Best practices:**
```javascript
// Offer valuable rewards
- 100 coins per ad (generous)
- Continue game after death
- Unlock premium items
- 2x rewards booster

// Strategic placement
- Game over screen (high motivation)
- Before boss battle (power-up)
- Daily login bonus multiplier
```

### 2. Balance Interstitial Ads

**Current implementation:**
```java
// 3-minute cooldown (optimal)
private static final long INTERSTITIAL_COOLDOWN = 180000;

// Show after:
- Complete 2-3 levels
- Return to main menu
- Enter shop
```

**Don't spam:** User akan uninstall!

### 3. Banner Ads Strategy

```
✅ Show: Menu, shop, leaderboard
❌ Hide: During gameplay (bad UX)

Position: Bottom center (320x50)
Visibility: Always on in menu
```

### 4. User Acquisition

**Organic (Free):**
```
- SEO Play Store listing
- Keywords: "arrow game", "casual game", "offline game"
- High-quality screenshots
- Gameplay video
- Social sharing in-game
```

**Paid ($0.50-$2 per install):**
```
- Google Ads (Universal App Campaign)
- Facebook Ads (gaming audience)
- TikTok Ads (viral potential)
- Instagram Ads (visual appeal)
```

**ROI Calculation:**
```
Cost per install: $1.00
LTV per user: $0.50 per month
Breakeven: 2 months
Profitable: Month 3+
```

---

## 📋 CHECKLIST COMPLETE

Sebelum publish, pastikan semua ini sudah:

- [ ] ✅ Akun AdMob dibuat
- [ ] ✅ 4 Production IDs didapat
- [ ] ✅ `setup_production_ads.py` dijalankan
- [ ] ✅ Build sukses dengan `./build_release.sh`
- [ ] ✅ Test di real device (bukan emulator)
- [ ] ✅ Ads muncul dengan benar
- [ ] ✅ Play Console account created ($25 paid)
- [ ] ✅ App icon & screenshots ready
- [ ] ✅ Store listing lengkap
- [ ] ✅ APK uploaded
- [ ] ✅ Review submitted

**Setelah semua checklist:** Wait 1-7 hari untuk approval!

---

## 📞 RESOURCES

### Documentation
- AdMob Help: https://support.google.com/admob
- Play Console Help: https://support.google.com/googleplay/android-developer
- AdMob Policies: https://support.google.com/admob/answer/6128543

### Tools
- AdMob Console: https://admob.google.com
- Firebase Console: https://console.firebase.google.com
- Play Console: https://play.google.com/console

### Scripts (in project)
- `setup_production_ads.py` - Setup Production IDs
- `build_release.sh` - Build Release APK
- `verify_ads.sh` - Verify ads configuration

---

## 🎉 CONCLUSION

**Kode Android sudah 100% siap menghasilkan uang!**

**Timeline ke monetisasi:**
```
NOW          → Buat AdMob account (15 min)
NOW + 20 min → Setup & build (5 min)
NOW + 30 min → Upload to Play Store
NOW + 1-7 d  → App approved & live
NOW + 7 d    → First revenue visible
NOW + 30 d   → First payout ($100 minimum)
```

**Fastest path:** Bisa mulai earning dalam **1 minggu**!

**Revenue potential:** Rp 6.8M - 340M per bulan (tergantung user acquisition)

**Next action:** Buka https://admob.google.com dan buat akun sekarang!

---

**Last updated:** 11 Oktober 2026  
**Version:** 1.0.1  
**Status:** 🟢 READY TO MONETIZE
