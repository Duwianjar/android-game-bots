#!/bin/bash
# Script otomatis untuk build Release APK
# APK ini yang akan di-upload ke Play Store

set -e  # Exit on error

echo "=================================="
echo "🚀 Building Release APK"
echo "=================================="
echo ""

# Check apakah di direktori yang benar
if [ ! -f "android/app/build.gradle" ]; then
    echo "❌ Error: Jalankan script ini dari direktori dragon-arrow-escape/"
    exit 1
fi

# Check apakah sudah menggunakan Production IDs
echo "🔍 Checking Ad IDs..."
if grep -q "3940256099942544" android/app/src/main/AndroidManifest.xml; then
    echo "⚠️  WARNING: AndroidManifest masih menggunakan TEST ID!"
    echo "⚠️  Iklan TIDAK akan menghasilkan uang nyata!"
    echo ""
    read -p "Lanjutkan build dengan TEST ID? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Build dibatalkan. Jalankan setup_production_ads.py dulu."
        exit 1
    fi
else
    echo "✅ Production IDs detected"
fi

echo ""
echo "📦 Cleaning previous builds..."
cd android
./gradlew clean

echo ""
echo "🔨 Building Release APK..."
./gradlew assembleRelease

echo ""
echo "=================================="
echo "✅ BUILD SUCCESSFUL!"
echo "=================================="
echo ""

APK_PATH="app/build/outputs/apk/release/app-release-unsigned.apk"
if [ -f "$APK_PATH" ]; then
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo "📱 APK Location: $APK_PATH"
    echo "📊 APK Size: $APK_SIZE"
    echo ""
    echo "Next steps:"
    echo "1. Sign APK (required untuk Play Store)"
    echo "2. Test di real device: adb install $APK_PATH"
    echo "3. Upload ke Play Store Console"
else
    echo "⚠️  APK not found at expected location"
    echo "Check: android/app/build/outputs/apk/"
fi

echo ""
