#!/usr/bin/env python3
"""
Bot Coin Dash Shot - Auto Main + Withdraw Rp 500 + Telegram Notification
Game: com.coin.sortdash.remove
"""

import subprocess
import time
import re
import sys
import os
from pathlib import Path
import json
import html

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

# ============= KONFIGURASI =============
PACKAGE_NAME = "com.coin.sortdash.remove"
MIN_WITHDRAW_RP = 20000  # Minimal saldo untuk klik ≈Rp / tarik dana
AD_WAIT_SECONDS = 6   # Tunggu iklan 6 detik lalu restart game
OCR_HELPER_PATH = "/Users/macbookair/ocr_helper"

# Telegram (opsional - akan diambil dari file jika ada)
TELEGRAM_BOT_TOKEN = None
TELEGRAM_CHAT_ID = None

# ============= FUNGSI HELPER =============

def send_telegram_async(message):
    """Kirim notifikasi ke Telegram (async, tidak blocking)"""
    try:
        token = TELEGRAM_BOT_TOKEN
        chat_id = TELEGRAM_CHAT_ID
        
        # Coba ambil dari file config jika tidak ada
        if not token or not chat_id:
            try:
                import sys
                sys.path.insert(0, '/Users/macbookair/telegram_venv/lib/python3.11/site-packages')
                from telegram_bot_helper import get_telegram_config
                token, chat_id = get_telegram_config()
            except:
                pass
        
        # Fallback: pakai tujuan Telegram yang sama seperti soda_pack_puzzle_bot.
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

def log_event(event_type, description, data=None):
    """Log event ke file JSON"""
    try:
        log_file = Path('/Users/macbookair/coin_dash_shot_activity_log.json')
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S WIB"),
            "event_type": event_type,
            "description": description,
            "data": data or {}
        }
        
        logs.append(log_entry)
        
        # Keep only last 100 entries
        if len(logs) > 100:
            logs = logs[-100:]
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"[!] Log error: {e}", flush=True)

def get_connected_devices():
    """Ambil list device Android yang terhubung via ADB"""
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=3.0
        )
        lines = result.stdout.strip().split('\n')[1:]
        devices = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == 'device':
                devices.append(parts[0])
        return devices
    except Exception as e:
        print(f"[!] Error getting devices: {e}", flush=True)
        return []

# ============= CLASS BOT =============

