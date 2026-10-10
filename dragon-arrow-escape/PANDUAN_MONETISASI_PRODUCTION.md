# 🚀 PANDUAN LENGKAP MONETISASI PRODUCTION
**Game:** Dragon Arrow Escape  
**Target:** Menghasilkan uang nyata dari iklan  
**Status:** ⚠️ MASIH PAKAI TEST IDs - TIDAK MENGHASILKAN UANG!

---

## ❌ MASALAH SAAT INI

### Aplikasi Sedang Pakai TEST AD UNIT IDs
```java
// AndroidManifest.xml (Line 41)
android:value="ca-app-pub-3940256099942544~3347511713"  ← TEST ID!

// AdsManager.java (Lines 42, 46, 50)
REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917"      ← TEST ID!
INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712" ← TEST ID!
BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/6300978111"       ← TEST ID!
```

**DAMPAK:** 
- ✅ Iklan tampil di aplikasi (bagus untuk testing)
- ❌ TIDAK menghasilkan uang sama sekali
- ❌ Google AdMob TIDAK menghitung impressions
- ❌ Revenue tetap $0.00

---

## ✅ SOLUSI: SETUP PRODUCTION ADMOB

### LANGKAH 1: Buat Akun AdMob
1. Buka https://admob.google.com
2. Login dengan akun Google
3. Klik "Get Started" atau "Mulai"
4. Setujui Terms & Conditions
5. Isi informasi pembayaran (untuk terima revenue):
   - Nama lengkap
   - Alamat
   - Nomor rekening bank / PayPal
   - Tax information (sesuai negara)

**PENTING:** AdMob minimal payout $100 USD

---

### LANGKAH 2: Daftarkan Aplikasi Android

1. Di dashboard AdMob, klik **"Apps"** → **"Add App"**

2. Pilih platform: **Android**

3. Apakah app sudah di Google Play Store?
   - **Belum:** Pilih "No" → Isi nama app: **Dragon Arrow Escape**
   - **Sudah:** Pilih "Yes" → Masukkan package name: `com.dragonarrowescape.game`

4. Klik **"Add"** atau **"Tambahkan"**

5. **CATAT APP ID** yang muncul:
   ```
   Format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY
   
   Contoh: ca-app-pub-1234567890123456~0987654321
   ```
   ⚠️ **SIMPAN ID INI - AKAN DIPAKAI DI KODE!**

---

### LANGKAH 3: Buat Ad Units (3 jenis)

#### A. REWARDED AD (Priority #1 - Revenue tertinggi)
1. Di app yang baru dibuat, klik **"Add Ad Unit"**
2. Pilih format: **"Rewarded"** atau **"Rewarded video"**
3. Nama ad unit: **"Dragon Arrow Rewarded"**
4. Klik **"Create Ad Unit"**
5. **CATAT AD UNIT ID:**
   ```
   ca-app-pub-XXXXXXXXXXXXXXXX/1111111111
   ```

**Gunakan untuk:**
- Continue game setelah game over
- Double coins
- Unlock premium items
- Bonus energy/lives

**Revenue:** $10-$30 CPM (per 1000 views)

---

#### B. INTERSTITIAL AD (Priority #2 - Revenue sedang)
1. Klik **"Add Ad Unit"** lagi
2. Pilih format: **"Interstitial"**
3. Nama ad unit: **"Dragon Arrow Interstitial"**
4. Klik **"Create Ad Unit"**
5. **CATAT AD UNIT ID:**
   ```
   ca-app-pub-XXXXXXXXXXXXXXXX/2222222222
   ```

**Gunakan untuk:**
- Level complete (setiap 2-3 level)
- Transisi menu → gameplay
- Otomatis ada cooldown 3 menit

**Revenue:** $3-$8 CPM

---

#### C. BANNER AD (Priority #3 - Revenue kecil tapi konsisten)
1. Klik **"Add Ad Unit"** lagi
2. Pilih format: **"Banner"**
3. Nama ad unit: **"Dragon Arrow Banner"**
4. Banner size: **"Standard (320x50)"**
5. Klik **"Create Ad Unit"**
6. **CATAT AD UNIT ID:**
   ```
   ca-app-pub-XXXXXXXXXXXXXXXX/3333333333
   ```

**Gunakan untuk:**
- Menu utama
- Shop/store
- Leaderboard
- **JANGAN** tampilkan saat gameplay!

