#!/bin/bash
# Build dan Test Script untuk Dragon Arrow Escape
# Memastikan semua ads berfungsi dengan baik sebelum publish

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${BOLD}${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║        DRAGON ARROW ESCAPE - BUILD & TEST SCRIPT                     ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Change to project directory
cd "$(dirname "$0")"

# Function untuk print colored messages
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_header() {
    echo -e "\n${BOLD}${BLUE}$1${NC}\n"
}

# Check prerequisites
print_header "🔍 CHECKING PREREQUISITES"

if ! command -v java &> /dev/null; then
    print_error "Java tidak ditemukan. Install JDK 11 atau 17."
    exit 1
fi
print_success "Java: $(java -version 2>&1 | head -n 1)"

if [ ! -d "android" ]; then
    print_error "Folder android tidak ditemukan!"
    exit 1
fi
print_success "Project structure OK"

# Verify AdMob setup
print_header "📋 VERIFYING ADMOB SETUP"

MANIFEST_FILE="android/app/src/main/AndroidManifest.xml"
ADS_MANAGER_FILE="android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
GOOGLE_SERVICES="android/app/google-services.json"

# Check for test IDs
if grep -q "ca-app-pub-3940256099942544" "$MANIFEST_FILE" 2>/dev/null; then
    print_warning "AndroidManifest.xml masih menggunakan TEST App ID"
    print_info "Jalankan: python setup_admob_production.py"
else
    print_success "Production App ID detected in AndroidManifest.xml"
fi

if grep -q "ca-app-pub-3940256099942544" "$ADS_MANAGER_FILE" 2>/dev/null; then
    print_warning "AdsManager.java masih menggunakan TEST Ad Unit IDs"
    print_info "Jalankan: python setup_admob_production.py"
else
    print_success "Production Ad Unit IDs detected in AdsManager.java"
fi

if [ ! -f "$GOOGLE_SERVICES" ]; then
    print_warning "google-services.json tidak ditemukan"
    print_info "Download dari Firebase Console dan letakkan di android/app/"
elif grep -q "xxxxx\|redacted" "$GOOGLE_SERVICES"; then
    print_warning "google-services.json masih template"
else
    print_success "google-services.json OK"
fi

# Build options
print_header "🔨 BUILD OPTIONS"
echo "1. Debug Build (cepat, dengan logging)"
echo "2. Release Build (optimized, siap publish)"
echo "3. Clean Build (hapus cache dulu)"
echo "4. Install ke device (via ADB)"
echo "5. Run logcat untuk monitor ads"
echo ""
read -p "Pilih opsi (1-5): " choice

cd android

case $choice in
    1)
        print_header "🔨 BUILDING DEBUG APK"
        ./gradlew assembleDebug
        
        APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
        if [ -f "$APK_PATH" ]; then
            print_success "Debug APK created: $APK_PATH"
            print_info "Size: $(du -h $APK_PATH | cut -f1)"
            print_info "\nTo install: adb install $APK_PATH"
        fi
        ;;
        
    2)
        print_header "🔨 BUILDING RELEASE APK"
        
        # Check signing config
        if [ ! -f "keystore.jks" ] && [ ! -f "app/keystore.jks" ]; then
            print_warning "Keystore tidak ditemukan. Akan generate keystore baru."
            print_info "\nMasukkan informasi untuk keystore:"
            read -p "Alias name: " KEY_ALIAS
            read -sp "Password: " KEY_PASSWORD
            echo ""
            
            keytool -genkey -v -keystore keystore.jks -alias "$KEY_ALIAS" \
                -keyalg RSA -keysize 2048 -validity 10000 \
                -storepass "$KEY_PASSWORD" -keypass "$KEY_PASSWORD"
            
            print_success "Keystore created: keystore.jks"
            print_warning "SIMPAN PASSWORD INI DENGAN AMAN!"
        fi
        
        ./gradlew assembleRelease
        
        APK_PATH="app/build/outputs/apk/release/app-release.apk"
        if [ -f "$APK_PATH" ]; then
            print_success "Release APK created: $APK_PATH"
            print_info "Size: $(du -h $APK_PATH | cut -f1)"
            print_success "\n✨ APK siap untuk upload ke Play Store!"
        fi
        ;;
        
    3)
        print_header "🧹 CLEANING BUILD"
        ./gradlew clean
        print_success "Build cache cleared"
        
        print_info "Build ulang? (y/n)"
        read -p "> " rebuild
        if [ "$rebuild" = "y" ]; then
            ./gradlew assembleDebug
        fi
        ;;
        
    4)
        print_header "📱 INSTALLING TO DEVICE"
        
        # Check ADB
        if ! command -v adb &> /dev/null; then
            print_error "ADB tidak ditemukan. Install Android SDK Platform Tools."
            exit 1
        fi
        
        # Check device
        DEVICES=$(adb devices | grep -v "List" | grep "device$" | wc -l)
        if [ "$DEVICES" -eq 0 ]; then
            print_error "Tidak ada device terhubung. Enable USB Debugging dan hubungkan device."
            exit 1
        fi
        print_success "Device terhubung: $(adb devices | grep device$ | awk '{print $1}')"
        
        # Build dan install
        ./gradlew installDebug
        
        print_success "App installed!"
        print_info "\nLaunch app dengan:"
        print_info "adb shell am start -n com.dragonarrowescape.game/.MainActivity"
        
        # Prompt untuk launch
        read -p "Launch app sekarang? (y/n): " launch
        if [ "$launch" = "y" ]; then
            adb shell am start -n com.dragonarrowescape.game/.MainActivity
            print_success "App launched!"
            
            # Prompt untuk logcat
            read -p "Monitor logcat untuk ads? (y/n): " monitor
            if [ "$monitor" = "y" ]; then
                print_info "Monitoring ads logs (Ctrl+C to stop)..."
                adb logcat | grep -iE "DragonArrowEscape|AdsManager|AdRevenueTracker|Google Mobile Ads"
            fi
        fi
        ;;
        
    5)
        print_header "📊 MONITORING ADS LOGS"
        
        if ! command -v adb &> /dev/null; then
            print_error "ADB tidak ditemukan."
            exit 1
        fi
        
        DEVICES=$(adb devices | grep -v "List" | grep "device$" | wc -l)
        if [ "$DEVICES" -eq 0 ]; then
            print_error "Tidak ada device terhubung."
            exit 1
        fi
        
        print_info "Monitoring ads logs... (Ctrl+C to stop)\n"
        echo -e "${YELLOW}Cari log berikut:${NC}"
        echo "  ✅ Ad Loaded Successfully"
        echo "  📺 Showing rewarded ad"
        echo "  💎 User earned reward"
        echo "  💰 Ad impression recorded"
        echo "  ❌ Ad failed to load (normal di test mode)"
        echo ""
        
        adb logcat -c  # Clear old logs
        adb logcat | grep -iE "DragonArrowEscape|AdsManager|AdRevenueTracker|Google Mobile Ads|Ads"
        ;;
        
    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

cd ..

# Post-build checks
print_header "✅ POST-BUILD CHECKLIST"
echo "Sebelum publish, pastikan:"
echo "  [ ] Production App ID sudah di AndroidManifest.xml"
echo "  [ ] Production Ad Unit IDs sudah di AdsManager.java"
echo "  [ ] google-services.json dari Firebase Console"
echo "  [ ] Tested di real device - ads muncul dengan benar"
echo "  [ ] Signed dengan production keystore"
echo "  [ ] Version code dan version name sudah benar"
echo ""
print_info "Panduan lengkap: android/MONETIZATION_SETUP.md"
print_success "\n🎉 Build process complete!\n"
