#!/bin/bash
set -euo pipefail

echo "=================================================="
echo "  INSTALLER APLIKASI & BOT WAJIB (SETELAH RESTART HP)"
echo "=================================================="

SERIAL="${1:-}"

# Cari device jika serial tidak ditentukan
if [ -z "$SERIAL" ]; then
  DEVICES=$(adb devices | awk 'NR>1 && $2=="device" {print $1}')
  COUNT=$(echo "$DEVICES" | grep -c . || true)
  if [ "$COUNT" -eq 1 ]; then
    SERIAL="$DEVICES"
  elif [ "$COUNT" -gt 1 ]; then
    SERIAL=$(echo "$DEVICES" | head -n 1)
  fi
fi

ADB_CMD="adb"
if [ -n "$SERIAL" ]; then
  ADB_CMD="adb -s $SERIAL"
  echo "[+] Menggunakan perangkat: $SERIAL"
else
  echo "[!] Menunggu perangkat Android terdeteksi via ADB..."
  echo "    (Pastikan USB Debugging AKTIF dan pilih 'Selalu Izinkan dari komputer ini')"
  adb wait-for-device
  DEVICES=$(adb devices | awk 'NR>1 && $2=="device" {print $1}')
  SERIAL=$(echo "$DEVICES" | head -n 1)
  ADB_CMD="adb -s $SERIAL"
  echo "[✔] Perangkat terdeteksi: $SERIAL"
fi

echo ""
echo "--- 1. INSTALL BOT BLOCKED GAME DETECTOR ---"
BLOCKED_APK="/Users/macbookair/android-game-bots/blocked-game-detector/app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$BLOCKED_APK" ]; then
  echo "[+] Menginstal Blocked Game Detector ($BLOCKED_APK)..."
  $ADB_CMD install -r -d "$BLOCKED_APK"
  echo "[✔] Blocked Game Detector berhasil diinstal."
  echo "[+] Menjalankan MainActivity Blocked Game Detector..."
  $ADB_CMD shell am start -n com.openclaw.blockeddetector/.MainActivity || true
else
  echo "[!] File APK Blocked Game Detector tidak ditemukan di $BLOCKED_APK"
fi

echo ""
echo "--- 2. INSTALL BOT INJECT IKLAN ---"
INJECT_APK="/Users/macbookair/android-game-bots/inject-iklan-android/app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$INJECT_APK" ]; then
  echo "[+] Menginstal Inject Iklan ($INJECT_APK)..."
  $ADB_CMD install -r -d "$INJECT_APK"
  echo "[✔] Inject Iklan berhasil diinstal."
  echo "[+] Menjalankan MainActivity Inject Iklan..."
  $ADB_CMD shell am start -n com.openclaw.injectiklan/.MainActivity || true
else
  echo "[!] File APK Inject Iklan tidak ditemukan di $INJECT_APK"
fi

echo ""
echo "--- 3. INSTALL BOT & CEK GAME BUS JAM PARKING ---"
BUSJAM_BOT_APK="/Users/macbookair/android-game-bots/bus-jam-parking-android/app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$BUSJAM_BOT_APK" ]; then
  echo "[+] Menginstal Bus Jam Bot ($BUSJAM_BOT_APK)..."
  $ADB_CMD install -r -d "$BUSJAM_BOT_APK"
  echo "[✔] Bus Jam Bot berhasil diinstal."
fi

# Cek apakah game Bus Jam Parking Master terpasang
if $ADB_CMD shell pm list packages | grep -q "com.busjam.parking.master"; then
  echo "[✔] Game Bus Jam Parking Master (com.busjam.parking.master) sudah terpasang di HP."
else
  echo "[!] Game Bus Jam Parking Master belum terpasang di HP."
  echo "[+] Membuka Google Play Store di HP untuk Bus Jam Parking Master..."
  $ADB_CMD shell am start -a android.intent.action.VIEW -d "market://details?id=com.busjam.parking.master" || true
fi

echo ""
echo "=================================================="
echo "  [✔] INSTALASI APLIKASI WAJIB SELESAI"
echo "=================================================="
