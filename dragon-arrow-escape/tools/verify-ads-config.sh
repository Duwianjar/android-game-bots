#!/bin/bash

# Script untuk verifikasi konfigurasi ads sebelum production
# Usage: ./tools/verify-ads-config.sh

set -e

echo "🔍 VERIFIKASI KONFIGURASI ADS"
echo "=============================="
echo ""

PROJECT_ROOT="/Users/macbookair/android-game-bots/dragon-arrow-escape"
MANIFEST="$PROJECT_ROOT/android/app/src/main/AndroidManifest.xml"
ADS_MANAGER="$PROJECT_ROOT/android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

echo "📁 Checking files..."

# Check files exist
if [ ! -f "$MANIFEST" ]; then
    echo -e "${RED}❌ AndroidManifest.xml not found!${NC}"
    exit 1
fi

if [ ! -f "$ADS_MANAGER" ]; then
    echo -e "${RED}❌ AdsManager.java not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Files found${NC}"
echo ""

# Check AndroidManifest.xml for App ID
echo "1️⃣ Checking AndroidManifest.xml..."
echo "-----------------------------------"

APP_ID=$(grep -A1 "com.google.android.gms.ads.APPLICATION_ID" "$MANIFEST" | grep "android:value" | sed 's/.*value="\([^"]*\)".*/\1/')

if [ -z "$APP_ID" ]; then
    echo -e "${RED}❌ ERROR: App ID tidak ditemukan!${NC}"
    ((ERRORS++))
else
    echo "App ID: $APP_ID"
    
    if [[ $APP_ID == *"3940256099942544"* ]]; then
        echo -e "${RED}❌ ERROR: Masih menggunakan TEST App ID!${NC}"
        echo -e "${YELLOW}   → Ganti dengan Production App ID dari AdMob${NC}"
        echo -e "${YELLOW}   → File: $MANIFEST${NC}"
        echo -e "${YELLOW}   → Baris ~40${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}✅ Production App ID detected${NC}"
    fi
fi

echo ""

# Check AdsManager.java for Ad Unit IDs
echo "2️⃣ Checking AdsManager.java..."
echo "-------------------------------"

REWARDED_ID=$(grep "REWARDED_AD_UNIT_ID" "$ADS_MANAGER" | head -1 | sed 's/.*"\([^"]*\)".*/\1/')
INTERSTITIAL_ID=$(grep "INTERSTITIAL_AD_UNIT_ID" "$ADS_MANAGER" | head -1 | sed 's/.*"\([^"]*\)".*/\1/')
BANNER_ID=$(grep "BANNER_AD_UNIT_ID" "$ADS_MANAGER" | head -1 | sed 's/.*"\([^"]*\)".*/\1/')

echo "Rewarded Ad ID: $REWARDED_ID"
if [[ $REWARDED_ID == *"3940256099942544"* ]]; then
    echo -e "${RED}❌ ERROR: Rewarded Ad masih TEST ID!${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}✅ Production Rewarded Ad ID${NC}"
fi

echo ""
echo "Interstitial Ad ID: $INTERSTITIAL_ID"
if [[ $INTERSTITIAL_ID == *"3940256099942544"* ]]; then
    echo -e "${RED}❌ ERROR: Interstitial Ad masih TEST ID!${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}✅ Production Interstitial Ad ID${NC}"
fi

echo ""
echo "Banner Ad ID: $BANNER_ID"
if [[ $BANNER_ID == *"3940256099942544"* ]]; then
    echo -e "${RED}❌ ERROR: Banner Ad masih TEST ID!${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}✅ Production Banner Ad ID${NC}"
fi

echo ""

# Check google-services.json
echo "3️⃣ Checking google-services.json..."
echo "------------------------------------"

GOOGLE_SERVICES="$PROJECT_ROOT/android/app/google-services.json"

if [ ! -f "$GOOGLE_SERVICES" ]; then
    echo -e "${YELLOW}⚠️  WARNING: google-services.json not found${NC}"
    ((WARNINGS++))
else
    if grep -q "123456789012" "$GOOGLE_SERVICES"; then
        echo -e "${YELLOW}⚠️  WARNING: google-services.json masih placeholder${NC}"
        echo -e "${YELLOW}   → Download yang asli dari Firebase Console${NC}"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✅ google-services.json looks valid${NC}"
    fi
fi

echo ""

# Check build configuration
echo "4️⃣ Checking build configuration..."
echo "-----------------------------------"

BUILD_GRADLE="$PROJECT_ROOT/android/app/build.gradle"

if grep -q "versionCode 2" "$BUILD_GRADLE"; then
    VERSION_CODE=$(grep "versionCode" "$BUILD_GRADLE" | awk '{print $2}')
    VERSION_NAME=$(grep "versionName" "$BUILD_GRADLE" | sed 's/.*"\([^"]*\)".*/\1/')
    echo "Version Code: $VERSION_CODE"
    echo "Version Name: $VERSION_NAME"
    echo -e "${GREEN}✅ Build configuration OK${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: Could not verify version${NC}"
    ((WARNINGS++))
fi

echo ""

# Check dependencies
echo "5️⃣ Checking dependencies..."
echo "----------------------------"

if grep -q "com.google.android.gms:play-services-ads:23.5.0" "$BUILD_GRADLE"; then
    echo -e "${GREEN}✅ AdMob SDK version: 23.5.0 (latest)${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: AdMob SDK version might be outdated${NC}"
    ((WARNINGS++))
fi

echo ""

# Summary
echo "=============================="
echo "📊 SUMMARY"
echo "=============================="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 SEMUA CHECKS PASSED!${NC}"
    echo ""
    echo "✅ Konfigurasi ads sudah benar"
    echo "✅ Siap untuk production build"
    echo ""
    echo "Next steps:"
    echo "  1. Build release APK:"
    echo "     cd android && ./gradlew assembleRelease"
    echo ""
    echo "  2. Test di device:"
    echo "     adb install app/build/outputs/apk/release/app-release-unsigned.apk"
    echo ""
    echo "  3. Sign dan upload ke Play Store"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $ERRORS ERROR(S) FOUND${NC}"
    echo -e "${YELLOW}⚠️  $WARNINGS WARNING(S)${NC}"
    echo ""
    
    if [ $ERRORS -gt 0 ]; then
        echo "ERRORS harus diperbaiki sebelum production!"
        echo ""
        echo "🔧 Cara fix:"
        echo ""
        echo "1. Setup AdMob Account:"
        echo "   → https://admob.google.com"
        echo "   → Buat app 'Dragon Arrow Escape'"
        echo "   → Buat 3 Ad Units (Rewarded, Interstitial, Banner)"
        echo ""
        echo "2. Update AndroidManifest.xml:"
        echo "   → Ganti App ID di line ~40"
        echo "   → File: $MANIFEST"
        echo ""
        echo "3. Update AdsManager.java:"
        echo "   → Ganti 3 Ad Unit IDs"
        echo "   → File: $ADS_MANAGER"
        echo "   → Lines: 42, 46, 50"
        echo ""
        echo "Lihat PRODUCTION_READY_CHECKLIST.md untuk panduan lengkap!"
        echo ""
    fi
    
    exit 1
fi
