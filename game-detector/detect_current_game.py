#!/usr/bin/env python3
"""
Game Detector Bot - Deteksi game yang sedang terbuka di Android
Author: Duwi Anjar
Created: 2026-10-07
"""

import subprocess
import time
import json
import os
from datetime import datetime

class GameDetector:
    def __init__(self):
        self.state_file = os.path.expanduser("~/game_detector_state.json")
        self.log_file = os.path.expanduser("~/game_detector.log")
        
    def log(self, message):
        """Log dengan timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")
    
    def run_adb(self, command):
        """Jalankan ADB command"""
        try:
            result = subprocess.run(
                f"adb {command}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip()
        except Exception as e:
            self.log(f"❌ ADB error: {e}")
            return ""
    
    def get_current_app(self):
        """Dapatkan package name aplikasi yang sedang aktif"""
        output = self.run_adb("shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")
        
        if not output:
            return None
        
        # Parse package name dari output
        # Format: mCurrentFocus=Window{xxx u0 package_name/activity}
        for line in output.split('\n'):
            if 'mCurrentFocus' in line or 'mFocusedApp' in line:
                # Extract package name
                parts = line.split()
                for part in parts:
                    if '/' in part and not part.startswith('Window'):
                        package_name = part.split('/')[0]
                        # Remove trailing characters
                        package_name = package_name.split('}')[0]
                        return package_name
        
        return None
    
    def get_app_label(self, package_name):
        """Dapatkan nama user-friendly dari aplikasi"""
        output = self.run_adb(f"shell pm list packages -f | grep {package_name}")
        
        if not output:
            return package_name
        
        # Ambil nama aplikasi yang lebih readable
        # Coba dump aplikasi info
        dump_output = self.run_adb(f"shell dumpsys package {package_name} | grep -A 1 'applicationInfo'")
        
        # Fallback: parse dari package name
        # Contoh: com.soda.pack.puzzle -> Soda Pack Puzzle
        name_parts = package_name.split('.')[-1]  # Ambil bagian terakhir
        readable_name = ' '.join(word.capitalize() for word in name_parts.split('_'))
        
        return readable_name
    
    def get_detailed_app_info(self, package_name):
        """Dapatkan informasi detail aplikasi"""
        # Coba beberapa metode untuk nama app
        
        # Method 1: Dari app label
        label_output = self.run_adb(f"shell pm dump {package_name} | grep 'labelRes'")
        
        # Method 2: Dari aapt (jika ada APK path)
        apk_path_output = self.run_adb(f"shell pm path {package_name}")
        if apk_path_output and apk_path_output.startswith("package:"):
            apk_path = apk_path_output.replace("package:", "").strip()
            label = self.run_adb(f"shell dumpsys package {package_name} | grep 'versionName' | head -1")
        
        # Method 3: Parse package name menjadi readable
        readable_name = self.parse_package_to_name(package_name)
        
        return {
            "package_name": package_name,
            "app_name": readable_name,
            "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def parse_package_to_name(self, package_name):
        """Parse package name menjadi nama yang readable"""
        # Dictionary untuk game yang umum
        known_games = {
            "com.soda.pack.puzzle": "Soda Pack Puzzle",
            "com.lucky.mahjong": "Lucky Mahjong",
            "com.juice.pack": "Juice Pack",
            "com.bus.jam.parking": "Bus Jam Parking",
            "com.bus.parking.dash": "Bus Parking Dash",
            "com.can.sort": "Can Sort",
            "com.coin.dash.shot": "Coin Dash Shot",
            "com.color.power.pop": "Color Power Pop",
            "com.soda.jam.puzzle": "Soda Jam Puzzle",
            "com.jungle.animal.eliminate": "Jungle Animal Eliminate",
            "com.dragon.arrow.escape": "Dragon Arrow Escape",
            # Tambahkan game lain yang sering dimainkan
        }
        
        if package_name in known_games:
            return known_games[package_name]
        
        # Parsing otomatis dari package name
        # Ambil bagian terakhir atau 2-3 bagian terakhir
        parts = package_name.split('.')
        
        if len(parts) >= 3:
            # Ambil 2-3 bagian terakhir
            name_parts = parts[-3:] if len(parts) > 3 else parts[-2:]
            # Filter out common prefixes
            name_parts = [p for p in name_parts if p not in ['com', 'app', 'game', 'play']]
            readable = ' '.join(word.capitalize() for word in name_parts)
        else:
            readable = parts[-1].capitalize()
        
        return readable
    
    def save_state(self, app_info):
        """Simpan state ke file JSON"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(app_info, f, indent=2)
            self.log(f"💾 State saved: {app_info['app_name']}")
        except Exception as e:
            self.log(f"❌ Error saving state: {e}")
    
    def load_state(self):
        """Load state dari file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"⚠️ Error loading state: {e}")
        return None
    
    def detect_and_monitor(self, continuous=False, interval=5):
        """Deteksi game yang sedang terbuka"""
        self.log("🔍 Memulai deteksi game...")
        
        previous_app = None
        
        while True:
            # Cek device terhubung
            devices = self.run_adb("devices | grep device | grep -v 'List of devices'")
            if not devices:
                self.log("⚠️ Tidak ada device Android yang terhubung!")
                self.log("   Sambungkan HP via USB dan enable USB Debugging")
                time.sleep(5)
                continue
            
            # Dapatkan aplikasi yang aktif
            current_package = self.get_current_app()
            
            if current_package and current_package != previous_app:
                # Filter out system apps
                if not any(x in current_package for x in ['launcher', 'systemui', 'settings']):
                    app_info = self.get_detailed_app_info(current_package)
                    
                    self.log(f"🎮 Game terdeteksi: {app_info['app_name']}")
                    self.log(f"   Package: {app_info['package_name']}")
                    
                    # Simpan state
                    self.save_state(app_info)
                    
                    previous_app = current_package
            
            if not continuous:
                break
            
            time.sleep(interval)
    
    def get_current_game_info(self):
        """Dapatkan info game yang sedang aktif (single check)"""
        self.detect_and_monitor(continuous=False)
        return self.load_state()
    
    def start_monitoring(self, interval=5):
        """Mulai monitoring continuous"""
        self.log("🚀 Monitoring mode aktif")
        self.log(f"   Interval check: {interval} detik")
        self.log("   Tekan Ctrl+C untuk stop")
        
        try:
            self.detect_and_monitor(continuous=True, interval=interval)
        except KeyboardInterrupt:
            self.log("\n⏹️ Monitoring dihentikan")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Deteksi game Android yang sedang aktif')
    parser.add_argument('--monitor', '-m', action='store_true', 
                       help='Monitor continuous (default: single check)')
    parser.add_argument('--interval', '-i', type=int, default=5,
                       help='Interval check dalam detik (default: 5)')
    parser.add_argument('--json', '-j', action='store_true',
                       help='Output dalam format JSON')
    
    args = parser.parse_args()
    
    detector = GameDetector()
    
    if args.monitor:
        detector.start_monitoring(interval=args.interval)
    else:
        info = detector.get_current_game_info()
        
        if args.json:
            if info:
                print(json.dumps(info, indent=2))
            else:
                print(json.dumps({"error": "No game detected"}, indent=2))
        else:
            if info:
                print(f"\n🎮 Game yang terdeteksi:")
                print(f"   Nama: {info['app_name']}")
                print(f"   Package: {info['package_name']}")
                print(f"   Waktu: {info['detected_at']}")
            else:
                print("\n⚠️ Tidak ada game yang terdeteksi")

if __name__ == "__main__":
    main()
