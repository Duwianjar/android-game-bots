#!/usr/bin/env python3
"""
Script untuk setup Production AdMob IDs
Mengganti TEST IDs dengan Production IDs dari AdMob account

CARA PAKAI:
1. Dapatkan Production IDs dari https://admob.google.com
2. Jalankan script ini: python3 setup_production_ids.py
3. Masukkan IDs saat diminta
4. Script otomatis update semua file

Author: Kiro AI
Date: 2026-10-11
"""

import re
import os
import sys
from pathlib import Path

# Warna untuk terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

def validate_admob_id(ad_id, id_type):
    """Validasi format AdMob ID"""
    if not ad_id:
        return False
    
    # Format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY (App ID)
    # Format: ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY (Ad Unit ID)
    pattern = r'^ca-app-pub-\d{16}[~/]\d{10}$'
    
    if not re.match(pattern, ad_id):
        print_error(f"Format {id_type} tidak valid!")
        print_info("Format yang benar: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY (App ID)")
        print_info("                 : ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY (Ad Unit ID)")
        return False
    
    # Check bukan TEST ID
    if '3940256099942544' in ad_id:
        print_error(f"{id_type} masih TEST ID!")
        return False
    
    return True

def get_production_ids():
    """Minta user input Production IDs"""
    print_header("INPUT PRODUCTION AdMob IDs")
    
    print(f"{Colors.BOLD}Dapatkan IDs dari:{Colors.END}")
    print("1. Buka https://admob.google.com")
    print("2. Login dengan Google Account")
    print("3. Daftarkan aplikasi: Dragon Arrow Escape")
    print("4. Buat Ad Units: Rewarded, Interstitial, Banner")
    print("5. Copy IDs di bawah ini\n")
    
    ids = {}
    
    # App ID
    while True:
        print(f"\n{Colors.BOLD}1. AdMob App ID{Colors.END}")
        print("   Lokasi: Apps > Dragon Arrow Escape > App settings")
        print("   Format: ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY")
        app_id = input("   Paste di sini: ").strip()
        
        if validate_admob_id(app_id, "App ID"):
            ids['app_id'] = app_id
            print_success("App ID valid!")
            break
    
    # Rewarded Ad Unit ID
    while True:
        print(f"\n{Colors.BOLD}2. Rewarded Ad Unit ID{Colors.END}")
        print("   Lokasi: Apps > Dragon Arrow Escape > Ad units > Rewarded")
        print("   Format: ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY")
        rewarded_id = input("   Paste di sini: ").strip()
        
        if validate_admob_id(rewarded_id, "Rewarded Ad Unit ID"):
            ids['rewarded_id'] = rewarded_id
            print_success("Rewarded ID valid!")
            break
    
    # Interstitial Ad Unit ID
    while True:
        print(f"\n{Colors.BOLD}3. Interstitial Ad Unit ID{Colors.END}")
        print("   Lokasi: Apps > Dragon Arrow Escape > Ad units > Interstitial")
        print("   Format: ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY")
        interstitial_id = input("   Paste di sini: ").strip()
        
        if validate_admob_id(interstitial_id, "Interstitial Ad Unit ID"):
            ids['interstitial_id'] = interstitial_id
            print_success("Interstitial ID valid!")
            break
    
    # Banner Ad Unit ID
    while True:
        print(f"\n{Colors.BOLD}4. Banner Ad Unit ID{Colors.END}")
        print("   Lokasi: Apps > Dragon Arrow Escape > Ad units > Banner")
        print("   Format: ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY")
        banner_id = input("   Paste di sini: ").strip()
        
        if validate_admob_id(banner_id, "Banner Ad Unit ID"):
            ids['banner_id'] = banner_id
            print_success("Banner ID valid!")
            break
    
    return ids

def update_android_manifest(ids):
    """Update AndroidManifest.xml dengan Production App ID"""
    manifest_path = Path("android/app/src/main/AndroidManifest.xml")
    
    if not manifest_path.exists():
        print_error(f"File tidak ditemukan: {manifest_path}")
        return False
    
    content = manifest_path.read_text()
    
    # Replace App ID
    old_pattern = r'android:value="ca-app-pub-3940256099942544~\d+"'
    new_value = f'android:value="{ids["app_id"]}"'
    
    updated_content = re.sub(old_pattern, new_value, content)
    
    if updated_content != content:
        manifest_path.write_text(updated_content)
        print_success(f"Updated: {manifest_path}")
        return True
    else:
        print_warning(f"Tidak ada perubahan di: {manifest_path}")
        return False

