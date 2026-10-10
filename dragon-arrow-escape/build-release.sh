#!/bin/bash

# Build Release APK untuk Dragon Arrow Escape
# Script ini akan:
# 1. Clean build artifacts
# 2. Build release APK dengan signing
# 3. Verify APK
# 4. Show output location

set -e  # Exit on error

echo "🚀 Dragon Arrow Escape - Release Build"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "android/build.gradle" ]; then
    echo -e "${RED}❌ Error: Must run from project root directory${NC}"
    echo "Current directory: $(pwd)"
    exit 1
fi

cd android

# Check for keystore
KEYSTORE_FILE="dragon-arrow-release.keystore"
if [ ! -f "$KEYSTORE_FILE" ]; then
    echo -e "${YELLOW}⚠️  Keystore not found!${NC}"
    echo ""
    echo "Generate keystore with:"
    echo ""
    echo "keytool -genkey -v -keystore $KEYSTORE_FILE \\"
    echo "  -alias dragon-arrow -keyalg RSA -keysize 2048 -validity 10000"
    echo ""
    echo -e "${RED}❌ Build cancelled${NC}"
    exit 1
fi

# Check if production Ad IDs configured
echo ""
echo "🔍 Checking Ad Configuration..."
if grep -q "ca-app-pub-3940256099942544" app/src/main/java/com/dragonarrowescape/game/AdsManager.java; then
    echo -e "${YELLOW}⚠️  WARNING: Still using TEST AD IDs!${NC}"
    echo -e "${YELLOW}   App will NOT generate real revenue!${NC}"
    echo ""
    echo "To fix:"
    echo "1. Create AdMob account: https://admob.google.com"
    echo "2. Register app and create Ad Units"
    echo "3. Replace TEST IDs in AdsManager.java"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Build cancelled"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Production Ad IDs configured${NC}"
fi

# Clean previous builds
echo ""
echo "🧹 Cleaning previous builds..."
./gradlew clean

# Build release APK
echo ""
echo "🔨 Building release APK..."
./gradlew assembleRelease

# Check if build succeeded
APK_PATH="app/build/outputs/apk/release/app-release.apk"
if [ -f "$APK_PATH" ]; then
    echo ""
    echo -e "${GREEN}✅ Build successful!${NC}"
    echo ""
    echo "📦 APK Location:"
    echo "   $(pwd)/$APK_PATH"
    echo ""
    
    # Get APK info
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo "📊 APK Size: $APK_SIZE"
    
    # Show APK info using aapt if available
    if command -v aapt &> /dev/null; then
        echo ""
        echo "📋 APK Info:"
        aapt dump badging "$APK_PATH" | grep -E "package:|application-label:|sdkVersion:|targetSdkVersion:"
    fi
    
    echo ""
    echo "Next steps:"
    echo "1. Test APK on real device:"
    echo "   adb install -r $APK_PATH"
    echo ""
    echo "2. Upload to Play Console:"
    echo "   https://play.google.com/console"
    echo ""
    echo "3. Monitor AdMob revenue:"
    echo "   https://admob.google.com"
    
else
    echo -e "${RED}❌ Build failed!${NC}"
    echo "Check error messages above"
    exit 1
fi
