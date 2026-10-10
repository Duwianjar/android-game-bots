#!/bin/bash

# Build Script untuk Dragon Arrow Escape
# Compile APK untuk testing dan release

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running from correct directory
if [ ! -d "android" ]; then
    print_error "Direktori 'android' tidak ditemukan!"
    print_info "Jalankan script ini dari: ~/android-game-bots/dragon-arrow-escape/"
    exit 1
fi

print_header "🚀 BUILD DRAGON ARROW ESCAPE"

# Check for production IDs
print_info "Checking for TEST Ad IDs..."
if grep -r "ca-app-pub-3940256099942544" android/app/src/main/ > /dev/null 2>&1; then
    print_warning "⚠️  WARNING: Masih menggunakan TEST AD IDs!"
    print_warning "    App TIDAK akan menghasilkan uang nyata!"
    print_info "    Jalankan: python setup_admob.py untuk setup production IDs"
    echo ""
    read -p "Lanjutkan build dengan TEST IDs? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Build dibatalkan. Setup production IDs dulu."
        exit 0
    fi
else
    print_success "Production Ad IDs detected"
fi

# Check for google-services.json
if [ ! -f "android/app/google-services.json" ]; then
    print_warning "⚠️  google-services.json tidak ditemukan!"
    print_info "    Download dari Firebase/AdMob Console"
    print_info "    Letakkan di: android/app/google-services.json"
    echo ""
    read -p "Lanjutkan tanpa google-services.json? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
else
    print_success "google-services.json found"
fi

# Choose build type
echo ""
print_info "Pilih build type:"
echo "  1) Debug APK (untuk testing)"
echo "  2) Release APK (untuk publish)"
echo ""
read -p "Pilihan (1/2): " -n 1 -r BUILD_TYPE
echo ""

cd android

if [[ $BUILD_TYPE == "1" ]]; then
    print_header "📦 Building DEBUG APK"
    
    # Clean
    print_info "Cleaning previous build..."
    ./gradlew clean
    
    # Build debug
    print_info "Building debug APK..."
    ./gradlew assembleDebug
    
    if [ $? -eq 0 ]; then
        print_success "Build successful!"
        
        APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
        
        if [ -f "$APK_PATH" ]; then
            APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
            print_success "APK created: $APK_PATH"
            print_info "Size: $APK_SIZE"
            
            # Copy ke root untuk easy access
            cp "$APK_PATH" ../dragon-arrow-escape-debug.apk
            print_success "Copied to: dragon-arrow-escape-debug.apk"
            
            # Install ke device jika tersambung
            echo ""
            read -p "Install ke device sekarang? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                print_info "Installing to device..."
                adb install -r "$APK_PATH"
                
                if [ $? -eq 0 ]; then
                    print_success "App installed!"
                    print_info "Launch dengan: adb shell am start -n com.dragonarrowescape.game/.MainActivity"
                else
                    print_error "Install failed. Install manual: adb install -r $APK_PATH"
                fi
            fi
        fi
    else
        print_error "Build failed!"
        exit 1
    fi
    
elif [[ $BUILD_TYPE == "2" ]]; then
    print_header "📦 Building RELEASE APK"
    
    # Check keystore
    KEYSTORE_PATH="$HOME/.android/debug.keystore"
    if [ ! -f "$KEYSTORE_PATH" ]; then
        print_warning "Keystore tidak ditemukan di: $KEYSTORE_PATH"
        print_info "Untuk production, buat keystore dengan:"
        print_info "  keytool -genkey -v -keystore my-release-key.keystore -alias my-key-alias -keyalg RSA -keysize 2048 -validity 10000"
        exit 1
    fi
    
    # Clean
    print_info "Cleaning previous build..."
    ./gradlew clean
    
    # Build release
    print_info "Building release APK..."
    ./gradlew assembleRelease
    
    if [ $? -eq 0 ]; then
        print_success "Build successful!"
        
        APK_PATH="app/build/outputs/apk/release/app-release-unsigned.apk"
        
        if [ -f "$APK_PATH" ]; then
            APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
            print_success "APK created: $APK_PATH"
            print_info "Size: $APK_SIZE"
            
            # Copy ke root
            cp "$APK_PATH" ../dragon-arrow-escape-release.apk
            print_success "Copied to: dragon-arrow-escape-release.apk"
            
            print_warning "⚠️  APK belum signed untuk production!"
            print_info "Untuk publish ke Play Store:"
            print_info "  1. Sign APK dengan release keystore"
            print_info "  2. Zipalign APK"
            print_info "  3. Upload ke Google Play Console"
        fi
    else
        print_error "Build failed!"
        exit 1
    fi
else
    print_error "Invalid choice"
    exit 1
fi

cd ..

print_header "✅ BUILD COMPLETE"

echo ""
print_info "Next steps:"
echo "  • Test di real device (bukan emulator untuk ads)"
echo "  • Check logcat: adb logcat | grep -i 'DragonArrowEscape\\|Ads'"
echo "  • Verify ads muncul"
echo "  • Upload ke Google Play Store (internal testing first)"
echo ""

print_success "Happy monetizing! 💰"
