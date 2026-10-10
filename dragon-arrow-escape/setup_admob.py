#!/usr/bin/env python3
"""
Setup AdMob Production IDs untuk Dragon Arrow Escape
Script ini membantu mengganti Test Ad IDs dengan Production IDs
"""

import os
import re
import json
import shutil
from datetime import datetime

# Warna untuk terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")

def print_info(text):
    print(f"{BLUE}ℹ {text}{RESET}")

def validate_app_id(app_id):
    """Validasi format AdMob App ID"""
    pattern = r'^ca-app-pub-\d{16}~\d{10}$'
    return re.match(pattern, app_id) is not None

def validate_ad_unit_id(ad_unit_id):
    """Validasi format AdMob Ad Unit ID"""
    pattern = r'^ca-app-pub-\d{16}/\d{10}$'
    return re.match(pattern, ad_unit_id) is not None

def backup_file(file_path):
    """Backup file sebelum modifikasi"""
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{file_path}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        print_success(f"Backup dibuat: {backup_path}")
        return backup_path
    return None

def get_user_input():
    """Ambil input production IDs dari user"""
    print_header("INPUT PRODUCTION AD IDs")
    
    print_info("Dapatkan IDs dari: https://admob.google.com")
    print_warning("Format App ID: ca-app-pub-1234567890123456~0987654321")
    print_warning("Format Ad Unit: ca-app-pub-1234567890123456/1234567890\n")
    
    # App ID
    while True:
        app_id = input(f"{BLUE}Masukkan AdMob App ID: {RESET}").strip()
        if not app_id:
            print_error("App ID tidak boleh kosong!")
            continue
        if not validate_app_id(app_id):
            print_error("Format App ID tidak valid!")
            print_warning("Contoh: ca-app-pub-1234567890123456~0987654321")
            continue
        break
    
    # Rewarded Ad Unit
    while True:
        rewarded_id = input(f"{BLUE}Masukkan Rewarded Ad Unit ID: {RESET}").strip()
        if not rewarded_id:
            print_error("Rewarded Ad Unit ID tidak boleh kosong!")
            continue
        if not validate_ad_unit_id(rewarded_id):
            print_error("Format Ad Unit ID tidak valid!")
            print_warning("Contoh: ca-app-pub-1234567890123456/1234567890")
            continue
        break
    
    # Interstitial Ad Unit (optional)
    interstitial_id = input(f"{BLUE}Masukkan Interstitial Ad Unit ID (Enter untuk skip): {RESET}").strip()
    if interstitial_id and not validate_ad_unit_id(interstitial_id):
        print_warning("Format tidak valid, skip interstitial")
        interstitial_id = ""
    
    # Banner Ad Unit (optional)
    banner_id = input(f"{BLUE}Masukkan Banner Ad Unit ID (Enter untuk skip): {RESET}").strip()
    if banner_id and not validate_ad_unit_id(banner_id):
        print_warning("Format tidak valid, skip banner")
        banner_id = ""
    
    return {
        'app_id': app_id,
        'rewarded_id': rewarded_id,
        'interstitial_id': interstitial_id,
        'banner_id': banner_id
    }

def update_manifest(app_id):
    """Update AndroidManifest.xml dengan production App ID"""
    manifest_path = 'android/app/src/main/AndroidManifest.xml'
    
    if not os.path.exists(manifest_path):
        print_error(f"File tidak ditemukan: {manifest_path}")
        return False
    
    # Backup
    backup_file(manifest_path)
    
    # Baca file
    with open(manifest_path, 'r') as f:
        content = f.read()
    
    # Ganti App ID
    old_pattern = r'android:value="ca-app-pub-3940256099942544~3347511713"'
    new_value = f'android:value="{app_id}"'
    
    if re.search(old_pattern, content):
        content = re.sub(old_pattern, new_value, content)
        print_success("Test App ID ditemukan dan akan diganti")
    else:
        # Coba pattern umum
        pattern = r'(android:name="com\.google\.android\.gms\.ads\.APPLICATION_ID"\s+android:value=")[^"]+(")'
        content = re.sub(pattern, f'\\1{app_id}\\2', content)
    
    # Tulis kembali
    with open(manifest_path, 'w') as f:
        f.write(content)
    
    print_success(f"AndroidManifest.xml updated dengan App ID: {app_id}")
    return True

def update_ads_manager(ad_ids):
    """Update AdsManager.java dengan production Ad Unit IDs"""
    ads_manager_path = 'android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java'
    
    if not os.path.exists(ads_manager_path):
        print_error(f"File tidak ditemukan: {ads_manager_path}")
        return False
    
    # Backup
    backup_file(ads_manager_path)
    
    # Baca file
    with open(ads_manager_path, 'r') as f:
        content = f.read()
    
    # Ganti Rewarded Ad Unit ID
    old_rewarded = r'private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917";'
    new_rewarded = f'private static final String REWARDED_AD_UNIT_ID = "{ad_ids["rewarded_id"]}";'
    content = re.sub(old_rewarded, new_rewarded, content)
    
    # Tambahkan Interstitial jika ada
    if ad_ids['interstitial_id']:
        if 'INTERSTITIAL_AD_UNIT_ID' not in content:
            # Insert setelah REWARDED_AD_UNIT_ID
            insert_line = f'    private static final String INTERSTITIAL_AD_UNIT_ID = "{ad_ids["interstitial_id"]}";\n'
            content = re.sub(
                r'(private static final String REWARDED_AD_UNIT_ID = "[^"]+";)',
                f'\\1\n{insert_line}',
                content
            )
            print_success(f"Interstitial Ad Unit ID ditambahkan: {ad_ids['interstitial_id']}")
    
    # Tambahkan Banner jika ada
    if ad_ids['banner_id']:
        if 'BANNER_AD_UNIT_ID' not in content:
            insert_line = f'    private static final String BANNER_AD_UNIT_ID = "{ad_ids["banner_id"]}";\n'
            content = re.sub(
                r'(private static final String REWARDED_AD_UNIT_ID = "[^"]+";)',
                f'\\1\n{insert_line}',
                content
            )
            print_success(f"Banner Ad Unit ID ditambahkan: {ad_ids['banner_id']}")
    
    # Tulis kembali
    with open(ads_manager_path, 'w') as f:
        f.write(content)
    
    print_success(f"AdsManager.java updated dengan Rewarded Ad Unit: {ad_ids['rewarded_id']}")
    return True

