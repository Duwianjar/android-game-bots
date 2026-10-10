#!/bin/bash

# Script untuk build production APK dengan verifikasi
# Usage: ./tools/build-production.sh

set -e

echo "🚀 BUILDING PRODUCTION APK"
echo "=========================="
echo ""

PROJECT_ROOT="/Users/macbookair/android-game-bots/dragon-arrow-escape"
cd "$PROJECT_ROOT"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Verify configuration
echo -e "${BLUE}Step 1: Verifying ad configuration...${NC}"
echo "--------------------------------------"

if ! ./tools/verify-ads-config.sh; then
    echo ""
    echo -e "${RED}❌ Verification failed!${NC}"
    echo ""
    echo "PRODUCTION BUILD CANCELLED"
    echo "Perbaiki errors di atas sebelum build production."
    echo ""
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Verification passed${NC}"
echo ""

# Step 2: Clean build
echo -e "${BLUE}Step 2: Cleaning previous builds...${NC}"
echo "------------------------------------"
cd android
./gradlew clean
echo -e "${GREEN}✅ Clean complete${NC}"
echo ""

# Step 3: Build release APK
echo -e "${BLUE}Step 3: Building release APK...${NC}"
echo "--------------------------------"
echo "This may take a few minutes..."
echo ""

if ./gradlew assembleRelease; then
    echo ""
    echo -e "${GREEN}✅ Build successful!${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Build failed!${NC}"
    echo "Check error messages above."
    exit 1
fi

# Step 4: Verify APK exists
echo -e "${BLUE}Step 4: Verifying APK...${NC}"
echo "-----------------------"

APK_PATH="app/build/outputs/apk/release/app-release-unsigned.apk"

if [ -f "$APK_PATH" ]; then
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo -e "${GREEN}✅ APK created successfully${NC}"
    echo ""
    echo "📦 APK Details:"
    echo "   Path: $APK_PATH"
    echo "   Size: $APK_SIZE"
    echo ""
else
    echo -e "${RED}❌ APK not found!${NC}"
    exit 1
fi

# Step 5: Summary
echo "=============================="
echo "🎉 BUILD COMPLETE!"
echo "=============================="
echo ""
echo "APK Location:"
echo "  $PROJECT_ROOT/android/$APK_PATH"
echo ""
echo "Next Steps:"
echo ""
echo "1️⃣ Test APK di device:"
echo "   adb install -r $APK_PATH"
echo ""
echo "2️⃣ Verify ads muncul dengan benar"
echo ""
echo "3️⃣ Sign APK untuk production:"
echo "   jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 \\"
echo "     -keystore dragon-arrow.keystore $APK_PATH dragon-key"
echo ""
echo "4️⃣ Upload ke Google Play Console"
echo ""
echo "💰 REMINDER: Pastikan sudah ganti TEST IDs dengan Production IDs!"
echo ""
