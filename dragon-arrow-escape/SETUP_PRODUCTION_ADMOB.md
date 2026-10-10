# 🎯 Setup Production AdMob - Dragon Arrow Escape

## ⚠️ PENTING: Ganti Test IDs dengan Production IDs

**Status Saat Ini:** Aplikasi menggunakan **TEST Ad Unit IDs** yang **TIDAK menghasilkan uang nyata**

**Yang Harus Dilakukan:** Daftar AdMob dan ganti semua Test IDs dengan Production IDs

---

## 📋 Langkah-Langkah Setup AdMob

### 1️⃣ Buat Akun AdMob (GRATIS)
1. Buka https://admob.google.com
2. Login dengan akun Google
3. Klik "Get Started" / "Mulai"
4. Verifikasi informasi pembayaran (untuk terima pembayaran iklan)

### 2️⃣ Daftarkan Aplikasi
1. Di dashboard AdMob → klik "Apps" → "Add App"
2. Pilih platform: **Android**
3. Pilih "No" (app belum dipublish di Google Play)
4. Masukkan nama app: **Dragon Arrow Escape**
5. Klik "Add"
6. **CATAT App ID** yang muncul (format: `ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY`)

### 3️⃣ Buat Ad Units (3 jenis iklan)

#### A. Rewarded Ad Unit (PRIORITAS TERTINGGI - RPM $10-$30)
1. Di app page → "Ad units" → "Add ad unit"
2. Pilih format: **Rewarded**
3. Nama: `Dragon Arrow Escape - Rewarded`
4. Klik "Create ad unit"
5. **CATAT Rewarded Ad Unit ID** (format: `ca-app-pub-XXXXXXXXXXXXXXXX/1234567890`)

#### B. Interstitial Ad Unit (RPM $3-$8)
1. Kembali ke app page → "Ad units" → "Add ad unit"
2. Pilih format: **Interstitial**
3. Nama: `Dragon Arrow Escape - Interstitial`
4. Klik "Create ad unit"
5. **CATAT Interstitial Ad Unit ID**

#### C. Banner Ad Unit (RPM $0.5-$2)
1. Kembali ke app page → "Ad units" → "Add ad unit"
2. Pilih format: **Banner**
3. Nama: `Dragon Arrow Escape - Banner`
4. Size: **320x50 (Standard)**
5. Klik "Create ad unit"
6. **CATAT Banner Ad Unit ID**

---

## 🔧 Update Kode dengan Production IDs

### File 1: `android/app/src/main/AndroidManifest.xml`
**Baris 40-41:** Ganti App ID

```xml
<!-- SEBELUM (TEST ID) -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-3940256099942544~3347511713" />

<!-- SESUDAH (PRODUCTION ID - ganti dengan ID kamu) -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY" />
```

### File 2: `android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java`
**Baris 42, 46, 50:** Ganti Ad Unit IDs

```java
// SEBELUM (TEST IDs)
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917"; // ⚠️ TEST
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712"; // ⚠️ TEST
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/6300978111"; // ⚠️ TEST

// SESUDAH (PRODUCTION IDs - ganti dengan ID kamu)
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/1111111111";
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/2222222222";
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/3333333333";
```

---

## 🏗️ Build APK Production

### Prasyarat
```bash
# Install Android SDK dan set ANDROID_HOME
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
```

### Build Debug APK (untuk testing)
```bash
cd android
./gradlew assembleDebug

# APK output:
# android/app/build/outputs/apk/debug/app-debug.apk
```

### Build Release APK (untuk publish/distribusi)
```bash
cd android
./gradlew assembleRelease

# APK output:
# android/app/build/outputs/apk/release/app-release-unsigned.apk
```

### Sign APK (opsional - untuk Google Play)
```bash
# Generate keystore (hanya sekali)
keytool -genkey -v -keystore dragon-arrow-escape.keystore \
  -alias dragon-arrow-escape -keyalg RSA -keysize 2048 -validity 10000

# Sign APK
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore dragon-arrow-escape.keystore \
  app-release-unsigned.apk dragon-arrow-escape

# Zipalign
zipalign -v 4 app-release-unsigned.apk dragon-arrow-escape-release.apk
```

---

## 📊 Strategi Monetisasi - Memaksimalkan Pendapatan

