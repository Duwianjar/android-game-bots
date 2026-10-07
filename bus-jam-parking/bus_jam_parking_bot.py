#!/usr/bin/env python3
"""
Bus Jam Parking Automation Bot (com.busjam.parking.master)
Multi-Device Parallel Engine - Precision Floor-Masked Bus Detection, Matching Queue Colors,
Auto Fail Recovery ('Main lagi'), Smart Reward OCR, Iklan 30s & DANA Withdrawal
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

import threading
import json
import html
import requests
from datetime import datetime
from pathlib import Path

PACKAGE_NAME = "com.busjam.parking.master"
TELEGRAM_BOT_TOKEN = "8849203378:AAEmh0zmO6GoC1x2eb-s5yUVAUDSqremF44"
TELEGRAM_CHAT_ID = "-5421593398"
TELEGRAM_REPORT_INTERVAL = int(os.environ.get("BUSJAM_TG_INTERVAL", "180"))
STATE_FILE_PATH = "/Users/macbookair/bus_jam_telegram_reporter_state.json"

def send_telegram_msg(text):
    """Kirim pesan Telegram (HTML parse mode)."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        requests.post(url, data=payload, timeout=10)
    except Exception:
        pass

def send_telegram_async(text):
    """Kirim pesan Telegram di background thread agar tidak memperlambat loop game."""
    try:
        t = threading.Thread(target=send_telegram_msg, args=(text,), daemon=True)
        t.start()
    except Exception:
        pass

LAUNCH_ACTIVITY = "com.busjam.parking.master/.LauncherAty"
OCR_HELPER_PATH = "/Users/macbookair/ocr_helper"
CLICK_REWARD_DURING_AD_WAIT = False  # Nonaktif: jangan klik Koleksi/Klaim/Unduh saat menunggu iklan
AD_WAIT_SECONDS = 10         # Menonton iklan selama 10 detik
MIN_WITHDRAWAL_RP = 20000      # Target saldo =Rp minimal 150 untuk penarikan

# Rentang Warna HSV Presisi untuk Bus & Penumpang (Floor-Masked & Anti-Keliru Orange/Red)
COLOR_RANGES = {
    'Red': [((0, 55, 55), (5, 255, 255)), ((170, 55, 55), (180, 255, 255))],
    'Orange': [((6, 55, 55), (16, 255, 255))],
    'Yellow': [((17, 45, 45), (34, 255, 255))],
    'Green': [((35, 45, 45), (84, 255, 255))],
    'Cyan': [((85, 60, 50), (104, 255, 255))],
    'Blue': [((105, 60, 50), (130, 255, 255))],
    'Pink': [((131, 55, 55), (169, 255, 255))]
}

