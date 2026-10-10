#!/usr/bin/env python3
"""
Setup AdMob Production IDs
Script untuk mengganti TEST IDs dengan PRODUCTION IDs dari AdMob

WAJIB dijalankan sebelum publish ke Play Store!
"""

import os
import sys
import re
import json
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def validate_ad_id(ad_id, ad_type):
    """Validasi format Ad ID dari AdMob"""
    # Format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY (App ID)
    # atau ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY (Ad Unit ID)
    
    if ad_type == "app":
        pattern = r'^ca-app-pub-\d{16}~\d{10}$'
    else:
        pattern = r'^ca-app-pub-\d{16}/\d{10}$'
    
    if not re.match(pattern, ad_id):
        return False
    
    # Cek bukan test ID
    test_ids = [
        'ca-app-pub-3940256099942544',  # Google test publisher
    ]
    
    for test_id in test_ids:
        if test_id in ad_id:
            print_error(f"Ini adalah TEST ID! Gunakan Production ID dari akun AdMob Anda.")
            return False
    
    return True

def backup_file(file_path):
    """Backup file sebelum modifikasi"""
    backup_path = f"{file_path}.backup"
    if os.path.exists(file_path):
        import shutil
        shutil.copy2(file_path, backup_path)
        print_success(f"Backup dibuat: {backup_path}")
        return True
    return False

def update_manifest(app_id):
    """Update AndroidManifest.xml dengan App ID production"""
    manifest_path = "android/app/src/main/AndroidManifest.xml"
    
    if not os.path.exists(manifest_path):
        print_error(f"File tidak ditemukan: {manifest_path}")
        return False
    
    backup_file(manifest_path)
    
    with open(manifest_path, 'r') as f:
        content = f.read()
    
    # Ganti App ID
    pattern = r'(android:name="com\.google\.android\.gms\.ads\.APPLICATION_ID"\s+android:value=")[^"]+(")'
    new_content = re.sub(pattern, rf'\g<1>{app_id}\g<2>', content)
    
    if new_content == content:
        print_warning("App ID tidak berubah - mungkin sudah diset?")
        return False
    
    with open(manifest_path, 'w') as f:
        f.write(new_content)
    
    print_success(f"AndroidManifest.xml updated dengan App ID: {app_id}")
    return True

def update_ads_manager(rewarded_id, interstitial_id, banner_id):
    """Update AdsManager.java dengan Ad Unit IDs production"""
    ads_manager_path = "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
    
    if not os.path.exists(ads_manager_path):
        print_error(f"File tidak ditemukan: {ads_manager_path}")
        return False
    
    backup_file(ads_manager_path)
    
    with open(ads_manager_path, 'r') as f:
        content = f.read()
    
    # Ganti Rewarded Ad Unit ID
    pattern = r'(private static final String REWARDED_AD_UNIT_ID = ")[^"]+(")'
    content = re.sub(pattern, rf'\g<1>{rewarded_id}\g<2>', content)
    
    # Ganti Interstitial Ad Unit ID
    pattern = r'(private static final String INTERSTITIAL_AD_UNIT_ID = ")[^"]+(")'
    content = re.sub(pattern, rf'\g<1>{interstitial_id}\g<2>', content)
    
    # Ganti Banner Ad Unit ID
    pattern = r'(private static final String BANNER_AD_UNIT_ID = ")[^"]+(")'
    content = re.sub(pattern, rf'\g<1>{banner_id}\g<2>', content)
    
    with open(ads_manager_path, 'w') as f:
        f.write(content)
    
    print_success("AdsManager.java updated dengan Production Ad Unit IDs")
    return True

def check_google_services_json():
    """Cek apakah google-services.json ada"""
    json_path = "android/app/google-services.json"
    
    if not os.path.exists(json_path):
        print_warning("google-services.json TIDAK DITEMUKAN!")
        print_info("Download dari Firebase Console atau AdMob:")
        print_info("1. Buka https://console.firebase.google.com")
        print_info("2. Pilih project Anda")
        print_info("3. Project Settings > Download google-services.json")
        print_info(f"4. Letakkan di: {json_path}")
        return False
    
    # Cek apakah bukan template
    with open(json_path, 'r') as f:
        content = f.read()
        if 'xxxxx' in content or '«redacted:' in content:
            print_warning("google-services.json masih template!")
            print_info("Download yang asli dari Firebase Console")
            return False
    
    print_success("google-services.json ditemukan dan valid")
    return True

