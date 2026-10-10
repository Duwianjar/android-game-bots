# ✅ QUICK ACTION: Setup Production & Mulai Hasilkan Uang

## 🎯 RINGKASAN SINGKAT
Kode sudah 100% siap. Tinggal ganti TEST IDs ke Production IDs, build release, dan upload ke Play Store.

## ⚡ LANGKAH CEPAT (2 JAM)

### 1️⃣ Setup AdMob (20 menit)
```
1. Buka https://admob.google.com
2. Login & buat account
3. Add app: "Dragon Arrow Escape"
4. Package: com.dragonarrowescape.game
5. Buat 3 Ad Units:
   - Rewarded: "Bonus Coins"
   - Interstitial: "Level Complete"
   - Banner: "Menu Banner"
6. Catat 4 IDs
```

### 2️⃣ Update IDs (10 menit)
```bash
# Edit file:
# 1. android/app/src/main/AndroidManifest.xml (line 41)
# 2. android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java (lines 42, 46, 50)

# Ganti semua yang ada "3940256099942544" dengan Production IDs

# Verify tidak ada TEST IDs:
grep -r "3940256099942544" android/app/src/
# Harus: no results found
```

### 3️⃣ Build Release (15 menit)
```bash
cd android
./gradlew clean assembleRelease

# APK output:
# android/app/build/outputs/apk/release/app-release-unsigned.apk
```

### 4️⃣ Sign APK (10 menit)
```bash
# Generate keystore (sekali saja):
keytool -genkey -v -keystore dragon.keystore \
  -alias dragon -keyalg RSA -keysize 2048 -validity 10000

# Sign:
jarsigner -verbose -sigalg SHA1withRSA \
  -keystore dragon.keystore \
  app-release-unsigned.apk dragon

# Zipalign:
zipalign -v 4 app-release-unsigned.apk dragon-arrow-escape.apk
```

### 5️⃣ Upload Play Store (30 menit)
```
1. https://play.google.com/console
2. Create app
3. Upload APK
4. Fill store listing
5. Content rating
6. Submit review
```

### 6️⃣ Wait & Earn (1-3 hari)
```
- Play Store review: 1-3 hari
- App goes live
- Ads start serving
- Revenue starts counting
- Check AdMob dashboard daily
```

## 💰 ESTIMASI REVENUE
- **100 users/day:** $4/day = $120/bulan
- **1,000 users/day:** $40/day = $1,200/bulan  
- **10,000 users/day:** $400/day = $12,000/bulan

## ✅ DONE!
Setelah langkah ini, game akan mulai menghasilkan uang dari iklan!
