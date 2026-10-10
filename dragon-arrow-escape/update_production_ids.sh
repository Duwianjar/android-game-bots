#!/bin/bash
# Script untuk update Production Ad IDs
# Dragon Arrow Escape - AdMob Setup Helper

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MANIFEST_FILE="$SCRIPT_DIR/android/app/src/main/AndroidManifest.xml"
ADSMANAGER_FILE="$SCRIPT_DIR/android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
GOOGLE_SERVICES="$SCRIPT_DIR/android/app/google-services.json"

echo "🚀 Dragon Arrow Escape - Production AdMob Setup"
echo "================================================"
echo ""

# Check if files exist
if [ ! -f "$MANIFEST_FILE" ]; then
    echo "❌ Error: AndroidManifest.xml not found!"
    exit 1
fi

if [ ! -f "$ADSMANAGER_FILE" ]; then
    echo "❌ Error: AdsManager.java not found!"
    exit 1
fi

echo "📋 Masukkan Production IDs dari AdMob Dashboard"
echo "   (Format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY)"
echo ""

# 1. App ID
echo "1️⃣  AdMob App ID:"
echo "   Dapatkan dari: AdMob Console → Apps → App Settings"
read -p "   App ID: " APP_ID

if [[ ! "$APP_ID" =~ ^ca-app-pub-[0-9]+~[0-9]+$ ]]; then
    echo "⚠️  Warning: App ID format tidak sesuai (seharusnya: ca-app-pub-XXX~YYY)"
    read -p "   Lanjutkan? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        echo "Dibatalkan."
        exit 1
    fi
fi

echo ""

# 2. Rewarded Ad Unit ID
echo "2️⃣  Rewarded Ad Unit ID:"
echo "   Dapatkan dari: AdMob → Ad Units → Bonus Reward"
read -p "   Rewarded ID: " REWARDED_ID

if [[ ! "$REWARDED_ID" =~ ^ca-app-pub-[0-9]+/[0-9]+$ ]]; then
    echo "⚠️  Warning: Format tidak sesuai (seharusnya: ca-app-pub-XXX/YYY)"
fi

echo ""

# 3. Interstitial Ad Unit ID
echo "3️⃣  Interstitial Ad Unit ID:"
echo "   Dapatkan dari: AdMob → Ad Units → Level Transition"
read -p "   Interstitial ID: " INTERSTITIAL_ID

if [[ ! "$INTERSTITIAL_ID" =~ ^ca-app-pub-[0-9]+/[0-9]+$ ]]; then
    echo "⚠️  Warning: Format tidak sesuai"
fi

echo ""

# 4. Banner Ad Unit ID
echo "4️⃣  Banner Ad Unit ID:"
echo "   Dapatkan dari: AdMob → Ad Units → Menu Banner"
read -p "   Banner ID: " BANNER_ID

if [[ ! "$BANNER_ID" =~ ^ca-app-pub-[0-9]+/[0-9]+$ ]]; then
    echo "⚠️  Warning: Format tidak sesuai"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 REVIEW PRODUCTION IDs:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "App ID:          $APP_ID"
echo "Rewarded:        $REWARDED_ID"
echo "Interstitial:    $INTERSTITIAL_ID"
echo "Banner:          $BANNER_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "✅ Confirm dan update semua file? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "❌ Dibatalkan. Tidak ada perubahan."
    exit 0
fi

echo ""
echo "🔧 Updating files..."

# Backup files
echo "📦 Creating backups..."
cp "$MANIFEST_FILE" "$MANIFEST_FILE.backup"
cp "$ADSMANAGER_FILE" "$ADSMANAGER_FILE.backup"
echo "   ✓ Backups created (.backup)"

# Update AndroidManifest.xml
echo "📝 Updating AndroidManifest.xml..."
sed -i.tmp "s/ca-app-pub-3940256099942544~3347511713/$APP_ID/g" "$MANIFEST_FILE"
rm "$MANIFEST_FILE.tmp"
echo "   ✓ App ID updated"

# Update AdsManager.java
echo "📝 Updating AdsManager.java..."

# Rewarded
sed -i.tmp "s|private static final String REWARDED_AD_UNIT_ID = \"ca-app-pub-3940256099942544/5224354917\"|private static final String REWARDED_AD_UNIT_ID = \"$REWARDED_ID\"|g" "$ADSMANAGER_FILE"
rm "$ADSMANAGER_FILE.tmp"

# Interstitial
sed -i.tmp "s|private static final String INTERSTITIAL_AD_UNIT_ID = \"ca-app-pub-3940256099942544/1033173712\"|private static final String INTERSTITIAL_AD_UNIT_ID = \"$INTERSTITIAL_ID\"|g" "$ADSMANAGER_FILE"
rm "$ADSMANAGER_FILE.tmp"

# Banner
sed -i.tmp "s|private static final String BANNER_AD_UNIT_ID = \"ca-app-pub-3940256099942544/6300978111\"|private static final String BANNER_AD_UNIT_ID = \"$BANNER_ID\"|g" "$ADSMANAGER_FILE"
rm "$ADSMANAGER_FILE.tmp"

echo "   ✓ All Ad Unit IDs updated"

# Check google-services.json
echo ""
echo "📂 Checking google-services.json..."
if [ ! -f "$GOOGLE_SERVICES" ]; then
    echo "⚠️  WARNING: google-services.json NOT FOUND!"
    echo ""
    echo "📥 DOWNLOAD google-services.json:"
    echo "   1. Buka: https://admob.google.com"
    echo "   2. Go to: Apps → Dragon Arrow Escape → App Settings"
    echo "   3. Click: 'Download google-services.json'"
    echo "   4. Save to: $GOOGLE_SERVICES"
    echo ""
    echo "⚠️  App TIDAK akan berfungsi tanpa file ini!"
else
    echo "   ✓ google-services.json found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SETUP COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1️⃣  Download google-services.json (jika belum):"
echo "   → https://admob.google.com"
echo "   → Simpan ke: android/app/google-services.json"
echo ""
echo "2️⃣  Build Release APK:"
echo "   cd android"
echo "   ./gradlew assembleRelease"
echo ""
echo "3️⃣  Test APK:"
echo "   adb install app/build/outputs/apk/release/app-release.apk"
echo ""
echo "4️⃣  Verify ads:"
echo "   - Main game → Die → Watch Ad button"
echo "   - Check logcat: adb logcat | grep AdMob"
echo ""
echo "5️⃣  Upload ke Play Store:"
echo "   → https://play.google.com/console"
echo ""
echo "💰 Setelah approved → Mulai hasilkan uang!"
echo ""
echo "🔄 Rollback jika perlu:"
echo "   mv android/app/src/main/AndroidManifest.xml.backup AndroidManifest.xml"
echo "   mv android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java.backup AdsManager.java"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
