# ✅ CHECKLIST PRODUCTION - MENGHASILKAN UANG DARI IKLAN

## 🎯 TUJUAN: Game bisa menghasilkan uang nyata dari iklan

---

## 📋 LANGKAH WAJIB (HARUS DIKERJAKAN!)

### 1️⃣ Setup AdMob Account (15 menit)

**Status: ⚠️ BELUM SELESAI - WAJIB!**

Tanpa ini, iklan TIDAK akan menghasilkan uang!

```
✅ Langkah-langkah:

1. Buka https://admob.google.com
2. Sign in dengan Google Account
3. Klik "Get Started" atau "Add App"
4. Pilih "Android"
5. Masukkan info app:
   - Name: Dragon Arrow Escape
   - Platform: Android
   - Package name: com.dragonarrowescape.game
   
6. SIMPAN App ID yang diberikan!
   Format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY
```

### 2️⃣ Buat Ad Units (10 menit)

**Status: ⚠️ BELUM SELESAI - WAJIB!**

Kamu perlu 3 Ad Units untuk monetisasi optimal:

```
Di dashboard AdMob:

1. Klik app "Dragon Arrow Escape"
2. Klik "Ad units" → "ADD AD UNIT"

3. Buat 3 Ad Units:

   A. REWARDED AD (Revenue tertinggi $10-$30 per 1000 views)
      - Klik "Rewarded"
      - Name: "Dragon Rewarded Bonus"
      - SIMPAN Ad Unit ID!
   
   B. INTERSTITIAL AD (Revenue sedang $3-$8 per 1000 views)
      - Klik "Interstitial"
      - Name: "Dragon Interstitial Level"
      - SIMPAN Ad Unit ID!
   
   C. BANNER AD (Revenue rendah tapi konsisten $0.5-$2 per 1000)
      - Klik "Banner"
      - Name: "Dragon Banner Menu"
      - SIMPAN Ad Unit ID!

4. Catat semua 3 Ad Unit IDs!
   Format: ca-app-pub-XXXXXXXXXXXXXXXX/1234567890
```

### 3️⃣ Update Kode dengan Production IDs (5 menit)

**Status: ⚠️ MENGGUNAKAN TEST IDs - TIDAK MENGHASILKAN UANG!**

File yang harus diubah:

#### A. AndroidManifest.xml
```bash
File: android/app/src/main/AndroidManifest.xml
Baris 40

GANTI:
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-3940256099942544~3347511713" />

DENGAN:
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-XXXX~YYYY" />  ← App ID kamu dari step 1!
```

#### B. AdsManager.java
```bash
File: android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java
Baris 42, 46, 50

GANTI semua 3 TEST IDs dengan Production Ad Unit IDs dari step 2:

Line 42 - REWARDED_AD_UNIT_ID = "ca-app-pub-XXXX/1111"
Line 46 - INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-XXXX/2222"
Line 50 - BANNER_AD_UNIT_ID = "ca-app-pub-XXXX/3333"
```

### 4️⃣ Build APK Production (2 menit)

```bash
cd /Users/macbookair/android-game-bots/dragon-arrow-escape/android
./gradlew assembleRelease

# APK akan ada di:
# android/app/build/outputs/apk/release/app-release-unsigned.apk
```

### 5️⃣ Sign APK (5 menit)

Kamu perlu keystore untuk sign APK sebelum upload ke Play Store:

```bash
# Generate keystore (sekali saja)
keytool -genkey -v -keystore dragon-arrow.keystore \
  -alias dragon-key -keyalg RSA -keysize 2048 -validity 10000

# Sign APK
jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 \
  -keystore dragon-arrow.keystore \
  app-release-unsigned.apk dragon-key

# Zipalign
zipalign -v 4 app-release-unsigned.apk DragonArrowEscape-v1.0.1.apk
```

### 6️⃣ Upload ke Google Play Console (20 menit)

```
1. Buka https://play.google.com/console
2. Create new app "Dragon Arrow Escape"
3. Upload APK yang sudah di-sign
4. Isi semua required info:
   - Description
   - Screenshots
   - Privacy Policy
   - Content rating
5. Submit untuk Review
```

