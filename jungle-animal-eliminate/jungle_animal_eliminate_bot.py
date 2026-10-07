#!/usr/bin/env python3
"""
Bot Jungle Animal Eliminate - Auto Play + Telegram Notification
Game: com.jungle.bear.tiger.wild.animal.eliminate
"""

import subprocess
import time
import re
import sys
from pathlib import Path
import json
import html

# ============= KONFIGURASI =============
PACKAGE_NAME = "com.jungle.bear.tiger.wild.animal.eliminate"
MIN_WITHDRAW_RP = 300
AD_WAIT_SECONDS = 15

def send_telegram_async(message):
    """Kirim notifikasi ke Telegram"""
    try:
        token = None
        chat_id = None
        
        # Coba ambil dari file config jika ada
        try:
            sys.path.insert(0, '/Users/macbookair/telegram_venv/lib/python3.11/site-packages')
            from telegram_bot_helper import get_telegram_config
            token, chat_id = get_telegram_config()
        except:
            pass
        
        # Fallback: pakai kredensial default
        if not token or not chat_id:
            token = "8849203378:AAEmh0zmO6GoC1x2eb-s5yUVAUDSqremF44"
            chat_id = "-5421593398"
        
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print(f"[!] Telegram error: {e}", flush=True)

def get_connected_devices():
    """Ambil list device Android"""
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3.0)
        lines = result.stdout.strip().split('\n')[1:]
        devices = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == 'device':
                devices.append(parts[0])
        return devices
    except:
        return []

