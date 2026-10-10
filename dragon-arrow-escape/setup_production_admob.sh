#!/bin/bash
# Script untuk update Production Ad Unit IDs dari AdMob
# Mengganti TEST IDs dengan PRODUCTION IDs yang menghasilkan uang

set -e

echo "🚀 Dragon Arrow Escape - Production AdMob Setup"
echo "=============================================="
echo ""
echo "⚠️  PENTING: Script ini akan mengganti TEST IDs dengan PRODUCTION IDs"
echo "    TEST IDs = $0 revenue (tidak menghasilkan uang)"
echo "    PRODUCTION IDs = revenue nyata dari iklan"
echo ""
echo "📋 Kamu perlu 4 IDs dari AdMob:"
echo "   1. App ID (format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY)"
echo "   2. Rewarded Ad Unit ID (format: ca-app-pub-XXXXXXXXXXXXXXXX/1111111111)"
echo "   3. Interstitial Ad Unit ID (format: ca-app-pub-XXXXXXXXXXXXXXXX/2222222222)"
echo "   4. Banner Ad Unit ID (format: ca-app-pub-XXXXXXXXXXXXXXXX/3333333333)"
echo ""
echo "📖 Belum punya? Baca: CARA_PRODUCTION_ADMOB.md"
echo ""

# Validasi format Ad ID
validate_id() {
    local id=$1
    local type=$2
    
    if [[ ! $id =~ ^ca-app-pub-[0-9]{16}[~/][0-9]{10}$ ]]; then
        echo "❌ Format $type salah!"
        echo "   Format benar: ca-app-pub-XXXXXXXXXXXXXXXX~/1234567890"
        echo "   Kamu masukkan: $id"
        return 1
    fi
    return 0
}

# Input App ID
echo "📱 Masukkan App ID dari AdMob:"
read -p "   App ID: " APP_ID
if ! validate_id "$APP_ID" "App ID"; then
    exit 1
fi

echo ""
echo "💎 Masukkan Rewarded Ad Unit ID:"
read -p "   Rewarded ID: " REWARDED_ID
if ! validate_id "$REWARDED_ID" "Rewarded Ad Unit ID"; then
    exit 1
fi

echo ""
echo "📺 Masukkan Interstitial Ad Unit ID:"
read -p "   Interstitial ID: " INTERSTITIAL_ID
if ! validate_id "$INTERSTITIAL_ID" "Interstitial Ad Unit ID"; then
    exit 1
fi

echo ""
echo "🏷️  Masukkan Banner Ad Unit ID:"
read -p "   Banner ID: " BANNER_ID
if ! validate_id "$BANNER_ID" "Banner Ad Unit ID"; then
    exit 1
fi

echo ""
echo "✅ Semua IDs valid!"
echo ""
echo "📋 Review IDs yang akan di-update:"
echo "   App ID:          $APP_ID"
echo "   Rewarded ID:     $REWARDED_ID"
echo "   Interstitial ID: $INTERSTITIAL_ID"
echo "   Banner ID:       $BANNER_ID"
echo ""
read -p "Lanjutkan update? (y/n): " CONFIRM

if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
    echo "❌ Update dibatalkan"
    exit 0
fi

echo ""
echo "🔧 Updating files..."

# Backup files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"

echo "📦 Backing up original files to $BACKUP_DIR/"
cp android/app/src/main/AndroidManifest.xml "$BACKUP_DIR/"
cp android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java "$BACKUP_DIR/"

# Update AndroidManifest.xml
echo "   Updating AndroidManifest.xml..."
sed -i.bak "s|ca-app-pub-3940256099942544~3347511713|$APP_ID|g" \
    android/app/src/main/AndroidManifest.xml
rm android/app/src/main/AndroidManifest.xml.bak

# Update AdsManager.java
echo "   Updating AdsManager.java..."
sed -i.bak "s|ca-app-pub-3940256099942544/5224354917|$REWARDED_ID|g" \
    android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java
sed -i.bak "s|ca-app-pub-3940256099942544/1033173712|$INTERSTITIAL_ID|g" \
    android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java
sed -i.bak "s|ca-app-pub-3940256099942544/6300978111|$BANNER_ID|g" \
    android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java
rm android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java.bak

# Update comments
sed -i.bak "s|// ⚠️ TEST ID|// ✅ PRODUCTION ID|g" \
    android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java
rm android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java.bak

echo ""
echo "✅ Update selesai!"
echo ""
echo "📊 Verifikasi perubahan:"
echo ""
echo "AndroidManifest.xml:"
grep "com.google.android.gms.ads.APPLICATION_ID" android/app/src/main/AndroidManifest.xml | grep -v "<!--"
echo ""
echo "AdsManager.java:"
grep "private static final String.*_AD_UNIT_ID" android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java
echo ""

echo "=============================================="
echo "🎉 PRODUCTION IDs BERHASIL DI-UPDATE!"
echo "=============================================="
echo ""
echo "📋 Next steps:"
echo "   1. Verifikasi: ./verify_monetization.sh"
echo "   2. Build Release APK: cd android && ./gradlew assembleRelease"
echo "   3. Test di device fisik (bukan emulator)"
echo "   4. Upload ke Play Store"
echo "   5. Tunggu 24-48 jam untuk ads aktif"
echo ""
echo "💰 Setelah itu, game SIAP MENGHASILKAN UANG dari iklan!"
echo ""
echo "📖 Backup tersimpan di: $BACKUP_DIR/"
echo "   Untuk restore: cp $BACKUP_DIR/* ke lokasi asli"
echo ""
