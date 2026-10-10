#!/bin/bash
# Script untuk verifikasi production readiness

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Dragon Arrow Escape - Production Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

ERRORS=0
WARNINGS=0

# Check 1: AndroidManifest.xml App ID
echo -e "${BLUE}[1/6] Checking AndroidManifest.xml...${NC}"
MANIFEST_PATH="android/app/src/main/AndroidManifest.xml"
if [ -f "$MANIFEST_PATH" ]; then
    APP_ID=$(grep -o 'ca-app-pub-[0-9~]*' "$MANIFEST_PATH" | head -1)
    if [[ $APP_ID == *"3940256099942544"* ]]; then
        echo -e "${RED}  ❌ FAIL: Masih menggunakan TEST App ID!${NC}"
        echo -e "     Current: $APP_ID"
        echo -e "     Action: Ganti dengan Production ID dari AdMob"
        ((ERRORS++))
    else
        echo -e "${GREEN}  ✅ PASS: Production App ID detected${NC}"
        echo -e "     App ID: $APP_ID"
    fi
else
    echo -e "${RED}  ❌ FAIL: AndroidManifest.xml not found!${NC}"
    ((ERRORS++))
fi
echo ""

# Check 2: AdsManager.java Ad Unit IDs
echo -e "${BLUE}[2/6] Checking AdsManager.java...${NC}"
ADSMANAGER_PATH="android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
if [ -f "$ADSMANAGER_PATH" ]; then
    TEST_IDS=$(grep -c "3940256099942544" "$ADSMANAGER_PATH")
    if [ $TEST_IDS -gt 0 ]; then
        echo -e "${RED}  ❌ FAIL: Ditemukan $TEST_IDS TEST Ad Unit IDs!${NC}"
        echo -e "     Action: Ganti dengan Production Ad Unit IDs"
        ((ERRORS++))
    else
        echo -e "${GREEN}  ✅ PASS: No TEST IDs found${NC}"
    fi
else
    echo -e "${RED}  ❌ FAIL: AdsManager.java not found!${NC}"
    ((ERRORS++))
fi
echo ""

# Check 3: google-services.json
echo -e "${BLUE}[3/6] Checking google-services.json...${NC}"
GOOGLE_SERVICES="android/app/google-services.json"
if [ -f "$GOOGLE_SERVICES" ]; then
    PROJECT_ID=$(grep -o '"project_id": "[^"]*"' "$GOOGLE_SERVICES" | cut -d'"' -f4)
    if [[ $PROJECT_ID == *"xxxxx"* ]] || [ -z "$PROJECT_ID" ]; then
        echo -e "${YELLOW}  ⚠️  WARNING: google-services.json masih template${NC}"
        echo -e "     Current: $PROJECT_ID"
        echo -e "     Action: Download dari Firebase Console (optional untuk ads)"
        ((WARNINGS++))
    else
        echo -e "${GREEN}  ✅ PASS: Valid google-services.json${NC}"
        echo -e "     Project ID: $PROJECT_ID"
    fi
else
    echo -e "${YELLOW}  ⚠️  WARNING: google-services.json not found${NC}"
    echo -e "     Action: Download dari Firebase Console (optional)"
    ((WARNINGS++))
fi
echo ""

# Check 4: Build files
echo -e "${BLUE}[4/6] Checking build configuration...${NC}"
BUILD_GRADLE="android/app/build.gradle"
if [ -f "$BUILD_GRADLE" ]; then
    if grep -q "play-services-ads" "$BUILD_GRADLE"; then
        ADS_VERSION=$(grep "play-services-ads" "$BUILD_GRADLE" | grep -o '[0-9.]*' | head -1)
        echo -e "${GREEN}  ✅ PASS: AdMob SDK configured (v$ADS_VERSION)${NC}"
    else
        echo -e "${RED}  ❌ FAIL: AdMob SDK not found in build.gradle!${NC}"
        ((ERRORS++))
    fi
else
    echo -e "${RED}  ❌ FAIL: build.gradle not found!${NC}"
    ((ERRORS++))
fi
echo ""

# Check 5: Game HTML assets
echo -e "${BLUE}[5/6] Checking game assets...${NC}"
INDEX_HTML="android/app/src/main/assets/index.html"
ADS_BRIDGE="android/app/src/main/assets/android-ads-bridge.js"

if [ -f "$INDEX_HTML" ]; then
    if grep -q "AndroidAds" "$INDEX_HTML"; then
        echo -e "${GREEN}  ✅ PASS: Game HTML menggunakan AndroidAds interface${NC}"
    else
        echo -e "${YELLOW}  ⚠️  WARNING: AndroidAds not referenced in game${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}  ❌ FAIL: index.html not found!${NC}"
    ((ERRORS++))
fi

if [ -f "$ADS_BRIDGE" ]; then
    echo -e "${GREEN}  ✅ PASS: android-ads-bridge.js exists${NC}"
else
    echo -e "${YELLOW}  ⚠️  WARNING: android-ads-bridge.js not found${NC}"
    ((WARNINGS++))
fi
echo ""

# Check 6: Setup script
echo -e "${BLUE}[6/6] Checking setup script...${NC}"
if [ -f "setup_production.py" ]; then
    echo -e "${GREEN}  ✅ PASS: setup_production.py available${NC}"
    echo -e "     Run: python3 setup_production.py"
else
    echo -e "${YELLOW}  ⚠️  WARNING: setup_production.py not found${NC}"
    ((WARNINGS++))
fi
echo ""

# Final summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SUMMARY${NC}"
echo -e "${BLUE}========================================${NC}"

if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✅ PRODUCTION READY!${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Build release: cd android && ./gradlew assembleRelease"
        echo "  2. Test di device fisik"
        echo "  3. Upload ke Play Store"
        echo "  4. Tunggu 24-48 jam untuk ads aktif"
    else
        echo -e "${YELLOW}⚠️  MOSTLY READY (${WARNINGS} warnings)${NC}"
        echo ""
        echo "Fix warnings untuk hasil optimal, tapi sudah bisa build."
    fi
else
    echo -e "${RED}❌ NOT READY (${ERRORS} errors, ${WARNINGS} warnings)${NC}"
    echo ""
    echo "WAJIB fix errors sebelum production!"
    echo "Jika masih pakai TEST IDs, run: python3 setup_production.py"
fi
echo ""