def classify_hsv_color(h, s, v):
    if s < 45 or v < 50:
        return None
    if (h <= 5 or h >= 170):
        return 'Red'
    elif 6 <= h <= 16:
        return 'Orange'
    elif 17 <= h <= 34:
        return 'Yellow'
    elif 35 <= h <= 84:
        return 'Green'
    elif 85 <= h <= 104:
        return 'Cyan'
    elif 105 <= h <= 130:
        return 'Blue'
    elif 131 <= h <= 169:
        return 'Pink'
    return None

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
        print(f"[{serial}] [+] Membuka jendela tampilan layar scrcpy (Bus Jam Parking)...", flush=True)
        try:
            subprocess.Popen(
                ["scrcpy", "-s", serial, "--window-title", f"Bus Jam Parking - {serial}", "--max-fps=25", "--no-audio"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.2)
            print(f"[{serial}] [✔] Jendela scrcpy berhasil dibuka!", flush=True)
        except Exception as e:
            print(f"[{serial}] [!] Catatan scrcpy: {e}", flush=True)

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

class BusParkingDashRunner:
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
        self.recently_tapped_points = []
        self.latest_game_data = self.load_cached_state()
        if not self.latest_game_data:
            self.latest_game_data = {
                'saldo_rp': None,
                'saldo_poin': None,
                'level': None,
                'front_passenger': None,
                'parked_buses': [],
                'last_captured_time': None,
                'last_status': 'Starting',
                'device': self.serial
            }
        self.last_tg_report_time = time.time()
        self.tg_report_interval = TELEGRAM_REPORT_INTERVAL
        self.stop_event = threading.Event()
        self.start_telegram_reporter_thread()

    def load_cached_state(self):
        try:
            if os.path.exists(STATE_FILE_PATH):
                with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
        return {}

    def save_cached_state(self):
        try:
            with open(STATE_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.latest_game_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def send_startup_telegram(self):
        waktu_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
        msg = (
            "🚀 <b>BOT BUS JAM PARKING DIMULAI</b>\n"
            f"🕐 <b>Waktu:</b> {waktu_start}\n"
            f"📱 <b>Device:</b> <code>{self.serial}</code>\n"
            f"⚙️ <b>Target Saldo DANA:</b> <b>Rp{MIN_WITHDRAWAL_RP}</b>\n"
            f"⏱️ <i>Laporan berkala setiap {int(self.tg_report_interval // 60)} menit aktif (data layar bus terbaru).</i>"
        )
        send_telegram_async(msg)

    def start_telegram_reporter_thread(self):
        """Thread background independen yang menjamin laporan terkirim tepat waktu setiap 3 menit."""
        def reporter_loop():
            while not self.stop_event.is_set():
                interrupted = self.stop_event.wait(timeout=self.tg_report_interval)
                if interrupted:
                    break
                try:
                    self.send_periodic_tg_report()
                except Exception as e:
                    print(f"{self.tag} [!] Error kirim laporan berkala TG: {e}", flush=True)

        t = threading.Thread(target=reporter_loop, daemon=True, name=f"TGReporter_{self.serial}")
        t.start()

    def send_shutdown_telegram(self):
        self.stop_event.set()
        waktu_stop = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
        msg = (
            "🛑 <b>BOT BUS JAM PARKING DIHENTIKAN</b>\n"
            f"🕐 <b>Waktu:</b> {waktu_stop}\n"
            f"📱 <b>Device:</b> <code>{self.serial}</code>\n"
            "⚠️ <i>Worker bot telah berhenti.</i>"
        )
        send_telegram_async(msg)

    def tap_bubble_burst(self, bx, by):
        """Burst tap multi-titik menyebar cepat di sekitar koordinat bubble dengan leading motion coverage agar 100% kena meski bubble melayang cepat."""
        sx, sy = self.scale_x, self.scale_y
        pts = [
            (bx, by),
            (int(bx - 20 * sx), int(by + 20 * sy)),
            (int(bx - 35 * sx), int(by + 35 * sy)),
            (int(bx + 20 * sx), int(by - 20 * sy)),
            (int(bx + 35 * sx), int(by - 35 * sy)),
            (int(bx - 25 * sx), by),
            (int(bx + 25 * sx), by),
            (bx, int(by - 25 * sy)),
            (bx, int(by + 25 * sy)),
            (bx, by)
        ]
        self.tap_burst(pts, delay=0.01)

    def send_periodic_tg_report(self):
        """Mengirim laporan data terbaru dari halaman bus ke Telegram setiap 3 menit."""
        d = self.latest_game_data
        waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")

        saldo_rp = d.get('saldo_rp') or '-'
        saldo_poin = d.get('saldo_poin') or '-'
        level = d.get('level') or '-'
        front = d.get('front_passenger') or '-'
        buses = ", ".join(d.get('parked_buses') or []) or '-'
        last_capture = d.get('last_captured_time') or waktu_sekarang
        app_status = d.get('last_status') or 'Game aktif'

        msg = (
            "🚌 <b>BUS JAM PARKING - LAPORAN BERKALA</b>\n"
            f"🕐 <b>Waktu Lapor:</b> {html.escape(waktu_sekarang)}\n\n"
            f"💰 <b>Saldo =Rp:</b> <b>{html.escape(str(saldo_rp))}</b>\n"
            f"💎 <b>Poin/Rp Kanan:</b> <b>{html.escape(str(saldo_poin))}</b>\n"
            f"🎮 <b>Tingkat/Level:</b> <b>{html.escape(str(level))}</b>\n"
            f"👥 <b>Penumpang Depan:</b> <code>{html.escape(str(front))}</code>\n"
            f"🚏 <b>Bus Terdeteksi:</b> <code>{html.escape(str(buses))}</code>\n\n"
            f"📱 <b>Device:</b> <code>{html.escape(str(self.serial))}</code>\n"
            f"🧭 <b>Status:</b> <b>{html.escape(str(app_status))}</b>\n"
            f"⏱️ <i>Data diambil: {html.escape(str(last_capture))}</i>\n"
            f"<i>Laporan otomatis setiap {int(self.tg_report_interval // 60)} menit (data terbaru layar bus).</i>"
        )
        send_telegram_async(msg)
        print(f"{self.tag} [📱 TG] Laporan berkala terkirim ke Telegram: =Rp {saldo_rp} | Level {level} | Penumpang {front}", flush=True)

    def update_latest_game_data(self, ocr_items=None, front_color=None, analyzed_buses=None, app_status="Game aktif"):
        """Mengambil dan menyimpan data terbaru setiap kali bot berada di halaman bus gameplay."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
        updated = False

        if ocr_items:
            sx, sy = self.scale_x, self.scale_y
            for it in ocr_items:
                text = it.get("text", "")
                cx, cy = it.get("cx", 0), it.get("cy", 0)

                # Saldo Header y: 45..150
                if int(45 * sy) <= cy <= int(150 * sy):
                    t = text.replace("o", "0").replace("O", "0").replace("I", "1").replace("l", "1")
                    m = re.search(r"Rp\s*([0-9]+)", t, re.IGNORECASE)
                    if m:
                        val = m.group(1)
                        if cx <= int(330 * sx):
                            if val != self.latest_game_data.get('saldo_rp'):
                                self.latest_game_data['saldo_rp'] = val
                                updated = True
                        else:
                            if val != self.latest_game_data.get('saldo_poin'):
                                self.latest_game_data['saldo_poin'] = val
                                updated = True

                # Level / Tingkat
                if self.latest_game_data.get('level') is None or "tingkat" in text.lower() or "level" in text.lower():
                    m = re.search(r"(?:tingkat|level)\s*[: ]?\s*(\d+)", text, re.I)
                    if m:
                        lv = m.group(1)
                        if lv != self.latest_game_data.get('level'):
                            self.latest_game_data['level'] = lv
                            updated = True

        if front_color and front_color != self.latest_game_data.get('front_passenger'):
            self.latest_game_data['front_passenger'] = front_color
            updated = True

        if analyzed_buses is not None:
            bus_list = [f"{b.get('color','?')}@{b.get('cx','?')},{b.get('cy','?')}" for b in analyzed_buses[:6]]
            if bus_list and bus_list != self.latest_game_data.get('parked_buses'):
                self.latest_game_data['parked_buses'] = bus_list
                updated = True

        if app_status and app_status != self.latest_game_data.get('last_status'):
            self.latest_game_data['last_status'] = app_status
            updated = True

        if updated:
            self.latest_game_data['last_captured_time'] = now_str
            self.latest_game_data['device'] = self.serial
            self.save_cached_state()



    def is_coord_recent(self, cx, cy, threshold_dist=35):
        for bx, by in self.recently_tapped_points:
            if abs(cx - bx) <= threshold_dist * self.scale_x and abs(cy - by) <= threshold_dist * self.scale_y:
                return True
        return False

    def record_tapped_coord(self, cx, cy):
        self.recently_tapped_points.append((int(cx), int(cy)))
        if len(self.recently_tapped_points) > 12:
            self.recently_tapped_points.pop(0)

    def run_adb(self, cmd, timeout=5.0):
        try:
            res = subprocess.run(["adb", "-s", self.serial] + cmd, capture_output=True, text=True, timeout=timeout, check=False)
            return res.stdout.strip()
        except Exception:
            return ""

    def bring_game_to_foreground(self):
        """Membawa aplikasi Bus Jam Parking kembali ke layar depan secara aman."""
        self.run_adb(["shell", "am", "start", "-n", f"{PACKAGE_NAME}/.LauncherAty"])
        self.run_adb(["shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])

    def tap(self, x, y):
        subprocess.run(["adb", "-s", self.serial, "shell", f"input tap {int(x)} {int(y)}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def tap_burst(self, coords, delay=0.03):
        """Mengeklik banyak titik koordinat secara cepat/paralel."""
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
        """Mengecek apakah Bus Jam Parking terpasang di HP."""
        installed = self.run_adb(["shell", "pm", "list", "packages"])
        if PACKAGE_NAME in installed:
            return True
        return False

    def get_foreground_focus(self):
        try:
            res = subprocess.run(["adb", "-s", self.serial, "shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"], capture_output=True, text=True, timeout=2.0, check=False)
            return res.stdout.strip()
        except Exception:
            return ""

    def get_current_window(self):
        try:
            res = subprocess.run(["adb", "-s", self.serial, "shell", "dumpsys window | grep 'mCurrentFocus'"], capture_output=True, text=True, timeout=2.0, check=False)
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
        """Menutup iklan secara menyeluruh: BACK -> Dialog Konfirmasi Tutup ('Continue') -> Endcard X -> Kembali Game."""
        sx, sy = self.scale_x, self.scale_y
        self.press_back()
        time.sleep(0.4)

        img = self.get_screenshot()
        if img is not None:
            ocr_items = self.run_full_ocr(img)
            for it in ocr_items:
                t = it["text"].lower()
                if any(k in t for k in ["continue", "continui", "continu", "lanjutkan", "resume"]) and it["cy"] > int(200 * sy):
                    print(f"{self.tag} [+] Terdeteksi dialog peringatan iklan. Mengeklik 'Continue' di ({it['cx']}, {it['cy']})...", flush=True)
                    self.tap(it["cx"], it["cy"])
                    time.sleep(1.2)
                    break

        close_points = [
            (int(665 * sx), int(70 * sy)),
            (int(665 * sx), int(115 * sy)),
            (int(665 * sx), int(250 * sy)),
            (int(635 * sx), int(75 * sy)),
            (int(55 * sx), int(70 * sy)),
            (int(55 * sx), int(115 * sy)),
            (int(55 * sx), int(250 * sy))
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
        """Menunggu iklan dan kirim notifikasi ke Telegram"""
        # Kirim notifikasi Telegram
        now_time = time.strftime("%Y-%m-%d %H:%M:%S WIB")
        ad_msg = (
            f"📺 <b>MEMBUKA IKLAN</b>\n"
            f"🕐 <code>{now_time}</code>\n\n"
            f"📱 <b>Game:</b> {PACKAGE_NAME}\n"
            f"🎯 <b>Alasan:</b> {html.escape(reason)}\n"
            f"⏳ <i>Bot sedang menonton iklan...</i>"
        )
        send_telegram_async(ad_msg)
        
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
        cur_win = self.get_current_window()

        # 1. Notification Shade / Status Bar / Desktop Launcher menutup game -> Tutup status bar & kembalikan game
        if any(s in cur_win.lower() for s in ["statusbar", "notificationshade", "quickstep", "xoslauncher", "launcher"]):
            print(f"{self.tag} [!] Layar sistem / Notification Shade / Launcher terdeteksi aktif. Mengembalikan game ke layar depan...", flush=True)
            self.press_back()
            time.sleep(0.3)
            self.bring_game_to_foreground()
            time.sleep(0.8)
            return False

        # 1b. Google Play Store / Browser terbuka oleh iklan -> Tutup paksa & kembali ke game
        if any(pkg in focus.lower() or pkg in cur_win.lower() for pkg in ["com.android.vending", "com.android.chrome", "org.chromium.chrome", "com.google.android.apps.chrome", "browser"]):
            print(f"{self.tag} [!] Eksternal Browser/Play Store terbuka oleh iklan! Menutup paksa & kembali ke game...", flush=True)
            self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
            self.run_adb(["shell", "am", "force-stop", "com.android.chrome"])
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

        self.ad_wait_done = False
        self.aggressive_ad_dismiss_count = 0

        # 3. Jika aplikasi Bus Jam Parking sama sekali tidak di layar
        if PACKAGE_NAME not in focus:
            print(f"{self.tag} [!] Bus Jam Parking tidak di layar. Membuka aplikasi...", flush=True)
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

        tmp_path = f"/tmp/busjam_ocr_{self.serial}.png"
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
            y1, y2 = int(540 * self.scale_y), int(640 * self.scale_y)
            x1, x2 = int(100 * self.scale_x), int(340 * self.scale_x)
            dana_roi = img[y1:y2, x1:x2]
            if dana_roi.size > 0:
                hsv = cv2.cvtColor(dana_roi, cv2.COLOR_BGR2HSV)
                blue_pixels = np.sum((hsv[:, :, 0] > 95) & (hsv[:, :, 0] < 135) & (hsv[:, :, 1] > 70) & (hsv[:, :, 2] > 70))
                if blue_pixels > 3000:
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

    def is_bus_game_page_text(self, text):
        """True jika OCR sudah menunjukkan halaman utama permainan bus."""
        t = (text or "").lower()
        return (
            any(k in t for k in ["tingkat", "level"])
            and any(k in t for k in ["antri", "buka kunci", "urutkan", "bus"])
        )

    def is_withdrawal_rp_zero_text(self, text):
        """Deteksi saldo penarikan Rp0 di popup/halaman penarikan."""
        raw = (text or "").lower()
        norm = (
            raw.replace("o", "0")
               .replace("O", "0")
               .replace("l", "1")
               .replace("I", "1")
        )
        compact = re.sub(r"\s+", "", norm)
        has_zero_rp = any(k in compact for k in ["rp0", "=rp0", "~rp0", "≈rp0", "diterima:rp0", "dana:rp0", "danarp0"])
        has_withdraw_context = any(k in norm for k in [
            "pilih metode", "saldo saya", "penukaran", "menarik", "tarik",
            "pastikan", "informasi", "periksa", "diterima", "kurang rp",
            "dana", "ovo", "nomor rekening", "nomor akun"
        ])
        return has_zero_rp and has_withdraw_context

    def back_until_bus_game_page(self, reason=""):
        """Tekan BACK berulang sampai popup penarikan tertutup dan halaman bus aktif."""
        reason_txt = f" ({reason})" if reason else ""
        print(f"{self.tag} [↩] Menutup popup/halaman penarikan{reason_txt}. BACK sampai halaman bus...", flush=True)
        for _ in range(7):
            img = self.get_screenshot()
            if img is not None:
                ocr_items = self.run_full_ocr(img)
                text = " ".join([it["text"].lower() for it in ocr_items])
                if self.is_bus_game_page_text(text):
                    print(f"{self.tag} [✔] Sudah kembali ke halaman bus.", flush=True)
                    return True
            self.press_back()
            time.sleep(0.55)

        self.bring_game_to_foreground()
        time.sleep(0.8)
        img = self.get_screenshot()
        if img is not None:
            ocr_items = self.run_full_ocr(img)
            text = " ".join([it["text"].lower() for it in ocr_items])
            if self.is_bus_game_page_text(text):
                print(f"{self.tag} [✔] Halaman bus aktif setelah bring-to-front.", flush=True)
                return True
        print(f"{self.tag} [!] Belum bisa memastikan halaman bus, tapi popup penarikan sudah dicoba ditutup.", flush=True)
        return False

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

            # 0. Jika saldo sudah Rp0 / penarikan selesai, tutup popup sampai halaman bus.
            if self.is_withdrawal_rp_zero_text(all_text_lower):
                print(f"{self.tag} [✔] Saldo penarikan sudah Rp0. Berarti sudah ditarik / tidak ada saldo. Keluar dari popup...", flush=True)
                self.back_until_bus_game_page("Rp0")
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
                all_text_lower = " ".join([it["text"].lower() for it in ocr_items])

                if self.is_withdrawal_rp_zero_text(all_text_lower):
                    print(f"{self.tag} [✔] Setelah memilih DANA, saldo terbaca Rp0. Keluar dari popup...", flush=True)
                    self.back_until_bus_game_page("DANA Rp0")
                    self.withdrawn_pending_ad = True
                    return

                menarik_btn = None
                for it in ocr_items:
                    if "menarik" in it["text"].lower() and int(750 * sy) < it["cy"] < int(1200 * sy):
                        menarik_btn = it
                        break
                m_cx = menarik_btn["cx"] if menarik_btn else int(360 * sx)
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
            self.update_latest_game_data(ocr_items=ocr_items)
            right_str = f" | Rp Kanan: {right_rp}" if right_rp is not None else ""
            if left_rp >= MIN_WITHDRAWAL_RP:
                send_telegram_async(
                    f"🎉 <b>PENARIKAN SALDO DANA DILAKUKAN!</b>\n"
                    f"📱 Device: <code>{self.serial}</code>\n"
                    f"💰 Saldo =Rp: <b>Rp{left_rp}</b>{right_str}\n"
                    f"🕐 Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}"
                )
                print(f"\n{self.tag} [★] MENEMUKAN Saldo =Rp{left_rp} >= {MIN_WITHDRAWAL_RP} (Target Tercapai!{right_str})", flush=True)
                print(f"{self.tag}     -> Mengeklik tombol =Rp KIRI di ({click_coords[0]}, {click_coords[1]})...", flush=True)
                self.tap(click_coords[0], click_coords[1])
                time.sleep(0.6)
                self.handle_withdrawal_modal_flow()
                return True
            elif self.step_counter % 5 == 1:
                print(f"{self.tag} [.] Status Saldo Header: =Rp{left_rp} / {MIN_WITHDRAWAL_RP}{right_str}", flush=True)

        return False

    def detect_floating_reward_bubble(self, ocr_items, img=None):
        """Mendeteksi Kado Terbang, Uang/Koin, Gelembung Balon Iklan, dan Floating Reward bergerak di layar bus secara presisi tanpa false positive."""
        sx, sy = self.scale_x, self.scale_y

        # 1. Deteksi Berbasis Teks / Simbol OCR (Cakupan aman di luar UI tetap)
        reward_kw = [
            "kado", "gift", "box", "hadiah", "parcel", "bonus", "spin", "film", "tonton",
            "buble", "balon", "bubble", "balloon", "uang", "koin", "coin", "cash", "gold",
            "free", "gratis", "klaim", "claim", "reward", "dapatkan", "ambil", "ad", "video", "play", "kupon",
            "x2", "2x"
        ]
        if ocr_items:
            for it in ocr_items:
                cy, cx = it["cy"], it["cx"]
                # Abaikan header atas (y < 180)
                if cy < int(180 * sy):
                    continue
                # Abaikan level banner statis tengah atas (cy: 230..390, cx: 200..520)
                if int(230 * sy) <= cy <= int(390 * sy) and int(200 * sx) <= cx <= int(520 * sx):
                    continue
                # Abaikan badge antri kiri atas (cx < 200, cy: 230..400)
                if cx <= int(200 * sx) and int(230 * sy) <= cy <= int(400 * sy):
                    continue
                # Abaikan area slot halte bus (cy: 450..690)
                if int(450 * sy) <= cy <= int(690 * sy):
                    continue
                # Abaikan booster tombol kanan HUD (cx: 480..640, cy: 850..1050)
                if int(480 * sx) <= cx <= int(640 * sx) and int(850 * sy) <= cy <= int(1050 * sy):
                    continue
                # Abaikan kontrol tombol bawah (cy >= 1450)
                if cy >= int(1450 * sy):
                    continue

                t = it["text"].lower().strip()
                if any(ig in t for ig in ["tingkat", "antri", "buka kunci", "level", "refresh", "urutkan", "menarik", "kurang", "saldo"]):
                    continue

                import re
                if re.search(r'(\+\s*\d+|\d+\s*koin|\d+\s*rp|rp\s*\d+|\d+\s*%|[xX]\s*\d+|\d+\s*[xX]|\+\s*[0-9]+k)', t) or any(kw in t for kw in reward_kw):
                    return cx, cy, f"Reward Teks/Icon '{it['text']}'"

        # 2. Deteksi Visual Objek Bulat Melayang (Kado/Balon/Gelembung)
        if img is not None:
            y1, y2 = int(180 * sy), int(1450 * sy)
            x1, x2 = int(10 * sx), int(710 * sx)
            crop = img[y1:y2, x1:x2]
            if crop.size > 0:
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                floor_mask = (hsv[:,:,0] >= 95) & (hsv[:,:,0] <= 125) & (hsv[:,:,1] <= 90) & (hsv[:,:,2] >= 180)
                sat_mask = (hsv[:,:,1] > 40) & (hsv[:,:,2] > 60)
                bright_mask = (hsv[:,:,2] > 190) & (hsv[:,:,1] > 25)
                combined_mask = (sat_mask | bright_mask) & (~floor_mask)

                # Exclude Level Banner
                lv_y1, lv_y2 = int((230 - 180) * sy), int((390 - 180) * sy)
                lv_x1, lv_x2 = int((200 - 10) * sx), int((520 - 10) * sx)
                combined_mask[lv_y1:lv_y2, lv_x1:lv_x2] = 0

                # Exclude Badge Antri
                aq_y1, aq_y2 = int((230 - 180) * sy), int((400 - 180) * sy)
                aq_x1, aq_x2 = 0, int((200 - 10) * sx)
                combined_mask[aq_y1:aq_y2, aq_x1:aq_x2] = 0

                # Exclude Halte bays
                hb_y1, hb_y2 = int((450 - 180) * sy), int((690 - 180) * sy)
                combined_mask[hb_y1:hb_y2, :] = 0

                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                clean_mask = cv2.morphologyEx(combined_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
                cnts, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                candidates = []
                for c in cnts:
                    x, y, cw, ch = cv2.boundingRect(c)
                    area = cv2.contourArea(c)
                    perimeter = cv2.arcLength(c, True)
                    circ = (4 * np.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0
                    aspect = cw / float(ch) if ch > 0 else 0

                    # Kriteria ketat: bentuk bundar/oval kompak, ukuran gelembung 35-110px, sirkularitas tinggi
                    if (35 * sx <= cw <= 110 * sx) and (35 * sy <= ch <= 110 * sy) and (800 * sx * sy <= area <= 10000 * sx * sy):
                        if (0.80 <= aspect <= 1.25) and (circ >= 0.78):
                            cx = x1 + x + cw // 2
                            cy = y1 + y + ch // 2

                            # Abaikan booster HUD kanan bawah
                            if int(480 * sx) <= cx <= int(640 * sx) and int(850 * sy) <= cy <= int(1050 * sy):
                                continue

                            patch = crop[y:y+ch, x:x+cw]
                            if patch.size > 0 and np.std(patch) > 22:
                                candidates.append((cx, cy, area, circ))

                if candidates:
                    candidates.sort(key=lambda item: item[3], reverse=True)
                    best = candidates[0]
                    return best[0], best[1], f"Gelembung Visual ({best[0]}, {best[1]})"

        return None

    def detect_front_passenger_color(self, img):
        """Mendeteksi warna rombongan penumpang di bagian depan antrean secara presisi (fokus ke kepala antrean y: 365..420)."""
        sx, sy = self.scale_x, self.scale_y
        # Fokus ke rombongan paling depan (y: 365..420) yang siap naik ke halte
        patch = img[int(365 * sy):int(420 * sy), int(260 * sx):int(345 * sx)]
        if patch.size == 0:
            return None

        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        sat_mask = (hsv[:, :, 1] > 45) & (hsv[:, :, 2] > 55)
        h_vals = hsv[:, :, 0][sat_mask]
        s_vals = hsv[:, :, 1][sat_mask]
        v_vals = hsv[:, :, 2][sat_mask]

        if len(h_vals) < 30:
            return None

        color_counts = {}
        for h, s, v in zip(h_vals, s_vals, v_vals):
            col = classify_hsv_color(h, s, v)
            if col:
                color_counts[col] = color_counts.get(col, 0) + 1

        if not color_counts:
            return None

        best_color = max(color_counts, key=color_counts.get)
        if color_counts[best_color] > 80:
            return best_color
        return None

    def analyze_buses_with_lanes(self, buses):
        """
        Mengelompokkan bus ke dalam jalur/kolom vertikal.
        Bus teratas di setiap jalur adalah bus yang BEBAS (unblocked) untuk melaju keluar.
        Bus di bawahnya dianggap TERHALANG (blocked) oleh bus di atasnya.
        """
        if not buses:
            return []

        sx = self.scale_x
        col_tolerance = int(35 * sx)

        columns = []
        for b in buses:
            assigned = False
            for col in columns:
                avg_cx = sum(item['cx'] for item in col) / len(col)
                if abs(b['cx'] - avg_cx) <= col_tolerance:
                    col.append(b)
                    assigned = True
                    break
            if not assigned:
                columns.append([b])

        analyzed_buses = []
        for col in columns:
            col.sort(key=lambda item: item['cy'])
            top_bus = col[0]
            for i, b in enumerate(col):
                b_copy = dict(b)
                if i == 0:
                    b_copy['unblocked'] = True
                    b_copy['blocker'] = None
                else:
                    b_copy['unblocked'] = False
                    b_copy['blocker'] = top_bus
                analyzed_buses.append(b_copy)

        return analyzed_buses

    def detect_open_buses(self, img):
        """Mendeteksi bus individual di area parkir (y: 700..1300) dengan memfilter latar belakang lantai."""
        sx, sy = self.scale_x, self.scale_y
        grid = img[int(700 * sy):int(1300 * sy), :]
        if grid.size == 0:
            return []

        hsv = cv2.cvtColor(grid, cv2.COLOR_BGR2HSV)
        
        # Mask lantai parkir (H: 102..110, S <= 85, V >= 200)
        floor_mask = (hsv[:,:,0] >= 102) & (hsv[:,:,0] <= 110) & (hsv[:,:,1] <= 85) & (hsv[:,:,2] >= 200)
        buses = []

        for color_name, ranges in COLOR_RANGES.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lower, upper in ranges:
                m = cv2.inRange(hsv, np.array(lower), np.array(upper))
                m[floor_mask] = 0
                mask |= m

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            cnts, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                x, y, w, h = cv2.boundingRect(c)
                area = cv2.contourArea(c)
                # Filter ukuran bus individual
                if (400 <= area <= 20000) and (25 <= w <= int(220 * sx)) and (25 <= h <= int(220 * sy)):
                    cx = x + w // 2
                    cy = int(700 * sy) + y + h // 2
                    buses.append({
                        'cx': cx,
                        'cy': cy,
                        'w': w,
                        'h': h,
                        'color': color_name,
                        'area': area
                    })

        # Urutkan bus dari baris teratas (paling tidak terhalang)
        buses.sort(key=lambda b: (b['cy'], b['cx']))
        return buses

    def check_and_unlock_halte_slot(self, ocr_items):
        """Mendeteksi dan mengeklik tombol 'Buka Kunci' pada slot halte bus di bawah antrean penumpang."""
        sx, sy = self.scale_x, self.scale_y
        unlock_slots = []
        for it in ocr_items:
            cy, cx = it["cy"], it["cx"]
            # Di area halte sebelah kanan: y: 480..680, x: 360..705
            if int(480 * sy) <= cy <= int(680 * sy) and int(360 * sx) <= cx <= int(705 * sx):
                t = it["text"].lower()
                if any(k in t for k in ["buka kunci", "buka", "kunci", "unlock"]):
                    unlock_slots.append(it)

        if unlock_slots:
            # Pilih slot paling kiri yang masih terkunci
            unlock_slots.sort(key=lambda s: s["cx"])
            target_slot = unlock_slots[0]
            sx_val, sy_val = target_slot["cx"], target_slot["cy"]
            print(f"{self.tag} [★] MENEMUKAN Slot Halte Terkunci '{target_slot['text']}' di ({sx_val}, {sy_val})! Mengeklik untuk membuka slot baru...", flush=True)
            self.tap(sx_val, sy_val)
            time.sleep(0.8)
            img_after = self.get_screenshot()
            if img_after is not None:
                ocr_after = self.run_full_ocr(img_after)
                if not any("tingkat" in it["text"].lower() for it in ocr_after):
                    self.wait_ad_and_close_ad("Iklan Buka Kunci Slot Halte")
            return True
        return False

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
        self.update_latest_game_data(ocr_items=ocr_items, app_status="Game aktif")
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

        # 5. Deteksi tombol 'MAIN LAGI' / 'MAIN ULANG' saat level gagal ("Habis Ruang")
        main_ulang_keywords = ["main lagi", "main ulang", "coba lagi", "ulang", "restart", "play again"]
        for it in ocr_items:
            t = it["text"].lower()
            if any(kw in t for kw in main_ulang_keywords) and it["cy"] > int(500 * sy):
                print(f"{self.tag} [★] Menemukan tombol '{it['text']}' di ({it['cx']}, {it['cy']})! Mengeklik Main Lagi...", flush=True)
                self.tap(it["cx"], it["cy"])
                time.sleep(1.2)
                return

        if "anda gagal" in all_text_lower or "habis ruang" in all_text_lower:
            ml_x, ml_y = int(360 * sx), int(1250 * sy)
            print(f"{self.tag} [★] Terdeteksi status 'Habis Ruang' / Gagal! Mengeklik Main Lagi di ({ml_x}, {ml_y})...", flush=True)
            self.tap(ml_x, ml_y)
            time.sleep(1.2)
            return

        # 6. Deteksi Dialog Modal (Feedback, Pengaturan / Menetapkan, Check-in, dll) -> KLIK TOMBOL X DI KANAN TEKS
        modal_dismiss_item = None
        for it in ocr_items:
            t = it["text"].lower()
            if any(k in t for k in ["feedback", "umpan balik", "not playing", "misleading", "menetapkan", "pengaturan", "settings"]):
                modal_dismiss_item = it
                break

        if modal_dismiss_item is not None:
            t_y = modal_dismiss_item["cy"]
            close_pts = [
                (int(620 * sx), t_y),
                (int(620 * sx), int(t_y - 6 * sy)),
                (int(636 * sx), t_y),
                (int(645 * sx), t_y),
                (int(620 * sx), int(580 * sy)),
                (int(636 * sx), int(t_y - 45 * sy)),
                (int(640 * sx), int(470 * sy)),
                (int(635 * sx), int(520 * sy))
            ]
            print(f"{self.tag} [★] Menemukan dialog '{modal_dismiss_item['text']}'! Mengeklik burst tombol X di kanan ({close_pts[0][0]}, {close_pts[0][1]})...", flush=True)
            self.tap_burst(close_pts, delay=0.03)
            time.sleep(0.2)
            self.press_back()
            time.sleep(0.4)
            return
        elif "check-in" in all_text_lower or "login sehari" in all_text_lower:
            px, py = int(640 * sx), int(470 * sy)
            print(f"{self.tag} [★] Menemukan dialog modal! Mengeklik tombol X di ({px}, {py})...", flush=True)
            self.tap(px, py)
            time.sleep(0.4)
            return

        # 7. Periksa Saldo =Rp di Header (Target >= 150)
        if self.check_and_handle_top_rp(ocr_items):
            return

        # 8. Periksa Tombol Reward Modal Nyata Berbasis OCR ('Bebas Klik', 'Koleksi', 'Klaim', 'Menarik')
        # DISABLED: Skip Koleksi untuk hindari loop iklan, fokus main game
        popup_btn = None  # detect_popup_reward_button_ocr(ocr_items, self.scale_y)
        if False and popup_btn:
            bx, by, desc = popup_btn
            # Cooldown untuk Koleksi (jangan spam iklan)
            if "koleksi" in desc.lower():
                last_koleksi = getattr(self, 'last_koleksi_time', 0)
                cooldown = 30  # detik
                if time.time() - last_koleksi < cooldown:
                    remaining = int(cooldown - (time.time() - last_koleksi))
                    print(f"{self.tag} [⏸] Skip Koleksi (cooldown {remaining}s lagi, fokus main game dulu)", flush=True)
                    return
                self.last_koleksi_time = time.time()
            
            print(f"{self.tag} [★] MENEMUKAN {desc} di ({bx}, {by})! Mengeklik...", flush=True)
            self.tap(bx, by)
            time.sleep(0.6)
            img_after = self.get_screenshot()
            if img_after is not None:
                ocr_after = self.run_full_ocr(img_after)
                if not any("tingkat" in it["text"].lower() for it in ocr_after):
                    self.wait_ad_and_close_ad("Iklan Terbuka Setelah Klik Reward / Koleksi")
            return

        # 8b. Deteksi Tombol 'Buka Kunci' Slot Halte Bus
        # 8c. Deteksi Kado Hadiah / Bubble / Balon Terbang di Layar
        # DISABLED: Skip bubble untuk hindari loop iklan, fokus main game ONLY
        bubble = None  # self.detect_floating_reward_bubble(ocr_items, img)
        if False and bubble:
            bx, by, desc = bubble
            print(f"{self.tag} [★] MENEMUKAN {desc} di ({bx}, {by})! Mengeklik burst bubble...", flush=True)
            self.tap_bubble_burst(bx, by)
            time.sleep(0.6)
            img_after = self.get_screenshot()
            if img_after is not None:
                ocr_after = self.run_full_ocr(img_after)
                if not any("tingkat" in it["text"].lower() for it in ocr_after):
                    self.wait_ad_and_close_ad("Iklan Terbuka Setelah Klik Bubble Terbang")
            return

        # 9. DETEKSI WARNA PENUMPANG TERDEPAN & ROUND-ROBIN BUS SELECTOR
        front_color = self.detect_front_passenger_color(img)
        all_buses = self.detect_open_buses(img)
        analyzed_buses = self.analyze_buses_with_lanes(all_buses)
        self.update_latest_game_data(ocr_items=ocr_items, front_color=front_color, analyzed_buses=analyzed_buses, app_status="Game aktif")

        target_bus_to_tap = None
        action_reason = ""

        # 1. Prioritas Utama: Coba SEMUA Bus yang Warnanya Cocok dengan Penumpang Terdepan Terlebih Dahulu!
        if front_color:
            # 1a. Cari bus warna cocok yang bebas (unblocked)
            unblocked_matches = [
                b for b in analyzed_buses
                if b['color'] == front_color and b['unblocked'] and not self.is_coord_recent(b['cx'], b['cy'])
            ]
            if unblocked_matches:
                unblocked_matches.sort(key=lambda b: b['cy'])
                target_bus_to_tap = unblocked_matches[0]
                action_reason = f"KLIK BUS COCOK BEBAS [{target_bus_to_tap['color']}] di ({target_bus_to_tap['cx']}, {target_bus_to_tap['cy']})"
            else:
                # 1b. Coba SEMUA bus warna cocok lainnya di seluruh posisi papan sampai habis!
                all_same_color_candidates = [
                    b for b in analyzed_buses
                    if b['color'] == front_color and not self.is_coord_recent(b['cx'], b['cy'])
                ]
                if all_same_color_candidates:
                    all_same_color_candidates.sort(key=lambda b: b['cy'])
                    target_bus_to_tap = all_same_color_candidates[0]
                    action_reason = f"Mencoba Bus Cocok [{target_bus_to_tap['color']}] Posisi Lain di ({target_bus_to_tap['cx']}, {target_bus_to_tap['cy']})"
                else:
                    # 1c. Jika SEMUA bus warna cocok sudah dicoba & tidak bisa bergerak, cari bus penghalang di depannya (blocker)
                    blocked_matches = [
                        b for b in analyzed_buses
                        if b['color'] == front_color and b.get('blocker')
                    ]
                    for bm in blocked_matches:
                        blk = bm['blocker']
                        if not self.is_coord_recent(blk['cx'], blk['cy']):
                            target_bus_to_tap = blk
                            action_reason = f"Semua Bus [{front_color}] Terhalang -> KLIK BUS PENGHALANG [{blk['color']}] di ({blk['cx']}, {blk['cy']}) agar jalur terbuka!"
                            break

        # 2. Prioritas Kedua (Hanya jika SEMUA bus warna cocok & penghalangnya sudah dicoba): KLIK BERGANTIAN BUS TERBUKA LAINNYA
        if not target_bus_to_tap and analyzed_buses:
            unblocked_any = [
                b for b in analyzed_buses
                if b['unblocked'] and not self.is_coord_recent(b['cx'], b['cy'])
            ]
            if unblocked_any:
                unblocked_any.sort(key=lambda b: b['cy'])
                target_bus_to_tap = unblocked_any[0]
                action_reason = f"KLIK BEBAS BUS TERBUKA LAINNYA [{target_bus_to_tap['color']}] di ({target_bus_to_tap['cx']}, {target_bus_to_tap['cy']})"
            else:
                # Jika semua bus terbuka sudah masuk riwayat, coba bus mana saja yang belum baru ditap
                other_candidates = [b for b in analyzed_buses if not self.is_coord_recent(b['cx'], b['cy'])]
                if other_candidates:
                    other_candidates.sort(key=lambda b: b['cy'])
                    target_bus_to_tap = other_candidates[0]
                    action_reason = f"Mencoba Bus Jalur Lain [{target_bus_to_tap['color']}] di ({target_bus_to_tap['cx']}, {target_bus_to_tap['cy']})"
                else:
                    # Geser riwayat tertua dan coba bus teratas berikutnya
                    if self.recently_tapped_points:
                        self.recently_tapped_points.pop(0)
                    analyzed_buses.sort(key=lambda b: b['cy'])
                    target_bus_to_tap = analyzed_buses[0]
                    action_reason = f"Rotasi Riwayat -> Tap Bus [{target_bus_to_tap['color']}] di ({target_bus_to_tap['cx']}, {target_bus_to_tap['cy']})"

        # Eksekusi Tap & Rekam Riwayat Koordinat
        if target_bus_to_tap:
            tcx, tcy = target_bus_to_tap['cx'], target_bus_to_tap['cy']
            print(f"{self.tag} [🚌] Penumpang Depan: [{front_color or '?'}] -> {action_reason}", flush=True)
            self.tap(tcx, tcy)
            self.record_tapped_coord(tcx, tcy)
            time.sleep(0.45)

            # Ambil screenshot setelah tap untuk cek apakah bus benar-benar bergerak
            img_after = self.get_screenshot()
            if img_after is not None and img is not None:
                roi_before = img[int(450 * sy):int(1300 * sy), :]
                roi_after = img_after[int(450 * sy):int(1300 * sy), :]
                diff = cv2.absdiff(roi_before, roi_after)
                diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                changed_pixels = np.sum(diff_gray > 25)

                if changed_pixels < 800:
                    print(f"{self.tag} [!] Bus di ({tcx}, {tcy}) terhalang. Berganti ke posisi bus lain di langkah berikutnya...", flush=True)
                else:
                    print(f"{self.tag} [✔] Bus bergerak melaju ke halte!", flush=True)
        else:
            # Jika tidak ada bus sama sekali terdeteksi di area parkir
            if not all_buses:
                close_btn = detect_dialog_close_x_button(img, sx, sy)
                if close_btn:
                    cx_val, cy_val, desc = close_btn
                    print(f"{self.tag} [★] Menemukan {desc} di ({cx_val}, {cy_val})! Menutup popup...", flush=True)
                    self.tap(cx_val, cy_val)
                    time.sleep(0.5)
                else:
                    self.press_back()
                    time.sleep(0.4)
            else:
                # Jika ada bus tapi belum terpilih di atas, pilih bus teratas yang ada
                top_b = sorted(all_buses, key=lambda item: item['cy'])[0]
                print(f"{self.tag} [🚌] Klik Bus Terbuka Teratas [{top_b['color']}] di ({top_b['cx']}, {top_b['cy']})...", flush=True)
                self.tap(top_b['cx'], top_b['cy'])
                self.record_tapped_coord(top_b['cx'], top_b['cy'])
                time.sleep(0.4)


def run_device_worker(serial, parent_pid):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    print(f"[{serial}] [+] Worker proses aktif dan berjalan untuk {serial}!", flush=True)
    runner = BusParkingDashRunner(serial)
    runner.send_startup_telegram()
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
    finally:
        runner.send_shutdown_telegram()

def main():
    print("==================================================================", flush=True)
    print("   BOT BUS PARKING DASH - MULTI-DEVICE PARALLEL ENGINE            ", flush=True)
    print("==================================================================", flush=True)
    active_processes = {}
    main_pid = os.getpid()
    print("[+] Memindai semua perangkat Android yang terhubung via ADB...", flush=True)
    print(f"[+] Target Game: Bus Jam Parking (com.busjam.parking.master)", flush=True)
    print(f"[+] Aturan Aktif: Floor-Masked Bus Match, Main Lagi, Iklan {AD_WAIT_SECONDS}s, DANA (>= {MIN_WITHDRAWAL_RP}).\n", flush=True)
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