class CoinDashShotBot:
    def __init__(self, serial: str):
        self.serial = serial
        self.tag = f"[{serial}]"
        self.screen_w = 720
        self.screen_h = 1600
        self.scale_x = self.screen_w / 720.0
        self.scale_y = self.screen_h / 1600.0
        self.last_recorded_rp = 0
        self.last_reward_probe = 0
        self.reward_probe_interval = 2
        self.open_ad_after_game_open = True
        self.balance_report_sent_for_open = False
        self.last_forced_ad_open_attempt = 0
        self.balance_state_path = Path('/Users/macbookair/coin_dash_shot_balance_state.json')
        self.last_withdraw_click_ts = 0
        self.last_orange_menarik_click_ts = 0
        self.last_confirm_click_ts = 0
        self.last_green_confirm_click_ts = 0
        self.withdraw_confirm_count = 0
        self.last_withdraw_success_restart_ts = 0
        self.stop_flag = False
        
    def run_adb(self, cmd, timeout=5.0):
        """Jalankan perintah ADB"""
        try:
            full_cmd = ["adb", "-s", self.serial] + cmd
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout.strip()
        except Exception as e:
            return ""
    
    def tap(self, x, y):
        """Tap di koordinat (x, y)"""
        self.run_adb(["shell", "input", "tap", str(int(x)), str(int(y))])
        time.sleep(0.01)
    
    def tap_burst(self, coords, delay=0.006):
        """Tap multiple coordinates dengan delay minimal"""
        for x, y in coords:
            self.tap(x, y)
            time.sleep(delay)
    
    def press_back(self):
        """Tekan tombol BACK"""
        self.run_adb(["shell", "input", "keyevent", "KEYCODE_BACK"])
        time.sleep(0.025)
    
    def get_screenshot(self):
        """Ambil screenshot sebagai OpenCV image dan update skala layar."""
        if cv2 is None or np is None:
            return None
        try:
            result = subprocess.run(
                ["adb", "-s", self.serial, "exec-out", "screencap", "-p"],
                capture_output=True,
                timeout=4.0
            )
            if not result.stdout:
                return None
            arr = np.frombuffer(result.stdout, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                h, w = img.shape[:2]
                self.screen_w = w
                self.screen_h = h
                self.scale_x = self.screen_w / 720.0
                self.scale_y = self.screen_h / 1600.0
            return img
        except Exception:
            return None

    def run_full_ocr(self, img):
        """OCR ringan untuk deteksi popup/tombol iklan."""
        if img is None or cv2 is None or not os.path.exists(OCR_HELPER_PATH):
            return []
        tmp_path = f"/tmp/coin_dash_ocr_{self.serial}.png"
        try:
            cv2.imwrite(tmp_path, img)
            h, w = img.shape[:2]
            out = subprocess.check_output(
                [OCR_HELPER_PATH, tmp_path],
                stderr=subprocess.DEVNULL,
                timeout=2.8
            ).decode("utf-8", errors="ignore")
            items = []
            for line in out.strip().splitlines():
                parts = line.split("|")
                if len(parts) != 2:
                    continue
                text = parts[0].strip()
                coords = [float(x) for x in parts[1].split(",")]
                cx = int((coords[0] + coords[2] / 2.0) * w)
                cy = int((1.0 - (coords[1] + coords[3] / 2.0)) * h)
                items.append({"text": text, "cx": cx, "cy": cy})
            return items
        except Exception:
            return []

    def ocr_text(self, img=None):
        if img is None:
            img = self.get_screenshot()
        items = self.run_full_ocr(img)
        return " ".join([it["text"].lower() for it in items]), items

    def format_elapsed(self, seconds):
        try:
            seconds = int(max(0, seconds))
        except Exception:
            return "-"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h:
            return f"{h}j {m}m {s}d"
        if m:
            return f"{m}m {s}d"
        return f"{s}d"

    def read_current_reward_balance_rp(self, retries=4):
        """Baca saldo header merah ≈Rp (bukan total cash hijau/oranye)."""
        for _ in range(retries):
            img = self.get_screenshot()
            text, items = self.ocr_text(img)
            candidates = []
            for it in items:
                t_raw = it.get("text", "")
                t = t_raw.lower().replace("o", "0").replace("O", "0")
                if "rp" not in t:
                    continue
                cy = int(it.get("cy", 0))
                cx = int(it.get("cx", 0))
                # Header atas saja. Saldo ≈Rp ada di tombol merah kiri-tengah (cx kira-kira 180-330).
                if cy > int(175 * self.scale_y):
                    continue
                m = re.search(r"rp\s*([0-9][0-9\.,]*)", t, re.I)
                if not m:
                    continue
                try:
                    val = int(re.sub(r"\D", "", m.group(1)))
                except Exception:
                    continue
                if val <= 0:
                    continue
                score = 0
                if cx < int(350 * self.scale_x):
                    score += 100
                if int(150 * self.scale_x) <= cx <= int(330 * self.scale_x):
                    score += 80
                if any(k in t_raw for k in ["≈", "~", "="]):
                    score += 60
                # Hindari saldo cash/penarikan besar di kanan atas.
                if cx > int(340 * self.scale_x):
                    score -= 120
                candidates.append((score, val, t_raw, cx, cy))

            if candidates:
                candidates.sort(reverse=True)
                score, val, raw, cx, cy = candidates[0]
                print(f"{self.tag} [💰] Saldo ≈Rp terbaca: Rp {val} dari OCR '{raw}' ({cx},{cy})", flush=True)
                return val
            time.sleep(0.08)
        print(f"{self.tag} [!] Gagal membaca saldo ≈Rp dari header.", flush=True)
        return None

    def send_balance_report_before_ad(self):
        """Kirim saldo sekarang vs saldo sebelumnya sebelum bot klik iklan."""
        if self.balance_report_sent_for_open:
            return
        self.balance_report_sent_for_open = True

        now_ts = time.time()
        now_time = time.strftime("%Y-%m-%d %H:%M:%S WIB")
        current = self.read_current_reward_balance_rp()

        prev_balance = None
        prev_ts = None
        try:
            if self.balance_state_path.exists():
                st = json.loads(self.balance_state_path.read_text())
                prev_balance = st.get("last_balance_rp")
                prev_ts = st.get("last_ts")
        except Exception:
            pass

        if current is not None:
            self.last_recorded_rp = current
            try:
                self.balance_state_path.write_text(json.dumps({
                    "last_balance_rp": current,
                    "last_ts": now_ts,
                    "updated_at": now_time,
                    "serial": self.serial,
                }, indent=2))
            except Exception:
                pass

        current_txt = f"Rp {current}" if current is not None else "Gagal dibaca"
        prev_num_txt = str(prev_balance) if prev_balance is not None else "-"
        if current is not None and prev_balance is not None:
            delta = current - int(prev_balance)
            delta_txt = f"{delta:+d}"
        else:
            delta_txt = "-"
        elapsed_txt = self.format_elapsed(now_ts - float(prev_ts)) if prev_ts else "-"
        focus_now = html.escape(self.get_foreground_focus() or "-")

        short_time = time.strftime("%H:%M:%S")
        msg = (
            f"💰 <b>SALDO = {html.escape(current_txt)} [{html.escape(prev_num_txt)} {html.escape(delta_txt)}]</b>\n"
            f"🕐 <code>{short_time}</code>"
        )
        send_telegram_async(msg)
        log_event("saldo_sebelum_iklan", "Cek saldo sebelum klik iklan", {
            "current": current,
            "previous": prev_balance,
            "delta": (current - int(prev_balance)) if current is not None and prev_balance is not None else None,
            "elapsed_seconds": (now_ts - float(prev_ts)) if prev_ts else None,
        })

    def is_checkin_button_gray(self, img):
        """Cek apakah tombol Check-in pada popup Login sehari berwarna abu-abu/nonaktif."""
        if img is None or cv2 is None:
            return True
        h, w = img.shape[:2]
        sx = w / 720.0
        sy = h / 1600.0

        # Area tombol Check-in di bawah popup. Koordinat dibuat agak lebar
        # supaya tetap kena walau tombol bergeser beberapa piksel.
        x1 = max(0, int(175 * sx))
        x2 = min(w, int(545 * sx))
        y1 = max(0, int(1238 * sy))
        y2 = min(h, int(1342 * sy))
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            return True

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]

        # Tombol nonaktif dominan abu-abu: saturasi rendah dan brightness sedang/tinggi.
        gray_mask = (sat < 55) & (val > 70) & (val < 245)
        bright_color_mask = (sat > 80) & (val > 110)
        gray_ratio = float(gray_mask.mean())
        color_ratio = float(bright_color_mask.mean())
        sat_mean = float(sat.mean())

        is_gray = gray_ratio > 0.45 and color_ratio < 0.28 and sat_mean < 75
        print(
            f"{self.tag} [DEBUG] Check-in color: gray_ratio={gray_ratio:.2f}, "
            f"color_ratio={color_ratio:.2f}, sat_mean={sat_mean:.1f}, gray={is_gray}",
            flush=True
        )
        return is_gray

    def handle_daily_login_popup(self):
        """Handle popup Login sehari.

        Aturan user:
        - Jika tombol Check-in abu-abu/nonaktif: jangan klik Check-in, klik X kanan atas popup.
        - Jika tombol Check-in bukan abu-abu: klik Check-in.
        """
        img = self.get_screenshot()
        text, _ = self.ocr_text(img)
        if not any(k in text for k in ["login sehari", "login sehar", "check-in", "hari 365"]):
            return False

        if self.is_checkin_button_gray(img):
            print(f"{self.tag} [+] Popup Login sehari: tombol Check-in abu-abu, klik X.", flush=True)
            # X popup kanan atas dekat judul Login sehari.
            self.tap_burst([
                (int(631 * self.scale_x), int(341 * self.scale_y)),
                (int(631 * self.scale_x), int(349 * self.scale_y)),
                (int(640 * self.scale_x), int(341 * self.scale_y)),
            ], delay=0.04)
            time.sleep(0.07)
            return True

        print(f"{self.tag} [+] Popup Login sehari: tombol Check-in aktif, klik Check-in.", flush=True)
        self.tap(int(360 * self.scale_x), int(1292 * self.scale_y))
        time.sleep(0.12)
        return True

    def close_popup_or_ad(self):
        """Tutup popup gagal iklan/end-card iklan tanpa force reward palsu."""
        sx, sy = self.scale_x, self.scale_y
        close_points = [
            (int(635 * sx), int(605 * sy)),  # X popup game
            (int(620 * sx), int(580 * sy)),  # X dialog feedback iklan
            (int(632 * sx), int(815 * sy)),  # X menu "Lebih" pada iklan Bytedance/Pangle
            (int(60 * sx), int(130 * sy)),   # X custom-tab/landing page iklan kiri atas
            (int(635 * sx), int(500 * sy)),  # X end-card iklan dalam game
            (int(675 * sx), int(500 * sy)),
            (int(662 * sx), int(108 * sy)),  # tombol > / >> playable/end-card kanan atas
            (int(662 * sx), int(160 * sy)),  # tombol >> / skip Pangle kanan atas
            (int(665 * sx), int(75 * sy)),   # X iklan kanan atas
            (int(55 * sx), int(75 * sy)),    # X iklan kiri atas
            (int(55 * sx), int(115 * sy)),
        ]
        self.tap_burst(close_points, delay=0.04)
        self.press_back()
        time.sleep(0.045)

        focus = self.get_foreground_focus().lower()
        # Kalau tombol iklan membuka landing page/aplikasi eksternal, tutup dan balik ke game.
        external_pkgs = [
            "com.android.chrome", "com.android.browser", "com.transsion.phoenix",
            "com.heytap.browser", "com.opera.browser", "com.opera.mini.native",
            "com.android.vending", "com.taxsee.driver", "com.gojek.driver",
            "com.grabtaxi.driver2", "id.co.taximaxim.driver"
        ]
        if PACKAGE_NAME.lower() not in focus:
            for pkg in external_pkgs:
                if pkg in focus:
                    print(f"{self.tag} [!] Landing/app iklan terbuka ({pkg}), force-stop dan balik game.", flush=True)
                    self.run_adb(["shell", "am", "force-stop", pkg])
                    time.sleep(0.045)
                    self.bring_game_to_foreground()
                    break

    def is_ad_like_screen(self, text="", focus=""):
        """Deteksi layar iklan meski activity masih GameActivity."""
        text = (text or "").lower()
        focus = (focus or "").lower()
        ad_focus_words = [
            "adactivity", "rewardvideo", "applovin", "mbridge", "mintegral",
            "unity", "vungle", "ironsource", "pangle", "audiencenetwork",
            "chartboost", "bigo", "yandex", "bytedance", "openadsdk",
            "ttreward", "ttrewardexpress", "pangle"
        ]
        ad_text_words = [
            "buka toko", "instal sekarang", "install now", "google play",
            "get it on", "download", "unduh", "skip", "lewati", "close ad",
            "kunjungi situs", "bonus akumulasi", "feedback", "not playing",
            "sound problems", "misleading", "mintegral", "lihat sekarang",
            "iklan", "lebih", "coba lagi", "salin tautan", "buka di browser"
        ]
        return (
            any(k in focus for k in ad_focus_words)
            or any(k in text for k in ad_text_words)
            or bool(re.search(r"\b\d{1,2}\s*s\b", text))
        )

    def wait_and_close_rewarded_ad(self, source="Iklan terdeteksi"):
        """Setelah buka iklan: notif ringkas, tunggu 10 detik, lalu restart game."""
        wait_time = 6
        now_time = time.strftime("%H:%M:%S")
        source_txt = html.escape(str(source or "Iklan terdeteksi"))
        ad_msg = (
            f"🎬 <b>MEMBUKA IKLAN</b> <code>{now_time}</code>\n"
            f"📍 {source_txt}"
        )
        send_telegram_async(ad_msg)
        log_event("nonton_iklan", f"Membuka iklan: {source}", {"source": source})

        print(f"{self.tag} [📺] Iklan terbuka dari {source}, tunggu {wait_time}s lalu restart game...", flush=True)
        time.sleep(wait_time)

        self.clean_restart_all_apps_and_game(f"Tutup iklan: {source}")
        return True

    def detect_and_click_reward_popup(self):
        """Klik tombol video reward pada popup seperti 'Bebas/Gratis/Tonton'."""
        img = self.get_screenshot()
        text, items = self.ocr_text(img)
        if not text:
            return False

        # Popup gagal: tutup supaya bot tidak stuck.
        if any(k in text for k in ["gagal", "failed", "tidak tersedia", "no ad", "no fill", "memuat video"]):
            print(f"{self.tag} [!] Popup gagal muat video terdeteksi, ditutup.", flush=True)
            log_event("ad_failed_popup", "Popup gagal muat video ditutup", {"text": text[:200]})
            self.close_popup_or_ad()
            return True

        reward_words = ["bebas", "gratis", "free", "tonton", "video", "klaim", "collect", "claim"]
        modal_words = ["menghapus", "petunjuk", "hadiah", "reward", "bonus", "x2", "iklan"]
        if not any(k in text for k in modal_words + reward_words):
            return False

        # Utamakan hasil OCR tombol "Bebas/Gratis/Tonton/Video".
        for it in items:
            t = it["text"].lower()
            if any(k in t for k in reward_words) and int(720 * self.scale_y) <= it["cy"] <= int(1125 * self.scale_y):
                print(f"{self.tag} [+] Klik tombol reward '{it['text']}' di ({it['cx']},{it['cy']})", flush=True)
                self.tap(it["cx"], it["cy"])
                time.sleep(0.25)
                self.wait_and_close_rewarded_ad(f"Popup tombol {it['text']}")
                return True

        # Fallback untuk popup Coin Dash: tombol oranye besar sekitar bawah tengah.
        if any(k in text for k in ["menghapus", "petunjuk", "bebas", "gratis", "video"]):
            x = int(360 * self.scale_x)
            y = int(1015 * self.scale_y)
            print(f"{self.tag} [+] Klik fallback tombol video reward di ({x},{y})", flush=True)
            self.tap(x, y)
            time.sleep(0.25)
            self.wait_and_close_rewarded_ad("Fallback tombol video/Bebas")
            return True

        return False

    def probe_reward_buttons(self, force=False):
        """Coba buka tombol reward/video iklan.

        force=True dipakai setelah game baru dibuka/restart agar langsung klik ikon iklan.
        """
        now = time.time()
        if force:
            if now - self.last_forced_ad_open_attempt < 1:
                return False
            self.last_forced_ad_open_attempt = now
            print(f"{self.tag} [+] Game baru terbuka: coba klik ikon iklan/video/Bebas...", flush=True)
        else:
            if now - self.last_reward_probe < self.reward_probe_interval:
                return False
            self.last_reward_probe = now

        # Kandidat ikon iklan/video:
        # - tombol + bantuan bawah (sapu/lampu/hapus)
        # - crate/kotak video di area bawah kanan
        # - slot/video reward dekat kotak jika ada
        points = [
            (int(575 * self.scale_x), int(1192 * self.scale_y)),
            (int(582 * self.scale_x), int(1058 * self.scale_y)),
            (int(618 * self.scale_x), int(1348 * self.scale_y)),
            (int(407 * self.scale_x), int(1348 * self.scale_y)),
            (int(195 * self.scale_x), int(1348 * self.scale_y)),
            (int(650 * self.scale_x), int(505 * self.scale_y)),
        ]
        for x, y in points:
            self.tap(x, y)
            time.sleep(0.08)
            if self.detect_and_click_reward_popup():
                return True
            # Jika hanya popup info terbuka tanpa iklan, tutup.
            img = self.get_screenshot()
            text, _ = self.ocr_text(img)
            if self.is_ad_like_screen(text, self.get_foreground_focus()):
                self.wait_and_close_rewarded_ad("Ikon video/reward terdeteksi")
                return True
            if any(k in text for k in ["menghapus", "petunjuk", "bebas", "gratis", "video"]):
                self.close_popup_or_ad()
                time.sleep(0.045)
        return False

    def get_screenshot_dummy_removed(self):
        return None
    
    def get_foreground_focus(self):
        """Cek aplikasi/activity yang sedang aktif di foreground.

        Beberapa Android tidak lagi mengeluarkan mCurrentFocus lewat
        `dumpsys window windows`, jadi pakai fallback `dumpsys window` dan
        `dumpsys activity activities`.
        """
        outputs = []
        for cmd in (
            ["shell", "dumpsys", "window"],
            ["shell", "dumpsys", "window", "windows"],
            ["shell", "dumpsys", "activity", "activities"],
        ):
            out = self.run_adb(cmd, timeout=2.5)
            if out:
                outputs.append(out)

        result = "\n".join(outputs)
        patterns = [
            r'mCurrentFocus=Window\{[^}]+ ([^\s}]+/[^\s}]+)',
            r'mFocusedApp=.*?ActivityRecord\{[^}]+ ([^\s}]+/[^\s}]+)',
            r'mResumedActivity: ActivityRecord\{[^}]+ ([^\s}]+/[^\s}]+)',
            r'topResumedActivity=.*?ActivityRecord\{[^}]+ ([^\s}]+/[^\s}]+)',
        ]
        for pat in patterns:
            match = re.search(pat, result, re.S)
            if match:
                return match.group(1).lower()

        # Fallback kasar: cukup tahu package muncul di dump focus/activity.
        if PACKAGE_NAME.lower() in result.lower():
            return PACKAGE_NAME.lower()
        return ""
    
    def bring_game_to_foreground(self):
        """Bawa game ke foreground"""
        self.open_ad_after_game_open = True
        self.balance_report_sent_for_open = False
        self.run_adb(["shell", "am", "start", "-n", f"{PACKAGE_NAME}/com.coin.sortdash.remove.GameActivity"])
        time.sleep(0.17)
    
    def is_game_main_coin_box_page(self, img=None):
        """Cek apakah sudah benar kembali ke halaman utama game (koin + kotak)."""
        focus = self.get_foreground_focus().lower()
        if PACKAGE_NAME.lower() not in focus:
            return False

        img = img if img is not None else self.get_screenshot()
        text, _ = self.ocr_text(img)
        text = (text or "").lower()

        # Kalau masih activity/teks iklan, belum dianggap balik game.
        ad_activity_words = [
            "adactivity", "rewardvideo", "openadsdk", "ttreward", "pangle",
            "applovin", "mbridge", "mintegral", "vungle", "ironsource"
        ]
        if any(k in focus for k in ad_activity_words) or self.is_ad_like_screen(text, focus):
            return False

        # Kalau popup besar masih nutup halaman utama, jangan dianggap beres.
        blocking_popup_words = [
            "login sehari", "check-in", "menghapus", "petunjuk", "bebas",
            "gratis", "gagal", "failed", "tidak tersedia"
        ]
        if any(k in text for k in blocking_popup_words):
            return False

        # Halaman utama Coin Dash biasanya punya header saldo/menarik + level/tingkat.
        main_markers = ["tingkat", "menarik", "kurang", "penarikan", "rp"]
        if "gameactivity" in focus and any(k in text for k in main_markers):
            return True

        # Fallback: jika OCR gagal tapi fokus sudah GameActivity dan tidak ada indikasi iklan.
        return "gameactivity" in focus and not text

    def clean_restart_all_apps_and_game(self, reason="bottleneck"):
        """Bersihkan aplikasi di HP lalu buka game ulang jika stuck/bottleneck."""
        print(f"{self.tag} [🧹] BOTTLENECK: {reason}. Bersihkan aplikasi dan buka game ulang...", flush=True)
        focus_now = self.get_foreground_focus()
        log_event("bottleneck_recovery", reason, {"focus": focus_now})
        now_time = time.strftime("%H:%M:%S")
        close_msg = f"🧹 <b>TUTUP IKLAN / RESTART</b> <code>{now_time}</code>"
        send_telegram_async(close_msg)

        pkgs_to_stop = [
            PACKAGE_NAME,
            "com.android.vending", "com.google.android.gms",
            "com.android.chrome", "com.android.browser", "com.transsion.phoenix",
            "com.heytap.browser", "com.opera.browser", "com.opera.mini.native",
            "com.ss.android.ugc.trill", "com.zhiliaoapp.musically",
            "com.facebook.katana", "com.instagram.android",
            "com.shopee.id", "com.lazada.android", "com.tokopedia.tkpd",
            "com.taxsee.driver", "id.co.taximaxim.driver",
        ]
        for pkg in pkgs_to_stop:
            self.run_adb(["shell", "am", "force-stop", pkg], timeout=2.0)

        # Minta Android kill proses latar belakang yang bisa dikill, lalu kembali home.
        self.run_adb(["shell", "am", "kill-all"], timeout=3.0)
        self.run_adb(["shell", "input", "keyevent", "3"], timeout=2.0)
        time.sleep(0.12)

        self.bring_game_to_foreground()
        self.open_ad_after_game_open = True
        self.balance_report_sent_for_open = False
        self.last_forced_ad_open_attempt = 0
        time.sleep(0.35)

    def detect_game_screen(self):
        """Deteksi apakah game di layar"""
        focus = self.get_foreground_focus()
        # Debug
        if focus:
            print(f"{self.tag} [DEBUG] Focus: {focus[:100]}", flush=True)
        return PACKAGE_NAME.lower() in focus.lower()
    
    def play_game(self):
        """Main game - tap coins/objects"""
        # Tap di beberapa area untuk klik coin
        tap_points = [
            (int(360 * self.scale_x), int(800 * self.scale_y)),
            (int(200 * self.scale_x), int(700 * self.scale_y)),
            (int(520 * self.scale_x), int(700 * self.scale_y)),
            (int(360 * self.scale_x), int(900 * self.scale_y)),
        ]
        
        for x, y in tap_points:
            self.tap(x, y)
            time.sleep(0.017)
    
    def check_and_withdraw(self):
        """Jika saldo ≈Rp sudah >= MIN_WITHDRAW_RP, klik tombol ≈Rp untuk tarik dana."""
        now = time.time()
        if now - self.last_withdraw_click_ts < 20:
            return False

        saldo = self.read_current_reward_balance_rp(retries=2)
        if saldo is None:
            return False

        if saldo < MIN_WITHDRAW_RP:
            print(f"{self.tag} [💰] Saldo ≈Rp {saldo} belum cukup untuk tarik dana (min {MIN_WITHDRAW_RP}).", flush=True)
            return False

        self.last_withdraw_click_ts = now
        self.withdraw_confirm_count = 0
        x = int(245 * self.scale_x)
        y = int(92 * self.scale_y)
        print(f"{self.tag} [💸] Saldo ≈Rp {saldo} >= {MIN_WITHDRAW_RP}. Klik tombol ≈Rp untuk tarik dana di ({x},{y}).", flush=True)
        send_telegram_async(
            f"💸 <b>TARIK DANA</b>\n"
            f"🕐 <code>{time.strftime('%Y-%m-%d %H:%M:%S WIB')}</code>\n"
            f"💰 Saldo: <b>≈Rp {saldo}</b>"
        )
        log_event("tarik_dana_click", "Klik tombol ≈Rp untuk tarik dana", {"saldo": saldo, "x": x, "y": y})
        self.tap(x, y)
        time.sleep(0.23)
        return True
    
    def restart_game_after_withdraw_success(self):
        """Keluar game dan buka ulang setelah penarikan berhasil."""
        print(f"{self.tag} [✅] Penarikan berhasil terdeteksi (Rp0). Keluar game dan buka ulang...", flush=True)
        send_telegram_async(
            f"✅ <b>PENARIKAN BERHASIL</b>\n"
            f"🕐 <code>{time.strftime('%Y-%m-%d %H:%M:%S WIB')}</code>\n"
            f"💰 Saldo penarikan: Rp0"
        )
        log_event("penarikan_berhasil", "Saldo penarikan Rp0, restart game", {"confirm_count": self.withdraw_confirm_count})
        self.run_adb(["shell", "am", "force-stop", PACKAGE_NAME], timeout=2.0)
        self.run_adb(["shell", "input", "keyevent", "3"], timeout=2.0)
        time.sleep(0.12)
        self.open_ad_after_game_open = True
        self.balance_report_sent_for_open = False
        self.withdraw_confirm_count = 0
        self.last_forced_ad_open_attempt = 0
        self.bring_game_to_foreground()
        time.sleep(0.35)

    def handle_withdraw_success_zero_balance(self):
        """Jika setelah konfirmasi muncul Rp0/RpO, anggap tarik dana berhasil lalu restart game."""
        now = time.time()
        if now - self.last_withdraw_success_restart_ts < 20:
            return False

        focus = self.get_foreground_focus().lower()
        if "ptactivity" not in focus:
            return False

        img = self.get_screenshot()
        text, items = self.ocr_text(img)
        text_l = (text or "").lower()

        # OCR sering membaca Rp0 sebagai RpO/Rpo.
        zero_seen = bool(re.search(r"rp\s*[0o]", text_l, re.I)) or any(
            re.search(r"rp\s*[0o]", it.get("text", "").lower(), re.I) for it in items
        )
        success_context = any(k in text_l for k in [
            "jumlah penarikan minimum", "perlu dapatkan", "kurang", "bisa tarik tunai", "menarik"
        ])

        if zero_seen and (self.withdraw_confirm_count >= 3 or success_context):
            self.last_withdraw_success_restart_ts = now
            self.restart_game_after_withdraw_success()
            return True
        return False

    def handle_green_confirmation_popup(self):
        """Klik Konfirmasi hijau jika muncul popup konfirmasi lanjutan."""
        now = time.time()
        if now - self.last_green_confirm_click_ts < 8:
            return False

        focus = self.get_foreground_focus().lower()
        if PACKAGE_NAME.lower() not in focus:
            return False

        img = self.get_screenshot()
        text, items = self.ocr_text(img)
        text_l = (text or "").lower()
        if "konfirmasi" not in text_l:
            return False

        # 1) Utamakan OCR tulisan Konfirmasi yang berada di tombol hijau.
        for it in items:
            t = it.get("text", "").lower()
            cx = int(it.get("cx", 0))
            cy = int(it.get("cy", 0))
            if "konfirmasi" not in t:
                continue
            if cy < int(650 * self.scale_y):
                continue
            if img is not None and cv2 is not None:
                x1, x2 = max(0, cx-95), min(img.shape[1], cx+95)
                y1, y2 = max(0, cy-38), min(img.shape[0], cy+38)
                patch = img[y1:y2, x1:x2]
                if patch.size:
                    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
                    # Hijau OpenCV kira-kira H 35-95, saturasi cukup, terang.
                    mask = (hsv[:,:,0] >= 35) & (hsv[:,:,0] <= 95) & (hsv[:,:,1] > 70) & (hsv[:,:,2] > 80)
                    if float(mask.mean()) > 0.12:
                        self.last_green_confirm_click_ts = now
                        print(f"{self.tag} [✅] Popup konfirmasi hijau terdeteksi OCR. Klik ({cx},{cy}).", flush=True)
                        send_telegram_async(
                            f"✅ <b>KONFIRMASI HIJAU</b>\n"
                            f"🕐 <code>{time.strftime('%Y-%m-%d %H:%M:%S WIB')}</code>"
                        )
                        self.withdraw_confirm_count += 1
                        log_event("klik_konfirmasi_hijau", "Klik tombol Konfirmasi hijau", {"x": cx, "y": cy, "count": self.withdraw_confirm_count})
                        self.tap(cx, cy)
                        time.sleep(0.06)
                        return True

        # 2) Fallback visual: cari tombol hijau besar di setengah bawah layar.
        if img is not None and cv2 is not None:
            h, w = img.shape[:2]
            y_start = int(620 * self.scale_y)
            crop = img[y_start:h, :]
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            mask = ((hsv[:,:,0] >= 35) & (hsv[:,:,0] <= 95) & (hsv[:,:,1] > 75) & (hsv[:,:,2] > 90)).astype('uint8') * 255
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            best = None
            for c in cnts:
                x, y, bw, bh = cv2.boundingRect(c)
                area = cv2.contourArea(c)
                if area < 2500 or bw < 90 or bh < 35:
                    continue
                cy = y_start + y + bh//2
                cx = x + bw//2
                # Hindari icon kecil; tombol biasanya tengah/bawah.
                score = area - abs(cx - int(360*self.scale_x)) * 3
                if best is None or score > best[0]:
                    best = (score, cx, cy, bw, bh)
            if best:
                _, cx, cy, bw, bh = best
                self.last_green_confirm_click_ts = now
                print(f"{self.tag} [✅] Tombol hijau terdeteksi visual. Klik ({cx},{cy}).", flush=True)
                send_telegram_async(
                    f"✅ <b>KONFIRMASI HIJAU</b>\n"
                    f"🕐 <code>{time.strftime('%Y-%m-%d %H:%M:%S WIB')}</code>"
                )
                self.withdraw_confirm_count += 1
                log_event("klik_konfirmasi_hijau", "Klik tombol hijau visual", {"x": cx, "y": cy, "w": bw, "h": bh, "count": self.withdraw_confirm_count})
                self.tap(cx, cy)
                time.sleep(0.05)
                return True

        return False

    def handle_withdraw_confirmation(self):
        """Klik tombol Konfirmasi pada halaman input tarik dana."""
        now = time.time()
        if now - self.last_confirm_click_ts < 12:
            return False

        focus = self.get_foreground_focus().lower()
        img = self.get_screenshot()
        text, items = self.ocr_text(img)
        text_l = (text or "").lower()
        if not ("ptactivity" in focus and "konfirmasi" in text_l):
            return False

        candidates = []
        for it in items:
            t = it.get("text", "").lower()
            cx = int(it.get("cx", 0))
            cy = int(it.get("cy", 0))
            if "konfirmasi" in t and int(900 * self.scale_y) <= cy <= int(1320 * self.scale_y):
                candidates.append((abs(cx - int(360*self.scale_x)), cy, it))

        if candidates:
            candidates.sort(key=lambda v: (v[0], v[1]))
            it = candidates[0][2]
            x, y = int(it["cx"]), int(it["cy"])
        else:
            x, y = int(360 * self.scale_x), int(1208 * self.scale_y)

        self.last_confirm_click_ts = now
        print(f"{self.tag} [✅] Tombol Konfirmasi terdeteksi. Klik di ({x},{y}).", flush=True)
        send_telegram_async(
            f"✅ <b>KONFIRMASI TARIK</b>\n"
            f"🕐 <code>{time.strftime('%Y-%m-%d %H:%M:%S WIB')}</code>"
        )
        self.withdraw_confirm_count += 1
        log_event("klik_konfirmasi_tarik", "Klik tombol Konfirmasi tarik dana", {"x": x, "y": y, "count": self.withdraw_confirm_count})
        self.tap(x, y)
        time.sleep(0.23)
        return True

    def handle_withdraw_page(self):
        """Jika sudah masuk halaman Menarik/Tarik Dana, klik tombol Menarik oren yang valid."""
        now = time.time()
        if now - self.last_orange_menarik_click_ts < 15:
            return False

        focus = self.get_foreground_focus().lower()
        img = self.get_screenshot()
        text, items = self.ocr_text(img)
        text_l = (text or "").lower()

        is_withdraw_page = (
            "ptactivity" in focus
            or ("saldo saya" in text_l and "menarik" in text_l)
            or "saldo anda cukup untuk penarikan" in text_l
        )
        if not is_withdraw_page:
            return False

        candidates = []
        for it in items:
            t = it.get("text", "").lower()
            cx = int(it.get("cx", 0))
            cy = int(it.get("cy", 0))
            # Abaikan judul atas "Menarik". Ambil tombol nominal di kartu.
            if "menarik" in t and cy > int(850 * self.scale_y):
                # Prioritas baris paling atas, lalu kiri (DANA).
                candidates.append((cy, cx, it))

        if candidates:
            candidates.sort(key=lambda v: (v[0], v[1]))
            _, _, best = candidates[0]
            x, y = int(best["cx"]), int(best["cy"])
        else:
            # Fallback tombol Menarik pertama kiri atas pada halaman penarikan.
            x, y = int(200 * self.scale_x), int(1112 * self.scale_y)

        self.last_orange_menarik_click_ts = now
        print(f"{self.tag} [💸] Halaman Menarik terdeteksi. Klik tombol Menarik oren di ({x},{y}).", flush=True)
        send_telegram_async(
            f"💸 <b>KLIK MENARIK</b>\n"
            f"🕐 <code>{time.strftime('%Y-%m-%d %H:%M:%S WIB')}</code>"
        )
        log_event("klik_menarik_oren", "Klik tombol Menarik oren", {"x": x, "y": y, "focus": focus})
        self.tap(x, y)
        time.sleep(0.23)
        return True

    def handle_ads(self):
        """Handle iklan jika muncul"""
        focus = self.get_foreground_focus()
        img = self.get_screenshot()
        text, _ = self.ocr_text(img)
        if self.is_ad_like_screen(text, focus):
            self.wait_and_close_rewarded_ad("Layar iklan terdeteksi")
            return True

        if self.detect_and_click_reward_popup():
            return True
        
        # Deteksi iklan
        ad_keywords = ["ad", "rewarded", "interstitial", "applovin", "unity", "bytedance", "openadsdk", "ttreward", "pangle"]
        if any(k in focus for k in ad_keywords):
            self.wait_and_close_rewarded_ad("Activity iklan/focus iklan")
            return True
        
        return False
    
    def worker(self):
        """Main loop bot"""
        print(f"{self.tag} [+] Worker aktif untuk Coin Dash Shot!", flush=True)
        
        # Kirim notifikasi start
        start_msg = (
            f"🎮 <b>BOT COIN DASH SHOT STARTED</b>\n"
            f"📱 Device: <code>{self.serial}</code>\n"
            f"💰 Target: Rp {MIN_WITHDRAW_RP}\n"
            f"⏱️ <code>{time.strftime('%Y-%m-%d %H:%M:%S WIB')}</code>"
        )
        send_telegram_async(start_msg)
        log_event("bot_start", "Bot Coin Dash Shot dimulai", {"serial": self.serial})
        
        last_action_time = time.time()
        stuck_threshold = 30  # Deteksi stuck jika tidak ada aksi 30 detik
        
        while not self.stop_flag:
            try:
                # Cek apakah game di layar
                if not self.detect_game_screen():
                    print(f"{self.tag} [!] Game tidak di layar, membuka...", flush=True)
                    self.bring_game_to_foreground()
                    time.sleep(0.23)
                    continue
                
                # Handle popup Login sehari sebelum aksi lain.
                if self.handle_daily_login_popup():
                    last_action_time = time.time()
                    continue

                # Jika saldo penarikan sudah Rp0/RpO setelah konfirmasi, berarti berhasil: restart game.
                if self.handle_withdraw_success_zero_balance():
                    last_action_time = time.time()
                    continue

                # Jika muncul popup konfirmasi hijau setelah klik Konfirmasi, klik lagi.
                if self.handle_green_confirmation_popup():
                    last_action_time = time.time()
                    continue

                # Jika ada halaman konfirmasi tarik dana, klik Konfirmasi dulu.
                if self.handle_withdraw_confirmation():
                    last_action_time = time.time()
                    continue

                # Jika sudah di halaman tarik dana, klik tombol Menarik oren.
                if self.handle_withdraw_page():
                    last_action_time = time.time()
                    continue

                # Handle iklan jika ada
                if self.handle_ads():
                    last_action_time = time.time()
                    continue

                # Prioritas: kalau saldo ≈Rp sudah >= minimal, klik ≈Rp untuk tarik dana sebelum buka iklan lagi.
                if self.is_game_main_coin_box_page() and self.check_and_withdraw():
                    last_action_time = time.time()
                    continue

                # Setelah game baru dibuka/restart, langsung coba klik ikon iklan/video/Bebas.
                if self.open_ad_after_game_open and self.is_game_main_coin_box_page():
                    self.send_balance_report_before_ad()
                    if self.probe_reward_buttons(force=True):
                        last_action_time = time.time()
                        continue

                # Coba tombol reward video secara berkala. Kalau iklan no-fill,
                # bot akan menutup popup dan lanjut main level.
                if self.probe_reward_buttons():
                    last_action_time = time.time()
                    continue
                
                # Main game
                self.play_game()
                last_action_time = time.time()
                
                # Anti-stuck
                if time.time() - last_action_time > stuck_threshold:
                    print(f"{self.tag} [⚠️] Stuck terdeteksi, refresh game...", flush=True)
                    self.press_back()
                    time.sleep(0.06)
                    self.bring_game_to_foreground()
                    last_action_time = time.time()
                
                time.sleep(0.05)
                
            except KeyboardInterrupt:
                print(f"\n{self.tag} [!] Interrupted by user", flush=True)
                break
            except Exception as e:
                print(f"{self.tag} [!] Worker error: {e}", flush=True)
                time.sleep(0.23)
        
        print(f"{self.tag} [✔] Worker stopped", flush=True)

# ============= MAIN =============

def main():
    print("=" * 66, flush=True)
    print("   BOT COIN DASH SHOT - AUTO PLAY + WITHDRAW Rp 500", flush=True)
    print("=" * 66, flush=True)
    print(f"[+] Target Game: {PACKAGE_NAME}", flush=True)
    print(f"[+] Minimal Withdraw: Rp {MIN_WITHDRAW_RP}", flush=True)
    print(f"[+] Tekan Ctrl+C untuk berhenti.\n", flush=True)
    
    while True:
        devices = get_connected_devices()
        
        if not devices:
            print("[!] Tidak ada HP Android terhubung via ADB. Menunggu perangkat...", flush=True)
            time.sleep(5)
            continue
        
        for serial in devices:
            print(f"[+] Perangkat terdeteksi: {serial}", flush=True)
            bot = CoinDashShotBot(serial)
            
            try:
                bot.worker()
            except KeyboardInterrupt:
                print("\n[!] Stopping bot...", flush=True)
                sys.exit(0)
            except Exception as e:
                print(f"[!] Error: {e}", flush=True)
                time.sleep(5)

if __name__ == "__main__":
    main()
