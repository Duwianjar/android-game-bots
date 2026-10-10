#!/bin/bash
# Script Verifikasi - Cek Kesiapan Monetisasi
# Jalankan: bash verify_ads_ready.sh

echo "=================================="
echo "   VERIFIKASI MONETISASI ANDROID"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Function untuk check file
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅ Found: $1${NC}"
        return 0
    else
        echo -e "${RED}❌ Missing: $1${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Function untuk check TEST IDs
check_test_ids() {
    local file="$1"
    if grep -q "3940256099942544" "$file" 2>/dev/null; then
        echo -e "${RED}❌ TEST IDs found in: $file${NC}"
        echo -e "${YELLOW}   → Must replace with Production IDs!${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    else
        echo -e "${GREEN}✅ No TEST IDs in: $file${NC}"
        return 0
    fi
}

echo "=== 1. Checking Files ==="
echo ""

# Check key files
check_file "android/app/src/main/AndroidManifest.xml"
check_file "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
check_file "android/app/src/main/java/com/dragonarrowescape/game/AdRevenueTracker.java"
check_file "android/app/src/main/java/com/dragonarrowescape/game/MainActivity.java"
check_file "android/app/src/main/assets/index.html"
check_file "android/app/src/main/assets/android-ads-bridge.js"

echo ""
echo "=== 2. Checking Ad IDs ==="
echo ""

# Check TEST IDs
if [ -f "android/app/src/main/AndroidManifest.xml" ]; then
    check_test_ids "android/app/src/main/AndroidManifest.xml"
fi

if [ -f "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java" ]; then
    check_test_ids "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
fi

echo ""
echo "=== 3. Checking Dependencies ==="
echo ""

# Check build.gradle
if [ -f "android/app/build.gradle" ]; then
    if grep -q "com.google.android.gms:play-services-ads" "android/app/build.gradle"; then
        echo -e "${GREEN}✅ AdMob SDK dependency found${NC}"
    else
        echo -e "${RED}❌ AdMob SDK dependency missing${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}❌ build.gradle not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "=== 4. Checking Game Integration ==="
echo ""

# Check game HTML
if [ -f "android/app/src/main/assets/index.html" ]; then
    if grep -q "AndroidAds" "android/app/src/main/assets/index.html"; then
        echo -e "${GREEN}✅ AndroidAds interface integrated in game${NC}"
    else
        echo -e "${YELLOW}⚠️  AndroidAds not found in game HTML${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Check ads bridge
if [ -f "android/app/src/main/assets/android-ads-bridge.js" ]; then
    if grep -q "class AndroidAdsBridge" "android/app/src/main/assets/android-ads-bridge.js"; then
        echo -e "${GREEN}✅ AndroidAdsBridge class found${NC}"
    else
        echo -e "${RED}❌ AndroidAdsBridge class missing${NC}"
        ERRORS=$((ERRORS + 1))
    fi
fi

echo ""
echo "=== 5. Checking Permissions ==="
echo ""

# Check permissions
if [ -f "android/app/src/main/AndroidManifest.xml" ]; then
    if grep -q "android.permission.INTERNET" "android/app/src/main/AndroidManifest.xml"; then
        echo -e "${GREEN}✅ INTERNET permission declared${NC}"
    else
        echo -e "${RED}❌ INTERNET permission missing${NC}"
        ERRORS=$((ERRORS + 1))
    fi
    
    if grep -q "android.permission.ACCESS_NETWORK_STATE" "android/app/src/main/AndroidManifest.xml"; then
        echo -e "${GREEN}✅ ACCESS_NETWORK_STATE permission declared${NC}"
    else
        echo -e "${YELLOW}⚠️  ACCESS_NETWORK_STATE permission missing (recommended)${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

echo ""
echo "=== SUMMARY ==="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ ALL CHECKS PASSED!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}Monetization code: ✅ READY${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  NEXT STEP:${NC}"
    echo "   1. Setup Production AdMob IDs"
    echo "   2. Run: python3 setup_production_ids.py"
    echo ""
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⚠️  $WARNINGS WARNING(S)${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Code is ready but has minor warnings."
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ $ERRORS ERROR(S), $WARNINGS WARNING(S)${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Please fix errors before proceeding."
    exit 1
fi

echo ""