**Revenue:** $0.5-$2 CPM (kecil per view, tapi cumulative tinggi)

---

### LANGKAH 4: Update Kode dengan Production IDs

#### File 1: `AndroidManifest.xml`
**Lokasi:** `android/app/src/main/AndroidManifest.xml`

**Ganti baris 41:**
```xml
<!-- SEBELUM (TEST ID) -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-3940256099942544~3347511713" />

<!-- SESUDAH (PRODUCTION ID) -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY" />
```

⚠️ **Ganti dengan APP ID dari Langkah 2!**

---

#### File 2: `AdsManager.java`
**Lokasi:** `android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java`

**Ganti baris 42, 46, 50:**
```java
// SEBELUM (TEST IDs)
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917";
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712";
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/6300978111";

// SESUDAH (PRODUCTION IDs)
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/1111111111";
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/2222222222";
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/3333333333";
```

⚠️ **Ganti dengan Ad Unit IDs dari Langkah 3!**

---

### LANGKAH 5: Build APK Production

```bash
cd ~/android-game-bots/dragon-arrow-escape/android

# Clean build
./gradlew clean

# Build release APK
./gradlew assembleRelease

# APK akan ada di:
# android/app/build/outputs/apk/release/app-release-unsigned.apk
```

---

### LANGKAH 6: Sign APK (Required untuk Production)

#### Generate Keystore (sekali saja)
```bash
keytool -genkey -v -keystore dragon-arrow-escape.keystore \
  -alias dragon_arrow_escape \
  -keyalg RSA -keysize 2048 -validity 10000

# Isi informasi:
# - Password: [pilih password kuat, JANGAN LUPA!]
# - First and last name: [nama developer]
# - Organization: [nama company/personal]
# - City, State, Country: [sesuai lokasi]
```

⚠️ **BACKUP KEYSTORE INI! Jika hilang, tidak bisa update app!**

#### Sign APK
```bash
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore dragon-arrow-escape.keystore \
  app/build/outputs/apk/release/app-release-unsigned.apk \
  dragon_arrow_escape

# Align APK
zipalign -v 4 \
  app/build/outputs/apk/release/app-release-unsigned.apk \
  app/build/outputs/apk/release/dragon-arrow-escape-signed.apk
```

**APK siap upload:** `dragon-arrow-escape-signed.apk`

---

### LANGKAH 7: Publish ke Google Play Store (OPSIONAL tapi RECOMMENDED)

#### Kenapa Publish?
- ✅ Revenue lebih tinggi (user trust app dari Play Store)
- ✅ Auto-update (mudah push fixes dan features)
- ✅ Better ad fill rate (AdMob prioritas app official)
- ✅ Analytics dan user reviews

#### Cara Publish:
1. Buka https://play.google.com/console
2. Pay registration fee: $25 USD (sekali seumur hidup)
3. Create new app: **Dragon Arrow Escape**
4. Upload APK signed
5. Isi store listing:
   - Title: Dragon Arrow Escape
   - Short description: Game arkade menghindari panah
   - Long description: [tulis detail gameplay]
   - Screenshots: minimal 2 (ambil dari game)
   - Icon: 512x512 PNG
   - Feature graphic: 1024x500 PNG
6. Content rating: Everyone / Teen
7. Submit for review (1-3 hari)

**ALTERNATIVE (Tanpa Play Store):**
- Distribusi APK langsung (via WhatsApp, Telegram, website)
- Revenue tetap jalan, tapi lebih rendah ~30%

---

## 💰 PROYEKSI REVENUE

### Asumsi Conservative
```
Daily Active Users (DAU): 100 users
Avg session: 10 menit
Rewarded ads: 2 per session × 100 users = 200 impressions/hari
Interstitial ads: 1 per session × 100 users = 100 impressions/hari
Banner impressions: 5 per session × 100 users = 500 impressions/hari

Revenue:
  Rewarded:     200 × $20 CPM ÷ 1000 = $4.00/hari
  Interstitial: 100 × $5 CPM ÷ 1000  = $0.50/hari
  Banner:       500 × $1 CPM ÷ 1000  = $0.50/hari
  
TOTAL: $5.00/hari = $150/bulan
```