class JungleAnimalBot:
    def __init__(self, serial: str):
        self.serial = serial
        self.tag = f"[{serial}]"
        self.screen_w = 720
        self.screen_h = 1600
        self.scale_x = self.screen_w / 720.0
        self.scale_y = self.screen_h / 1600.0
        self.stop_flag = False
        self.ad_stuck_counter = 0
        self.last_ad_focus = ""
        
    def run_adb(self, cmd, timeout=5.0):
        """Jalankan perintah ADB"""
        try:
            full_cmd = ["adb", "-s", self.serial] + cmd
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
            return result.stdout.strip()
        except:
            return ""
    
    def tap(self, x, y):
        """Tap di koordinat"""
        self.run_adb(["shell", "input", "tap", str(int(x)), str(int(y))])
        time.sleep(0.15)
    
    def swipe(self, x1, y1, x2, y2, duration=300):
        """Swipe dari (x1,y1) ke (x2,y2)"""
        self.run_adb(["shell", "input", "swipe", str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(duration)])
        time.sleep(0.3)
    
    def press_back(self):
        """Tekan BACK"""
        self.run_adb(["shell", "input", "keyevent", "KEYCODE_BACK"])
        time.sleep(0.2)
    
    def get_foreground_focus(self):
        """Cek aplikasi aktif"""
        result = self.run_adb(["shell", "dumpsys", "window"], timeout=2.0)
        if not result:
            return ""
        # Cari mCurrentFocus
        for line in result.split('\n'):
            if 'mCurrentFocus' in line:
                # Extract package name
                return line.lower()
        return ""
    
    def bring_game_to_foreground(self):
        """Buka game"""
        self.run_adb(["shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])
        time.sleep(2)
    
    def detect_game_screen(self):
        """Deteksi game di layar"""
        focus = self.get_foreground_focus()
        # Debug focus
        print(f"{self.tag} [DEBUG] Focus: {focus[:80]}", flush=True)
        return "jungle" in focus or PACKAGE_NAME in focus
    
    def read_saldo_rp(self):
        """Baca saldo Rp dari layar (dummy untuk sekarang, butuh OCR)"""
        # TODO: Implementasi OCR untuk baca saldo
        # Untuk sekarang return 0
        return 0
    
    def check_and_withdraw(self):
        """Coba klik tombol withdraw/tarik setiap 5 menit"""
        # Cek apakah sudah 5 menit sejak last withdraw attempt
        last_withdraw_attempt = getattr(self, 'last_withdraw_attempt', 0)
        now = time.time()
        
        # Coba withdraw setiap 5 menit (300 detik)
        if now - last_withdraw_attempt < 300:
            return False
        
        self.last_withdraw_attempt = now
        
        now_time = time.strftime("%Y-%m-%d %H:%M:%S WIB")
        
        # Kirim notifikasi
        withdraw_msg = (
            f"💰 <b>MENCOBA WITHDRAW</b>\n"
            f"🕐 <code>{now_time}</code>\n\n"
            f"🎮 <b>Game:</b> Jungle Animal Eliminate\n"
            f"🔄 <i>Klik tombol tarik/withdraw...</i>"
        )
        send_telegram_async(withdraw_msg)
        
        print(f"{self.tag} [💰] Coba klik tombol withdraw/tarik...", flush=True)
        
        # Tap area tombol withdraw (pojok kanan atas, tengah atas)
        withdraw_positions = [
            (int(80 * self.scale_x), int(120 * self.scale_y)),   # Kiri atas 1
            (int(100 * self.scale_x), int(150 * self.scale_y)),  # Kiri atas 2
            (int(120 * self.scale_x), int(180 * self.scale_y)),  # Kiri atas 3
            (int(150 * self.scale_x), int(150 * self.scale_y)),  # Kiri atas 4
            (int(360 * self.scale_x), int(150 * self.scale_y)),  # Tengah atas
            (int(600 * self.scale_x), int(180 * self.scale_y)),  # Kanan atas
            (int(650 * self.scale_x), int(150 * self.scale_y)),  # Pojok kanan atas
        ]
        
        for x, y in withdraw_positions:
            self.tap(x, y)
            time.sleep(0.5)
        
        # Cek teks "tarik", "withdraw", "Rp" di layar dan tap
        print(f"{self.tag} [💰] Coba tap area tengah untuk tombol konfirmasi...", flush=True)
        confirm_positions = [
            (int(360 * self.scale_x), int(1100 * self.scale_y)),  # Tombol konfirmasi bawah
            (int(360 * self.scale_x), int(1000 * self.scale_y)),  # Tombol tengah
            (int(450 * self.scale_x), int(1100 * self.scale_y)),  # Kanan bawah
        ]
        
        for x, y in confirm_positions:
            self.tap(x, y)
            time.sleep(0.3)
        
        return True
    
    def detect_warning_popup(self):
        """Deteksi popup peringatan dan klik X di kanan"""
        print(f"{self.tag} [⚠️] Cek popup warning & klik X...", flush=True)
        # Strategi agresif: klik grid pattern di seluruh area kanan
        x_positions = [620, 640, 660, 680, 700]  # 5 kolom dari tengah ke kanan
        y_positions = [180, 220, 260, 300, 340, 380, 420, 460]  # 8 baris dari atas ke bawah
        
        for y in y_positions:
            for x in x_positions:
                self.tap(int(x * self.scale_x), int(y * self.scale_y))
                time.sleep(0.05)  # Delay singkat
        
        # Tekan BACK berkali-kali untuk memastikan popup tertutup
        for _ in range(2):
            self.press_back()
            time.sleep(0.2)
        
        return True
    
    def detect_claim_popup(self):
        """Deteksi popup Selamat / Claim button"""
        # Untuk sekarang gunakan koordinat umum tombol Claim
        # Area tengah-bawah layar
        claim_positions = [
            (int(360 * self.scale_x), int(1100 * self.scale_y)),  # Tengah bawah
            (int(360 * self.scale_x), int(1000 * self.scale_y)),  # Tengah
            (int(360 * self.scale_x), int(900 * self.scale_y)),   # Tengah atas
        ]
        
        # Coba tap area claim
        for x, y in claim_positions:
            self.tap(x, y)
            time.sleep(0.3)
        
        return True
    
    def play_game(self):
        """Main game - tap area permainan"""
        # Tap di beberapa area untuk eliminasi animal
        tap_points = [
            (int(180 * self.scale_x), int(600 * self.scale_y)),
            (int(360 * self.scale_x), int(600 * self.scale_y)),
            (int(540 * self.scale_x), int(600 * self.scale_y)),
            (int(180 * self.scale_x), int(800 * self.scale_y)),
            (int(360 * self.scale_x), int(800 * self.scale_y)),
            (int(540 * self.scale_x), int(800 * self.scale_y)),
        ]
        
        for x, y in tap_points:
            self.tap(x, y)
            time.sleep(0.2)
    
    def handle_ads(self):
        """Handle iklan - deteksi activity iklan spesifik"""
        focus = self.get_foreground_focus()
        
        # Deteksi HANYA activity iklan, bukan game normal
        ad_keywords = ["adactivity", "rewarded", "interstitial", "fyber", "inneractive", "applovin"]
        is_ad = any(k in focus for k in ad_keywords)
        
        if is_ad:
            # Anti-stuck mechanism
            if focus == self.last_ad_focus:
                self.ad_stuck_counter += 1
                print(f"{self.tag} [⚠️] Stuck di iklan yang sama (counter: {self.ad_stuck_counter})", flush=True)
            else:
                self.ad_stuck_counter = 1
                self.last_ad_focus = focus
            
            # Jika stuck lebih dari 3 kali, force escape dengan restart game
            if self.ad_stuck_counter > 3:
                print(f"{self.tag} [🚨] STUCK DETECTED! Force restart game...", flush=True)
                self.run_adb(["shell", "am", "force-stop", PACKAGE_NAME])
                time.sleep(2)
                self.bring_game_to_foreground()
                time.sleep(5)
                self.ad_stuck_counter = 0
                self.last_ad_focus = ""
                return True
            # Kirim notifikasi: Buka iklan
            now_time = time.strftime("%Y-%m-%d %H:%M:%S WIB")
            ad_start_msg = (
                f"📺 <b>MEMBUKA IKLAN</b>\n"
                f"🕐 <code>{now_time}</code>\n\n"
                f"🎮 <b>Game:</b> Jungle Animal Eliminate\n"
                f"⏳ <i>Menunggu {AD_WAIT_SECONDS} detik...</i>"
            )
            send_telegram_async(ad_start_msg)
            
            print(f"{self.tag} [📺] Iklan terdeteksi, tunggu {AD_WAIT_SECONDS} detik...", flush=True)
            time.sleep(AD_WAIT_SECONDS)
            
            # Coba klik X di pojok kanan atas
            print(f"{self.tag} [🔘] Coba klik X pojok kanan atas...", flush=True)
            self.tap(int(665 * self.scale_x), int(70 * self.scale_y))
            time.sleep(0.3)
            
            # Coba klik X di pojok kiri atas
            print(f"{self.tag} [🔘] Coba klik X pojok kiri atas...", flush=True)
            self.tap(int(55 * self.scale_x), int(70 * self.scale_y))
            time.sleep(0.3)
            
            # Klik tombol Google Play di pojok kanan atas (area lebih luas)
            print(f"{self.tag} [🎮] Coba klik tombol Google Play pojok kanan...", flush=True)
            google_play_right = [
                (int(665 * self.scale_x), int(100 * self.scale_y)),
                (int(630 * self.scale_x), int(90 * self.scale_y)),
                (int(650 * self.scale_x), int(120 * self.scale_y)),
            ]
            for x, y in google_play_right:
                self.tap(x, y)
                time.sleep(0.2)
            
            # Klik tombol Google Play di pojok kiri atas
            print(f"{self.tag} [🎮] Coba klik tombol Google Play pojok kiri...", flush=True)
            google_play_left = [
                (int(55 * self.scale_x), int(100 * self.scale_y)),
                (int(90 * self.scale_x), int(90 * self.scale_y)),
                (int(70 * self.scale_x), int(120 * self.scale_y)),
            ]
            for x, y in google_play_left:
                self.tap(x, y)
                time.sleep(0.2)
            
            # Jika tidak ada X, tekan BACK berkali-kali
            print(f"{self.tag} [⬅️] Tekan BACK untuk keluar dari iklan...", flush=True)
            for _ in range(3):
                self.press_back()
                time.sleep(0.4)
            
            # Klik area tombol "Close", "Skip Ad" di tengah bawah dan kanan bawah
            print(f"{self.tag} [🔘] Coba klik tombol Close/Skip Ad...", flush=True)
            close_positions = [
                (int(360 * self.scale_x), int(1150 * self.scale_y)),  # Tengah bawah
                (int(650 * self.scale_x), int(1200 * self.scale_y)),  # Kanan bawah
                (int(360 * self.scale_x), int(100 * self.scale_y)),   # Tengah atas
                (int(650 * self.scale_x), int(50 * self.scale_y)),    # Kanan atas pojok
                (int(50 * self.scale_x), int(50 * self.scale_y)),     # Kiri atas pojok
            ]
            for x, y in close_positions:
                self.tap(x, y)
                time.sleep(0.3)
            
            # Tekan BACK lagi untuk memastikan
            print(f"{self.tag} [⬅️] Tekan BACK sekali lagi...", flush=True)
            for _ in range(2):
                self.press_back()
                time.sleep(0.4)
            
            # Verifikasi apakah sudah kembali ke game
            time.sleep(1)
            focus = self.get_foreground_focus()
            if "eliminate" not in focus.lower():
                print(f"{self.tag} [⚠️] Masih belum kembali ke game, coba BACK lagi...", flush=True)
                for _ in range(3):
                    self.press_back()
                    time.sleep(0.5)

            
            # Kirim notifikasi: Iklan selesai
            now_time = time.strftime("%Y-%m-%d %H:%M:%S WIB")
            ad_end_msg = (
                f"✅ <b>IKLAN SELESAI</b>\n"
                f"🕐 <code>{now_time}</code>\n\n"
                f"🎮 <b>Game:</b> Jungle Animal Eliminate\n"
                f"🔄 <i>Kembali ke game...</i>"
            )
            send_telegram_async(ad_end_msg)
            
            return True
        
        return False
    
    def worker(self):
        """Main loop bot"""
        print(f"{self.tag} [+] Worker aktif untuk Jungle Animal Eliminate!", flush=True)
        
        # Notifikasi start
        start_msg = (
            f"🎮 <b>BOT JUNGLE ANIMAL ELIMINATE STARTED</b>\n"
            f"📱 Device: <code>{self.serial}</code>\n"
            f"💰 Target: Rp {MIN_WITHDRAW_RP}\n"
            f"⏱️ <code>{time.strftime('%Y-%m-%d %H:%M:%S WIB')}</code>"
        )
        send_telegram_async(start_msg)
        
        last_action_time = time.time()
        stuck_threshold = 30
        
        while not self.stop_flag:
            try:
                if not self.detect_game_screen():
                    print(f"{self.tag} [!] Game tidak di layar, membuka...", flush=True)
                    self.bring_game_to_foreground()
                    time.sleep(2)
                    continue
                
                if self.handle_ads():
                    last_action_time = time.time()
                    continue
                
                # Cek popup peringatan dulu
                # self.detect_warning_popup()  # DIMATIKAN
                
                # Cek withdraw dulu
                # if self.check_and_withdraw():  # DIMATIKAN
                #                    last_action_time = time.time()
                #                    time.sleep(2)
                #                    continue
                
                # Cek popup Claim dulu
                if self.detect_claim_popup():
                                print(f"{self.tag} [🎁] Cek popup Claim...", flush=True)
                                time.sleep(0.5)
                
                self.play_game()
                last_action_time = time.time()
                
                if time.time() - last_action_time > stuck_threshold:
                    print(f"{self.tag} [⚠️] Stuck, refresh game...", flush=True)
                    self.press_back()
                    time.sleep(0.5)
                    self.bring_game_to_foreground()
                    last_action_time = time.time()
                
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                # Notifikasi stop
                stop_msg = (
                    f"🛑 <b>BOT DIHENTIKAN</b>\n"
                    f"🕐 <code>{time.strftime('%Y-%m-%d %H:%M:%S WIB')}</code>\n\n"
                    f"🎮 <b>Game:</b> Jungle Animal Eliminate\n"
                    f"📱 Device: <code>{self.serial}</code>"
                )
                send_telegram_async(stop_msg)
                print(f"{self.tag} [🛑] Bot dihentikan oleh user", flush=True)
                break
            except Exception as e:
                print(f"{self.tag} [!] Error: {e}", flush=True)
                # Notifikasi error
                error_msg = (
                    f"❌ <b>ERROR TERJADI</b>\n"
                    f"🕐 <code>{time.strftime('%Y-%m-%d %H:%M:%S WIB')}</code>\n\n"
                    f"🎮 <b>Game:</b> Jungle Animal Eliminate\n"
                    f"📱 Device: <code>{self.serial}</code>\n"
                    f"⚠️ <code>{str(e)[:100]}</code>"
                )
                send_telegram_async(error_msg)
                time.sleep(2)

def main():
    print("=" * 66, flush=True)
    print("   BOT JUNGLE ANIMAL ELIMINATE - AUTO PLAY", flush=True)
    print("=" * 66, flush=True)
    print(f"[+] Target Game: {PACKAGE_NAME}", flush=True)
    print(f"[+] Tekan Ctrl+C untuk berhenti.\n", flush=True)
    
    while True:
        devices = get_connected_devices()
        
        if not devices:
            print("[!] Menunggu perangkat...", flush=True)
            time.sleep(5)
            continue
        
        for serial in devices:
            print(f"[+] Perangkat: {serial}", flush=True)
            bot = JungleAnimalBot(serial)
            
            try:
                bot.worker()
            except KeyboardInterrupt:
                print("\n[!] Stopping...", flush=True)
                sys.exit(0)

if __name__ == "__main__":
    main()