### 1. **Rewarded Ads** - REVENUE UTAMA 💰💰💰
- **RPM:** $10 - $30 (TERTINGGI!)
- **Kapan:** User klik tombol "Tonton Iklan & Dapatkan Bonus"
- **Reward:** +500 poin bonus
- **Frekuensi:** Unlimited (user-triggered)
- **Tips:** Buat reward menarik agar user mau nonton

### 2. **Interstitial Ads** - REVENUE PASIF 💰💰
- **RPM:** $3 - $8 (MENENGAH)
- **Kapan:** Setiap game over (dengan cooldown 3 menit otomatis)
- **Frekuensi:** Auto, tidak ganggu gameplay
- **Tips:** Cooldown 3 menit cegah user kesal

### 3. **Banner Ads** - REVENUE KONTINYU 💰
- **RPM:** $0.5 - $2 (RENDAH tapi cumulative)
- **Kapan:** Saat di menu utama (hidden saat gameplay)
- **Lokasi:** Bottom screen
- **Tips:** Selalu tampilkan di menu untuk passive income

### Estimasi Pendapatan (100 pengguna aktif/hari)
```
Rewarded Ads:   100 user × 3 ads/day × $0.20 = $60/hari
Interstitial:   100 user × 5 views/day × $0.05 = $25/hari
Banner:         100 user × 50 impressions/day × $0.005 = $25/hari
────────────────────────────────────────────────────────
TOTAL:                                          $110/hari
                                                $3,300/bulan
```

---

## ✅ Checklist Pre-Launch

- [ ] Akun AdMob terdaftar dan verified
- [ ] App ID production sudah dicatat
- [ ] 3 Ad Unit IDs (Rewarded, Interstitial, Banner) sudah dicatat
- [ ] `AndroidManifest.xml` updated dengan App ID production
- [ ] `AdsManager.java` updated dengan 3 Ad Unit IDs production
- [ ] Build APK debug dan test di device fisik
- [ ] Test semua 3 jenis ads muncul dengan benar
- [ ] Test reward bonus bekerja (skor bertambah)
- [ ] Test interstitial muncul setiap game over
- [ ] Build APK release untuk distribusi

---

## 🐛 Troubleshooting

### Iklan tidak muncul
1. ✅ Pastikan device terkoneksi internet
2. ✅ Test IDs berfungsi instant, Production IDs butuh 1-2 jam approval
3. ✅ Cek logcat: `adb logcat | grep -i "admob\|ads"`
4. ✅ Pastikan `google-services.json` ada di `android/app/`

### Error "Ad failed to load"
```
❌ Error code 3: No fill (tidak ada advertiser yang bid)
   → Normal di production, coba lagi nanti
   
❌ Error code 0: Network error
   → Cek koneksi internet
   
❌ Error code 1: Invalid request
   → Cek Ad Unit IDs sudah benar
```

### Revenue tidak masuk
- Production IDs butuh **approval 24-48 jam** setelah app pertama kali load ads
- Revenue baru muncul di dashboard setelah **$10 threshold**
- Pembayaran dilakukan setiap bulan jika sudah >$100

---

## 📱 Testing di Device

### Install Debug APK
```bash
# Build dan install
cd android
./gradlew installDebug

# Atau install manual
adb install app-debug.apk

# Monitor logs
adb logcat | grep -E "DragonArrowEscape|AdsManager|AdRevenue"
```

### Test Ads Functionality
1. ✅ Buka app
2. ✅ Main game sampai game over
3. ✅ Klik "Tonton Iklan & Dapatkan Bonus"
4. ✅ Verifikasi reward +500 poin muncul
5. ✅ Verifikasi interstitial ad muncul di game over berikutnya (setelah 3 menit)

---

## 🚀 Go Live!

Setelah semua checklist selesai:
1. Build release APK
2. Upload ke Google Play Console
3. Submit untuk review
4. Tunggu approval (~2-7 hari)
5. Promosikan app ke user
6. Monitor revenue di AdMob dashboard

**💰 Uang mulai masuk setelah user nonton iklan pertama!**

---

## 📞 Support

- AdMob Help: https://support.google.com/admob
- Google Play Console: https://play.google.com/console
- Android Dev Guide: https://developer.android.com

**Sukses untuk monetisasi game kamu! 🎮💰**
