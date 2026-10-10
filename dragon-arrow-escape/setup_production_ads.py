#!/usr/bin/env python3
"""
Script otomatis untuk setup Production Ad IDs dari AdMob
Mengganti TEST IDs dengan Production IDs agar bisa menghasilkan uang

Usage:
    python3 setup_production_ads.py
"""

import os
import sys
import re
from datetime import datetime

# ANSI colors untuk output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}  🚀 SETUP PRODUCTION AD IDs - Dragon Arrow Escape{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_step(step, message):
    print(f"{BLUE}[STEP {step}]{RESET} {message}")

def print_success(message):
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message):
    print(f"{RED}❌ {message}{RESET}")

def print_warning(message):
    print(f"{YELLOW}⚠️  {message}{RESET}")

def validate_ad_id(ad_id, id_type):
    """Validasi format Ad ID"""
    # Format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY (App ID)
    # Format: ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY (Ad Unit ID)
    
    if id_type == "app":
        pattern = r'^ca-app-pub-\d{16}~\d{10}$'
    else:
        pattern = r'^ca-app-pub-\d{16}/\d{10}$'
    
    if not re.match(pattern, ad_id):
        return False
    
    # Check bukan TEST ID
    if "3940256099942544" in ad_id:
        print_warning(f"ID ini adalah TEST ID! Tidak akan menghasilkan uang nyata.")
        return False
    
    return True

def backup_file(filepath):
    """Backup file sebelum dimodifikasi"""
    if not os.path.exists(filepath):
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    with open(backup_path, 'w') as f:
        f.write(content)
    
    print_success(f"Backup created: {os.path.basename(backup_path)}")
    return True

def get_user_input():
    """Get Production Ad IDs dari user"""
    print(f"\n{YELLOW}Dapatkan Production IDs dari:{RESET}")
    print(f"1. Buka https://admob.google.com")
    print(f"2. Create App: Dragon Arrow Escape")
    print(f"3. Create 3 Ad Units (Rewarded, Interstitial, Banner)")
    print(f"4. Copy IDs berikut:\n")
    
    ids = {}
    
    # App ID
    print(f"{BLUE}App ID{RESET} (format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY)")
    while True:
        app_id = input("Enter App ID: ").strip()
        if validate_ad_id(app_id, "app"):
            ids['app_id'] = app_id
            print_success("App ID valid!")
            break
        else:
            print_error("Invalid format atau masih TEST ID. Coba lagi.")
    
    print()
    
    # Rewarded Ad Unit ID
    print(f"{BLUE}Rewarded Ad Unit ID{RESET} (format: ca-app-pub-XXXXXXXXXXXXXXXX/1111111111)")
    while True:
        rewarded_id = input("Enter Rewarded ID: ").strip()
        if validate_ad_id(rewarded_id, "unit"):
            ids['rewarded_id'] = rewarded_id
            print_success("Rewarded ID valid!")
            break
        else:
            print_error("Invalid format atau masih TEST ID. Coba lagi.")
    
    print()
    
    # Interstitial Ad Unit ID
    print(f"{BLUE}Interstitial Ad Unit ID{RESET} (format: ca-app-pub-XXXXXXXXXXXXXXXX/2222222222)")
    while True:
        interstitial_id = input("Enter Interstitial ID: ").strip()
        if validate_ad_id(interstitial_id, "unit"):
            ids['interstitial_id'] = interstitial_id
            print_success("Interstitial ID valid!")
            break
        else:
            print_error("Invalid format atau masih TEST ID. Coba lagi.")
    
    print()
    
    # Banner Ad Unit ID
    print(f"{BLUE}Banner Ad Unit ID{RESET} (format: ca-app-pub-XXXXXXXXXXXXXXXX/3333333333)")
    while True:
        banner_id = input("Enter Banner ID: ").strip()
        if validate_ad_id(banner_id, "unit"):
            ids['banner_id'] = banner_id
            print_success("Banner ID valid!")
            break
        else:
            print_error("Invalid format atau masih TEST ID. Coba lagi.")
    
    return ids

def update_manifest(app_id):
    """Update AndroidManifest.xml dengan Production App ID"""
    manifest_path = "android/app/src/main/AndroidManifest.xml"
    
    if not os.path.exists(manifest_path):
        print_error(f"File not found: {manifest_path}")
        return False
    
    # Backup
    backup_file(manifest_path)
    
    # Read file
    with open(manifest_path, 'r') as f:
        content = f.read()
    
    # Replace App ID
    old_pattern = r'android:value="ca-app-pub-\d{16}~\d{10}"'
    new_value = f'android:value="{app_id}"'
    
    updated_content = re.sub(old_pattern, new_value, content)
    
    # Write back
    with open(manifest_path, 'w') as f:
        f.write(updated_content)
    
    print_success(f"AndroidManifest.xml updated with Production App ID")
    return True

