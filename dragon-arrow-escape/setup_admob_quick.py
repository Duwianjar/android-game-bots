#!/usr/bin/env python3
"""
Setup Production AdMob IDs - Quick Script
Ganti TEST Ad IDs dengan Production IDs dari AdMob

Usage:
    python3 setup_admob_quick.py

Author: Hermes Automation
Date: 10 Oktober 2026
"""

import os
import re
import sys
from datetime import datetime

# Colors for terminal output
class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header():
    print(f"\n{Color.CYAN}{Color.BOLD}{'='*70}{Color.END}")
    print(f"{Color.CYAN}{Color.BOLD}   🚀 SETUP PRODUCTION ADMOB IDs - Dragon Arrow Escape{Color.END}")
    print(f"{Color.CYAN}{Color.BOLD}{'='*70}{Color.END}\n")

def print_success(msg):
    print(f"{Color.GREEN}✅ {msg}{Color.END}")

def print_error(msg):
    print(f"{Color.RED}❌ {msg}{Color.END}")

def print_warning(msg):
    print(f"{Color.YELLOW}⚠️  {msg}{Color.END}")

def print_info(msg):
    print(f"{Color.BLUE}ℹ️  {msg}{Color.END}")

def validate_ad_id(ad_id, id_type):
    """Validate AdMob ID format"""
    if id_type == "app":
        pattern = r'^ca-app-pub-\d{16}~\d{10}$'
    else:  # ad unit
        pattern = r'^ca-app-pub-\d{16}/\d{10}$'
    
    if not re.match(pattern, ad_id):
        return False
    
    # Check not TEST ID
    if "3940256099942544" in ad_id:
        print_warning(f"Ini adalah TEST ID! Gunakan Production ID dari AdMob.")
        return False
    
    return True

