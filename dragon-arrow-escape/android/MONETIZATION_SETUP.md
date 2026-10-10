# 🎯 Setup Monetisasi AdMob - Dragon Arrow Escape

## ⚠️ MASALAH SAAT INI
Aplikasi masih menggunakan **TEST AD IDs** yang TIDAK menghasilkan uang nyata!

### Test IDs yang Perlu Diganti:
- **App ID**: `ca-app-pub-3940256099942544~3347511713` (TEST)
- **Rewarded Ad Unit**: `ca-app-pub-3940256099942544/5224354917` (TEST)

## 📋 Langkah Setup AdMob (WAJIB untuk Monetisasi)

### 1. Buat Akun AdMob
1. Buka https://admob.google.com
2. Daftar dengan akun Google
3. Lengkapi informasi pembayaran dan pajak
4. Verifikasi akun (bisa butuh 24-48 jam)

### 2. Daftarkan Aplikasi di AdMob
1. Login ke AdMob console
2. Klik **"Add App"** atau **"Tambah Aplikasi"**
3. Pilih platform: **Android**
4. Nama aplikasi: **Dragon Arrow Escape**
5. Package name: **com.dragonarrowescape.game**
6. Catat **App ID** yang diberikan (format: `ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY`)

### 3. Buat Ad Units
Buat 3 jenis ad unit untuk monetisasi optimal:

#### A. Rewarded Ad (Iklan Hadiah)
- Klik **"Ad Units"** → **"Add Ad Unit"** → **"Rewarded"**
- Nama: `Dragon Arrow Reward`
- Catat **Ad Unit ID** (format: `ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY`)

#### B. Interstitial Ad (Iklan Fullscreen)
- Klik **"Ad Units"** → **"Add Ad Unit"** → **"Interstitial"**
- Nama: `Dragon Arrow Interstitial`
- Catat **Ad Unit ID**

#### C. Banner Ad (Iklan Banner)
- Klik **"Ad Units"** → **"Add Ad Unit"** → **Banner**
- Nama: `Dragon Arrow Banner`
- Size: 320x50 (Standard)
- Catat **Ad Unit ID**

### 4. Update Kode dengan Production IDs

#### File: `android/app/src/main/AndroidManifest.xml`
Ganti baris 22:
```xml
<!-- SEBELUM (TEST) -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-3940256099942544~3347511713" />

<!-- SESUDAH (PRODUCTION) -->
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY" />
```

#### File: `android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java`
Ganti baris 24:
```java
// SEBELUM (TEST)
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917";

// SESUDAH (PRODUCTION)
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY";
```

Tambahkan juga untuk Interstitial dan Banner:
```java
private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/ZZZZZZZZZZ";
private static final String BANNER_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/AAAAAAAAAA";
```

### 5. Download google-services.json
1. Di AdMob atau Firebase Console
2. Pilih aplikasi Android Anda
3. Download `google-services.json`
4. Letakkan di: `android/app/google-services.json`

## 💰 Strategi Monetisasi Optimal

### Kapan Menampilkan Iklan?

#### 1. Rewarded Ad (Prioritas Tertinggi - RPM Tertinggi)
- ✅ **Saat game over**: tawarkan "continue" dengan nonton iklan
- ✅ **Unlock item premium**: power-up, skins, karakter baru
- ✅ **Bonus coins**: 2x coins setelah level
- ✅ **Revive/Continue**: kesempatan kedua setelah mati
- 📊 **CPM**: $10-$30 (tertinggi)

#### 2. Interstitial Ad (Sedang)
- ✅ **Setelah complete level** (setiap 2-3 level)
- ✅ **Saat keluar ke menu utama**
- ✅ **Setelah session 3-5 menit**
- ⚠️ **Jangan terlalu sering** (max 1x per 3 menit)
- 📊 **CPM**: $3-$8

#### 3. Banner Ad (Terendah tapi Konsisten)
- ✅ **Di menu utama** (tidak saat gameplay)
- ✅ **Di leaderboard/stats screen**
- ✅ **Di shop/upgrade screen**
- ❌ **Jangan di gameplay aktif** (mengganggu)
- 📊 **CPM**: $0.50-$2

### Frekuensi Iklan yang Sehat
```
Session 10 menit:
- Rewarded: 2-3x (user triggered)
- Interstitial: 1-2x (auto)
- Banner: always on (di menu saja)
```

## 🚀 Quick Setup Script

Jalankan script ini setelah mendapat production IDs:

```bash
cd ~/android-game-bots/dragon-arrow-escape
python setup_admob.py
```

Script akan:
1. ✅ Validasi format Ad IDs
2. ✅ Update AndroidManifest.xml
3. ✅ Update AdsManager.java
4. ✅ Cek keberadaan google-services.json
5. ✅ Backup file lama
6. ✅ Build dan test aplikasi

## 📊 Estimasi Pendapatan

### Asumsi:
- 1000 active users/hari
- Setiap user: 5 rewarded ads, 3 interstitial, 20 banner impressions
- CPM: Rewarded $15, Interstitial $5, Banner $1

### Perhitungan:
```
Rewarded:   5000 impressions × $15 CPM = $75/hari
Interstitial: 3000 impressions × $5 CPM = $15/hari
Banner:     20000 impressions × $1 CPM = $20/hari
----------------------------------------
TOTAL: ~$110/hari = $3,300/bulan
```

**Dengan 10,000 users**: ~$33,000/bulan 💰

## ⚠️ Penting untuk Diingat

### DO ✅
- Tawarkan value untuk rewarded ads (coins, continues, power-ups)
- Buat ads optional tapi menarik
- Track ad performance di AdMob dashboard
- Test ads dengan real device sebelum publish
- Respect user experience - jangan spam iklan

### DON'T ❌
- Jangan klik iklan sendiri (banned permanently!)
- Jangan paksa user nonton iklan terlalu sering
- Jangan tampilkan ads saat gameplay aktif
- Jangan misleading - jangan bilang "Loading" padahal ads
- Jangan lupa ganti TEST IDs ke PRODUCTION IDs!

## 🔍 Validasi Setup

Sebelum publish, cek:
- [ ] App ID production sudah di AndroidManifest.xml
- [ ] Semua Ad Unit IDs production (bukan test)
- [ ] google-services.json ada di android/app/
- [ ] Build berhasil tanpa error
- [ ] Test ads muncul di real device
- [ ] AdMob dashboard showing impressions

## 🐛 Troubleshooting

### Ads tidak muncul
1. Cek logcat: `adb logcat | grep -i "ads"`
2. Pastikan internet tersedia
3. Tunggu beberapa jam setelah setup (AdMob butuh waktu)
4. Cek AdMob dashboard - app sudah approved?

### "Ad failed to load"
- Normal di development/testing
- Production ads butuh 24-48 jam untuk aktif
- Cek Ad Unit IDs benar

### Revenue tidak masuk
- AdMob butuh minimum $100 untuk payout
- Cek payment settings di AdMob console
- Verifikasi identitas dan pajak

## 📞 Support

Masalah? Kontak:
- AdMob Support: https://support.google.com/admob
- Documentation: https://developers.google.com/admob/android/quick-start
