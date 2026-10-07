#!/usr/bin/env python3
"""
Juice Pack Frenzy Automation Bot (com.apnabankshop.juice)
Multi-Device Parallel Engine - Calibrated Coordinates, Fast Burst Tap, Smart Reward OCR,
Robust Ad Dismissal (No Ad Loop), Auto-Install, Main Ulang & DANA Withdrawal
"""
import subprocess
import multiprocessing
import time
import sys
import os
import re
import signal
import cv2
import numpy as np

PACKAGE_NAME = "com.apnabankshop.juice"
LAUNCH_ACTIVITY = "com.apnabankshop.juice/.jui.ja.Splash"
GAME_ACTIVITY = "com.apnabankshop.juice/com.apnabankshop.juice.jui.ja.Juice"
OCR_HELPER_PATH = "/Users/macbookair/ocr_helper"
CLICK_REWARD_DURING_AD_WAIT = False  # Nonaktif: jangan klik Koleksi/Klaim/Unduh saat menunggu iklan
AD_WAIT_SECONDS = 10          # Menonton iklan selama 10 detik
MIN_WITHDRAWAL_RP = 20000      # Target saldo =Rp minimal 150 untuk penarikan

# Koordinat 8 Kolom Rak Juice & Baris Slot Botol (Terkalibrasi 720x1640)
SHELF_COLUMNS_X = [55, 140, 225, 310, 400, 490, 580, 665]
SHELF_SLOTS_Y = [765, 685, 605, 525, 445]

def get_connected_devices():
    """Mengambil daftar semua HP Android yang terhubung via ADB."""
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3.0, check=False)
        lines = res.stdout.strip().splitlines()[1:]
        devices = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices
    except Exception:
        return []

def is_scrcpy_running_for(serial):
    try:
        res = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=2.0, check=False)
        return any("scrcpy" in line and serial in line for line in res.stdout.splitlines())
    except Exception:
        return False