---

## 💰 ESTIMASI REVENUE

Dengan setup yang benar:

### Scenario Konservatif (1000 players/day):
```
Per Hari:
- 500 Rewarded Ads × $15 CPM = $7.50
- 800 Interstitial Ads × $5 CPM = $4.00
- 2000 Banner Impressions × $1 CPM = $2.00
TOTAL: ~$13.50/hari

Per Bulan: ~$400/bulan
```

### Scenario Optimistik (5000 players/day):
```
Per Hari:
- 2500 Rewarded Ads × $20 CPM = $50
- 4000 Interstitial Ads × $6 CPM = $24
- 10000 Banner Impressions × $1.5 CPM = $15
TOTAL: ~$89/hari

Per Bulan: ~$2,670/bulan
```

---

## 🔍 VERIFIKASI SEBELUM PRODUCTION

Run verification script:

```bash
cd /Users/macbookair/android-game-bots/dragon-arrow-escape/android
./gradlew app:verifyAdConfiguration
```

Atau manual check:

```bash
# Check AndroidManifest.xml
grep -n "ca-app-pub" android/app/src/main/AndroidManifest.xml

# Check AdsManager.java
grep -n "AD_UNIT_ID" android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java

# Jika masih muncul "3940256099942544" = MASIH TEST ID!
```

---

## 🚨 WARNING PENTING!

### ❌ JANGAN:
- Upload APK dengan TEST Ad IDs (tidak akan dapat uang!)
- Klik iklan sendiri (banned dari AdMob!)
- Force user nonton iklan terlalu sering (bad UX)

### ✅ LAKUKAN:
- Ganti semua TEST IDs dengan Production IDs
- Test di device nyata sebelum publish
- Monitor AdMob dashboard setiap hari
- Optimize placement berdasarkan analytics

---

## 📊 MONITORING REVENUE

Setelah publish:

1. **Dashboard AdMob**: https://admob.google.com
   - Lihat revenue harian
   - Check impression counts
   - Monitor fill rate

2. **Analytics Game**:
   - Cek logcat untuk ad performance
   - Monitor AdRevenueTracker stats
   - Adjust frequency berdasarkan user retention

3. **Optimize**:
   - A/B test interstitial frequency
   - Test different rewarded ad incentives
   - Adjust banner visibility

---

## 🎯 CURRENT STATUS

```
✅ Kode game: SIAP
✅ Ad integration: LENGKAP
✅ Revenue tracking: AKTIF
✅ Analytics: BERFUNGSI

⚠️ AdMob Account: PERLU SETUP
⚠️ Production Ad IDs: PERLU GANTI
⚠️ APK: PERLU BUILD & SIGN
⚠️ Play Store: PERLU UPLOAD
```

---

## 🚀 QUICK START (30 MENIT)

Jika kamu ingin cepat mulai menghasilkan uang:

```bash
# 1. Setup AdMob (15 menit)
# → Ikuti step 1-2 di atas

# 2. Update IDs (5 menit)
# → Edit AndroidManifest.xml dan AdsManager.java

# 3. Build APK (5 menit)
cd android
./gradlew assembleRelease

# 4. Test di device (5 menit)
adb install -r app/build/outputs/apk/release/app-release-unsigned.apk

# 5. Verify ads muncul
# → Buka app, cek logcat, pastikan ads loading
```

---

## 📞 TROUBLESHOOTING

### "Ads tidak muncul"
```
1. Check internet connection
2. Check Ad IDs sudah benar
3. Check App ID di AndroidManifest
4. Tunggu 1-2 jam setelah setup baru
5. Check logcat untuk error messages
```

### "Revenue masih $0"
```
1. Pastikan sudah ganti TEST IDs
2. Tunggu 24-48 jam untuk processing
3. Check AdMob account status
4. Verify app sudah di-approve
```

### "Ads loading lambat"
```
1. Preload ads saat game start
2. Check network quality
3. Monitor fill rate di dashboard
4. Consider fallback ad networks
```

---

**NEXT ACTION: Setup AdMob account dan ganti Production IDs!**
