# Dragon Arrow Escape - Panduan Monetisasi dengan Google AdMob

## Overview
Aplikasi Android game "Dragon Arrow Escape" telah diintegrasikan dengan Google Mobile Ads SDK untuk menghasilkan revenue melalui Rewarded Ads.

## Fitur Monetisasi
1. **Rewarded Ads** - User dapat menonton iklan untuk mendapatkan bonus poin
2. **Seamless Integration** - Iklan terintegrasi dengan gameplay
3. **User-Friendly** - Dialog reward yang menarik dan responsif

## Langkah-Langkah Setup

### 1. Daftar di Google AdMob
- Kunjungi https://admob.google.com
- Login dengan akun Google Anda
- Daftarkan aplikasi Android
- Buat Ad Unit untuk Rewarded Ads
- Catat Ad Unit ID (format: ca-app-pub-xxxxxxxxxxxxxxxx/yyyyyyyyyyyyyy)

### 2. Update Ad Unit ID
Edit file `AdsManager.java`:
```java
private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-YOUR-ADMOB-ID/YOUR-UNIT-ID";
```

### 3. Update App ID di AndroidManifest.xml
Edit `AndroidManifest.xml`:
```xml
<meta-data
    android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-xxxxxxxxxxxxxxxx~yyyyyyyyyyyyyy" />
```

### 4. Build & Deployment

#### Build APK
```bash
cd android
./gradlew assembleRelease
```

#### Install untuk Testing
```bash
adb install android/app/build/outputs/apk/release/app-release.apk
```

### 5. Testing dengan Test Ad Unit
Gunakan Ad Unit ID test untuk development:
- **Rewarded Ads Test ID**: `ca-app-pub-3940256099942544/5224354917`

## Cara Kerja Monetisasi

### User Flow
1. Game Over/Permainan Selesai
2. User klik tombol "Tonton Iklan & Dapatkan Bonus"
3. Rewarded Ad dimuat dan ditampilkan
4. User menonton iklan sampai selesai
5. Terima reward (+500 poin per reward)
6. Mulai game baru dengan bonus poin

### Technical Flow
1. **MainActivity** - Inisialisasi Google Mobile Ads SDK
2. **AdsManager** - Handle loading & menampilkan rewarded ads
3. **JavaScript Interface** - Komunikasi antara WebView dan Native Code
4. **Game HTML** - UI untuk trigger watch ads

## File yang Dimodifikasi

### Java Files
- `MainActivity.java` - Activity utama dengan Ads integration
- `AdsManager.java` - Manager untuk rewarded ads

### Configuration Files
- `build.gradle` (root) - Gradle dependencies
- `app/build.gradle` - App-specific dependencies
- `AndroidManifest.xml` - Permissions dan metadata

### Assets
- `index.html` - Game dengan UI reward ads

## Revenue Model

### Earning Calculation
- **CPM** (Cost Per Mille): Rata-rata $2-10 per 1000 impressions
- **RPM** (Revenue Per Mille): Rata-rata $1-5 per 1000 impressions
- **Completion Rate**: ~60-80% user akan menonton iklan sampai selesai

### Contoh Proyeksi
- 1000 DAU (Daily Active Users)
- 2 ads per user per day = 2000 impressions
- RPM $3 = Revenue harian ~$6
- Revenue bulanan = ~$180

## Best Practices

1. **Frequency Capping** - Limit ads untuk menghindari user annoyance
2. **Placement** - Tunjukkan ads di moment yang tepat (saat game over)
3. **User Experience** - Pastikan ads tidak mengganggu gameplay
4. **Testing** - Gunakan test IDs sebelum go live
5. **Monitoring** - Monitor performance di AdMob dashboard

## AdMob Dashboard

Setelah setup selesai, monitor metrics di https://admob.google.com:
- Impressions
- Clicks
- RPM / CPM
- Estimated Earnings

## Troubleshooting

### Ads tidak muncul
1. Pastikan internet connection aktif
2. Cek apakah Ad Unit ID benar
3. Pastikan app sudah terdaftar di AdMob
4. Gunakan test Ad Unit ID untuk testing

### Low RPM
1. Tingkatkan traffic/DAU
2. Optimize placement iklan
3. Cek demographic target
4. Monitor completion rate

### JavaScript Interface Error
1. Pastikan `@JavascriptInterface` decorator ada
2. Pastikan method public
3. Cek WebView settings (JavaScript enabled)

## Next Steps

1. Lakukan testing dengan test Ad Unit ID
2. Registrasi app di Google Play Store
3. Submit untuk review AdMob
4. Setelah approval, update dengan production Ad Unit ID
5. Monitor earnings di AdMob dashboard

## Support Resources

- Google Mobile Ads SDK: https://developers.google.com/admob/android/start
- AdMob Best Practices: https://support.google.com/admob/answer/6128017
- Troubleshooting: https://support.google.com/admob/answer/9972781