#!/bin/bash
# Script untuk verifikasi setup monetisasi
# Usage: ./verify_monetization.sh

echo "🔍 Dragon Arrow Escape - Monetization Verification"
echo "=================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0

function check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASS++))
}

function check_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAIL++))
}

function check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARN++))
}

function check_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo "📋 Checking files..."
echo ""

# Check AndroidManifest.xml
if [ -f "android/app/src/main/AndroidManifest.xml" ]; then
    check_pass "AndroidManifest.xml exists"
    
    # Check if using test IDs
    if grep -q "ca-app-pub-3940256099942544" android/app/src/main/AndroidManifest.xml; then
        check_fail "AndroidManifest.xml masih menggunakan TEST App ID"
        echo "          Action: Update dengan production ID dari AdMob"
    else
        # Extract App ID
        APP_ID=$(grep -o 'ca-app-pub-[0-9]\{16\}~[0-9]\{10\}' android/app/src/main/AndroidManifest.xml)
        if [ -n "$APP_ID" ]; then
            check_pass "Production App ID detected: $APP_ID"
        else
            check_fail "App ID format tidak valid"
        fi
    fi
else
    check_fail "AndroidManifest.xml not found"
fi

echo ""

# Check AdsManager.java
if [ -f "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java" ]; then
    check_pass "AdsManager.java exists"
    
    # Check if using test IDs
    TEST_COUNT=$(grep -c "ca-app-pub-3940256099942544" android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java)
    
    if [ $TEST_COUNT -gt 0 ]; then
        check_fail "AdsManager.java masih menggunakan $TEST_COUNT TEST Ad Unit IDs"
        echo "          Action: Update dengan production IDs dari AdMob"
        echo "          Run: ./update_production_ids.sh"
    else
        check_pass "Production Ad Unit IDs detected"
        
        # Extract and show IDs
        REWARDED_ID=$(grep "REWARDED_AD_UNIT_ID" android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java | grep -o 'ca-app-pub-[0-9]\{16\}/[0-9]\{10\}')
        INTERSTITIAL_ID=$(grep "INTERSTITIAL_AD_UNIT_ID" android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java | grep -o 'ca-app-pub-[0-9]\{16\}/[0-9]\{10\}')
        BANNER_ID=$(grep "BANNER_AD_UNIT_ID" android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java | grep -o 'ca-app-pub-[0-9]\{16\}/[0-9]\{10\}')
        
        if [ -n "$REWARDED_ID" ]; then
            check_info "Rewarded ID: $REWARDED_ID"
        fi
        if [ -n "$INTERSTITIAL_ID" ]; then
            check_info "Interstitial ID: $INTERSTITIAL_ID"
        fi
        if [ -n "$BANNER_ID" ]; then
            check_info "Banner ID: $BANNER_ID"
        fi
    fi
else
    check_fail "AdsManager.java not found"
fi

echo ""

# Check MainActivity.java
if [ -f "android/app/src/main/java/com/dragonarrowescape/game/MainActivity.java" ]; then
    check_pass "MainActivity.java exists"
    
    # Check JavaScript interface
    if grep -q "addJavascriptInterface.*AdsJavascriptInterface" android/app/src/main/java/com/dragonarrowescape/game/MainActivity.java; then
        check_pass "JavaScript interface configured"
    else
        check_warn "JavaScript interface tidak ditemukan"
    fi
else
    check_fail "MainActivity.java not found"
fi

echo ""

# Check google-services.json
if [ -f "android/app/google-services.json" ]; then
    check_pass "google-services.json exists"
    
    # Check if dummy/template
    if grep -q "dragon-arrow-escape-xxxxx" android/app/google-services.json; then
        check_warn "google-services.json masih template/dummy"
        echo "          Action: Download dari Firebase Console"
    else
        check_pass "google-services.json configured"
    fi
else
    check_fail "google-services.json not found"
fi

echo ""

# Check build.gradle
if [ -f "android/app/build.gradle" ]; then
    check_pass "build.gradle exists"
    
    # Check Google Services plugin
    if grep -q "com.google.gms.google-services" android/app/build.gradle; then
        check_pass "Google Services plugin configured"
    else
        check_fail "Google Services plugin not found"
    fi
    
    # Check AdMob dependency
    if grep -q "play-services-ads" android/app/build.gradle; then
        AD_VERSION=$(grep "play-services-ads" android/app/build.gradle | grep -o '[0-9]\{2\}\.[0-9]\.[0-9]')
        check_pass "AdMob SDK dependency found (version: $AD_VERSION)"
    else
        check_fail "AdMob SDK dependency not found"
    fi
else
    check_fail "build.gradle not found"
fi

echo ""

# Check assets
if [ -f "android/app/src/main/assets/index.html" ]; then
    check_pass "Game HTML exists"
    
    # Check if ads integrated in HTML
    if grep -q "AndroidAds" android/app/src/main/assets/index.html; then
        check_pass "HTML integrated with AndroidAds"
    else
        check_warn "AndroidAds integration not found in HTML"
    fi
else
    check_fail "index.html not found"
fi

echo ""

# Check if APK exists
if [ -f "android/app/build/outputs/apk/release/app-release.apk" ]; then
    APK_SIZE=$(du -h android/app/build/outputs/apk/release/app-release.apk | cut -f1)
    check_pass "Release APK exists (size: $APK_SIZE)"
else
    check_warn "Release APK not built yet"
    echo "          Action: Run './gradlew assembleRelease'"
fi

echo ""
echo "=================================================="
echo "📊 Summary"
echo "=================================================="
echo ""
echo -e "✅ Passed:  ${GREEN}$PASS${NC}"
echo -e "⚠️  Warnings: ${YELLOW}$WARN${NC}"
echo -e "❌ Failed:  ${RED}$FAIL${NC}"
echo ""

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}❌ Ada masalah yang harus diperbaiki!${NC}"
    echo ""
    echo "🔧 Recommended actions:"
    echo "1. Update production IDs: ./update_production_ids.sh"
    echo "2. Build APK: cd android && ./gradlew assembleRelease"
    echo "3. Read full guide: PANDUAN_MONETISASI_PRODUCTION.md"
    exit 1
elif [ $WARN -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Setup sudah OK, tapi ada warnings${NC}"
    echo ""
    echo "💡 Recommendations:"
    if grep -q "ca-app-pub-3940256099942544" android/app/src/main/AndroidManifest.xml 2>/dev/null || \
       grep -q "ca-app-pub-3940256099942544" android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java 2>/dev/null; then
        echo "• Update to production IDs untuk menghasilkan uang nyata"
        echo "  Run: ./update_production_ids.sh"
    fi
    if [ ! -f "android/app/build/outputs/apk/release/app-release.apk" ]; then
        echo "• Build production APK"
        echo "  Run: cd android && ./gradlew assembleRelease"
    fi
    exit 0
else
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "🚀 Ready to deploy!"
    echo ""
    echo "Next steps:"
    echo "1. Test APK on real device"
    echo "2. Monitor AdMob dashboard for impressions"
    echo "3. Track revenue after 24-48 hours"
    exit 0
fi
