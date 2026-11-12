#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bus Jam Escape Automation Bot (com.busjam.escape.frenzy)
Multi-Device Parallel Engine - Floor-Masked Bus Detection on Green Grass,
Matching Front Passenger Queue Colors, Halte Slot Management,
Reward OCR, Smart Ad Handling (AppLovin, InMobi, Vast, Playable), and Telegram Reporting.
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

PACKAGE_NAME = "com.busjam.escape.frenzy"
LAUNCH_ACTIVITY = "com.busjam.escape.frenzy/.LauncherAty"
OCR_HELPER_PATH = "/Users/macbookair/ocr_helper"
STATE_FILE_PATH = "/Users/macbookair/bus_jam_escape_telegram_state.json"
TELEGRAM_BOT_TOKEN = "8849203378:AAEmh0zmO6GoC1x2eb-s5yUVAUDSqremF44"
TELEGRAM_CHAT_ID = "-5421593398"
TELEGRAM_REPORT_INTERVAL = int(os.environ.get("BUSJAM_TG_INTERVAL", "180"))
AD_WAIT_SECONDS = int(os.environ.get("BUSJAM_AD_WAIT", "30"))
FAILED_TAP_RESET_THRESHOLD = 8
AD_KEYWORDS = [
    "mbrewardvideoactivity", "applovinfullscreenactivity", "vastrewardedactivity",
    "inmobiadactivity", "inmobi", "adactivity", "companionadactivity", "bigo",
    "bytedance", "pangle", "unity3d", "fullscreenwebviewdisplay", "adplayer",
    "applovin", "adcolony", "kwad", "mbridge", "vungle", "ironsource",
    "mintegral", "openadsdk", "googleads", "admob", "rewardvideo", "rewarded",
    "interstitial", "adunit", "mraid", "pubnative", "fyber", "inneractive",
    "moloco"
]

COLOR_RANGES = {
    "Red": [([0, 95, 90], [10, 255, 255]), ([170, 95, 90], [180, 255, 255])],
    "Orange": [([11, 95, 90], [25, 255, 255])],
    "Yellow": [([26, 80, 90], [35, 255, 255])],
    "Green": [([36, 75, 75], [85, 255, 255])],
    "Cyan": [([86, 75, 75], [104, 255, 255])],
    "Blue": [([105, 75, 75], [130, 255, 255])],
    "Purple": [([131, 60, 75], [169, 255, 255])],
}

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

