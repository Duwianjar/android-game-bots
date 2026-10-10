# 🐉 Dragon Arrow Escape

Arcade survival game Android dengan sistem monetisasi AdMob lengkap.

## 🎮 Game Features

- **Joystick controls** - Kontrol sentuh responsif
- **Obstacle avoidance** - Hindari panah dan rintangan
- **Progressive difficulty** - Semakin lama semakin sulit
- **High score tracking** - Simpan rekor terbaik Anda
- **Arcade gameplay** - Simple, addictive, replayable

## 💰 Monetization (AdMob)

### Implemented & Ready

- ✅ **Rewarded Ads** ($10-$30 RPM)
  - Continue game dengan bonus 500 poin
  - Double coins setelah game over
  - User-triggered, tidak mengganggu gameplay
  
- ✅ **Interstitial Ads** ($3-$8 RPM)
  - Auto-show setiap 2-3 game over
  - Built-in 3 menit cooldown
  - Smart frequency control
  
- ✅ **Banner Ads** ($0.5-$2 RPM)
  - Auto-show di menu dan game over
  - Auto-hide saat gameplay
  - Passive revenue stream

### Revenue Tracking

- Real-time impression tracking
- Daily/total statistics
- Performance analytics
- JSON export untuk dashboard

## 🚀 Quick Start

### Development (Test Ads)

```bash
# Clone/navigate ke project
cd android-game-bots/dragon-arrow-escape/android

# Build debug APK
./gradlew assembleDebug

# Install ke device
adb install app/build/outputs/apk/debug/app-debug.apk

# Watch logs
adb logcat -s DragonArrowEscape:V AdsManager:V
```

### Production (Real Money)

⚠️ **PENTING**: Aplikasi saat ini masih pakai TEST AD IDs!

**Untuk menghasilkan uang nyata:**

1. **Baca panduan lengkap**: [PRODUCTION_SETUP.md](./PRODUCTION_SETUP.md)
2. Daftar AdMob & dapatkan Production Ad Unit IDs
3. Ganti TEST IDs dengan PRODUCTION IDs
4. Build signed release
5. Upload ke Google Play Store
6. Mulai dapat revenue! 💰

## 📊 Revenue Estimation

| Daily Active Users | Estimated Monthly Revenue |
|-------------------|---------------------------|
| 1,000 DAU | $2,000 - $3,000 |
| 10,000 DAU | $20,000 - $30,000 |
| 100,000 DAU | $200,000+ |

*Tergantung geo, engagement, dan fill rate*

## 📁 Project Structure

```
dragon-arrow-escape/
├── android/                          # Android project
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── java/com/dragonarrowescape/game/
│   │   │   │   ├── MainActivity.java         # Entry point
│   │   │   │   ├── AdsManager.java          # Ad monetization
│   │   │   │   └── AdRevenueTracker.java    # Analytics
│   │   │   ├── assets/
│   │   │   │   ├── index.html               # HTML5 game
│   │   │   │   └── android-ads-bridge.js    # JS ↔ Android
│   │   │   ├── AndroidManifest.xml          # ⚠️ Ganti App ID
│   │   │   └── res/                         # Resources
│   │   └── build.gradle                     # ⚠️ Dependencies
│   └── build.gradle                         # Project config
├── PRODUCTION_SETUP.md                      # 📖 Panduan lengkap
├── CHANGELOG.md                             # Version history
└── README.md                                # This file
```

## 🔧 Configuration

### File yang WAJIB diganti untuk Production:

1. **AndroidManifest.xml** (line 41)
   ```xml
   <meta-data
       android:name="com.google.android.gms.ads.APPLICATION_ID"
       android:value="ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY" />
   ```

2. **AdsManager.java** (line 42-50)
   ```java
   private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/1111111111";
   private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/2222222222";
   private static final String BANNER_AD_UNIT_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/3333333333";
   ```

## 🧪 Testing

### Test Ads (Development)

Gunakan TEST Ad Unit IDs yang sudah ada (default) - **tidak menghasilkan uang**.

### Real Ads (Production)

⚠️ **JANGAN klik iklan sendiri!** Bisa banned dari AdMob.

Gunakan test device:
```java
AdRequest adRequest = new AdRequest.Builder()
    .addTestDevice("YOUR_DEVICE_ID")
    .build();
```

## 📱 Build Commands

```bash
# Debug build (untuk testing)
./gradlew assembleDebug

# Release build (untuk Play Store)
./gradlew assembleRelease

# AAB bundle (recommended untuk Play Store)
./gradlew bundleRelease

# Install ke device
./gradlew installDebug

# Clean build
./gradlew clean
```

## 🐛 Troubleshooting

### "Ads tidak muncul"

1. Pastikan device punya internet
2. Tunggu 1-2 jam setelah buat ad unit baru
3. Check logcat untuk error messages
4. Verify Ad Unit IDs benar

### "No fill" di production

1. Enable "Optimize" di AdMob console
2. Setup mediation (Meta, Unity Ads)
3. Check geo targeting
4. Normal di negara dengan low fill rate

### "Build failed"

```bash
./gradlew clean
./gradlew assembleDebug --stacktrace
```

## 📚 Documentation

- **[PRODUCTION_SETUP.md](./PRODUCTION_SETUP.md)** - Panduan lengkap 10 langkah untuk publish
- **[CHANGELOG.md](./CHANGELOG.md)** - Version history & updates
- [AdMob Documentation](https://developers.google.com/admob/android/quick-start)
- [Google Play Console Help](https://support.google.com/googleplay/android-developer)

## 🎯 Monetization Best Practices

### ✅ DO:
- Show rewarded ads as user-triggered options
- Respect interstitial cooldown (3 menit)
- Hide banner ads during gameplay
- Track metrics dan optimize
- A/B test different ad placements

### ❌ DON'T:
- Spam interstitial ads (user akan uninstall)
- Show banner ads during gameplay
- Click your own ads (ban!)
- Force users to watch ads
- Fake ad impressions (permanent ban!)

## 🏆 Success Metrics

Monitor di AdMob console:

- **eCPM** (effective Cost Per Mille)
  - Rewarded: target >$10
  - Interstitial: target >$3
  - Banner: target >$0.5

- **Fill Rate**: target >90%
- **Impression Rate**: target >80%
- **User Retention**:
  - Day 1: target >40%
  - Day 7: target >20%
  - Day 30: target >10%

## 💳 Payment

- **Minimum threshold**: $100 USD
- **Payment schedule**: Monthly (around 21st)
- **Setup**: AdMob Console → Payments → Add payment method
- **Indonesia**: Gunakan bank transfer (recommended)

## 📞 Support

- **Issues**: Check [PRODUCTION_SETUP.md](./PRODUCTION_SETUP.md) troubleshooting section
- **AdMob**: https://support.google.com/admob
- **Play Console**: https://support.google.com/googleplay/android-developer

## 📄 License

Copyright © 2026. All rights reserved.

---

**🚀 Ready to make money from ads?**

1. Read [PRODUCTION_SETUP.md](./PRODUCTION_SETUP.md)
2. Setup AdMob & get Production IDs
3. Replace TEST IDs
4. Build & publish to Play Store
5. Watch the revenue grow! 💰

**With 1,000 daily active users, you can earn $2,000-3,000/month.**

Good luck! 🎮💰
