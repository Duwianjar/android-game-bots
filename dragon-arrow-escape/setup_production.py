#!/usr/bin/env python3
"""
Quick Production Setup - Ganti TEST IDs dengan PRODUCTION IDs
Interactive script dengan validasi dan backup otomatis
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ANSI Colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{CYAN}{BOLD}{'='*70}{RESET}")
    print(f"{CYAN}{BOLD}{text}{RESET}")
    print(f"{CYAN}{BOLD}{'='*70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def validate_app_id(app_id):
    """Validate AdMob App ID format"""
    pattern = r'^ca-app-pub-\d{16}~\d{10}$'
    return re.match(pattern, app_id) is not None

def validate_ad_unit_id(unit_id):
    """Validate AdMob Ad Unit ID format"""
    pattern = r'^ca-app-pub-\d{16}/\d{10}$'
    return re.match(pattern, unit_id) is not None

def get_input_with_validation(prompt, validator, error_msg):
    """Get user input with validation"""
    while True:
        value = input(f"{prompt}: ").strip()
        if validator(value):
            return value
        print_error(error_msg)
        print(f"   Format benar: ca-app-pub-XXXXXXXXXXXXXXXX~/1234567890")

def backup_files():
    """Create backup of current files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backup_{timestamp}")
    backup_dir.mkdir(exist_ok=True)
    
    files_to_backup = [
        "android/app/src/main/AndroidManifest.xml",
        "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
    ]
    
    for file_path in files_to_backup:
        src = Path(file_path)
        if src.exists():
            dst = backup_dir / src.name
            dst.write_text(src.read_text())
    
    return backup_dir

def update_manifest(app_id):
    """Update AndroidManifest.xml with production App ID"""
    manifest_path = Path("android/app/src/main/AndroidManifest.xml")
    content = manifest_path.read_text()
    
    # Replace TEST App ID
    content = re.sub(
        r'ca-app-pub-3940256099942544~3347511713',
        app_id,
        content
    )
    
    manifest_path.write_text(content)
    print_success(f"AndroidManifest.xml updated with App ID")

def update_ads_manager(rewarded_id, interstitial_id, banner_id):
    """Update AdsManager.java with production Ad Unit IDs"""
    manager_path = Path("android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java")
    content = manager_path.read_text()
    
    # Replace TEST IDs
    replacements = {
        'ca-app-pub-3940256099942544/5224354917': rewarded_id,
        'ca-app-pub-3940256099942544/1033173712': interstitial_id,
        'ca-app-pub-3940256099942544/6300978111': banner_id
    }
    
    for old_id, new_id in replacements.items():
        content = content.replace(old_id, new_id)
    
    # Update comments
    content = content.replace('// ⚠️ TEST ID', '// ✅ PRODUCTION ID')
    
    manager_path.write_text(content)
    print_success(f"AdsManager.java updated with Ad Unit IDs")

def verify_updates():
    """Verify that updates were applied correctly"""
    manifest_path = Path("android/app/src/main/AndroidManifest.xml")
    manager_path = Path("android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java")
    
    manifest_content = manifest_path.read_text()
    manager_content = manager_path.read_text()
    
    # Check if TEST IDs still exist
    test_ids = [
        'ca-app-pub-3940256099942544~3347511713',
        'ca-app-pub-3940256099942544/5224354917',
        'ca-app-pub-3940256099942544/1033173712',
        'ca-app-pub-3940256099942544/6300978111'
    ]
    
    found_test_ids = []
    for test_id in test_ids:
        if test_id in manifest_content or test_id in manager_content:
            found_test_ids.append(test_id)
    
    if found_test_ids:
        print_warning(f"Masih ada {len(found_test_ids)} TEST ID yang tersisa")
        return False
    
    print_success("Semua TEST IDs berhasil diganti!")
    return True

def main():
    print_header("🚀 Dragon Arrow Escape - Production AdMob Setup")
    
    print("Script ini akan mengganti TEST IDs dengan PRODUCTION IDs dari AdMob")
    print("TEST IDs = $0 revenue (tidak menghasilkan uang)")
    print("PRODUCTION IDs = revenue nyata dari iklan\n")
    
    print_warning("Pastikan kamu sudah punya 4 IDs dari https://admob.google.com")
    print("Belum punya? Baca: CARA_PRODUCTION_ADMOB.md\n")
    
    response = input("Lanjutkan? (y/n): ").strip().lower()
    if response != 'y':
        print("Setup dibatalkan")
        sys.exit(0)
    
    print("\n📋 Masukkan IDs dari AdMob:\n")
    
    # Get App ID
    app_id = get_input_with_validation(
        "App ID (ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY)",
        validate_app_id,
        "Format App ID salah!"
    )
    
    # Get Rewarded Ad Unit ID
    rewarded_id = get_input_with_validation(
        "Rewarded Ad Unit ID (ca-app-pub-XXXXXXXXXXXXXXXX/1111111111)",
        validate_ad_unit_id,
        "Format Rewarded Ad Unit ID salah!"
    )
    
    # Get Interstitial Ad Unit ID
    interstitial_id = get_input_with_validation(
        "Interstitial Ad Unit ID (ca-app-pub-XXXXXXXXXXXXXXXX/2222222222)",
        validate_ad_unit_id,
        "Format Interstitial Ad Unit ID salah!"
    )
    
    # Get Banner Ad Unit ID
    banner_id = get_input_with_validation(
        "Banner Ad Unit ID (ca-app-pub-XXXXXXXXXXXXXXXX/3333333333)",
        validate_ad_unit_id,
        "Format Banner Ad Unit ID salah!"
    )
    
    # Confirm
    print("\n📋 Review IDs yang akan diupdate:")
    print(f"   App ID:          {app_id}")
    print(f"   Rewarded ID:     {rewarded_id}")
    print(f"   Interstitial ID: {interstitial_id}")
    print(f"   Banner ID:       {banner_id}\n")
    
    response = input("Update sekarang? (y/n): ").strip().lower()
    if response != 'y':
        print("Update dibatalkan")
        sys.exit(0)
    
    # Backup
    print("\n📦 Creating backup...")
    backup_dir = backup_files()
    print_success(f"Backup saved to: {backup_dir}/")
    
    # Update files
    print("\n🔧 Updating files...")
    update_manifest(app_id)
    update_ads_manager(rewarded_id, interstitial_id, banner_id)
    
    # Verify
    print("\n🔍 Verifying updates...")
    if verify_updates():
        print_header("🎉 PRODUCTION IDs BERHASIL DI-UPDATE!")
        
        print("📋 Next steps:")
        print("   1. Verifikasi: ./verify_monetization.sh")
        print("   2. Build Release: cd android && ./gradlew assembleRelease")
        print("   3. Test di device fisik")
        print("   4. Upload ke Play Store")
        print("   5. Tunggu 24-48 jam untuk ads aktif\n")
        
        print("💰 Setelah itu, game SIAP MENGHASILKAN UANG!\n")
    else:
        print_error("Update tidak lengkap, cek file secara manual")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup dibatalkan oleh user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)