def backup_file(filepath):
    """Backup file sebelum modify"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        with open(backup_path, 'w') as f:
            f.write(content)
        print_success(f"Backup created: {os.path.basename(backup_path)}")
        return True
    except Exception as e:
        print_error(f"Failed to backup: {e}")
        return False

def update_manifest(app_id):
    """Update AndroidManifest.xml dengan App ID"""
    manifest_path = "android/app/src/main/AndroidManifest.xml"
    
    if not os.path.exists(manifest_path):
        print_error(f"File not found: {manifest_path}")
        return False
    
    # Backup first
    if not backup_file(manifest_path):
        return False
    
    try:
        with open(manifest_path, 'r') as f:
            content = f.read()
        
        # Replace App ID
        old_pattern = r'android:value="ca-app-pub-3940256099942544~\d+"'
        new_value = f'android:value="{app_id}"'
        new_content = re.sub(old_pattern, new_value, content)
        
        if new_content == content:
            print_warning("App ID tidak berubah - sudah correct atau pattern tidak match")
        
        with open(manifest_path, 'w') as f:
            f.write(new_content)
        
        print_success("AndroidManifest.xml updated")
        return True
    except Exception as e:
        print_error(f"Failed to update manifest: {e}")
        return False

def update_ads_manager(rewarded_id, interstitial_id, banner_id):
    """Update AdsManager.java dengan Ad Unit IDs"""
    ads_manager_path = "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
    
    if not os.path.exists(ads_manager_path):
        print_error(f"File not found: {ads_manager_path}")
        return False
    
    # Backup first
    if not backup_file(ads_manager_path):
        return False
    
    try:
        with open(ads_manager_path, 'r') as f:
            content = f.read()
        
        # Replace Rewarded Ad ID
        content = re.sub(
            r'private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/\d+";.*',
            f'private static final String REWARDED_AD_UNIT_ID = "{rewarded_id}"; // ✅ PRODUCTION',
            content
        )
        
        # Replace Interstitial Ad ID
        content = re.sub(
            r'private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/\d+";.*',
            f'private static final String INTERSTITIAL_AD_UNIT_ID = "{interstitial_id}"; // ✅ PRODUCTION',
            content
        )
        
        # Replace Banner Ad ID
        content = re.sub(
            r'private static final String BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/\d+";.*',
            f'private static final String BANNER_AD_UNIT_ID = "{banner_id}"; // ✅ PRODUCTION',
            content
        )
        
        with open(ads_manager_path, 'w') as f:
            f.write(content)
        
        print_success("AdsManager.java updated")
        return True
    except Exception as e:
        print_error(f"Failed to update AdsManager: {e}")
        return False

def verify_setup():
    """Verify bahwa setup berhasil"""
    print(f"\n{Color.BOLD}Verifying setup...{Color.END}")
    
    manifest_path = "android/app/src/main/AndroidManifest.xml"
    ads_manager_path = "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
    
    issues = []
    
    # Check manifest
    try:
        with open(manifest_path, 'r') as f:
            manifest_content = f.read()
        
        if "3940256099942544" in manifest_content:
            issues.append("AndroidManifest.xml masih menggunakan TEST ID")
        else:
            print_success("AndroidManifest.xml: Production ID ✓")
    except:
        issues.append("Cannot read AndroidManifest.xml")
    
    # Check AdsManager
    try:
        with open(ads_manager_path, 'r') as f:
            ads_content = f.read()
        
        if "3940256099942544" in ads_content:
            issues.append("AdsManager.java masih menggunakan TEST ID")
        else:
            print_success("AdsManager.java: Production IDs ✓")
    except:
        issues.append("Cannot read AdsManager.java")
    
    if issues:
        print_warning("\nIssues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print_success("\n✅ Setup verification PASSED! All Production IDs configured correctly.")
    return True

def main():
    print_header()
    
    print(f"{Color.BOLD}Step 1: Dapatkan Production IDs dari AdMob{Color.END}")
    print_info("Buka https://admob.google.com")
    print_info("Create app & 3 ad units (Rewarded, Interstitial, Banner)")
    print()
    
    print(f"{Color.BOLD}Step 2: Input Production IDs{Color.END}\n")
    
    # Input App ID
    print(f"{Color.CYAN}App ID (AndroidManifest.xml):{Color.END}")
    print("Format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY")
    app_id = input("➜ App ID: ").strip()
    
    if not validate_ad_id(app_id, "app"):
        print_error("Invalid App ID format!")
        sys.exit(1)
    
    print()
    
    # Input Rewarded Ad ID
    print(f"{Color.CYAN}Rewarded Ad Unit ID:{Color.END}")
    print("Format: ca-app-pub-XXXXXXXXXXXXXXXX/1111111111")
    rewarded_id = input("➜ Rewarded ID: ").strip()
    
    if not validate_ad_id(rewarded_id, "unit"):
        print_error("Invalid Rewarded Ad ID format!")
        sys.exit(1)
    
    print()
    
    # Input Interstitial Ad ID
    print(f"{Color.CYAN}Interstitial Ad Unit ID:{Color.END}")
    print("Format: ca-app-pub-XXXXXXXXXXXXXXXX/2222222222")
    interstitial_id = input("➜ Interstitial ID: ").strip()
    
    if not validate_ad_id(interstitial_id, "unit"):
        print_error("Invalid Interstitial Ad ID format!")
        sys.exit(1)
    
    print()
    
    # Input Banner Ad ID
    print(f"{Color.CYAN}Banner Ad Unit ID:{Color.END}")
    print("Format: ca-app-pub-XXXXXXXXXXXXXXXX/3333333333")
    banner_id = input("➜ Banner ID: ").strip()
    
    if not validate_ad_id(banner_id, "unit"):
        print_error("Invalid Banner Ad ID format!")
        sys.exit(1)
    
    print()
    
    # Confirmation
    print(f"\n{Color.BOLD}Konfirmasi IDs:{Color.END}")
    print(f"App ID:          {app_id}")
    print(f"Rewarded ID:     {rewarded_id}")
    print(f"Interstitial ID: {interstitial_id}")
    print(f"Banner ID:       {banner_id}")
    print()
    
    confirm = input(f"{Color.YELLOW}Lanjutkan setup? (yes/no): {Color.END}").strip().lower()
    if confirm not in ['yes', 'y']:
        print_warning("Setup dibatalkan.")
        sys.exit(0)
    
    print(f"\n{Color.BOLD}Step 3: Updating files...{Color.END}\n")
    
    # Update files
    success = True
    
    if not update_manifest(app_id):
        success = False
    
    if not update_ads_manager(rewarded_id, interstitial_id, banner_id):
        success = False
    
    if not success:
        print_error("\n❌ Setup FAILED! Check errors above.")
        sys.exit(1)
    
    # Verify
    verify_setup()
    
    # Next steps
    print(f"\n{Color.GREEN}{Color.BOLD}{'='*70}{Color.END}")
    print(f"{Color.GREEN}{Color.BOLD}   🎉 SETUP COMPLETE!{Color.END}")
    print(f"{Color.GREEN}{Color.BOLD}{'='*70}{Color.END}\n")
    
    print(f"{Color.BOLD}Next Steps:{Color.END}")
    print(f"{Color.CYAN}1. Build release APK:{Color.END}")
    print(f"   cd android && ./gradlew assembleRelease")
    print()
    print(f"{Color.CYAN}2. Test di device:{Color.END}")
    print(f"   adb install app/build/outputs/apk/release/app-release.apk")
    print()
    print(f"{Color.CYAN}3. Upload ke Play Store:{Color.END}")
    print(f"   https://play.google.com/console")
    print()
    print(f"{Color.GREEN}{Color.BOLD}🚀 SIAP MENGHASILKAN UANG!{Color.END}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Color.YELLOW}Setup dibatalkan oleh user.{Color.END}")
        sys.exit(0)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        sys.exit(1)