### Asumsi Optimistic (1000 DAU)
```
Daily Active Users: 1,000 users
Rewarded ads: 2,000 impressions/hari
Interstitial ads: 1,000 impressions/hari
Banner impressions: 5,000 impressions/hari

Revenue:
  Rewarded:     2,000 × $25 CPM ÷ 1000 = $50/hari
  Interstitial: 1,000 × $6 CPM ÷ 1000  = $6/hari
  Banner:       5,000 × $1.5 CPM ÷ 1000 = $7.5/hari
  
TOTAL: $63.5/hari = $1,905/bulan
```

### Scaling Path
```
Target Month 1:  100 DAU  → $150/bulan
Target Month 2:  300 DAU  → $450/bulan
Target Month 3:  500 DAU  → $750/bulan
Target Month 6: 1000 DAU  → $1,900/bulan
Target Year 1:  2000+ DAU → $3,800+/bulan
```

---

## 🎯 BEST PRACTICES MONETISASI

### DO's ✅
1. **Rewarded ads selalu voluntary (user pilih)**
   - "Watch ad to continue?"
   - "Double your coins?"
   - "Unlock premium skin?"

2. **Interstitial timing yang smart:**
   - Setiap 2-3 level complete ✅
   - Saat natural break (menu ↔ gameplay) ✅
   - BUKAN di tengah gameplay ❌

3. **Banner hanya di menu:**
   - Menu utama ✅
   - Shop/Store ✅
   - Leaderboard ✅
   - Saat gameplay: HIDE! ❌

4. **Preload ads di background:**
   - Load saat game start
   - Load lagi setelah ad ditampilkan
   - User tidak tunggu

5. **Track performance:**
   - Cek AdRevenueTracker stats
   - Monitor CPM dan fill rate
   - A/B test timing dan placement

### DON'Ts ❌
1. **JANGAN spam interstitial:**
   - Cooldown minimum 3 menit ✅ (sudah ada di kode)
   - Max 1 interstitial per session awal ✅

2. **JANGAN hide "skip" button rewarded ads:**
   - User harus voluntary watch
   - Forcing = bad UX = uninstall

3. **JANGAN show banner saat gameplay:**
   - Mengganggu gameplay
   - User complain
   - Better hide, show di menu saja

4. **JANGAN fake ad interactions:**
   - Akan banned oleh AdMob
   - Kehilangan akun permanen

5. **JANGAN tes production ads berulang:**
   - Testing = pakai test IDs
   - Production = real users only

---

## 🔍 VERIFIKASI PRODUCTION

### Checklist Sebelum Deploy
- [ ] App ID di AndroidManifest.xml sudah production
- [ ] 3 Ad Unit IDs di AdsManager.java sudah production
- [ ] APK sudah di-sign dengan keystore
- [ ] Tested di device fisik (bukan emulator)
- [ ] google-services.json valid
- [ ] AdMob account verified dan payment setup

### Test Ads di Production APK
```bash
# Install production APK
adb install -r dragon-arrow-escape-signed.apk

# Monitor logs
adb logcat | grep -E "(AdsManager|AdMob|MainActivity)"

# Cek ads loading:
# ✅ "Google Mobile Ads SDK initialized"
# ✅ "Rewarded Ad Loaded Successfully"
# ✅ "Interstitial Ad Loaded Successfully"
# ✅ "Banner ad loaded"

# Cek BUKAN test ads:
# ❌ Jika muncul "test" dalam log = masih test mode!
# ✅ Harus muncul "production" atau ID production
```

### Verifikasi Revenue di AdMob Dashboard
1. Login ke https://admob.google.com
2. Klik **"Apps"** → pilih **Dragon Arrow Escape**
3. Lihat metrics (setelah 24 jam):
   - **Estimated earnings** harus > $0.00
   - **Impressions** harus naik
   - **Match rate** target > 90%
   - **Show rate** target > 85%

⚠️ **Revenue baru muncul 24-48 jam setelah impressions!**

---

## 🐛 TROUBLESHOOTING

### Problem 1: Ads tidak muncul
**Symptoms:** Log "Ad failed to load"

**Solutions:**
1. Cek internet connection
2. Verifikasi Ad Unit IDs benar (copy-paste dari AdMob)
3. Tunggu 1-2 jam setelah create ad units (AdMob butuh waktu aktivasi)
4. Cek apakah app sudah di-approve AdMob (biasanya instant)

