#!/usr/bin/env python3
"""
Monetization Checker - Dragon Arrow Escape
Validasi semua requirement untuk menghasilkan uang dari iklan

Checks:
1. Gradle wrapper exists
2. google-services.json exists
3. Production Ad IDs (bukan test)
4. AdMob SDK dependencies
5. Permissions in AndroidManifest
"""

import os
import re
import sys
from pathlib import Path

# Colors for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

PROJECT_ROOT = Path(__file__).parent
ANDROID_DIR = PROJECT_ROOT / "android"

class MonetizationChecker:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []
        
    def check_gradle_wrapper(self):
        """Check 1: Gradle wrapper"""
        print(f"\n{BLUE}[1/6] Checking Gradle Wrapper...{RESET}")
        
        gradlew = ANDROID_DIR / "gradlew"
        if gradlew.exists():
            print(f"  {GREEN}✓{RESET} Gradle wrapper found")
            self.passed.append("Gradle wrapper exists")
            return True
        else:
            print(f"  {RED}✗{RESET} Gradle wrapper NOT FOUND!")
            print(f"      {YELLOW}Fix:{RESET} Run 'gradle wrapper --gradle-version 8.1.2' in android/ directory")
            self.issues.append("Missing gradle wrapper - cannot build APK")
            return False
    
    def check_google_services_json(self):
        """Check 2: google-services.json"""
        print(f"\n{BLUE}[2/6] Checking google-services.json...{RESET}")
        
        google_services = ANDROID_DIR / "app" / "google-services.json"
        if google_services.exists():
            print(f"  {GREEN}✓{RESET} google-services.json found")
            self.passed.append("google-services.json configured")
            return True
        else:
            print(f"  {RED}✗{RESET} google-services.json NOT FOUND!")
            print(f"      {YELLOW}Fix:{RESET}")
            print(f"      1. Go to https://console.firebase.google.com")
            print(f"      2. Select your project (or create new)")
            print(f"      3. Add Android app with package: com.dragonarrowescape.game")
            print(f"      4. Download google-services.json")
            print(f"      5. Place at: {google_services}")
            self.issues.append("Missing google-services.json - AdMob won't work")
            return False
    
    def check_production_ids(self):
        """Check 3: Production Ad IDs (not test IDs)"""
        print(f"\n{BLUE}[3/6] Checking Ad IDs...{RESET}")
        
        # Check AndroidManifest.xml
        manifest = ANDROID_DIR / "app" / "src" / "main" / "AndroidManifest.xml"
        ads_manager = ANDROID_DIR / "app" / "src" / "main" / "java" / "com" / "dragonarrowescape" / "game" / "AdsManager.java"
        
        test_ids = {
            "ca-app-pub-3940256099942544~3347511713": "App ID (Manifest)",
            "ca-app-pub-3940256099942544/5224354917": "Rewarded Ad",
            "ca-app-pub-3940256099942544/1033173712": "Interstitial Ad",
            "ca-app-pub-3940256099942544/6300978111": "Banner Ad"
        }
        
        found_test_ids = []
        
        # Check Manifest
        if manifest.exists():
            content = manifest.read_text()
            for test_id, name in test_ids.items():
                if test_id in content:
                    found_test_ids.append(name)
        
        # Check AdsManager
        if ads_manager.exists():
            content = ads_manager.read_text()
            for test_id, name in test_ids.items():
                if test_id in content and name not in found_test_ids:
                    found_test_ids.append(name)
        
        if found_test_ids:
            print(f"  {RED}✗{RESET} Using TEST Ad IDs (NO REAL MONEY!):")
            for id_name in found_test_ids:
                print(f"      - {id_name}")
            print(f"\n      {YELLOW}Fix:{RESET}")
            print(f"      1. Create account at https://admob.google.com")
            print(f"      2. Register app 'Dragon Arrow Escape'")
            print(f"      3. Create Ad Units: Rewarded, Interstitial, Banner")
            print(f"      4. Run: python setup_admob.py --app-id YOUR_APP_ID --rewarded YOUR_REWARDED_ID ...")
            self.issues.append(f"Using {len(found_test_ids)} TEST Ad IDs - will NOT earn money")
            return False
        else:
            print(f"  {GREEN}✓{RESET} Production Ad IDs configured")
            self.passed.append("Production Ad IDs active")
            return True
    
    def check_admob_dependencies(self):
        """Check 4: AdMob SDK in build.gradle"""
        print(f"\n{BLUE}[4/6] Checking AdMob Dependencies...{RESET}")
        
        build_gradle = ANDROID_DIR / "app" / "build.gradle"
        
        if not build_gradle.exists():
            print(f"  {RED}✗{RESET} build.gradle not found")
            self.issues.append("Missing build.gradle")
            return False
        
        content = build_gradle.read_text()
        
        required_deps = {
            "play-services-ads": "AdMob SDK",
            "google-services": "Google Services plugin"
        }
        
        missing = []
        for dep, name in required_deps.items():
            if dep not in content:
                missing.append(name)
        
        if missing:
            print(f"  {RED}✗{RESET} Missing dependencies:")
            for dep in missing:
                print(f"      - {dep}")
            self.issues.append(f"Missing {len(missing)} required dependencies")
            return False
        else:
            print(f"  {GREEN}✓{RESET} All AdMob dependencies present")
            self.passed.append("AdMob SDK configured")
            return True
    
    def check_permissions(self):
        """Check 5: Required permissions"""
        print(f"\n{BLUE}[5/6] Checking Permissions...{RESET}")
        
        manifest = ANDROID_DIR / "app" / "src" / "main" / "AndroidManifest.xml"
        
        if not manifest.exists():
            print(f"  {RED}✗{RESET} AndroidManifest.xml not found")
            self.issues.append("Missing AndroidManifest.xml")
            return False
        
        content = manifest.read_text()
        
        required_permissions = {
            "android.permission.INTERNET": "Internet access (required)",
            "android.permission.ACCESS_NETWORK_STATE": "Network state (required)"
        }
        
        optional_permissions = {
            "android.permission.ACCESS_WIFI_STATE": "WiFi state (recommended for better CPM)"
        }
        
        missing_required = []
        missing_optional = []
        
        for perm, desc in required_permissions.items():
            if perm not in content:
                missing_required.append(desc)
        
        for perm, desc in optional_permissions.items():
            if perm not in content:
                missing_optional.append(desc)
        
        if missing_required:
            print(f"  {RED}✗{RESET} Missing required permissions:")
            for perm in missing_required:
                print(f"      - {perm}")
            self.issues.append(f"Missing {len(missing_required)} required permissions")
            return False
        else:
            print(f"  {GREEN}✓{RESET} All required permissions present")
            if missing_optional:
                print(f"  {YELLOW}⚠{RESET} Optional (recommended):")
                for perm in missing_optional:
                    print(f"      - {perm}")
                self.warnings.append("Missing optional permissions (lower CPM)")
            self.passed.append("Permissions configured")
            return True
    
    def check_ad_implementation(self):
        """Check 6: Ad implementation in code"""
        print(f"\n{BLUE}[6/6] Checking Ad Implementation...{RESET}")
        
        ads_manager = ANDROID_DIR / "app" / "src" / "main" / "java" / "com" / "dragonarrowescape" / "game" / "AdsManager.java"
        main_activity = ANDROID_DIR / "app" / "src" / "main" / "java" / "com" / "dragonarrowescape" / "game" / "MainActivity.java"
        
        issues = []
        
        if not ads_manager.exists():
            print(f"  {RED}✗{RESET} AdsManager.java not found")
            self.issues.append("Missing AdsManager implementation")
            return False
        
        if not main_activity.exists():
            print(f"  {RED}✗{RESET} MainActivity.java not found")
            self.issues.append("Missing MainActivity")
            return False
        
        # Check for key methods
        ads_content = ads_manager.read_text()
        main_content = main_activity.read_text()
        
        required_methods = [
            ("loadRewardedAd", "Rewarded ad loading"),
            ("showRewardedAd", "Rewarded ad display"),
            ("loadInterstitialAd", "Interstitial ad loading"),
            ("showInterstitialAd", "Interstitial ad display")
        ]
        
        missing = []
        for method, desc in required_methods:
            if method not in ads_content:
                missing.append(desc)
        
        if missing:
            print(f"  {RED}✗{RESET} Missing ad methods:")
            for method in missing:
                print(f"      - {method}")
            self.issues.append("Incomplete ad implementation")
            return False
        
        # Check JavaScript bridge
        if "AndroidAds" not in main_content:
            print(f"  {YELLOW}⚠{RESET} JavaScript bridge might not be connected")
            self.warnings.append("JavaScript bridge not detected")
        
        print(f"  {GREEN}✓{RESET} Ad implementation complete")
        self.passed.append("All ad types implemented")
        return True
    
    def print_summary(self):
        """Print final summary"""
        print(f"\n{'='*70}")
        print(f"{BLUE}MONETIZATION CHECK SUMMARY{RESET}")
        print(f"{'='*70}")
        
        print(f"\n{GREEN}✓ PASSED ({len(self.passed)}):{RESET}")
        for item in self.passed:
            print(f"  • {item}")
        
        if self.warnings:
            print(f"\n{YELLOW}⚠ WARNINGS ({len(self.warnings)}):{RESET}")
            for item in self.warnings:
                print(f"  • {item}")
        
        if self.issues:
            print(f"\n{RED}✗ CRITICAL ISSUES ({len(self.issues)}):{RESET}")
            for i, item in enumerate(self.issues, 1):
                print(f"  {i}. {item}")
        
        print(f"\n{'='*70}")
        
        if not self.issues:
            print(f"{GREEN}🎉 ALL CHECKS PASSED! Ready to earn money!{RESET}")
            print(f"\n{BLUE}Next steps:{RESET}")
            print(f"1. Build APK: cd android && ./gradlew assembleRelease")
            print(f"2. Test on device: adb install app/build/outputs/apk/release/app-release.apk")
            print(f"3. Publish to Play Store")
            print(f"4. Monitor revenue: https://admob.google.com")
            return True
        else:
            print(f"{RED}❌ {len(self.issues)} CRITICAL ISSUES MUST BE FIXED{RESET}")
            print(f"\n{BLUE}Priority actions:{RESET}")
            
            if "Missing gradle wrapper" in str(self.issues):
                print(f"\n1️⃣  Install Gradle Wrapper:")
                print(f"   cd {ANDROID_DIR}")
                print(f"   gradle wrapper --gradle-version 8.1.2")
                print(f"   chmod +x gradlew")
            
            if "Missing google-services.json" in str(self.issues):
                print(f"\n2️⃣  Get google-services.json:")
                print(f"   https://console.firebase.google.com → Add Android app")
            
            if "TEST Ad IDs" in str(self.issues):
                print(f"\n3️⃣  Replace TEST IDs with PRODUCTION IDs:")
                print(f"   python setup_admob.py --app-id YOUR_APP_ID --rewarded ... --interstitial ... --banner ...")
            
            return False

def main():
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Dragon Arrow Escape - Monetization Validator{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    checker = MonetizationChecker()
    
    # Run all checks
    checker.check_gradle_wrapper()
    checker.check_google_services_json()
    checker.check_production_ids()
    checker.check_admob_dependencies()
    checker.check_permissions()
    checker.check_ad_implementation()
    
    # Print summary
    success = checker.print_summary()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