def update_ads_manager(ids):
    """Update AdsManager.java dengan Production Ad Unit IDs"""
    ads_manager_path = Path("android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java")
    
    if not ads_manager_path.exists():
        print_error(f"File tidak ditemukan: {ads_manager_path}")
        return False
    
    content = ads_manager_path.read_text()
    
    # Replace Rewarded ID
    content = re.sub(
        r'REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/\d+";',
        f'REWARDED_AD_UNIT_ID = "{ids["rewarded_id"]}";',
        content
    )
    
    # Replace Interstitial ID
    content = re.sub(
        r'INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/\d+";',
        f'INTERSTITIAL_AD_UNIT_ID = "{ids["interstitial_id"]}";',
        content
    )
    
    # Replace Banner ID
    content = re.sub(
        r'BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/\d+";',
        f'BANNER_AD_UNIT_ID = "{ids["banner_id"]}";',
        content
    )
    
    # Update comments untuk remove warnings
    content = content.replace(
        '// ⚠️ TEST ID',
        '// ✅ PRODUCTION ID'
    )
    
    ads_manager_path.write_text(content)
    print_success(f"Updated: {ads_manager_path}")
    return True

def create_backup():
    """Buat backup file penting sebelum update"""
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/before_production_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_backup = [
        "android/app/src/main/AndroidManifest.xml",
        "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
    ]
    
    for file_path in files_to_backup:
        src = Path(file_path)
        if src.exists():
            dst = backup_dir / src.name
            shutil.copy2(src, dst)
            print_info(f"Backup: {src} -> {dst}")
    
    print_success(f"Backup created: {backup_dir}")
    return backup_dir

def verify_changes():
    """Verifikasi bahwa semua TEST IDs sudah diganti"""
    print_header("VERIFIKASI PERUBAHAN")
    
    files_to_check = [
        "android/app/src/main/AndroidManifest.xml",
        "android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java"
    ]
    
    all_clean = True
    
    for file_path in files_to_check:
        path = Path(file_path)
        if not path.exists():
            continue
        
        content = path.read_text()
        
        # Check untuk TEST IDs
        if '3940256099942544' in content:
            print_error(f"Masih ada TEST ID di: {file_path}")
            all_clean = False
        else:
            print_success(f"Clean: {file_path}")
    
    return all_clean

def print_summary(ids):
    """Print ringkasan IDs yang digunakan"""
    print_header("RINGKASAN PRODUCTION IDs")
    
    print(f"{Colors.BOLD}App ID:{Colors.END}")
    print(f"  {ids['app_id']}")
    
    print(f"\n{Colors.BOLD}Ad Unit IDs:{Colors.END}")
    print(f"  Rewarded:      {ids['rewarded_id']}")
    print(f"  Interstitial:  {ids['interstitial_id']}")
    print(f"  Banner:        {ids['banner_id']}")

def print_next_steps():
    """Print langkah-langkah selanjutnya"""
    print_header("LANGKAH SELANJUTNYA")
    
    print(f"{Colors.BOLD}1. Build Release APK:{Colors.END}")
    print("   cd android")
    print("   ./gradlew assembleRelease")
    
    print(f"\n{Colors.BOLD}2. Sign APK:{Colors.END}")
    print("   Gunakan Android Studio atau jarsigner")
    
    print(f"\n{Colors.BOLD}3. Upload ke Google Play Console:{Colors.END}")
    print("   https://play.google.com/console")
    
    print(f"\n{Colors.BOLD}4. Wait for Approval:{Colors.END}")
    print("   Review biasanya 1-3 hari")
    
    print(f"\n{Colors.BOLD}5. Monitor Revenue:{Colors.END}")
    print("   https://admob.google.com")
    print("   Check setiap hari untuk optimasi\n")

def main():
    """Main function"""
    print_header("SETUP PRODUCTION AdMob IDs")
    print("Script ini akan mengganti TEST IDs dengan Production IDs")
    print("dari AdMob account Anda untuk mulai menghasilkan uang nyata.\n")
    
    # Check current directory
    if not Path("android").exists():
        print_error("Harus dijalankan dari root directory project!")
        print_info("cd /Users/macbookair/android-game-bots/dragon-arrow-escape")
        sys.exit(1)
    
    # Konfirmasi
    print(f"{Colors.YELLOW}⚠️  PERINGATAN:{Colors.END}")
    print("File akan dimodifikasi. Backup otomatis akan dibuat.\n")
    
    response = input("Lanjutkan? (y/n): ").strip().lower()
    if response != 'y':
        print("Dibatalkan.")
        sys.exit(0)
    
    # Buat backup
    backup_dir = create_backup()
    
    # Get Production IDs dari user
    ids = get_production_ids()
    
    # Confirm IDs
    print_summary(ids)
    print()
    response = input("IDs sudah benar? (y/n): ").strip().lower()
    if response != 'y':
        print("Dibatalkan. Jalankan lagi untuk input ulang.")
        sys.exit(0)
    
    # Update files
    print_header("UPDATING FILES")
    
    success = True
    success &= update_android_manifest(ids)
    success &= update_ads_manager(ids)
    
    if not success:
        print_error("Ada error saat update files!")
        print_info(f"Restore dari backup: {backup_dir}")
        sys.exit(1)
    
    # Verify
    if verify_changes():
        print_success("\n✅ SEMUA TEST IDs BERHASIL DIGANTI!")
        print_success("✅ App siap untuk PRODUCTION!")
        
        print_next_steps()
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 SELAMAT! Game siap menghasilkan uang!{Colors.END}\n")
    else:
        print_error("Verifikasi gagal! Ada TEST IDs yang masih tersisa.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDibatalkan oleh user.")
        sys.exit(0)
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