def check_google_services():
    """Cek apakah google-services.json ada"""
    gs_path = 'android/app/google-services.json'
    
    if os.path.exists(gs_path):
        print_success(f"google-services.json ditemukan: {gs_path}")
        return True
    else:
        print_error(f"google-services.json TIDAK DITEMUKAN!")
        print_warning("Download dari AdMob/Firebase Console")
        print_warning(f"Letakkan di: {gs_path}")
        return False

def create_google_services_template():
    """Buat template google-services.json"""
    template = {
        "project_info": {
            "project_number": "123456789012",
            "project_id": "dragon-arrow-escape",
            "storage_bucket": "dragon-arrow-escape.appspot.com"
        },
        "client": [
            {
                "client_info": {
                    "mobilesdk_app_id": "1:123456789012:android:abcdef1234567890",
                    "android_client_info": {
                        "package_name": "com.dragonarrowescape.game"
                    }
                },
                "services": {
                    "admob": {
                        "app_id": "REPLACE_WITH_YOUR_APP_ID"
                    }
                }
            }
        ],
        "configuration_version": "1"
    }
    
    template_path = 'android/app/google-services.json.template'
    with open(template_path, 'w') as f:
        json.dump(template, f, indent=2)
    
    print_info(f"Template dibuat: {template_path}")
    print_warning("Ganti dengan file asli dari Firebase/AdMob Console!")

def verify_setup():
    """Verifikasi setup sudah benar"""
    print_header("VERIFIKASI SETUP")
    
    checks = []
    
    # Cek AndroidManifest.xml
    manifest_path = 'android/app/src/main/AndroidManifest.xml'
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            content = f.read()
        if 'ca-app-pub-3940256099942544' in content:
            print_error("AndroidManifest.xml masih menggunakan TEST App ID!")
            checks.append(False)
        else:
            print_success("AndroidManifest.xml menggunakan production App ID")
            checks.append(True)
    
    # Cek AdsManager.java
    ads_path = 'android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java'
    if os.path.exists(ads_path):
        with open(ads_path, 'r') as f:
            content = f.read()
        if 'ca-app-pub-3940256099942544' in content:
            print_error("AdsManager.java masih menggunakan TEST Ad Unit IDs!")
            checks.append(False)
        else:
            print_success("AdsManager.java menggunakan production Ad Unit IDs")
            checks.append(True)
    
    # Cek google-services.json
    gs_exists = check_google_services()
    checks.append(gs_exists)
    
    return all(checks)

def main():
    print_header("🎯 ADMOB SETUP TOOL - DRAGON ARROW ESCAPE")
    
    # Cek current directory
    if not os.path.exists('android'):
        print_error("Direktori 'android' tidak ditemukan!")
        print_info("Jalankan script ini dari root project: ~/android-game-bots/dragon-arrow-escape/")
        return
    
    print_warning("⚠️  PENTING: Backup sudah dilakukan otomatis")
    print_warning("⚠️  Pastikan Anda sudah memiliki AdMob App ID dan Ad Unit IDs")
    print()
    
    proceed = input(f"{BLUE}Lanjutkan setup? (y/n): {RESET}").strip().lower()
    if proceed != 'y':
        print_info("Setup dibatalkan")
        return
    
    # Ambil input dari user
    ad_ids = get_user_input()
    
    print_header("UPDATING FILES")
    
    # Update AndroidManifest.xml
    if update_manifest(ad_ids['app_id']):
        print_success("AndroidManifest.xml berhasil diupdate")
    
    # Update AdsManager.java
    if update_ads_manager(ad_ids):
        print_success("AdsManager.java berhasil diupdate")
    
    # Cek google-services.json
    if not check_google_services():
        create_google_services_template()
    
    # Verifikasi
    if verify_setup():
        print_header("✅ SETUP BERHASIL!")
        print_success("Semua file sudah diupdate dengan production IDs")
        print()
        print_info("Langkah selanjutnya:")
        print("1. Pastikan google-services.json sudah ada (download dari Firebase/AdMob)")
        print("2. Build aplikasi: cd android && ./gradlew assembleRelease")
        print("3. Test di real device")
        print("4. Upload ke Google Play Store")
        print()
        print(f"{GREEN}💰 Selamat! Aplikasi siap menghasilkan uang dari iklan!{RESET}")
    else:
        print_header("⚠️ SETUP TIDAK LENGKAP")
        print_warning("Periksa errors di atas dan perbaiki sebelum build")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Setup dibatalkan oleh user{RESET}")
    except Exception as e:
        print_error(f"Error: {str(e)}")