def verify_setup():
    """Verifikasi bahwa semua sudah disetup dengan benar"""
    print_header("🔍 VERIFIKASI SETUP")
    
    issues = []
    
    # Cek AndroidManifest
    manifest_path = "android/app/src/main/AndroidManifest.xml"
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            content = f.read()
            if 'ca-app-pub-3940256099942544' in content:
                issues.append("❌ AndroidManifest.xml masih menggunakan TEST App ID")
            else:
                print_success("AndroidManifest.xml menggunakan Production App ID")
    else:
        issues.append("❌ AndroidManifest.xml tidak ditemukan")
    
    # Cek AdsManager
    ads_path = "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
    if os.path.exists(ads_path):
        with open(ads_path, 'r') as f:
            content = f.read()
            if 'ca-app-pub-3940256099942544' in content:
                issues.append("❌ AdsManager.java masih menggunakan TEST Ad Unit IDs")
            else:
                print_success("AdsManager.java menggunakan Production Ad Unit IDs")
    else:
        issues.append("❌ AdsManager.java tidak ditemukan")
    
    # Cek google-services.json
    if not check_google_services_json():
        issues.append("❌ google-services.json belum valid")
    
    # Cek build.gradle
    gradle_path = "android/app/build.gradle"
    if os.path.exists(gradle_path):
        with open(gradle_path, 'r') as f:
            content = f.read()
            if 'com.google.android.gms:play-services-ads' in content:
                print_success("build.gradle memiliki AdMob dependencies")
            else:
                issues.append("❌ build.gradle tidak ada AdMob dependencies")
    
    if issues:
        print("\n" + "="*70)
        print_error("MASALAH DITEMUKAN:")
        for issue in issues:
            print(f"  {issue}")
        print("="*70 + "\n")
        return False
    else:
        print("\n" + "="*70)
        print_success("✨ SEMUA SETUP SUDAH BENAR!")
        print_info("Aplikasi siap untuk build production dan publish ke Play Store")
        print("="*70 + "\n")
        return True

def interactive_setup():
    """Setup interaktif dengan input dari user"""
    print_header("🎯 SETUP ADMOB PRODUCTION IDs")
    
    print_info("Pastikan Anda sudah:")
    print("  1. Membuat akun AdMob di https://admob.google.com")
    print("  2. Mendaftarkan aplikasi 'Dragon Arrow Escape'")
    print("  3. Membuat 3 Ad Units (Rewarded, Interstitial, Banner)")
    print("  4. Download google-services.json dari Firebase Console\n")
    
    response = input(f"{Colors.BOLD}Apakah Anda sudah siap dengan semua Production IDs? (y/n): {Colors.ENDC}")
    if response.lower() != 'y':
        print_warning("Setup dibatalkan. Lengkapi dulu setup di AdMob Console.")
        print_info("Baca panduan lengkap di: android/MONETIZATION_SETUP.md")
        return False
    
    print("\n" + "-"*70)
    print(f"{Colors.BOLD}Masukkan Production IDs dari AdMob Console:{Colors.ENDC}\n")
    
    # Input App ID
    while True:
        app_id = input("App ID (ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY): ").strip()
        if validate_ad_id(app_id, "app"):
            break
        print_error("Format App ID tidak valid atau masih TEST ID!")
    
    # Input Rewarded Ad Unit ID
    while True:
        rewarded_id = input("Rewarded Ad Unit ID (ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY): ").strip()
        if validate_ad_id(rewarded_id, "unit"):
            break
        print_error("Format Ad Unit ID tidak valid atau masih TEST ID!")
    
    # Input Interstitial Ad Unit ID
    while True:
        interstitial_id = input("Interstitial Ad Unit ID (ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY): ").strip()
        if validate_ad_id(interstitial_id, "unit"):
            break
        print_error("Format Ad Unit ID tidak valid atau masih TEST ID!")
    
    # Input Banner Ad Unit ID
    while True:
        banner_id = input("Banner Ad Unit ID (ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY): ").strip()
        if validate_ad_id(banner_id, "unit"):
            break
        print_error("Format Ad Unit ID tidak valid atau masih TEST ID!")
    
    print("\n" + "-"*70)
    print(f"{Colors.BOLD}Konfirmasi Production IDs:{Colors.ENDC}")
    print(f"  App ID:         {app_id}")
    print(f"  Rewarded:       {rewarded_id}")
    print(f"  Interstitial:   {interstitial_id}")
    print(f"  Banner:         {banner_id}")
    print("-"*70 + "\n")
    
    confirm = input(f"{Colors.BOLD}Apakah data sudah benar? (y/n): {Colors.ENDC}")
    if confirm.lower() != 'y':
        print_warning("Setup dibatalkan.")
        return False
    
    # Update files
    print_header("📝 UPDATING FILES")
    
    success = True
    success &= update_manifest(app_id)
    success &= update_ads_manager(rewarded_id, interstitial_id, banner_id)
    check_google_services_json()
    
    if success:
        print_success("\n✨ Setup berhasil!")
    
    # Verify
    return verify_setup()

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║          DRAGON ARROW ESCAPE - ADMOB PRODUCTION SETUP                ║")
    print("║                                                                      ║")
    print("║  Script ini akan mengganti TEST IDs dengan PRODUCTION IDs AdMob     ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        verify_setup()
        return
    
    if not interactive_setup():
        sys.exit(1)
    
    print_header("🚀 NEXT STEPS")
    print("1. Letakkan google-services.json di android/app/ (jika belum)")
    print("2. Build APK: cd android && ./gradlew assembleRelease")
    print("3. Test di real device dengan: adb install app/build/outputs/apk/release/app-release.apk")
    print("4. Upload ke Google Play Console")
    print("5. Monitor revenue di AdMob dashboard\n")
    
    print_info("💰 Estimasi revenue dengan 1000 active users/hari: $100-150/hari")
    print_success("Setup selesai! Good luck dengan monetisasi! 🎉\n")

if __name__ == "__main__":
    main()
