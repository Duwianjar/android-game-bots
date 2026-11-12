#!/usr/bin/env bash
# ==============================================================================
# Installer Script for Snake Out Jam (com.wiwvitsugeh.snack)
# ==============================================================================

set -e

APK_DIR="/Users/macbookair/Downloads/Snake_Out_Jam_Patched"

if [ ! -d "$APK_DIR" ]; then
    echo "[-] Folder installer tidak ditemukan di $APK_DIR"
    exit 1
fi

echo "[*] Mengecek perangkat ADB yang terhubung..."
DEVICES=$(adb devices | grep -v "List of devices" | grep "device$" | awk '{print $1}' || true)

if [ -z "$DEVICES" ]; then
    echo "[*] Perangkat belum terdeteksi. Silakan sambungkan kabel USB HP (dan pastikan USB debugging aktif)..."
    adb wait-for-device
    sleep 1
    DEVICES=$(adb devices | grep -v "List of devices" | grep "device$" | awk '{print $1}' || true)
fi

DEVICE_ID=$(echo "$DEVICES" | head -n 1)
echo "[+] Perangkat ditemukan: $DEVICE_ID"

echo "[*] Memasang Snake Out Jam (Split APK patched)..."
adb -s "$DEVICE_ID" install-multiple -r -d \
    "$APK_DIR/com.wiwvitsugeh.snack.apk" \
    "$APK_DIR/config.armeabi_v7a.apk" \
    "$APK_DIR/config.en.apk" \
    "$APK_DIR/config.mdpi.apk"

echo "[+] Berhasil terpasang!"
echo "[*] Membuka game di perangkat..."
adb -s "$DEVICE_ID" shell monkey -p com.wiwvitsugeh.snack -c android.intent.category.LAUNCHER 1

sleep 2
echo "[*] Status window saat ini:"
adb -s "$DEVICE_ID" shell dumpsys window | grep -E "mCurrentFocus|mFocusedApp" || true

echo "[+] Game Snake Out Jam berhasil dibuka di perangkat."