def classify_hsv_color(h, s, v):
    if s < 40 or v < 50:
        return None
    if h <= 10 or h >= 170:
        return "Red"
    elif 11 <= h <= 25:
        return "Orange"
    elif 26 <= h <= 35:
        return "Yellow"
    elif 36 <= h <= 85:
        return "Green"
    elif 86 <= h <= 104:
        return "Cyan"
    elif 105 <= h <= 130:
        return "Blue"
    elif 131 <= h <= 169:
        return "Purple"
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
        print(f"[{serial}] [+] Membuka jendela tampilan layar scrcpy (Bus Jam Escape)...", flush=True)
        try:
            subprocess.Popen(
                ["scrcpy", "-s", serial, "--window-title", f"Bus Jam Escape - {serial}", "--max-fps=25", "--no-audio"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.2)
        except Exception:
            pass

def detect_popup_reward_button_ocr(ocr_items, scale_y=1.0):
    """Mendeteksi tombol klaim / reward / lanjutkan / koleksi di layar popup."""
    keywords = ["koleksi", "klaim", "claim", "tingkatkan", "dapatkan", "ambil", "lanjutkan", "continue", "main lagi", "buka kunci", "ok"]
    for it in ocr_items:
        t = it["text"].lower().strip()
        if any(k in t for k in keywords):
            if it["cy"] >= int(200 * scale_y):
                return it["cx"], it["cy"], it["text"]
    return None

def detect_dialog_close_x_button(ocr_items, scale_y=1.0):
    """Mendeteksi tombol silang X penutup popup dialog."""
    for it in ocr_items:
        t = it["text"].strip().lower()
        if t in ["x", "✕", "✖", "×"] or (len(t) == 1 and t in "xX+"):
            return it["cx"], it["cy"]
    return None

class BusJamEscapeRunner:
    def __init__(self, serial):
        self.serial = serial
        self.tag = f"[{serial}]"
        self.width = 720
        self.height = 1640
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.tg_report_interval = TELEGRAM_REPORT_INTERVAL
        self.latest_game_data = {
            "saldo_rp": None,
            "saldo_poin": None,
            "level": None,
            "queue_count": None,
            "front_passenger": None,
            "parked_buses": [],
            "last_captured_time": None,
            "last_status": "Memulai bot",
            "ads_watched": 0
        }
        self.step_counter = 0
        self.consecutive_failed_taps = 0
        self.total_buses_tapped = 0
        self.total_ads_closed = 0
        self.init_device_specs()
        self.load_cached_state()
        self.start_telegram_reporter_thread()
        self.send_startup_telegram()

    def init_device_specs(self):
        """Ambil dimensi layar perangkat untuk scaling."""
        try:
            res = subprocess.run(["adb", "-s", self.serial, "shell", "wm", "size"], capture_output=True, text=True, timeout=3.0)
            m = re.search(r"(\d+)x(\d+)", res.stdout)
            if m:
                w, h = int(m.group(1)), int(m.group(2))
                self.width = min(w, h)
                self.height = max(w, h)
                self.scale_x = self.width / 720.0
                self.scale_y = self.height / 1640.0
                print(f"{self.tag} Layar HP: {self.width}x{self.height} (Scale X={self.scale_x:.2f}, Y={self.scale_y:.2f})", flush=True)
        except Exception as e:
            print(f"{self.tag} Gagal deteksi ukuran layar: {e}", flush=True)

    def load_cached_state(self):
        if os.path.exists(STATE_FILE_PATH):
            try:
                with open(STATE_FILE_PATH, "r") as f:
                    saved = json.load(f).get(self.serial, {})
                    if saved:
                        self.latest_game_data.update(saved)
            except Exception:
                pass

    def save_cached_state(self):
        try:
            all_states = {}
            if os.path.exists(STATE_FILE_PATH):
                with open(STATE_FILE_PATH, "r") as f:
                    all_states = json.load(f)
            all_states[self.serial] = self.latest_game_data
            with open(STATE_FILE_PATH, "w") as f:
                json.dump(all_states, f, indent=2)
        except Exception:
            pass

    def send_startup_telegram(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
        lines = [
            "🚌 <b>BUS JAM ESCAPE BOT - AKTIF</b>",
            f"🕐 <b>Waktu:</b> {html.escape(now)}",
            f"📱 <b>Device:</b> <code>{html.escape(self.serial)}</code>",
            f"🎯 <b>Target Game:</b> <code>{PACKAGE_NAME}</code>",
            "🚀 <i>Bot otomatis mendeteksi penumpang, bus, & menutup iklan.</i>"
        ]
        send_telegram_async("\n".join(lines))

    def start_telegram_reporter_thread(self):
        def reporter_loop():
            while True:
                time.sleep(self.tg_report_interval)
                try:
                    self.send_periodic_tg_report()
                except Exception:
                    pass
        t = threading.Thread(target=reporter_loop, daemon=True)
        t.start()

    def send_periodic_tg_report(self):
        d = self.latest_game_data
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
        saldo_rp = d.get("saldo_rp") or "-"
        level = d.get("level") or "-"
        antri = d.get("queue_count") or "-"
        front = d.get("front_passenger") or "-"
        buses = ", ".join(d.get("parked_buses") or []) or "-"
        app_status = d.get("last_status") or "Game aktif"
        ads = d.get("ads_watched", 0)

        lines = [
            "🚌 <b>BUS JAM ESCAPE - LAPORAN BERKALA</b>",
            f"🕐 <b>Waktu:</b> {html.escape(now)}",
            "",
            f"💰 <b>Saldo Rp:</b> <b>{html.escape(str(saldo_rp))}</b>",
            f"🎮 <b>Level/Tingkat:</b> <b>{html.escape(str(level))}</b>",
            f"👥 <b>Antrean:</b> <code>{html.escape(str(antri))} orang</code>",
            f"👤 <b>Penumpang Depan:</b> <code>{html.escape(str(front))}</code>",
            f"🚏 <b>Bus di Parkiran:</b> <code>{html.escape(str(buses))}</code>",
            f"📺 <b>Iklan Ditonton:</b> <b>{ads}</b>",
            "",
            f"📱 <b>Device:</b> <code>{html.escape(str(self.serial))}</code>",
            f"🧭 <b>Status:</b> <b>{html.escape(str(app_status))}</b>",
            f"<i>Laporan otomatis setiap {int(self.tg_report_interval // 60)} menit.</i>"
        ]
        send_telegram_async("\n".join(lines))
        print(f"{self.tag} [📱 TG] Laporan berkala terkirim: Rp {saldo_rp} | Level {level} | Antre {antri}", flush=True)

    def update_latest_game_data(self, ocr_items=None, front_color=None, analyzed_buses=None, app_status="Game aktif"):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
        self.latest_game_data["last_status"] = app_status
        self.latest_game_data["last_captured_time"] = now_str
        if front_color:
            self.latest_game_data["front_passenger"] = front_color
        if analyzed_buses is not None:
            self.latest_game_data["parked_buses"] = [b["color"] for b in analyzed_buses[:8]]

        if ocr_items:
            for it in ocr_items:
                text = it.get("text", "")
                t_clean = text.replace("o", "0").replace("O", "0").replace("I", "1").replace("l", "1")
                m_rp = re.search(r"Rp\s*([0-9]+)", t_clean, re.IGNORECASE)
                if m_rp:
                    self.latest_game_data["saldo_rp"] = m_rp.group(1)
                m_lv = re.search(r"(?:tingkat|level)\s*[: ]?\s*(\d+)", text, re.IGNORECASE)
                if m_lv:
                    self.latest_game_data["level"] = m_lv.group(1)
                if "antri" in text.lower():
                    m_q = re.search(r"(\d+)\s*antri", text, re.IGNORECASE)
                    if m_q:
                        self.latest_game_data["queue_count"] = m_q.group(1)
        self.save_cached_state()

    def run_adb(self, cmd_args, timeout=5.0):
        full_cmd = ["adb", "-s", self.serial] + cmd_args
        try:
            res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout, check=False)
            return res.stdout.strip()
        except Exception:
            return ""

    def bring_game_to_foreground(self):
        print(f"{self.tag} [*] Memastikan game berada di foreground ({LAUNCH_ACTIVITY})...", flush=True)
        self.run_adb(["shell", "am", "start", "-n", LAUNCH_ACTIVITY], timeout=4.0)
        time.sleep(1.0)

    def tap(self, x, y):
        self.run_adb(["shell", "input", "tap", str(int(x)), str(int(y))])

    def press_back(self):
        self.run_adb(["shell", "input", "keyevent", "4"])

    def get_screenshot(self):
        cmd = ["adb", "-s", self.serial, "exec-out", "screencap", "-p"]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=4.0)
            if proc.returncode == 0 and len(proc.stdout) > 5000:
                img_array = np.frombuffer(proc.stdout, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                return img
        except Exception:
            pass
        return None

    def get_foreground_focus(self):
        out = self.run_adb(["shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"], timeout=3.0)
        return out

    def is_ad_activity(self, focus_str):
        if not focus_str:
            return False
        f_lower = focus_str.lower()
        return any(k in f_lower for k in AD_KEYWORDS)

    def run_full_ocr(self, img):
        if not os.path.exists(OCR_HELPER_PATH) or img is None:
            return []
        tmp_path = f"/tmp/busjam_escape_ocr_{self.serial}.png"
        cv2.imwrite(tmp_path, img)
        try:
            out = subprocess.check_output([OCR_HELPER_PATH, tmp_path], stderr=subprocess.DEVNULL, timeout=2.5).decode("utf-8")
            items = []
            h_crop, w_crop = self.height, self.width
            for line in out.strip().splitlines():
                parts = line.split("|")
                if len(parts) == 2:
                    text = parts[0].strip()
                    coords = [float(x) for x in parts[1].split(",")]
                    cx = int((coords[0] + coords[2] / 2.0) * w_crop)
                    cy = int((1.0 - (coords[1] + coords[3] / 2.0)) * h_crop)
                    items.append({"text": text, "cx": cx, "cy": cy})
            return items
        except Exception:
            return []

    def detect_ad_countdown_seconds(self, img):
        """Mendeteksi countdown detik iklan di bagian atas layar."""
        if img is None:
            return None
        sx, sy = self.scale_x, self.scale_y
        top_patch = img[0:int(260 * sy), :]
        ocr_items = self.run_full_ocr(top_patch)
        for it in ocr_items:
            t = it["text"].strip()
            m_timer = re.search(r"(\d{1,2})\s*(?:s|detik|dtk)?$", t, re.IGNORECASE)
            if m_timer:
                val = int(m_timer.group(1))
                if 1 <= val <= 90:
                    return val
            m_colon = re.search(r"00:(\d{2})", t)
            if m_colon:
                val = int(m_colon.group(1))
                if 1 <= val <= 90:
                    return val
        return None

    def detect_and_click_ad_x_button(self, img=None):
        """Mendeteksi dan mengeklik tombol X / Tutup pada layar iklan."""
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return False
        sx, sy = self.scale_x, self.scale_y
        ocr_items = self.run_full_ocr(img)

        for it in ocr_items:
            if it["cy"] < int(350 * sy):
                t = it["text"].strip().lower()
                if t in ["x", "✕", "✖", "×", ">>", "skip", "close", "tutup"] or (len(t) == 1 and t in "xX+"):
                    print(f"{self.tag} [★] Menemukan tombol Tutup Iklan '{it['text']}' via OCR di ({it['cx']}, {it['cy']})!", flush=True)
                    self.tap(it["cx"], it["cy"])
                    time.sleep(0.4)
                    return True

        for x_start, x_end in [(int(580 * sx), int(710 * sx)), (int(10 * sx), int(140 * sx))]:
            y1, y2 = int(30 * sy), int(280 * sy)
            crop = img[y1:y2, x_start:x_end]
            if crop.size > 0:
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 40, 140)
                cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in cnts:
                    x, y, w, h = cv2.boundingRect(cnt)
                    if (15 <= w <= 80) and (15 <= h <= 80):
                        cx = x_start + x + w // 2
                        cy = y1 + y + h // 2
                        print(f"{self.tag} [★] Menemukan calon tombol X di ({cx}, {cy})! Mengeklik...", flush=True)
                        self.tap(cx, cy)
                        time.sleep(0.4)
                        return True
        return False

    def close_ad_screen_thoroughly(self):
        """Menutup iklan secara menyeluruh: BACK -> X pojok -> bawa launcher kembali."""
        self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
        self.run_adb(["shell", "am", "force-stop", "com.android.chrome"])
        sx, sy = self.scale_x, self.scale_y
        self.press_back()
        time.sleep(0.4)

        img = self.get_screenshot()
        if img is not None:
            self.detect_and_click_ad_x_button(img)

        close_points = [
            (int(665 * sx), int(70 * sy)),
            (int(665 * sx), int(115 * sy)),
            (int(662 * sx), int(110 * sy)),
            (int(652 * sx), int(200 * sy)),
            (int(635 * sx), int(75 * sy)),
            (int(665 * sx), int(250 * sy)),
            (int(55 * sx), int(70 * sy)),
            (int(55 * sx), int(115 * sy)),
            (int(55 * sx), int(250 * sy)),
            (int(40 * sx), int(120 * sy)),
            (int(680 * sx), int(50 * sy))
        ]
        for tx, ty in close_points:
            self.tap(tx, ty)
            time.sleep(0.1)

        self.press_back()
        time.sleep(0.4)
        self.bring_game_to_foreground()

    def wait_ad_and_close_ad(self, reason="Iklan Video/Interstitial"):
        """Menonton iklan dan menutupnya setelah selesai secara adaptif."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
        lines = [
            "📺 <b>MEMBUKA IKLAN</b>",
            f"🕐 <code>{now}</code>",
            f"📱 <b>Game:</b> {PACKAGE_NAME}",
            f"🎯 <b>Alasan:</b> {html.escape(reason)}",
            "⏳ <i>Bot sedang menonton iklan...</i>"
        ]
        send_telegram_async("\n".join(lines))
        print(f"\n{self.tag} [⏳] {reason} aktif! Menunggu iklan selama minimal {AD_WAIT_SECONDS}s...", flush=True)
        
        start_time = time.time()
        max_wait = AD_WAIT_SECONDS + 15
        
        while time.time() - start_time < max_wait:
            time.sleep(2.0)
            elapsed = time.time() - start_time
            focus = self.get_foreground_focus()

            focus_l = focus.lower()
            if any(pkg in focus_l for pkg in ["com.android.chrome", "org.chromium.chrome", "com.google.android.apps.chrome", "browser"]):
                print(f"{self.tag} [!] Browser terbuka oleh iklan. Menutup browser...", flush=True)
                self.run_adb(["shell", "am", "force-stop", "com.android.chrome"])
                time.sleep(0.4)
                self.press_back()
                self.bring_game_to_foreground()
                continue

            if any(pkg in focus_l for pkg in ["com.android.vending", "google.android.finsky"]):
                print(f"{self.tag} [!] Play Store terbuka oleh iklan. Menutup paksa Play Store & menekan BACK...", flush=True)
                self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
                time.sleep(0.4)
                self.press_back()
                self.bring_game_to_foreground()
                continue

            img = self.get_screenshot()
            if img is not None:
                ocr_items = self.run_full_ocr(img)
                for it in ocr_items:
                    t = it["text"].lower()
                    if "press anywhere" in t or "continue" in t:
                        print(f"{self.tag} [+] Menemukan prompt continue iklan di ({it['cx']}, {it['cy']}). Mengeklik...", flush=True)
                        self.tap(it["cx"], it["cy"])
                        time.sleep(1.0)
                        break

                if elapsed >= 18:
                    if self.detect_and_click_ad_x_button(img):
                        print(f"{self.tag} [✔] Tombol penutup iklan diklik pada detik ke-{int(elapsed)}.", flush=True)
                        time.sleep(1.0)
                        focus_chk = self.get_foreground_focus()
                        if not self.is_ad_activity(focus_chk):
                            break

                    if "inmobiadactivity" in focus_l:
                        self.tap(int(662 * self.scale_x), int(110 * self.scale_y))
                        time.sleep(0.8)

            focus_cur = self.get_foreground_focus()
            if "hmeactivity" in focus_cur.lower() and not self.is_ad_activity(focus_cur):
                print(f"{self.tag} [✔] Berhasil kembali ke layar game HmeActivity.", flush=True)
                break

        print(f"{self.tag} [✔] Waktu tonton iklan selesai. Memastikan layar tertutup...", flush=True)
        self.close_ad_screen_thoroughly()
        self.latest_game_data["ads_watched"] = self.latest_game_data.get("ads_watched", 0) + 1
        self.total_ads_closed += 1
        self.save_cached_state()

    def handle_app_focus_and_ads(self):
        """Cek apakah game sedang aktif di layar, atau sedang ada iklan/popup sistem."""
        focus = self.get_foreground_focus()
        if not focus:
            return False

        focus_l = focus.lower()

        # 1. System notification shade / status bar / launcher
        if any(s in focus_l for s in ["statusbar", "notificationshade", "quickstep", "xoslauncher", "launcher"]):
            print(f"{self.tag} [!] Layar sistem / Notification Shade / Launcher aktif. Mengembalikan game...", flush=True)
            self.press_back()
            time.sleep(0.3)
            self.bring_game_to_foreground()
            time.sleep(0.5)
            return False

        # 2. Browser terbuka oleh iklan
        if any(pkg in focus_l for pkg in ["com.android.chrome", "org.chromium.chrome", "com.google.android.apps.chrome", "browser"]):
            print(f"{self.tag} [!] Browser terbuka oleh iklan! Menutup paksa & kembali ke game...", flush=True)
            self.run_adb(["shell", "am", "force-stop", "com.android.chrome"])
            self.press_back()
            time.sleep(0.4)
            self.bring_game_to_foreground()
            time.sleep(0.5)
            return False

        # 3. Play Store terbuka oleh iklan
        if any(pkg in focus_l for pkg in ["com.android.vending", "google.android.finsky"]):
            print(f"{self.tag} [!] Play Store terbuka oleh iklan! Menutup paksa Play Store & kembali ke game...", flush=True)
            self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
            self.press_back()
            time.sleep(0.4)
            self.bring_game_to_foreground()
            time.sleep(0.5)
            return False

        # 4. Layar Iklan Aktif
        if self.is_ad_activity(focus):
            self.wait_ad_and_close_ad("Iklan Layar Penuh")
            return False

        if PACKAGE_NAME not in focus:
            print(f"{self.tag} [!] Game di background ({focus.strip()}). Membuka kembali...", flush=True)
            self.bring_game_to_foreground()
            return False

        return True

    def detect_front_passenger_color(self, img):
        """Mendeteksi warna kelompok penumpang di bagian paling depan antrean (y: 340..415, x: 250..390)."""
        sx, sy = self.scale_x, self.scale_y
        patch = img[int(340 * sy):int(415 * sy), int(250 * sx):int(390 * sx)]
        if patch.size == 0:
            return None

        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        sat_mask = (hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 70)
        h_vals = hsv[:, :, 0][sat_mask]
        s_vals = hsv[:, :, 1][sat_mask]
        v_vals = hsv[:, :, 2][sat_mask]

        if len(h_vals) < 40:
            return None

        color_counts = {}
        for h, s, v in zip(h_vals, s_vals, v_vals):
            col = classify_hsv_color(h, s, v)
            if col:
                color_counts[col] = color_counts.get(col, 0) + 1

        if not color_counts:
            return None

        best_color = max(color_counts, key=color_counts.get)
        if color_counts[best_color] > 50:
            return best_color
        return None

    def check_halte_slots_status(self, img):
        """
        Mengecek 7 slot halte di y: 532.
        Return: (empty_count, locked_count, occupied_count)
        """
        sx, sy = self.scale_x, self.scale_y
        slots_x_base = [69, 166, 263, 360, 457, 554, 651]
        y_center = int(532 * sy)
        
        empty_count = 0
        locked_count = 0
        occupied_count = 0

        for sx_val in slots_x_base:
            cx = int(sx_val * sx)
            patch = img[max(0, y_center - 25):min(self.height, y_center + 25), max(0, cx - 25):min(self.width, cx + 25)]
            if patch.size == 0:
                continue
            hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
            mean_h = hsv[:,:,0].mean()
            mean_s = hsv[:,:,1].mean()
            mean_v = hsv[:,:,2].mean()

            if 42 <= mean_h <= 50 and 70 <= mean_s <= 95 and 180 <= mean_v <= 215:
                locked_count += 1
            elif 95 <= mean_h <= 115 and 50 <= mean_s <= 75:
                empty_count += 1
            else:
                occupied_count += 1

        return empty_count, locked_count, occupied_count

    def detect_open_buses(self, img):
        """Mendeteksi semua bus individual di area parkiran rumput hijau (y: 780..1480)."""
        sx, sy = self.scale_x, self.scale_y
        lot = img[int(780 * sy):int(1480 * sy), :]
        if lot.size == 0:
            return []

        hsv = cv2.cvtColor(lot, cv2.COLOR_BGR2HSV)
        floor = (hsv[:,:,0] >= 44) & (hsv[:,:,0] <= 62) & (hsv[:,:,1] >= 45) & (hsv[:,:,2] >= 140)

        buses = []
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

        for color_name, ranges in COLOR_RANGES.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lower, upper in ranges:
                m = cv2.inRange(hsv, np.array(lower), np.array(upper))
                m[floor] = 0
                mask |= m

            mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            cnts, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                area = cv2.contourArea(c)
                if 700 <= area <= 25000:
                    x, y, w, h = cv2.boundingRect(c)
                    cx = x + w // 2
                    cy = int(780 * sy) + y + h // 2
                    buses.append({
                        "cx": cx,
                        "cy": cy,
                        "w": w,
                        "h": h,
                        "color": color_name,
                        "area": area
                    })

        buses.sort(key=lambda b: (b["cy"], b["cx"]))
        return buses

    def play_step(self):
        """Satu langkah siklus permainan: cek fokus/iklan -> OCR popups -> deteksi warna -> tap bus."""
        self.step_counter += 1

        if not self.handle_app_focus_and_ads():
            return

        img = self.get_screenshot()
        if img is None:
            time.sleep(1.0)
            return

        ocr_items = self.run_full_ocr(img)
        if ocr_items:
            reward_btn = detect_popup_reward_button_ocr(ocr_items, self.scale_y)
            if reward_btn:
                bx, by, desc = reward_btn
                print(f"{self.tag} [★] Menemukan tombol popup '{desc}' di ({bx}, {by})! Mengeklik...", flush=True)
                self.tap(bx, by)
                time.sleep(1.0)
                focus_after = self.get_foreground_focus()
                if self.is_ad_activity(focus_after):
                    self.wait_ad_and_close_ad(f"Iklan Reward dari {desc}")
                return

            dialog_x = detect_dialog_close_x_button(ocr_items, self.scale_y)
            if dialog_x and dialog_x[1] < int(400 * self.scale_y):
                print(f"{self.tag} [★] Menutup dialog modal X di ({dialog_x[0]}, {dialog_x[1]})...", flush=True)
                self.tap(dialog_x[0], dialog_x[1])
                time.sleep(0.8)
                return

        # Pastikan kita benar-benar berada di gameplay HmeActivity sebelum mendeteksi atau mengeklik bus
        focus_board = self.get_foreground_focus()
        if "hmeactivity" not in focus_board.lower() or self.is_ad_activity(focus_board):
            time.sleep(1.0)
            return

        front_color = self.detect_front_passenger_color(img)
        empty_slots, locked_slots, occupied_slots = self.check_halte_slots_status(img)
        buses = self.detect_open_buses(img)
        self.update_latest_game_data(ocr_items, front_color, buses, app_status="Bermain Level")

        if not buses:
            print(f"{self.tag} [?] Tidak ada bus terdeteksi di parkiran. Menunggu transisi level/animasi...", flush=True)
            time.sleep(1.5)
            return

        target_bus = None

        if front_color:
            matching_buses = [b for b in buses if b["color"] == front_color]
            if matching_buses:
                target_bus = matching_buses[0]
                print(f"{self.tag} [🎯] COCOK! Penumpang depan: {front_color}. Memilih bus {target_bus['color']} di ({target_bus['cx']}, {target_bus['cy']}).", flush=True)

        if not target_bus and empty_slots >= 2:
            target_bus = buses[0]
            print(f"{self.tag} [➡] Penumpang {front_color or 'N/A'}. Slot kosong={empty_slots}. Membuka jalan dengan bus teratas {target_bus['color']} di ({target_bus['cx']}, {target_bus['cy']}).", flush=True)

        if not target_bus:
            if empty_slots <= 1 and buses:
                print(f"{self.tag} [⚠️] Slot halte hampir penuh (kosong={empty_slots}). Mencoba klik booster Urutkan / Refresh...", flush=True)
                self.tap(int(550 * self.scale_x), int(1610 * self.scale_y))
                time.sleep(1.0)
                return
            target_bus = buses[0]

        tx, ty = target_bus["cx"], target_bus["cy"]
        print(f"{self.tag} [Tap] Mengeklik Bus {target_bus['color']} di ({tx}, {ty})...", flush=True)
        self.tap(tx, ty)
        self.total_buses_tapped += 1
        time.sleep(0.9)

    def loop_forever(self):
        print(f"{self.tag} [🚀] Memulai loop bot Bus Jam Escape...", flush=True)
        ensure_scrcpy_running(self.serial)
        self.bring_game_to_foreground()
        time.sleep(1.5)

        while True:
            try:
                self.play_step()
            except KeyboardInterrupt:
                print(f"\n{self.tag} Bot dihentikan oleh user.")
                break
            except Exception as e:
                print(f"{self.tag} [ERROR] Terjadi exception di step: {e}", flush=True)
                time.sleep(2.0)

def run_device_worker(serial):
    bot = BusJamEscapeRunner(serial)
    bot.loop_forever()

def main():
    devices = get_connected_devices()
    if not devices:
        print("[-] Tidak ada perangkat Android terhubung via ADB.")
        sys.exit(1)

    print(f"[+] Ditemukan {len(devices)} perangkat: {devices}")
    workers = []
    for serial in devices:
        p = multiprocessing.Process(target=run_device_worker, args=(serial,))
        p.daemon = True
        p.start()
        workers.append(p)

    def signal_handler(sig, frame):
        print("\n[+] Menghentikan semua worker bot...")
        for p in workers:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    for p in workers:
        p.join()

if __name__ == "__main__":
    main()