### Problem 2: Ads muncul tapi revenue $0
**Symptoms:** Impressions ada, tapi earnings $0.00

**Cause:** Masih pakai test IDs!

**Solution:**
1. Double-check AndroidManifest.xml (App ID)
2. Double-check AdsManager.java (Ad Unit IDs)
3. Rebuild dan re-sign APK
4. Re-install ke device

### Problem 3: Ad fill rate rendah
**Symptoms:** "Ad failed to load" sering muncul

**Causes:**
- Location: AdMob fill rate rendah di beberapa negara
- New app: Butuh 1-2 minggu untuk AdMob optimize
- Invalid traffic: AdMob detect bot/fake clicks

**Solutions:**
1. Tambahkan mediation networks (Facebook Audience Network, Unity Ads)
2. Tunggu 1-2 minggu (fill rate akan naik)
3. Target negara tier 1 (US, UK, AU, CA) = CPM lebih tinggi

### Problem 4: AdMob account suspended
**Symptoms:** "Invalid traffic detected"

**Causes:**
- Clicking own ads
- Fake traffic/bots
- Incentivizing clicks

**Prevention:**
- JANGAN click ads sendiri
- JANGAN tes production ads berulang
- Use test IDs untuk development
- Use production IDs untuk real users only

---

## 📊 MONITORING & ANALYTICS

### Daily Checks
```bash
# Revenue tracking
cat ~/android-game-bots/dragon-arrow-escape/revenue_log.txt

# Performance stats
adb shell run-as com.dragonarrowescape.game \
  cat /data/data/com.dragonarrowescape.game/shared_prefs/AdRevenuePrefs.xml
```

### Weekly Review
- Check AdMob dashboard
- Compare CPM trends
- Analyze best-performing ad units
- Adjust ad placements jika perlu

### Monthly Goals
- Increase DAU by 50%
- Maintain fill rate > 90%
- Improve session time (more ads shown)
- Reduce uninstall rate

---

## 🚀 SCALING STRATEGY

### Phase 1: Launch (Month 1)
- Target: 100 DAU
- Focus: Stability dan retention
- Revenue: $150/bulan

### Phase 2: Growth (Month 2-3)
- Marketing: Social media, WhatsApp groups
- Target: 500 DAU
- Revenue: $750/bulan

### Phase 3: Scale (Month 4-6)
- Play Store optimization (ASO)
- User acquisition campaigns
- Target: 1000 DAU
- Revenue: $1,900/bulan

### Phase 4: Expand (Month 6+)
- Launch game #2 (reuse code base)
- Cross-promote antar games
- Target: 2000+ DAU per game
- Revenue: $3,800+/bulan per game

---

## 📝 CHECKLIST FINAL

### Development
- [x] Code sudah terintegrasi ads (Rewarded, Interstitial, Banner)
- [x] JavaScript bridge sudah ready
- [x] Revenue tracking implemented
- [ ] Production IDs sudah di-update
- [ ] APK sudah di-build dan sign

### AdMob Account
- [ ] Account created
- [ ] Payment info setup
- [ ] App registered
- [ ] 3 Ad Units created (Rewarded, Interstitial, Banner)
- [ ] IDs di-copy ke kode

### Testing
- [ ] Test di device fisik
- [ ] Ads loading successfully
- [ ] Rewarded ad bisa diklaim
- [ ] Interstitial cooldown works
- [ ] Banner show/hide works

### Launch
- [ ] APK signed dengan keystore production
- [ ] Keystore di-backup aman
- [ ] Distribute APK atau publish ke Play Store
- [ ] Monitor AdMob dashboard setelah 24 jam

---

## 💡 NEXT STEPS

1. **Hari ini:** Setup AdMob account dan create ad units (30 menit)
2. **Hari ini:** Update kode dengan production IDs (10 menit)
3. **Hari ini:** Build, sign, dan test APK (30 menit)
4. **Besok:** Distribute ke 10-20 teman untuk alpha test
5. **Minggu depan:** Monitor revenue first week
6. **Bulan depan:** Scale to 100+ users

---

**STATUS SAAT INI:** ⚠️ Ready to monetize - tinggal ganti IDs!  
**ESTIMASI REVENUE FIRST MONTH:** $50-150 USD (conservative)  
**TIME TO FIRST DOLLAR:** 24-48 jam setelah deployment  

🚀 **Good luck monetizing!**
