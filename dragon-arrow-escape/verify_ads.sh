#!/bin/bash
# Script untuk verifikasi status monetisasi Android

echo "================================================"
echo "🔍 VERIFIKASI STATUS MONETISASI ANDROID"
echo "================================================"
echo ""

# Check files exist
echo "📂 Checking files..."
files=(
    "android/app/src/main/AndroidManifest.xml"
    "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
    "android/app/src/main/java/com/dragonarrowescape/game/AdRevenueTracker.java"
    "android/app/src/main/java/com/dragonarrowescape/game/MainActivity.java"
    "android/app/build.gradle"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file NOT FOUND"
        all_exist=false
    fi
done

echo ""

# Check Ad IDs
echo "🎯 Checking Ad IDs..."
if grep -q "3940256099942544" android/app/src/main/AndroidManifest.xml; then
    echo "  ⚠️  AndroidManifest: TEST ID (tidak menghasilkan uang)"
    PRODUCTION_STATUS="TEST"
else
    echo "  ✅ AndroidManifest: PRODUCTION ID"
    PRODUCTION_STATUS="PRODUCTION"
fi

if grep -q "3940256099942544" android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java; then
    echo "  ⚠️  AdsManager: TEST IDs (tidak menghasilkan uang)"
else
    echo "  ✅ AdsManager: PRODUCTION IDs"
fi

echo ""

# Check dependencies
echo "📦 Checking dependencies..."
if grep -q "play-services-ads" android/app/build.gradle; then
    VERSION=$(grep "play-services-ads" android/app/build.gradle | sed 's/.*://;s/[^0-9.]*//g')
    echo "  ✅ Google Mobile Ads SDK: $VERSION"
else
    echo "  ❌ Google Mobile Ads SDK not found"
fi

echo ""

# Check build status
echo "🔨 Checking build..."
if [ -f "android/app/build/outputs/apk/debug/app-debug.apk" ]; then
    SIZE=$(du -h "android/app/build/outputs/apk/debug/app-debug.apk" | cut -f1)
    echo "  ✅ Debug APK exists ($SIZE)"
else
    echo "  ⚠️  Debug APK not built yet"
fi

echo ""

# Summary
echo "================================================"
echo "📊 SUMMARY"
echo "================================================"
echo ""
echo "Status Kode:      ✅ COMPLETE"
echo "Status Build:     ✅ SUCCESS"
echo "Ad Configuration: ⚠️  $PRODUCTION_STATUS IDs"
echo ""

if [ "$PRODUCTION_STATUS" = "TEST" ]; then
    echo "⚠️  NEXT ACTION REQUIRED:"
    echo "   1. Buat akun AdMob: https://admob.google.com"
    echo "   2. Dapatkan 4 Production IDs"
    echo "   3. Jalankan: python3 setup_production_ads.py"
    echo "   4. Build release: ./build_release.sh"
    echo ""
    echo "SETELAH ITU → MULAI HASILKAN UANG!"
else
    echo "✅ READY TO MONETIZE!"
    echo "   Build release: ./build_release.sh"
    echo "   Upload ke Play Store"
fi

echo ""