def update_ads_manager(rewarded_id, interstitial_id, banner_id):
    """Update AdsManager.java dengan Production Ad Unit IDs"""
    ads_manager_path = "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
    
    if not os.path.exists(ads_manager_path):
        print_error(f"File not found: {ads_manager_path}")
        return False
    
    # Backup
    backup_file(ads_manager_path)
    
    # Read file
    with open(ads_manager_path, 'r') as f:
        content = f.read()
    
    # Replace Rewarded Ad Unit ID
    content = re.sub(
        r'private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-\d{16}/\d{10}";.*',
        f'private static final String REWARDED_AD_UNIT_ID = "{rewarded_id}"; // PRODUCTION ID',
        content
    )
    
    # Replace Interstitial Ad Unit ID
    content = re.sub(
        r'private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-\d{16}/\d{10}";.*',
        f'private static final String INTERSTITIAL_AD_UNIT_ID = "{interstitial_id}"; // PRODUCTION ID',
        content
    )
    
    # Replace Banner Ad Unit ID
    content = re.sub(
        r'private static final String BANNER_AD_UNIT_ID = "ca-app-pub-\d{16}/\d{10}";.*',
        f'private static final String BANNER_AD_UNIT_ID = "{banner_id}"; // PRODUCTION ID',
        content
    )
    
    # Write back
    with open(ads_manager_path, 'w') as f:
        f.write(content)
    
    print_success(f"AdsManager.java updated with Production Ad Unit IDs")
    return True

def verify_changes():
    """Verifikasi bahwa perubahan sudah diterapkan"""
    print(f"\n{BLUE}Verifying changes...{RESET}")
    
    # Check AndroidManifest
    manifest_path = "android/app/src/main/AndroidManifest.xml"
    with open(manifest_path, 'r') as f:
        manifest_content = f.read()
    
    if "3940256099942544" in manifest_content:
        print_error("AndroidManifest masih menggunakan TEST ID!")
        return False
    else:
        print_success("AndroidManifest sudah menggunakan Production ID")
    
    # Check AdsManager
    ads_manager_path = "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
    with open(ads_manager_path, 'r') as f:
        ads_content = f.read()
    
    if "3940256099942544" in ads_content:
        print_error("AdsManager masih menggunakan TEST ID!")
        return False
    else:
        print_success("AdsManager sudah menggunakan Production IDs")
    
    return True

def print_next_steps():
    """Print langkah selanjutnya"""
    print(f"\n{GREEN}{'='*60}{RESET}")
    print(f"{GREEN}  ✅ PRODUCTION IDs BERHASIL DISETUP!{RESET}")
    print(f"{GREEN}{'='*60}{RESET}\n")
    
    print(f"{YELLOW}Langkah selanjutnya:{RESET}\n")
    
    print(f"{BLUE}1. Build Release APK{RESET}")
    print(f"   cd android")
    print(f"   ./gradlew assembleRelease\n")
    
    print(f"{BLUE}2. Test di Real Device{RESET}")
    print(f"   adb install app/build/outputs/apk/release/app-release.apk")
    print(f"   adb logcat | grep -i admob\n")
    
    print(f"{BLUE}3. Upload ke Play Store{RESET}")
    print(f"   • Buka https://play.google.com/console")
    print(f"   • Create new app")
    print(f"   • Upload APK")
    print(f"   • Submit for review\n")
    
    print(f"{YELLOW}⚠️  PENTING:{RESET}")
    print(f"   • JANGAN klik iklan sendiri (banned!)")
    print(f"   • Monitor AdMob dashboard setiap hari")
    print(f"   • Revenue visible setelah 24-48 jam")
    print(f"   • Minimum payout: $100\n")

def main():
    print_header()
    
    # Check apakah di direktori yang benar
    if not os.path.exists("android/app/build.gradle"):
        print_error("Jalankan script ini dari direktori dragon-arrow-escape/")
        print(f"Current dir: {os.getcwd()}")
        sys.exit(1)
    
    print_step(1, "Get Production Ad IDs dari AdMob")
    ids = get_user_input()
    
    print(f"\n{BLUE}Konfirmasi IDs yang akan digunakan:{RESET}")
    print(f"  App ID:          {ids['app_id']}")
    print(f"  Rewarded ID:     {ids['rewarded_id']}")
    print(f"  Interstitial ID: {ids['interstitial_id']}")
    print(f"  Banner ID:       {ids['banner_id']}")
    
    confirm = input(f"\n{YELLOW}Lanjutkan update? (yes/no): {RESET}").strip().lower()
    if confirm != 'yes':
        print_warning("Setup dibatalkan.")
        sys.exit(0)
    
    print(f"\n{BLUE}Updating files...{RESET}\n")
    
    # Update files
    print_step(2, "Update AndroidManifest.xml")
    if not update_manifest(ids['app_id']):
        print_error("Failed to update AndroidManifest.xml")
        sys.exit(1)
    
    print_step(3, "Update AdsManager.java")
    if not update_ads_manager(ids['rewarded_id'], ids['interstitial_id'], ids['banner_id']):
        print_error("Failed to update AdsManager.java")
        sys.exit(1)
    
    # Verify
    print_step(4, "Verify changes")
    if not verify_changes():
        print_error("Verification failed!")
        sys.exit(1)
    
    # Success
    print_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Setup dibatalkan oleh user.{RESET}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Error: {str(e)}")
        sys.exit(1)
