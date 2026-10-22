#!/bin/bash

# Script untuk update AdMob Production IDs dengan mudah
# Menggantikan TEST IDs dengan Production IDs di semua file yang diperlukan

set -e

echo "============================================"
echo "🚀 AdMob Production IDs Setup Helper"
echo "============================================"
echo ""
echo "Script ini akan update AndroidManifest.xml dan AdsManager.java"
echo "dengan Production IDs dari AdMob account Anda."
echo ""
echo "⚠️  BACKUP otomatis akan dibuat sebelum update"
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Check files exist
MANIFEST_FILE="android/app/src/main/AndroidManifest.xml"
ADSMANAGER_FILE="android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"

if [ ! -f "$MANIFEST_FILE" ]; then
    echo "❌ Error: AndroidManifest.xml not found!"
    exit 1
fi

if [ ! -f "$ADSMANAGER_FILE" ]; then
    echo "❌ Error: AdsManager.java not found!"
    exit 1
fi

echo "Files found ✅"
echo ""

# Prompt for IDs
echo "📋 Masukkan Production IDs dari AdMob Dashboard:"
echo ""

read -p "1. AdMob App ID (ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY): " APP_ID
read -p "2. Rewarded Ad Unit ID (ca-app-pub-XXXXXXXXXXXXXXXX/1111111111): " REWARDED_ID
read -p "3. Interstitial Ad Unit ID (ca-app-pub-XXXXXXXXXXXXXXXX/2222222222): " INTERSTITIAL_ID
read -p "4. Banner Ad Unit ID (ca-app-pub-XXXXXXXXXXXXXXXX/3333333333): " BANNER_ID

echo ""
echo "============================================"
echo "📝 Verifikasi IDs yang akan digunakan:"
echo "============================================"
echo "App ID:          $APP_ID"
echo "Rewarded ID:     $REWARDED_ID"
echo "Interstitial ID: $INTERSTITIAL_ID"
echo "Banner ID:       $BANNER_ID"
echo ""

# Validate format
if [[ ! $APP_ID =~ ^ca-app-pub-[0-9]{16}~[0-9]{10}$ ]]; then
    echo "⚠️  Warning: App ID format mungkin tidak valid"
    echo "   Expected: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY"
fi

if [[ ! $REWARDED_ID =~ ^ca-app-pub-[0-9]{16}/[0-9]{10}$ ]]; then
    echo "⚠️  Warning: Rewarded Ad Unit ID format mungkin tidak valid"
fi

if [[ ! $INTERSTITIAL_ID =~ ^ca-app-pub-[0-9]{16}/[0-9]{10}$ ]]; then
    echo "⚠️  Warning: Interstitial Ad Unit ID format mungkin tidak valid"
fi

if [[ ! $BANNER_ID =~ ^ca-app-pub-[0-9]{16}/[0-9]{10}$ ]]; then
    echo "⚠️  Warning: Banner Ad Unit ID format mungkin tidak valid"
fi

echo ""
read -p "Lanjutkan dengan IDs di atas? (y/n): " CONFIRM

if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "❌ Dibatalkan"
    exit 0
fi

echo ""
echo "============================================"
echo "🔄 Updating files..."
echo "============================================"

# Create backups
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="backups/pre_production_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"

echo "📦 Creating backups..."
cp "$MANIFEST_FILE" "$BACKUP_DIR/AndroidManifest.xml.bak"
cp "$ADSMANAGER_FILE" "$BACKUP_DIR/AdsManager.java.bak"
echo "✅ Backups saved to: $BACKUP_DIR"
echo ""

# Update AndroidManifest.xml
echo "📝 Updating AndroidManifest.xml..."
sed -i.tmp "s/ca-app-pub-3940256099942544~3347511713/$APP_ID/g" "$MANIFEST_FILE"
rm "${MANIFEST_FILE}.tmp"
echo "✅ AndroidManifest.xml updated"

# Update AdsManager.java
echo "📝 Updating AdsManager.java..."

# Rewarded Ad ID
sed -i.tmp "s/ca-app-pub-3940256099942544\/5224354917/$REWARDED_ID/g" "$ADSMANAGER_FILE"
rm "${ADSMANAGER_FILE}.tmp"

# Interstitial Ad ID
sed -i.tmp "s/ca-app-pub-3940256099942544\/1033173712/$INTERSTITIAL_ID/g" "$ADSMANAGER_FILE"
rm "${ADSMANAGER_FILE}.tmp"

# Banner Ad ID
sed -i.tmp "s/ca-app-pub-3940256099942544\/6300978111/$BANNER_ID/g" "$ADSMANAGER_FILE"
rm "${ADSMANAGER_FILE}.tmp"

echo "✅ AdsManager.java updated"
echo ""

echo "============================================"
echo "✅ SUCCESS! Production IDs Updated"
echo "============================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Verify changes:"
echo "   git diff android/app/src/main/AndroidManifest.xml"
echo "   git diff android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
echo ""
echo "2. Build production APK:"
echo "   cd android"
echo "   ./gradlew assembleRelease"
echo ""
echo "3. Test pada device:"
echo "   adb install -r app/build/outputs/apk/release/app-release.apk"
echo "   adb logcat | grep 'AdsManager\\|AdMob'"
echo ""
echo "4. Verify di logcat:"
echo "   Cari: '✅ Production Ad IDs detected'"
echo ""
echo "5. Deploy ke production dan mulai hasilkan uang! 💰"
echo ""
echo "📂 Backups tersimpan di: $BACKUP_DIR"
echo ""
echo "⚠️  PENTING: Jangan klik iklan sendiri di production!"
echo "   Tambahkan test device di AdMob dashboard untuk testing"
echo ""