def ensure_scrcpy_running(serial):
    if not is_scrcpy_running_for(serial):
        print(f"[{serial}] [+] Membuka jendela tampilan layar scrcpy (Juice Pack Frenzy)...", flush=True)
        try:
            subprocess.Popen(
                ["scrcpy", "-s", serial, "--window-title", f"Juice Pack Frenzy - {serial}", "--max-fps=25", "--no-audio"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.2)
            print(f"[{serial}] [✔] Jendela scrcpy berhasil dibuka!", flush=True)
        except Exception as e:
            print(f"[{serial}] [!] Catatan scrcpy: {e}", flush=True)

def is_empty_shelf(patch):
    """Mendeteksi apakah slot rak adalah area kosong / latar belakang rak tanpa botol."""
    if patch is None or patch.size == 0:
        return True
    std = float(patch.std())
    if std < 40:
        return True
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    mean_hsv = np.mean(hsv, axis=(0, 1))
    if (100 <= mean_hsv[0] <= 135) and (mean_hsv[2] < 160) and (std < 50):
        return True
    return False

def detect_popup_reward_button_ocr(ocr_items, scale_y=1.0):
    """Mendeteksi tombol popup reward nyata berbasis teks OCR."""
    all_text = " ".join([it["text"].lower() for it in ocr_items])
    modal_indicators = ["selamat", "hadiah", "congratulations", "reward", "koin", "bonus", "menang", "gandakan", "klaim", "koleksi"]
    has_reward_modal = any(k in all_text for k in modal_indicators)

    # 1. Deteksi langsung teks tombol klaim/reward
    reward_keywords = ["bebas klik", "koleksi", "klaim", "claim", "collect", "gandakan", "dapatkan", "ambil", "terima"]
    for it in ocr_items:
        t = it["text"].lower()
        if any(kw in t for kw in reward_keywords) and it["cy"] > int(500 * scale_y):
            return it["cx"], it["cy"], f"Tombol Reward '{it['text']}'"

    # 2. Jika modal hadiah terbuka dan ada tombol 'Menarik' di bagian bawah (y > 900)
    if has_reward_modal and ("menarik" in all_text):
        for it in ocr_items:
            t = it["text"].lower()
            if "menarik" in t and it["cy"] > int(900 * scale_y):
                return it["cx"], it["cy"], "Tombol Menarik Modal Reward"

    return None

def detect_dialog_close_x_button(img, scale_x=1.0, scale_y=1.0):
    """Mendeteksi tombol X di sudut dialog modal saat popup menutup layar game."""
    y1, y2 = int(200 * scale_y), int(650 * scale_y)
    x1, x2 = int(520 * scale_x), int(695 * scale_x)
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 130)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    min_dim, max_dim = int(16 * min(scale_x, scale_y)), int(80 * max(scale_x, scale_y))
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if min_dim <= w <= max_dim and min_dim <= h <= max_dim:
            patch = crop[y:y+h, x:x+w]
            if patch.std() > 18:
                candidates.append((x1 + x + w // 2, y1 + y + h // 2, patch.std()))
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        best = candidates[0]
        return best[0], best[1], "Tombol X Tutup Modal"
    return None

class JuicePackRunner:
    def __init__(self, serial):
        self.serial = serial
        self.tag = f"[{self.serial}]"
        self.step_counter = 0
        self.width = 720
        self.height = 1640
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.ad_wait_done = False
        self.withdrawn_pending_ad = False
        self.aggressive_ad_dismiss_count = 0

    def run_adb(self, cmd, timeout=5.0):
        try:
            res = subprocess.run(["adb", "-s", self.serial] + cmd, capture_output=True, text=True, timeout=timeout, check=False)
            return res.stdout.strip()
        except Exception:
            return ""

    def tap(self, x, y):
        subprocess.run(["adb", "-s", self.serial, "shell", f"input tap {int(x)} {int(y)}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def tap_burst(self, coords, delay=0.03):
        """Mengeklik banyak titik koordinat secara cepat/paralel via adb background input."""
        if not coords:
            return
        try:
            cmd_parts = [f"input tap {int(x)} {int(y)}" for x, y in coords]
            chained_cmd = " & ".join(cmd_parts) + " & wait"
            subprocess.run(["adb", "-s", self.serial, "shell", chained_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4.0)
        except Exception:
            for x, y in coords:
                self.tap(x, y)
                if delay > 0:
                    time.sleep(delay)

    def bring_game_to_foreground(self):
        """Membawa aplikasi game kembali ke layar depan secara aman tanpa SecurityException."""
        self.run_adb(["shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])

    def press_back(self):
        subprocess.run(["adb", "-s", self.serial, "shell", "input keyevent 4"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def get_screenshot(self):
        try:
            res = subprocess.run(["adb", "-s", self.serial, "exec-out", "screencap -p"], capture_output=True, timeout=3.5)
            if len(res.stdout) > 0:
                img_arr = np.frombuffer(res.stdout, np.uint8)
                img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                if img is not None:
                    h, w = img.shape[:2]
                    self.height, self.width = h, w
                    self.scale_x = self.width / 720.0
                    self.scale_y = self.height / 1640.0
                    return img
        except Exception:
            pass
        return None

    def check_and_wake_device(self):
        power = self.run_adb(["shell", "dumpsys", "power"])
        if any(s in power for s in ["mWakefulness=Asleep", "mWakefulness=Dozing"]):
            print(f"{self.tag} [+] Membangunkan layar HP...", flush=True)
            self.run_adb(["shell", "input keyevent 224 && input keyevent 82"])
            time.sleep(1.0)
        return True

    def check_and_install_game_if_missing(self):
        """Mengecek apakah Juice Pack Frenzy terpasang di HP. Jika belum, otomatis download via Play Store."""
        installed = self.run_adb(["shell", "pm", "list", "packages"])
        if PACKAGE_NAME in installed:
            return True

        print(f"\n{self.tag} [!] Aplikasi Juice Pack Frenzy BELUM TERPASANG di HP ini!", flush=True)
        print(f"{self.tag} [+] Membuka Google Play Store untuk mencari & menginstal Juice Pack Frenzy...", flush=True)
        self.run_adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "market://search?q=Juice+Pack+Frenzy"])
        time.sleep(3.0)

        for _ in range(8):
            img = self.get_screenshot()
            if img is None:
                time.sleep(1.0)
                continue
            ocr_items = self.run_full_ocr(img)
            install_btn = None
            for it in ocr_items:
                t = it["text"].lower()
                if t in ["install", "instal", "pasang", "dapatkan", "unduh"] and (it["cy"] < int(550 * self.scale_y)):
                    install_btn = it
                    break
            if install_btn:
                print(f"{self.tag} [+] Menemukan tombol '{install_btn['text']}' di Play Store ({install_btn['cx']}, {install_btn['cy']})!", flush=True)
                print(f"{self.tag}     -> Mengeklik tombol Install sekarang...", flush=True)
                self.tap(install_btn["cx"], install_btn["cy"])
                break
            time.sleep(1.5)

        print(f"{self.tag} [⏳] Menunggu proses download & instalasi selesai...", flush=True)
        for wait_count in range(45):
            time.sleep(4.0)
            installed_now = self.run_adb(["shell", "pm", "list", "packages"])
            if PACKAGE_NAME in installed_now:
                print(f"{self.tag} [✔] Game Juice Pack Frenzy BERHASIL DIINSTAL di HP!", flush=True)
                time.sleep(2.0)
                self.bring_game_to_foreground()
                time.sleep(3.0)
                return True

            img = self.get_screenshot()
            if img is not None:
                ocr_items = self.run_full_ocr(img)
                for it in ocr_items:
                    if it["text"].lower() in ["buka", "open", "play", "mainkan"] and it["cy"] < int(550 * self.scale_y):
                        print(f"{self.tag} [✔] Menemukan tombol '{it['text']}' di Play Store. Membuka game sekarang...", flush=True)
                        self.tap(it["cx"], it["cy"])
                        time.sleep(3.0)
                        return True
        return False

    def get_foreground_focus(self):
        try:
            res = subprocess.run(["adb", "-s", self.serial, "shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"], capture_output=True, text=True, timeout=2.0, check=False)
            return res.stdout.strip()
        except Exception:
            return ""

    def detect_ad_countdown_seconds(self, img=None):
        """Mendeteksi countdown timer iklan di pojok kiri atas (misal: '53s left to be rewarded' / '16s left')."""
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return None
        ocr_items = self.run_full_ocr(img)
        for it in ocr_items:
            if it["cy"] < int(350 * self.scale_y):
                t = it["text"].lower()
                m = re.search(r'(\d{1,2})\s*s\s*(?:left|to be rewarded|remaining|sisa|detik)?', t, re.IGNORECASE)
                if m:
                    sec = int(m.group(1))
                    if 2 <= sec <= 90:
                        return sec
        return None

    def detect_and_click_ad_x_button(self, img=None):
        """Mendeteksi dan mengeklik tombol X / Tutup di pojok kanan atas pada layar iklan."""
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return False

        sx, sy = self.scale_x, self.scale_y
        ocr_items = self.run_full_ocr(img)

        # 1. Cek via OCR untuk karakter X / Tutup / Close / Skip di area atas (cy < 350 * sy)
        for it in ocr_items:
            if it["cy"] < int(350 * sy):
                t = it["text"].strip().lower()
                if t in ["x", "✕", "✖", "×", ">>", "skip", "close", "tutup"] or (len(t) == 1 and t in "xX+"):
                    print(f"{self.tag} [★] Menemukan tombol Tutup Iklan '{it['text']}' via OCR di ({it['cx']}, {it['cy']})! Mengeklik...", flush=True)
                    self.tap(it["cx"], it["cy"])
                    time.sleep(0.3)
                    return True

        # 2. Cek via deteksi kontur tombol X di pojok kanan atas (x: 580..710, y: 30..300)
        y1, y2 = int(30 * sy), int(300 * sy)
        x1, x2 = int(580 * sx), int(710 * sx)
        crop = img[y1:y2, x1:x2]
        if crop.size > 0:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 40, 140)
            cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            min_dim, max_dim = int(14 * min(sx, sy)), int(85 * max(sx, sy))
            candidates = []
            for cnt in cnts:
                x, y, w, h = cv2.boundingRect(cnt)
                if min_dim <= w <= max_dim and min_dim <= h <= max_dim:
                    patch = crop[y:y+h, x:x+w]
                    if patch.std() > 20:
                        candidates.append((x1 + x + w // 2, y1 + y + h // 2))
            if candidates:
                candidates.sort(key=lambda item: item[0], reverse=True)
                best_x, best_y = candidates[0]
                print(f"{self.tag} [★] Menemukan tombol X di pojok kanan atas di ({best_x}, {best_y})! Mengeklik...", flush=True)
                self.tap(best_x, best_y)
                time.sleep(0.3)
                return True

        # 3. Fallback tap burst semua titik X umum di kanan atas & letterbox
        top_right_x_pts = [
            (int(665 * sx), int(70 * sy)),
            (int(665 * sx), int(115 * sy)),
            (int(665 * sx), int(160 * sy)),
            (int(665 * sx), int(250 * sy)),
            (int(640 * sx), int(80 * sy)),
            (int(675 * sx), int(85 * sy)),
            (int(650 * sx), int(240 * sy)),
            (int(55 * sx), int(70 * sy)),
            (int(55 * sx), int(115 * sy)),
            (int(55 * sx), int(250 * sy))
        ]
        self.tap_burst(top_right_x_pts, delay=0.03)
        return True

    def close_ad_screen_thoroughly(self):
        """Menutup iklan secara menyeluruh: BACK -> Jika muncul peringatan (Continue vs Close It) klik CONTINUE -> Endcard X -> Kembali Game."""
        sx, sy = self.scale_x, self.scale_y
        self.press_back()
        time.sleep(0.4)

        img = self.get_screenshot()
        if img is not None:
            ocr_items = self.run_full_ocr(img)
            # 1. Jika muncul dialog peringatan (misal: 'Confirm to close?', 'You will not be rewarded', dsb)
            # dan ada tombol Continue / Continui / Lanjutkan, klik CONTINUE!
            for it in ocr_items:
                t = it["text"].lower()
                if any(k in t for k in ["continue", "continui", "continu", "lanjutkan", "resume"]) and it["cy"] > int(200 * sy):
                    print(f"{self.tag} [+] Terdeteksi dialog peringatan iklan. Mengeklik 'Continue' di ({it['cx']}, {it['cy']})...", flush=True)
                    self.tap(it["cx"], it["cy"])
                    time.sleep(1.2)
                    break

        # 2. Tap titik tombol X pojok kanan atas & kiri atas (posisi umum endcard / banner close)
        close_points = [
            (int(665 * sx), int(70 * sy)),
            (int(665 * sx), int(115 * sy)),
            (int(635 * sx), int(75 * sy)),
            (int(55 * sx), int(70 * sy)),
            (int(55 * sx), int(115 * sy))
        ]
        self.detect_and_click_ad_x_button(img)
        for tx, ty in close_points:
            self.tap(tx, ty)
            time.sleep(0.12)

        self.press_back()
        time.sleep(0.3)
        self.bring_game_to_foreground()
        time.sleep(0.5)

    def wait_ad_and_close_ad(self, reason="Iklan Video Reward"):
        """Menunggu iklan/reward. Jika timer iklan di pojok kiri atas terdeteksi, waktu tunggu disamakan."""
        print(f"\n{self.tag} [⏳] {reason} terdeteksi! Menunggu iklan (cek timer pojok kiri atas + klik Koleksi/Klaim jika muncul)...", flush=True)
        clicked_reward_during_wait = False
        remaining = AD_WAIT_SECONDS
        last_timer_seen = None

        while remaining > 0:
            img_wait = self.get_screenshot()

            # 1. Sinkronkan waktu tunggu dengan timer iklan di pojok kiri atas jika terlihat.
            if img_wait is not None:
                detected_timer = self.detect_ad_countdown_seconds(img_wait)
                if detected_timer and 1 <= detected_timer <= 90:
                    # Samakan dengan timer iklan yang tampil, terutama jika lebih lama dari default.
                    if last_timer_seen != detected_timer:
                        print(f"{self.tag} [⏱] Timer iklan terdeteksi di pojok kiri atas: {detected_timer} detik. Menyamakan waktu tunggu...", flush=True)
                    remaining = detected_timer
                    last_timer_seen = detected_timer

                # 2. Jika di tengah proses tunggu muncul tombol reward seperti Koleksi/Klaim, klik dulu lalu lanjut tunggu.
                ocr_wait = self.run_full_ocr(img_wait)
                reward_btn = detect_popup_reward_button_ocr(ocr_wait, self.scale_y)
                if CLICK_REWARD_DURING_AD_WAIT and reward_btn:
                    bx, by, desc = reward_btn
                    print(f"{self.tag} [★] Saat tunggu iklan, MENEMUKAN {desc} di ({bx}, {by})! Mengeklik AREA tombol dulu, lalu lanjut tunggu iklan...", flush=True)
                    # Klik agresif area tombol: OCR kadang memberi titik teks, bukan pusat tombol.
                    reward_tap_points = [
                        (bx, by),
                        (bx, by + int(28 * self.scale_y)),
                        (bx, by + int(56 * self.scale_y)),
                        (bx, by + int(86 * self.scale_y)),
                        (int(360 * self.scale_x), by),
                        (int(360 * self.scale_x), by + int(35 * self.scale_y)),
                        (int(360 * self.scale_x), by + int(70 * self.scale_y)),
                        (int(360 * self.scale_x), by + int(105 * self.scale_y)),
                    ]
                    # Pastikan titik tetap di area layar aman.
                    reward_tap_points = [(max(20, min(int(x), self.width - 20)), max(200, min(int(y), self.height - 80))) for x, y in reward_tap_points]
                    self.tap_burst(reward_tap_points, delay=0.04)
                    self.record_tapped_coord(bx, by)
                    clicked_reward_during_wait = True
                    time.sleep(1.2)

            print(f"{self.tag}    -> Menonton iklan: sisa {remaining} detik...", flush=True)
            sleep_for = 2 if remaining >= 2 else remaining
            time.sleep(sleep_for)
            remaining -= sleep_for

            focus = self.get_foreground_focus()
            if "com.android.vending" in focus:
                self.run_adb(["shell", "am", "force-stop", "com.android.vending"])

        if clicked_reward_during_wait:
            print(f"{self.tag} [✔] Tombol reward sempat diklik saat menunggu. Melanjutkan penutupan iklan...", flush=True)
        print(f"{self.tag} [✔] Waktu tunggu iklan selesai! Menutup iklan (BACK + Tap X pojok)...", flush=True)
        self.close_ad_screen_thoroughly()
        if self.withdrawn_pending_ad:
            self.withdrawn_pending_ad = False
            print(f"{self.tag} [✔] Selesai 1x menonton iklan! Fitur penarikan saldo =Rp kini aktif kembali.", flush=True)


    def handle_app_focus_and_ads(self):
        focus = self.get_foreground_focus()

        # 1. Google Play Store terbuka oleh iklan -> Tutup paksa Play Store & kembali ke game
        if "com.android.vending" in focus:
            print(f"{self.tag} [!] Google Play Store terbuka oleh iklan! Menutup paksa Play Store & kembali ke game...", flush=True)
            self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
            self.press_back()
            time.sleep(0.3)
            self.bring_game_to_foreground()
            time.sleep(0.8)
            self.ad_wait_done = False
            return False

        # 2. Periksa Dialog Konfirmasi Penarikan Sebelum Memeriksa Iklan (Anti-Salah Deteksi Iklan)
        img = self.get_screenshot()
        if img is not None:
            ocr_quick = self.run_full_ocr(img)
            quick_text = " ".join([it["text"].lower() for it in ocr_quick])

            # Cek jika layar Chrome terbuka
            if any(k in quick_text for k in ["selamat datang di chrome", "persyaratan layanan", "google chrome"]):
                print(f"{self.tag} [!] Layar browser Chrome terdeteksi! Menutup paksa Chrome & kembali ke game...", flush=True)
                self.run_adb(["shell", "am", "force-stop", "com.android.chrome"])
                self.press_back()
                time.sleep(0.3)
                self.bring_game_to_foreground()
                time.sleep(0.8)
                return False
            has_konfirmasi = any(any(k in it["text"].lower() for k in ["konfirmasi", "confirm", "setuju"]) and it["cy"] > int(450 * self.scale_y) for it in ocr_quick)
            has_withdr_text = any(k in quick_text for k in ["informasi sudah benar", "pastikan informasi", "periksa akun", "nomor rekening", "nomor akun", "pilih metode"])
            if has_konfirmasi or has_withdr_text:
                print(f"{self.tag} [★] Terdeteksi dialog Konfirmasi Penarikan di layar (Bukan Iklan)! Melanjutkan alur penarikan...", flush=True)
                self.handle_withdrawal_modal_flow()
                return False

        # 3. Iklan Video / Interstitial Ad (Khusus SDK Iklan Nyata)
        ad_keywords = ["mbrewardvideoactivity", "applovinfullscreenactivity", "adactivity", "companionadactivity", "bigo", "bytedance", "pangle", "unity3d", "applovin", "adcolony", "kwad", "mbridge", "vungle", "ironsource", "mintegral", "rewardvideo"]
        is_ad_activity = any(k in focus.lower() for k in ad_keywords)

        if is_ad_activity:
            if not self.ad_wait_done:
                self.wait_ad_and_close_ad("Iklan Video / Interstitial")
                self.ad_wait_done = True
                self.aggressive_ad_dismiss_count = 0
            else:
                self.aggressive_ad_dismiss_count += 1
                if self.aggressive_ad_dismiss_count >= 3:
                    print(f"\n{self.tag} [!] Layar iklan masih aktif berulang ({self.aggressive_ad_dismiss_count}x). Kembali menunggu iklan 10 detik sampai selesai...", flush=True)
                    self.wait_ad_and_close_ad("Iklan Masih Berjalan (Re-wait 10s)")
                    self.aggressive_ad_dismiss_count = 0
                    return False

                print(f"{self.tag} [!] Layar iklan masih aktif ({self.aggressive_ad_dismiss_count}x). Memeriksa timer & tombol X kanan atas...", flush=True)

                img = self.get_screenshot()
                # Cek apakah ada countdown timer di pojok atas
                remaining_sec = self.detect_ad_countdown_seconds(img)
                if remaining_sec and remaining_sec > 1:
                    print(f"{self.tag} [⏳] Terdeteksi timer iklan: '{remaining_sec}s' di pojok atas! Menunggu {remaining_sec} detik sampai selesai...", flush=True)
                    for rem in range(remaining_sec, 0, -2):
                        print(f"{self.tag}    -> Menunggu sisa timer iklan: {rem} detik...", flush=True)
                        time.sleep(2)
                    time.sleep(1.0)
                    self.aggressive_ad_dismiss_count = 0

                # Periksa dan klik tombol X di kanan atas
                self.detect_and_click_ad_x_button(img)
                self.close_ad_screen_thoroughly()
            return False

        # Reset status tunggu iklan saat game normal kembali aktif
        self.ad_wait_done = False
        self.aggressive_ad_dismiss_count = 0
        self.withdrawn_pending_ad = False

        # 3. Jika aplikasi Juice Pack Frenzy sama sekali tidak di layar
        if PACKAGE_NAME not in focus:
            print(f"{self.tag} [!] Juice Pack Frenzy tidak di layar. Membuka aplikasi...", flush=True)
            self.bring_game_to_foreground()
            time.sleep(1.5)
            return False

        return True

    def run_full_ocr(self, img, crop=None):
        if not os.path.exists(OCR_HELPER_PATH) or img is None:
            return []
        if crop is not None:
            x1, y1, x2, y2 = crop
            crop_img = img[y1:y2, x1:x2]
            off_x, off_y = x1, y1
            h_crop, w_crop = crop_img.shape[:2]
        else:
            crop_img = img
            off_x, off_y = 0, 0
            h_crop, w_crop = self.height, self.width

        tmp_path = f"/tmp/juice_ocr_{self.serial}.png"
        cv2.imwrite(tmp_path, crop_img)
        try:
            out = subprocess.check_output([OCR_HELPER_PATH, tmp_path], stderr=subprocess.DEVNULL, timeout=2.5).decode("utf-8")
            items = []
            for line in out.strip().splitlines():
                parts = line.split("|")
                if len(parts) == 2:
                    text = parts[0].strip()
                    coords = [float(x) for x in parts[1].split(",")]
                    cx = int((coords[0] + coords[2] / 2.0) * w_crop) + off_x
                    cy = int((1.0 - (coords[1] + coords[3] / 2.0)) * h_crop) + off_y
                    items.append({"text": text, "cx": cx, "cy": cy})
            return items
        except Exception:
            return []

    def is_dana_selected(self, img, ocr_items):
        for it in ocr_items:
            t = it["text"].lower()
            if ("→ dana" in t or "•dana" in t or "• dana" in t) and (int(400*self.scale_y) < it["cy"] < int(800*self.scale_y)):
                return True
        if img is not None:
            y1, y2 = int(600 * self.scale_y), int(730 * self.scale_y)
            x1, x2 = int(380 * self.scale_x), int(660 * self.scale_x)
            dana_roi = img[y1:y2, x1:x2]
            if dana_roi.size > 0:
                hsv = cv2.cvtColor(dana_roi, cv2.COLOR_BGR2HSV)
                red_pixels = np.sum(((hsv[:, :, 0] < 12) | (hsv[:, :, 0] > 168)) & (hsv[:, :, 1] > 80) & (hsv[:, :, 2] > 80))
                if red_pixels > 40:
                    return True
        return False

    def find_modal_confirm_button(self, img, ocr_items):
        """Mencari tombol Konfirmasi/Confirm/Kirim/OK pada modal penarikan via fuzzy OCR & Green Button CV."""
        sx, sy = self.scale_x, self.scale_y

        # 1. Deteksi berbasis teks OCR (Fuzzy match)
        kw = ["konfirm", "kontirm", "firmasi", "irmasi", "confirm", "setuju", "kirim", "mengetahui", "mengerti", "paham"]
        candidates = []
        for it in ocr_items:
            t = it["text"].lower().strip()
            cy, cx = it["cy"], it["cx"]
            if any(ig in t for ig in ["semakin", "aturan", "perkiraan", "diterima", "tingkat", "level"]):
                continue
            if int(950 * sy) <= cy <= int(1350 * sy):
                if any(k in t for k in kw) or t in ["ok", "ya", "lanjut", "tarik"]:
                    candidates.append((cx, cy, f"Tombol '{it['text']}'"))

        if candidates:
            candidates.sort(key=lambda c: c[1], reverse=True)
            return candidates[0]

        # 2. Deteksi berbasis Computer Vision Kontur Tombol Hijau
        if img is not None:
            y1, y2 = int(950 * sy), int(1350 * sy)
            x1, x2 = int(80 * sx), int(640 * sx)
            crop = img[y1:y2, x1:x2]
            if crop.size > 0:
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                green_mask = (hsv[:,:,0] >= 35) & (hsv[:,:,0] <= 85) & (hsv[:,:,1] >= 60) & (hsv[:,:,2] >= 70)
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5))
                clean_mask = cv2.morphologyEx(green_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
                cnts, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                btn_cnts = []
                for c in cnts:
                    x, y, w, h = cv2.boundingRect(c)
                    area = cv2.contourArea(c)
                    if (140 * sx <= w <= 560 * sx) and (30 * sy <= h <= 150 * sy) and (area >= 3500 * sx * sy):
                        btn_cnts.append((x1 + x + w // 2, y1 + y + h // 2, f"Tombol Hijau CV ({w}x{h})"))
                if btn_cnts:
                    btn_cnts.sort(key=lambda b: b[1], reverse=True)
                    return btn_cnts[0]

        return None

    def handle_withdrawal_modal_flow(self):
        """Alur penarikan saldo ke DANA saat =Rp >= MIN_WITHDRAWAL_RP."""
        print(f"\n{self.tag} =======================================================", flush=True)
        print(f"{self.tag}       [★] MEMULAI ALUR PENARIKAN DANA OTOMATIS        ", flush=True)
        print(f"{self.tag} =======================================================", flush=True)
        sx, sy = self.scale_x, self.scale_y

        for cycle in range(25):
            time.sleep(0.9)
            img = self.get_screenshot()
            if img is None:
                break
            ocr_items = self.run_full_ocr(img)
            all_text_lower = " ".join([it["text"].lower() for it in ocr_items])

            # 0. Jika saldo sudah Rp0 / penarikan selesai, segera tutup halaman penarikan
            is_saldo_zero = any(k in all_text_lower for k in ["diterima: rp0", "diterima: rp 0", "kurang rp", "~rp0", "~rp 0", "dana rpo", "dana rp0", "dana rp 0"]) or ("dana" in all_text_lower and any(r in all_text_lower for r in ["rpo", "rp0", "rp 0"]) and any(p in all_text_lower for p in ["pastikan", "informasi", "periksa"]))
            if is_saldo_zero and any(k in all_text_lower for k in ["pilih metode", "saldo saya", "penukaran", "menarik", "pastikan"]):
                print(f"{self.tag} [✔] Saldo penarikan sudah Rp0 (Penarikan Berhasil!). Menutup halaman penarikan kembali ke game...", flush=True)
                self.press_back()
                time.sleep(0.6)
                self.withdrawn_pending_ad = True
                return

            # 1. Jika soft keyboard terbuka menutupi layar, tekan BACK untuk sembunyikan keyboard
            if any(k in all_text_lower for k in ["?123", "indonesia", "q w", "z x"]) or (any(it["text"] in ["1","2","3","4","5"] and it["cy"] > int(1000 * sy) for it in ocr_items)):
                print(f"{self.tag} [+] Keyboard virtual terdeteksi terbuka. Menutup keyboard...", flush=True)
                self.press_back()
                time.sleep(0.6)
                img = self.get_screenshot()
                ocr_items = self.run_full_ocr(img)
                all_text_lower = " ".join([it["text"].lower() for it in ocr_items])

            # 1b. Jika muncul form kosong (misal OVO belum diisi: 'masukkan hp', 'silakan masukkan nama'), tekan BACK untuk kembali ke DANA
            if any(k in all_text_lower for k in ["masukkan hp", "silakan masukkan", "mulai 08"]):
                print(f"{self.tag} [!] Terdeteksi form akun kosong (bukan DANA terisi). Menekan BACK untuk kembali...", flush=True)
                self.press_back()
                time.sleep(0.6)
                continue

            # 2. PRIORITAS UTAMA: Cari dan klik tombol Konfirmasi (via OCR atau Green Button CV)
            confirm_btn = self.find_modal_confirm_button(img, ocr_items)
            if confirm_btn:
                k_cx, k_cy, k_desc = confirm_btn
                print(f"{self.tag} [+] [Konfirmasi Penarikan ({cycle+1})] Menemukan {k_desc} di ({k_cx}, {k_cy}). Mengeklik Konfirmasi...", flush=True)
                self.tap(k_cx, k_cy)
                time.sleep(1.0)
                continue

            # 3. Pilihan metode DANA
            if "pilih metode" in all_text_lower or ("ovo" in all_text_lower and "dana" in all_text_lower):
                print(f"\n{self.tag} [+] Terdeteksi halaman Pilih Metode Penarikan (Opsi OVO & DANA):", flush=True)
                dana_btn = None
                for it in ocr_items:
                    if "dana" in it["text"].lower() and int(500 * sy) < it["cy"] < int(800 * sy):
                        dana_btn = it
                        break
                d_x = dana_btn["cx"] if dana_btn else int(456 * sx)
                d_y = dana_btn["cy"] if dana_btn else int(661 * sy)
                print(f"{self.tag}     -> Memilih opsi DANA di ({d_x}, {d_y})...", flush=True)
                self.tap(d_x, d_y)
                time.sleep(0.6)
                img = self.get_screenshot()
                ocr_items = self.run_full_ocr(img)

                menarik_btn = None
                for it in ocr_items:
                    if "menarik" in it["text"].lower() and int(750 * sy) < it["cy"] < int(1200 * sy):
                        menarik_btn = it
                        break
                m_cx = menarik_btn["cx"] if menarik_btn else int(554 * sx)
                m_cy = menarik_btn["cy"] if menarik_btn else int(852 * sy)
                print(f"{self.tag}     -> Mengeklik tombol hijau Menarik di ({m_cx}, {m_cy})...", flush=True)
                self.tap(m_cx, m_cy)
                time.sleep(1.2)
                continue

            # 4. Dialog Modal Penarikan (Periksa Akun / Pastikan Informasi / Berhasil) jika tombol belum tertangkap di atas
            modal_keywords = ["periksa akun", "memastikan", "pastikan informasi", "informasi sudah benar", "nama lengkap", "telah berhasil", "berhasil", "sukses"]
            if any(k in all_text_lower for k in modal_keywords) and not any(k in all_text_lower for k in ["tingkat:", "antri"]):
                pts = [
                    (int(362 * sx), int(1118 * sy)),
                    (int(361 * sx), int(1250 * sy)),
                    (int(360 * sx), int(1200 * sy)),
                    (int(360 * sx), int(1080 * sy)),
                    (int(360 * sx), int(1150 * sy))
                ]
                print(f"{self.tag} [+] Terdeteksi dialog modal penarikan. Mengeklik burst tombol Konfirmasi di ({pts[0][0]}, {pts[0][1]})...", flush=True)
                self.tap_burst(pts, delay=0.08)
                time.sleep(1.2)
                continue

            # 5. Layar game utama kembali aktif
            if any(k in all_text_lower for k in ["tingkat:", "antri", "level"]):
                self.withdrawn_pending_ad = True
                print(f"{self.tag} [✔] Seluruh alur penarikan selesai! Layar game utama aktif.", flush=True)
                return

            self.press_back()
            time.sleep(0.8)

        self.withdrawn_pending_ad = True
        print(f"{self.tag} [✔] Penarikan selesai! Menandai jeda penarikan sampai 1x tonton iklan.", flush=True)
        print(f"{self.tag} [!] Kembali ke game utama.", flush=True)
        self.bring_game_to_foreground()
        time.sleep(0.5)


    def check_and_handle_top_rp(self, ocr_items):
        """Mengecek saldo =Rp KIRI di header atas. Jika >= MIN_WITHDRAWAL_RP, langsung tarik saldo."""
        if not ocr_items:
            return False

        if self.withdrawn_pending_ad:
            if self.step_counter % 8 == 1:
                print(f"{self.tag} [.] Penarikan saldo baru saja selesai. Menunggu 1x tonton iklan sebelum penarikan berikutnya.", flush=True)
            return False

        sx, sy = self.scale_x, self.scale_y
        left_rp, right_rp = None, None
        click_coords = (int(240 * sx), int(70 * sy))

        for item in ocr_items:
            cy, cx = item["cy"], item["cx"]
            # Hanya periksa baris badge saldo di y: 45..140 (abaikan banner notifikasi atas cy < 45)
            if not (int(45 * sy) <= cy <= int(140 * sy)):
                continue
            t = item["text"].replace("o", "0").replace("O", "0").replace("I", "1").replace("l", "1")
            m = re.search(r"Rp\s*([0-9]+)", t, re.IGNORECASE)
            if m:
                val = int(m.group(1))
                # Saldo KIRI (=Rp): terletak di area kiri tengah (cx <= 330)
                if cx <= int(330 * sx):
                    left_rp = val
                    click_coords = (cx, cy)
                # Saldo KANAN (Poin): terletak di area kanan (cx > 330)
                else:
                    right_rp = val

        if left_rp is not None:
            right_str = f" | Rp Kanan: {right_rp}" if right_rp is not None else ""
            if left_rp >= MIN_WITHDRAWAL_RP:
                print(f"\n{self.tag} [★] MENEMUKAN Saldo =Rp{left_rp} >= {MIN_WITHDRAWAL_RP} (Target Tercapai!{right_str})", flush=True)
                print(f"{self.tag}     -> Mengeklik tombol =Rp KIRI di ({click_coords[0]}, {click_coords[1]})...", flush=True)
                self.tap(click_coords[0], click_coords[1])
                time.sleep(0.6)
                self.handle_withdrawal_modal_flow()
                return True
            elif self.step_counter % 5 == 1:
                print(f"{self.tag} [.] Status Saldo Header: =Rp{left_rp} / {MIN_WITHDRAWAL_RP}{right_str}", flush=True)

        return False

    def detect_shelf_cans(self, img):
        """Mendeteksi posisi aktual botol terbawah/terdepan di setiap kolom rak."""
        sx, sy = self.scale_x, self.scale_y
        front_cans = []
        shelf_cols_x = [int(x * sx) for x in SHELF_COLUMNS_X]
        slots_y = [int(y * sy) for y in SHELF_SLOTS_Y]

        for col_idx, col_x in enumerate(shelf_cols_x):
            for y in slots_y:
                patch = img[max(0, y-18):min(self.height, y+18), max(0, col_x-18):min(self.width, col_x+18)]
                if patch.size == 0:
                    continue
                if not is_empty_shelf(patch) and patch.std() > 42:
                    front_cans.append({"col": col_idx + 1, "cx": col_x, "cy": y})
                    break

        return front_cans

    def detect_floating_reward_bubble(self, ocr_items, img=None):
        """Mendeteksi Kado Terbang, Uang/Koin, dan Gelembung Balon Iklan dengan ukuran fleksibel di mana pun melintas."""
        sx, sy = self.scale_x, self.scale_y

        # 1. Deteksi Berbasis Teks / Simbol OCR (Cakupan luas y: 260..1480)
        reward_kw = [
            "kado", "gift", "box", "hadiah", "parcel", "bonus", "spin", "film", "tonton",
            "buble", "balon", "bubble", "balloon", "uang", "koin", "coin", "cash", "gold",
            "free", "gratis", "klaim", "claim", "reward", "dapatkan", "ambil", "ad", "video", "play", "kupon"
        ]
        for it in ocr_items:
            cy, cx = it["cy"], it["cx"]
            if int(260 * sy) <= cy <= int(1480 * sy):
                if int(260 * sy) <= cy <= int(360 * sy) and cx <= int(200 * sx):
                    continue
                if int(260 * sy) <= cy <= int(360 * sy) and int(240 * sx) <= cx <= int(480 * sx):
                    continue
                t = it["text"].lower().strip()
                if any(ig in t for ig in ["tingkat", "antri", "buka kunci", "level", "refresh", "urutkan"]):
                    continue
                import re
                if re.search(r'(\+\s*\d+|\d+\s*koin|\d+\s*rp|rp\s*\d+|\d+\s*%)', t) or any(kw in t for kw in reward_kw):
                    if not self.is_coord_recent(cx, cy):
                        return cx, cy, f"Reward Teks/Icon '{it['text']}'"

        # 2. Deteksi Visual Adaptif Bebas Ukuran (y: 260..1480)
        if img is not None:
            y1, y2 = int(260 * sy), int(1500 * sy)
            x1, x2 = int(10 * sx), int(710 * sx)
            crop = img[y1:y2, x1:x2]
            if crop.size > 0:
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

                # Floor Masking agar lantai parkir tidak menggabungkan kontur gelembung
                floor_mask = (hsv[:,:,0] >= 100) & (hsv[:,:,0] <= 115) & (hsv[:,:,1] <= 90) & (hsv[:,:,2] >= 190)

                sat_mask = (hsv[:,:,1] > 35) & (hsv[:,:,2] > 50)
                bright_mask = (hsv[:,:,2] > 180) & (hsv[:,:,1] > 20)
                combined_mask = (sat_mask | bright_mask) & (~floor_mask)

                # 1. Exclude Level Banner ('Tingkat:X' banner di tengah atas y: 260..350)
                lv_y1, lv_y2 = int((260 - 260) * sy), int((350 - 260) * sy)
                lv_x1, lv_x2 = int((240 - 10) * sx), int((480 - 10) * sx)
                combined_mask[lv_y1:lv_y2, lv_x1:lv_x2] = 0

                # 2. Exclude Badge Antri (kiri atas y: 250..360)
                aq_y1, aq_y2 = 0, int((360 - 260) * sy)
                aq_x1, aq_x2 = 0, int((200 - 10) * sx)
                combined_mask[aq_y1:aq_y2, aq_x1:aq_x2] = 0

                # 3. Exclude Antrean Penumpang (y: 330..470)
                pq_y1, pq_y2 = int((330 - 260) * sy), int((470 - 260) * sy)
                pq_x1, pq_x2 = int((230 - 10) * sx), int((400 - 10) * sx)
                combined_mask[pq_y1:pq_y2, pq_x1:pq_x2] = 0

                # 4. Exclude Slot Halte (y: 480..680)
                hb_y1, hb_y2 = int((480 - 260) * sy), int((680 - 260) * sy)
                hb_x1, hb_x2 = 0, int((710 - 10) * sx)
                combined_mask[hb_y1:hb_y2, hb_x1:hb_x2] = 0

                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                clean_mask = cv2.morphologyEx(combined_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
                cnts, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                candidates = []
                for c in cnts:
                    x, y, cw, ch = cv2.boundingRect(c)
                    area = cv2.contourArea(c)
                    aspect = cw / float(ch) if ch > 0 else 0
                    perimeter = cv2.arcLength(c, True)
                    circ = (4 * np.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0

                    is_valid_size = (20 * sx <= cw <= 220 * sx) and (16 * sy <= ch <= 220 * sy) and (250 * sx * sy <= area <= 30000 * sx * sy)
                    is_valid_shape = (0.50 <= aspect <= 2.80)

                    if is_valid_size and is_valid_shape:
                        cx = x1 + x + cw // 2
                        cy = y1 + y + ch // 2

                        if cx <= int(200 * sx) and cy <= int(365 * sy):
                            continue
                        if int(480 * sy) <= cy <= int(680 * sy):
                            continue
                        if cy >= int(1440 * sy):
                            continue

                        # Exclude bodi bus stasioner di area parkir
                        if cy >= int(700 * sy) and area >= 2000 * sx * sy and (cw >= int(70 * sx) or ch >= int(70 * sy)):
                            continue

                        if self.is_coord_recent(cx, cy):
                            continue

                        patch = crop[y:y+ch, x:x+cw]
                        if patch.size > 0 and np.std(patch) > 12:
                            is_money = (1.30 <= aspect <= 2.80)
                            candidates.append((cx, cy, area, aspect, circ, is_money))

                if candidates:
                    candidates.sort(key=lambda item: item[2], reverse=True)
                    best = candidates[0]
                    if best[5]:
                        obj_name = "Uang / Koin Melayang"
                    elif 0.75 <= best[3] <= 1.30 and best[4] < 0.72:
                        obj_name = "Kado Hadiah Melayang"
                    else:
                        obj_name = "Gelembung Balon Iklan"
                    return best[0], best[1], f"{obj_name} (Posisi ({best[0]}, {best[1]}), Area={int(best[2])})"

        return None

    def play_step(self):
        self.step_counter += 1

        # 1. Pastikan fokus game aktif
        if not self.handle_app_focus_and_ads():
            return

        # 2. Ambil screenshot
        img = self.get_screenshot()
        if img is None:
            time.sleep(0.15)
            return

        # 3. Lakukan OCR untuk deteksi saldo & teks dialog popup
        ocr_items = self.run_full_ocr(img)
        all_text_lower = " ".join([it["text"].lower() for it in ocr_items])
        sx, sy = self.scale_x, self.scale_y

        # 4. Deteksi tombol 'CONTINUE' / 'CONTINUI' / 'LANJUTKAN'
        continue_keywords = ["continue", "continui", "continu", "lanjutkan", "lanjut", "teruskan"]
        for it in ocr_items:
            t = it["text"].lower()
            if any(kw in t for kw in continue_keywords):
                print(f"{self.tag} [★] Menemukan tombol '{it['text']}' di ({it['cx']}, {it['cy']})! Mengeklik Continue...", flush=True)
                self.tap(it["cx"], it["cy"])
                time.sleep(1.0)
                return

        # 5. Deteksi tombol 'MAIN ULANG' / 'COBA LAGI' saat level gagal
        main_ulang_keywords = ["main ulang", "coba lagi", "ulang", "restart", "play again"]
        for it in ocr_items:
            t = it["text"].lower()
            if any(kw in t for kw in main_ulang_keywords) and it["cy"] > int(500 * sy):
                print(f"{self.tag} [★] Menemukan tombol '{it['text']}' di ({it['cx']}, {it['cy']})! Mengeklik untuk memulai ulang level...", flush=True)
                self.tap(it["cx"], it["cy"])
                time.sleep(1.0)
                return

        if "gagal" in all_text_lower and ("level" in all_text_lower or "kurang" in all_text_lower or "rp" in all_text_lower):
            mu_x, mu_y = int(360 * sx), int(1160 * sy)
            print(f"{self.tag} [★] Terdeteksi status 'Gagal' di layar! Mengeklik tombol Main Ulang di ({mu_x}, {mu_y})...", flush=True)
            self.tap(mu_x, mu_y)
            time.sleep(1.0)
            return

        # 6. Deteksi Teks Modal (Pengaturan, Login Sehari, Tonton Iklan Spin, Check-in) -> KLIK TOMBOL X
        if any(k in all_text_lower for k in ["pengaturan", "menetapkan", "feedback", "umpan balik"]):
            modal_item = None
            for it in ocr_items:
                if any(k in it["text"].lower() for k in ["pengaturan", "menetapkan", "feedback", "umpan balik"]):
                    modal_item = it
                    break
            t_y = modal_item["cy"] if modal_item else int(470 * sy)
            close_pts = [
                (int(636 * sx), t_y),
                (int(645 * sx), t_y),
                (int(636 * sx), int(t_y - 45 * sy)),
                (int(636 * sx), int(t_y + 35 * sy)),
                (int(640 * sx), int(470 * sy)),
                (int(635 * sx), int(520 * sy))
            ]
            print(f"{self.tag} [★] Menemukan dialog modal ('Feedback/Pengaturan')! Mengeklik burst tombol X di kanan...", flush=True)
            self.tap_burst(close_pts, delay=0.03)
            time.sleep(0.2)
            self.press_back()
            time.sleep(0.4)
            return

        dismiss_keywords = [
            ("login sehari", "Login Sehari"),
            ("tonton iklan untuk spin", "Tonton Iklan Spin"),
            ("tonton iklan", "Tonton Iklan Spin"),
            ("check-in", "Check-in Harian")
        ]
        for kw, label in dismiss_keywords:
            if kw in all_text_lower:
                matched_item = None
                for it in ocr_items:
                    if kw in it["text"].lower():
                        matched_item = it
                        break
                target_y = matched_item["cy"] if matched_item else int(604 * sy)
                target_x = int(645 * sx)
                print(f"{self.tag} [★] Menemukan dialog '{label}' di y={target_y}! Mengeklik tombol X di ({target_x}, {target_y})...", flush=True)
                self.tap(target_x, target_y)
                time.sleep(0.2)
                self.tap(int(670 * sx), int(220 * sy))
                time.sleep(0.3)
                return

        # 7. Periksa Saldo =Rp di Header (Target >= 150)
        if self.check_and_handle_top_rp(ocr_items):
            return

        # 8. Periksa Tombol Reward Modal Nyata Berbasis OCR ('Bebas Klik', 'Koleksi', 'Klaim', 'Menarik')
        popup_btn = detect_popup_reward_button_ocr(ocr_items, self.scale_y)
        if popup_btn:
            bx, by, desc = popup_btn
            print(f"{self.tag} [★] MENEMUKAN {desc} di ({bx}, {by})! Mengeklik...", flush=True)
            self.tap(bx, by)
            time.sleep(0.6)
            img_after = self.get_screenshot()
            if img_after is not None:
                cans_after = self.detect_shelf_cans(img_after)
                if not cans_after:
                    self.wait_ad_and_close_ad("Iklan Terbuka Setelah Klik Reward / Koleksi")
            return

        # 8b. Deteksi Bubble / Balon Hadiah Terbang (+25 / Uang / Bonus / Film)
        bubble = self.detect_floating_reward_bubble(ocr_items, img)
        if bubble:
            bx, by, desc = bubble
            print(f"{self.tag} [★] MENEMUKAN {desc} di ({bx}, {by})! Mengeklik bubble...", flush=True)
            self.tap(bx, by)
            self.record_tapped_coord(bx, by)
            time.sleep(0.7)
            img_after = self.get_screenshot()
            if img_after is not None:
                cans_after = self.detect_shelf_cans(img_after)
                if not cans_after:
                    self.wait_ad_and_close_ad("Iklan Terbuka Setelah Klik Bubble Terbang")
            return

        # 9. Deteksi Botol Juice di Rak
        front_cans = self.detect_shelf_cans(img)

        # 10. Jika tidak ada botol di rak (mungkin ada popup tutorial atau modal)
        if not front_cans:
            close_x = detect_dialog_close_x_button(img, self.scale_x, self.scale_y)
            if close_x:
                cx, cy, desc = close_x
                print(f"{self.tag} [★] MENEMUKAN {desc} di ({cx}, {cy})! Menutup modal...", flush=True)
                self.tap(cx, cy)
                time.sleep(0.4)
                return
            else:
                if "selamat datang" in all_text_lower or "klik minuman" in all_text_lower:
                    print(f"{self.tag} [+] Dismiss teks tutorial...", flush=True)
                    self.tap(int(360 * sx), int(500 * sy))
                    time.sleep(0.4)
                    return
                self.press_back()
                time.sleep(0.4)
                return

        # 11. MODE BEBAS TURBO: Klik Semua Botol Juice yang Tersedia di Rak
        if front_cans:
            tap_points = [(c["cx"], c["cy"]) for c in front_cans]
            cols_desc = ", ".join([f"Col {c['col']} @y={c['cy']}" for c in front_cans])
            print(f"{self.tag} [⚡⚡] TAP BOTOL JUICE ({len(tap_points)} Botol): {cols_desc}", flush=True)
            self.tap_burst(tap_points, delay=0.03)
        else:
            shelf_cols_x = [int(x * sx) for x in SHELF_COLUMNS_X]
            fallback_points = [(x, int(765 * sy)) for x in shelf_cols_x]
            print(f"{self.tag} [⚡] TAP SEMUA 8 KOLOM RAK...", flush=True)
            self.tap_burst(fallback_points, delay=0.03)

def run_device_worker(serial, parent_pid):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    print(f"[{serial}] [+] Worker proses aktif dan berjalan untuk {serial}!", flush=True)
    runner = JuicePackRunner(serial)
    runner.check_and_wake_device()
    runner.check_and_install_game_if_missing()
    try:
        while True:
            if os.getppid() != parent_pid or os.getppid() == 1:
                break
            runner.play_step()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        print(f"[{serial}] [!] Worker error: {e}", flush=True)

def main():
    print("==================================================================", flush=True)
    print("   BOT JUICE PACK FRENZY - MULTI-DEVICE PARALLEL ENGINE           ", flush=True)
    print("==================================================================", flush=True)
    active_processes = {}
    main_pid = os.getpid()
    print("[+] Memindai semua perangkat Android yang terhubung via ADB...", flush=True)
    print(f"[+] Target Game: Juice Pack Frenzy (com.apnabankshop.juice)", flush=True)
    print(f"[+] Aturan Aktif: Auto-Install, Main Ulang, Smart Reward OCR, Iklan {AD_WAIT_SECONDS}s, DANA (>= {MIN_WITHDRAWAL_RP}).\n", flush=True)
    print("[+] Tekan Ctrl+C untuk berhenti kapan saja.\n", flush=True)

    try:
        while True:
            current_devices = get_connected_devices()
            for serial in list(active_processes.keys()):
                if serial not in current_devices:
                    print(f"[-] Perangkat {serial} terputus. Menghentikan worker...", flush=True)
                    active_processes[serial].terminate()
                    active_processes[serial].join(timeout=1.0)
                    del active_processes[serial]

            for serial in current_devices:
                if serial not in active_processes or not active_processes[serial].is_alive():
                    if serial in active_processes:
                        try:
                            active_processes[serial].terminate()
                        except Exception:
                            pass

                    print(f"\n[+] Perangkat terdeteksi: {serial}", flush=True)
                    ensure_scrcpy_running(serial)
                    p = multiprocessing.Process(target=run_device_worker, args=(serial, main_pid), daemon=True)
                    p.start()
                    active_processes[serial] = p

            if not current_devices:
                print("[!] Tidak ada HP Android terhubung via ADB. Menunggu perangkat...", end="\r", flush=True)

            time.sleep(2.0)
    except KeyboardInterrupt:
        print("\n[+] Menghentikan semua bot worker...", flush=True)
        for p in active_processes.values():
            try:
                p.terminate()
                p.join(timeout=1.0)
            except Exception:
                pass
        print("[+] Semua bot selesai dihentikan.", flush=True)

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    main()
