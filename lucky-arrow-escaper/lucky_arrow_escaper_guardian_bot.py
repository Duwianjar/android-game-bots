#!/usr/bin/env python3
"""
Lucky Arrow Escaper Guardian Bot

Fitur utama:
- Deteksi foreground, buka game jika belum aktif
- Tutup Chrome/Play Store/app lain yang terbuka karena iklan
- Deteksi & klik tombol DOBEL/AMBIL reward / bubble iklan
- Deteksi & tutup iklan (UI dump, OCR, Hough circle arrow kanan atas, contour)
- Deteksi popup "Confirm to Close" -> klik Continue
- Cek saldo OCR periodik + lapor Telegram
- Fallback: BACK button & restart game

Target game:
  App     : Lucky Arrow Escaper
  Package : com.starlightgame.luckyarrowescaper
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

TARGET_PACKAGE = "com.starlightgame.luckyarrowescaper"
TARGET_NAME = "Lucky Arrow Escaper"
LOG_FILE = os.path.expanduser("~/lucky_arrow_escaper_guardian_bot.log")
STATE_FILE = os.path.expanduser("~/lucky_arrow_escaper_saldo_state.json")
OCR_HELPER = "/Users/macbookair/ocr_helper"
TAP_MARKER = "/Users/macbookair/scrcpy_tap_marker"
TELEGRAM_SENDER = "/Users/macbookair/telegram_sender.py"
REWARD_HISTORY_FILE = os.path.expanduser("~/lucky_arrow_reward_history.json")
MIN_REWARD_THRESHOLD = float(os.environ.get("LUCKY_ARROW_MIN_REWARD", "5.0"))
MIN_AD_WATCH_SECONDS = float(os.environ.get("LUCKY_ARROW_MIN_AD_WATCH", "60.0"))
MAX_BUKA_AD_ATTEMPTS = 3
BUKA_AD_COOLDOWN_SECONDS = 15 * 60

CHEAP_AD_KEYWORDS = (
    "shopee", "tiktok", "lazada", "tokopedia", "install", "unduh", "pasang",
    "google play", "play store", "buka toko", "open store",
    "block", "blast", "puzzle", "match 3", "merge", "solitaire", "bubble shooter",
    "candy", "fish", "farm", "woody", "woodland", "tile match",
)

HIGH_TIER_AD_KEYWORDS = (
    "dewi", "pgtoto", "mposport", "slot", "taruhan", "deposit", "spin", "jackpot",
    "gacor", "pragmatic", "pg soft", "pgsoft", "olympus", "mahjong", "maxwin", "zeus",
    "casino", "poker", "roulette", "baccarat", "judi", "starlight princess",
    "emas", "meta", "kwai", "alliance", "saldo gratis", "klaim bonus", "bonus saldo", "bonus deposit",
    "dana", "gopay", "fintech", "pinjaman", "investasi", "trading", "crypto",
)

BLOCKED_PACKAGES = {
    "com.android.vending": "Play Store",
    "com.android.chrome": "Chrome",
    "com.chrome.beta": "Chrome Beta",
    "com.google.android.apps.chrome": "Chrome",
    "com.shopee.id": "Shopee",
    "com.shopee.app": "Shopee",
    "com.transsnet.store": "Palm Store",
    "com.transsion.XOSLauncher": "Launcher",
    "com.android.settings": "Settings",
    "com.google.android.youtube": "YouTube",
    "com.facebook.katana": "Facebook",
    "com.instagram.android": "Instagram",
}

AD_KEYWORDS = (
    "ads", "adactivity", "adplayer", "advert", "reward", "rewardvideo", "rewarded",
    "mbridge", "mintegral", "applovin", "vungle", "ironsource", "chartboost",
    "gms.ads", "adcolony", "pangle", "bytedance", "kwai", "fullscreenwebview",
    "webviewdisplay", "alliance", "adcommon", "emptyshell", "ksad",
)

REWARD_WORDS = (
    "claim", "get", "watch", "double", "dobel", "x2", "collect", "reward", "video",
    "ambil", "buka", "klaim", "dapat", "tonton", "bonus", "gratis", "lanjut", "next", "continue",
    "not now", "now not", "nanti", "tidak",
)

CLOSE_WORDS = (
    "x", "\u00d7", "close", "tutup", "skip", "lewati", "next", "lanjut", ">", "\u203a", "\u00bb",
)

STORE_WORDS = ("install", "instal", "pasang", "google play", "play store", "shopee", "buka toko", "open store")


@dataclass
class ForegroundApp:
    package: str
    activity: str = ""
    raw: str = ""


class Bot:
    def __init__(self, serial: str = "", interval: float = 0.08):
        if not serial:
            serial = "062322513B000705"
        self.serial = serial.strip()
        self.interval = interval
        self.last_fg = ""
        self.last_launch_ts = 0.0
        self.ad_start_ts: Optional[float] = None
        self.ad_activity = ""
        self.last_ad_close_tap_ts = 0.0
        self.last_ad_check_ts = 0.0
        self.ad_stuck_count = 0
        self.ad_stuck_activity = ""
        self.last_top_right_arrow_tap_ts = 0.0
        self.last_reward_tap_ts = 0.0
        self.last_saldo_check_ts = 0.0
        self.last_external_ts = 0.0
        self.last_gameplay_tap_ts = 0.0
        self.last_bubble_tap_ts = 0.0
        self.last_cache_clear_ts = 0.0
        self.dobel_consecutive_clicks = 0
        self.buka_consecutive_clicks = 0
        self.buka_ad_cooldown_until = 0.0
        self.pre_ad_saldo: Optional[float] = None
        self.post_ad_saldo: Optional[float] = None
        self.was_dobel_clicked: bool = False
        self.pending_ad_verification: bool = False
        self.current_ad_tier = "UNKNOWN"
        self.current_ad_network = "Meta Audience Network"
        self.current_ad_title = "Unknown"
        self.current_ad_match = "-"
        self.ad_title_confirmed = False
        self.last_reported_saldo: Optional[float] = None
        self.was_in_ad: bool = False

    # ===================== LOGGING =====================

    def log(self, msg: str) -> None:
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line, flush=True)
        if os.environ.get("LUCKY_ARROW_NO_FILE_LOG") == "1":
            return
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    # ===================== ADB HELPERS =====================

    def adb_cmd(self, args: list[str]) -> list[str]:
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        return cmd + args

    def adb_out(self, args: list[str], timeout: int = 10) -> str:
        try:
            r = subprocess.run(self.adb_cmd(args), capture_output=True, text=True, timeout=timeout)
            return r.stdout or ""
        except BaseException as exc:
            self.log(f"ADB error: {' '.join(args)} | {type(exc).__name__}: {exc}")
            return ""

    def adb_bytes(self, args: list[str], timeout: int = 10) -> bytes:
        try:
            r = subprocess.run(self.adb_cmd(args), capture_output=True, timeout=timeout)
            return r.stdout or b""
        except BaseException as exc:
            self.log(f"ADB bytes error: {' '.join(args)} | {type(exc).__name__}: {exc}")
            return b""

    def tap(self, x: int, y: int, natural: bool = True) -> None:
        if natural:
            jx = max(10, x + random.randint(-7, 7))
            jy = max(10, y + random.randint(-7, 7))
        else:
            jx, jy = x, y
        self.show_tap_marker([(int(jx), int(jy), "blue", 1.3, 58)])
        self.log(f"TAP ({jx},{jy})")
        self.adb_out(["shell", "input", "tap", str(int(jx)), str(int(jy))], timeout=4)
        if natural:
            time.sleep(random.uniform(0.08, 0.22))

    # ===================== TAP MARKER =====================

    def show_tap_marker(self, specs: list) -> None:
        if not os.path.exists(TAP_MARKER) or os.environ.get("LUCKY_ARROW_DISABLE_MARKER") == "1":
            return
        args: list[str] = []
        for x, y, color, duration, diameter in specs[:220]:
            args += [str(int(x)), str(int(y)), color, str(float(duration)), str(int(diameter))]
        try:
            subprocess.Popen([TAP_MARKER, *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    # ===================== FOREGROUND DETECTION =====================

    @staticmethod
    def parse_package_activity(text: str) -> Optional[ForegroundApp]:
        patterns = [
            r"u\d+\s+([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)/([^\s}\]]+)",
            r"([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)/([a-zA-Z0-9_.$]+)",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return ForegroundApp(m.group(1), m.group(2), text.strip())
        return None

    def foreground(self) -> Optional[ForegroundApp]:
        checks = [
            (["shell", "dumpsys", "window", "displays"], ("mCurrentFocus",)),
            (["shell", "dumpsys", "activity", "activities"], ("topResumedActivity", "mResumedActivity")),
            (["shell", "dumpsys", "window", "displays"], ("mFocusedApp",)),
            (["shell", "dumpsys", "activity", "top"], ("ACTIVITY",)),
        ]
        for args, keywords in checks:
            out = self.adb_out(args, timeout=6)
            in_last_anr = False
            for line in out.splitlines():
                if "Last ANR" in line:
                    in_last_anr = True
                    continue
                if in_last_anr:
                    if not line.startswith(" ") and not line.startswith("\t"):
                        in_last_anr = False
                    else:
                        continue
                if any(keyword in line for keyword in keywords):
                    app = self.parse_package_activity(line)
                    if app:
                        return app
        return None

    def verify_still_in_game(self) -> bool:
        app = self.foreground()
        if not app:
            self.launch_game("verifikasi: foreground hilang")
            return False
        if app.package != TARGET_PACKAGE:
            self.launch_game(f"verifikasi: foreground={app.package}")
            return False
        if self.is_ad(app):
            return False
        return True

    # ===================== SCREEN / CAPTURE / UI DUMP =====================

    def screen_size(self) -> Tuple[int, int]:
        out = self.adb_out(["shell", "wm", "size"], timeout=4)
        m = re.search(r"(\d+)x(\d+)", out)
        return (int(m.group(1)), int(m.group(2))) if m else (720, 1600)

    def capture_png(self):
        png = self.adb_bytes(["exec-out", "screencap", "-p"], timeout=8)
        if not png or len(png) < 1000:
            return None
        try:
            from PIL import Image
            from io import BytesIO
            image = Image.open(BytesIO(png))
            w, h = image.size
            return png, w, h
        except Exception:
            w, h = self.screen_size()
            return png, w, h

    def dump_ui(self):
        self.adb_out(["shell", "uiautomator", "dump", "/sdcard/luckyarrow_ui.xml"], timeout=5)
        xml = self.adb_out(["shell", "cat", "/sdcard/luckyarrow_ui.xml"], timeout=5)
        if "<hierarchy" not in xml:
            return None
        try:
            return ET.fromstring(xml)
        except Exception:
            return None

    @staticmethod
    def norm(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").lower().strip())

    @staticmethod
    def bounds_center(bounds: str):
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
        if not m:
            return None
        x1, y1, x2, y2 = map(int, m.groups())
        return (x1 + x2) // 2, (y1 + y2) // 2, x1, y1, x2, y2

    # ===================== OCR =====================

    def ocr_screen(self, prefix: str) -> list:
        if not os.path.exists(OCR_HELPER):
            return []
        cap = self.capture_png()
        if not cap:
            return []
        png, w, h = cap
        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
        path = f"/tmp/luckyarrow_{prefix}_{safe_serial}.png"
        try:
            with open(path, "wb") as f:
                f.write(png)
        except Exception:
            return []
        try:
            r = subprocess.run([OCR_HELPER, path], capture_output=True, text=True, timeout=10)
            raw = r.stdout or ""
        except Exception:
            return []
        entries = []
        for line in raw.strip().splitlines():
            text, _, bbox = line.partition("|")
            text = text.strip()
            bbox = bbox.strip()
            if not text or not bbox:
                continue
            try:
                bx, by, bw, bh = [float(p) for p in bbox.split(",")]
                x = int((bx + bw / 2) * w)
                y = int((1.0 - by - bh / 2) * h)
            except Exception:
                x, y = w // 2, h // 2
            entries.append((text, x, y, bbox))
        return entries

    # ===================== GAME LAUNCH =====================

    def clear_ad_cache(self) -> None:
        """Bersihkan cache iklan usang (termasuk 114MB video MBridge & Unity) agar SDK mediasi melelang iklan video baru bernilai tinggi (Meta & Kwai)."""
        try:
            self.adb_out(["shell", "rm -rf /sdcard/Android/data/com.starlightgame.luckyarrowescaper/files/mb/res/Movies/mb/res/.MBridge_VC/* /sdcard/Android/data/com.starlightgame.luckyarrowescaper/files/mb/res/.mbridge700/* /sdcard/Android/data/com.starlightgame.luckyarrowescaper/cache/kwaiadsdk/* /sdcard/Android/data/com.starlightgame.luckyarrowescaper/cache/UnityAdsCache/* 2>/dev/null"], timeout=3)
            self.adb_out(["shell", "settings put system pointer_location 0"], timeout=3)
        except Exception:
            pass

    def launch_game(self, reason: str = "", hard_restart: bool = False) -> None:
        if hard_restart:
            self.clear_ad_cache()
        now = time.time()
        if now - self.last_launch_ts < 3:
            return
        self.last_launch_ts = now
        self.log(f"BUKA GAME: {reason or 'ensure foreground'}{' [HARD]' if hard_restart else ''}")
        for pkg in BLOCKED_PACKAGES:
            self.adb_out(["shell", "am", "force-stop", pkg], timeout=3)
        if hard_restart:
            self.log("HARD RESTART: force-stop game dan tunggu 3 detik")
            self.adb_out(["shell", "am", "force-stop", TARGET_PACKAGE], timeout=5)
            time.sleep(3)
        self.adb_out(["shell", "monkey", "-p", TARGET_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"], timeout=6)
        time.sleep(0.4 if not hard_restart else 2)
        app = self.foreground()
        if not app or app.package != TARGET_PACKAGE:
            self.adb_out(["shell", "am", "start", "-n", f"{TARGET_PACKAGE}/.AppActivity"], timeout=6)
        self.ad_start_ts = None
        self.ad_title_confirmed = False

    def is_ad(self, app: ForegroundApp) -> bool:
        if app.package != TARGET_PACKAGE:
            return False
        low = f"{app.package}/{app.activity}".lower()
        return any(k in low for k in AD_KEYWORDS)

    # ===================== CONFIRM TO CLOSE POPUP =====================

    def find_continue_on_close_confirm(self):
        confirm_words = (
            "confirm to close", "not be rewarded", "will not be rewarded",
            "after closing", "closing the window",
        )
        continue_words = ("continue", "lanjut", "lanjutkan")

        entries = self.ocr_screen("confirm_continue")
        labels = [self.norm(text) for text, *_ in entries]
        if not any(any(word in label for word in confirm_words) for label in labels):
            return None
        candidates = []
        for text, x, y, _bbox in entries:
            n = self.norm(text)
            if any(word == n or word in n for word in continue_words):
                candidates.append((text, x, y, "ocr"))
        if not candidates:
            return None
        return sorted(candidates, key=lambda c: (-c[1], c[2]))[0]

    # ===================== HOUGH CIRCLE TOP-RIGHT (X / ARROW) =====================

    def find_ad_top_corner_button(self):
        """Deteksi tombol close/next iklan di pojok kanan atas via Hough circle & contour."""
        cap = self.capture_png()
        if not cap:
            return None
        png, width, height = cap
        try:
            import cv2
            import numpy as np
        except Exception:
            return None
        img = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return None

        # --- Hough circle di kanan atas ---
        try:
            rx1 = int(width * 0.72)
            ry1 = max(45, int(height * 0.030))
            ry2 = int(height * 0.170)
            roi = img[ry1:ry2, rx1:width]
            if roi.size:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                gray_blur = cv2.medianBlur(gray, 5)
                circles = cv2.HoughCircles(
                    gray_blur,
                    cv2.HOUGH_GRADIENT,
                    dp=1.2,
                    minDist=35,
                    param1=80,
                    param2=18,
                    minRadius=20,
                    maxRadius=45,
                )
                circle_candidates = []
                if circles is not None:
                    for cx, cy, radius in np.round(circles[0, :]).astype(int):
                        abs_x = rx1 + int(cx)
                        abs_y = ry1 + int(cy)
                        r = int(radius)
                        # Tombol X kanan atas tidak boleh menempel tepi border layar (lebar 720)
                        if abs_x < width * 0.78 or abs_x > width - 25:
                            continue
                        if abs_y < max(60, int(height * 0.035)) or abs_y > height * 0.16:
                            continue
                        patch = gray[
                            max(0, cy - r): min(gray.shape[0], cy + r),
                            max(0, cx - r): min(gray.shape[1], cx + r),
                        ]
                        if patch.size == 0:
                            continue
                        mean_gray = float(patch.mean())
                        if not (35 <= mean_gray <= 145):
                            continue
                        # Tap tepat di pusat lingkaran tombol tanpa digeser ke bawah
                        tap_x = abs_x
                        tap_y = abs_y
                        score = (abs_x / width) * 3000 + r * 40 - abs(abs_y - 115) * 8 - mean_gray
                        circle_candidates.append(
                            (score, tap_x, tap_y, f"hough circle r={r} mean={mean_gray:.1f} center=({abs_x},{abs_y})")
                        )
                if circle_candidates:
                    circle_candidates.sort(reverse=True)
                    _score, x, y, label = circle_candidates[0]
                    return "PANAH_KANAN/TOP", label, int(x), int(y)
        except Exception:
            pass

        # --- Contour fallback di kanan atas & kiri atas (hanya area status/header bar) ---
        search_h = int(height * 0.12)
        areas = [
            (int(width * 0.70), int(height * 0.025), width, search_h, "kanan-atas"),
            (0, int(height * 0.025), int(width * 0.25), search_h, "kiri-atas"),
        ]
        candidates = []
        for ax1, ay1, ax2, ay2, area_name in areas:
            roi = img[ay1:ay2, ax1:ax2]
            if roi.size == 0:
                continue
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            dark = cv2.inRange(gray, 35, 135)
            kernel = np.ones((3, 3), np.uint8)
            dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel)
            dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, kernel, iterations=2)
            contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h_c = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                if area < 450 or area > 6500:
                    continue
                if w < 25 or h_c < 25 or w > 95 or h_c > 95:
                    continue
                aspect = w / float(h_c)
                if aspect < 0.5 or aspect > 2.0:
                    continue
                abs_x = ax1 + x + w // 2
                abs_y = ay1 + y + h_c // 2
                priority = 2 if area_name == "kanan-atas" else 1
                score = priority * 1000 + area
                candidates.append((score, abs_x, abs_y, f"contour-{area_name} area={int(area)} size={w}x{h_c}"))
        if candidates:
            candidates.sort(reverse=True)
            _score, x, y, label = candidates[0]
            return "X_BUTTON", label, int(x), int(y)

        return None

    # ===================== ARROW ICON TOP RIGHT (HSV) =====================

    def find_top_right_arrow_button(self):
        cap = self.capture_png()
        if not cap:
            return None
        png, w, h = cap
        try:
            import cv2
            import numpy as np
        except Exception:
            return None
        img = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return None

        x_min = int(w * 0.80)
        y_min = 0
        y_max = int(h * 0.18)
        roi = img[y_min:y_max, x_min:w]
        if roi.size == 0:
            return None

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        dark = cv2.inRange(hsv, (80, 35, 15), (145, 255, 155))
        white = cv2.inRange(hsv, (0, 0, 175), (179, 90, 255))
        if cv2.countNonZero(dark) < 350:
            return None

        contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if area < 40 or area > 3000:
                continue
            bx, by, bw, bh = cv2.boundingRect(c)
            cx = x_min + bx + bw // 2
            cy = y_min + by + bh // 2
            return "arrow_icon", cx, cy, "cv2"
        return None

    # ===================== CLOSE BUTTON (UI + OCR) =====================

    def find_close_button(self):
        w, h = self.screen_size()
        entries = self.ocr_screen("close")
        for text, x, y, bbox in entries:
            n = self.norm(text)
            if any(sw in n for sw in STORE_WORDS):
                continue
            if n in ("x", "\u00d7") or any(t in n for t in ("close", "tutup", "skip", "lewati")):
                return text, x, y, "ocr"
        return None

    # ===================== AD HANDLING =====================

    def detect_ad_network(self, activity: str) -> str:
        act = (activity or "").lower()
        if "audiencenetwork" in act or "facebook" in act:
            return "Meta Audience Network"
        if "alliance" in act or "kwai" in act or "ksad" in act:
            return "Kwai Ads (Alliance)"
        if "applovin" in act:
            return "AppLovin MAX"
        if "gms.ads" in act or "google" in act:
            return "Google AdMob"
        if "unity3d" in act or "unityads" in act:
            return "Unity Ads"
        if "mbridge" in act or "mintegral" in act:
            return "Mintegral (MBridge)"
        if "pangle" in act or "bytedance" in act:
            return "Pangle (ByteDance)"
        if "ironsource" in act:
            return "ironSource"
        if "vungle" in act:
            return "Vungle"
        return activity.split(".")[-1] if activity else "Unknown Network"

    def analyze_ad_screen(self, app: ForegroundApp) -> tuple:
        """Menganalisis layar iklan untuk mengekstrak Asal Network, Judul/App, Matched Keywords, dan Kategori Tier."""
        network = self.detect_ad_network(app.activity)

        entries = self.ocr_screen("ad_classify")
        all_text = " ".join(t[0].lower() for t in entries)

        # Deteksi sub-network jika ada label Mintegral atau Unity di layar
        if "mintegral" in all_text and "mintegral" not in network.lower():
            network = f"{network} (Mintegral)"
        elif "unity" in all_text and "unity" not in network.lower():
            network = f"{network} (Unity)"

        matched_high = [w for w in HIGH_TIER_AD_KEYWORDS if w in all_text]
        matched_cheap = [w for w in CHEAP_AD_KEYWORDS if w in all_text]

        ignore_words = {
            "ad", "ads", "iklan", "buka", "open", "install", "instal", "pasang", "download",
            "unduh", "google play", "play store", "free", "gratis", "skip", "lewati", "close",
            "tutup", "lanjut", "continue", "privacy", "kebijakan", "terms", "aturan", "detik",
            "seconds", "level", "moves", "hint", "sound", "restart", "reward", "hadiah", "x", "x2",
            "penarikan", "saldo", "dana", "gopay", "dobel", "ambil", "claim", "confirm", "ok", "oke",
            "result", "guaranteed", "amount", "app", "just", "for", "you", "memasang", "cash out",
            "tarik tunai", "progres", "klaim hadiah",
        }

        candidates = []
        for text, x, y, _bbox in entries:
            clean = text.strip()
            clean_lower = clean.lower()
            if len(clean) < 3 or len(clean) > 40:
                continue
            if re.match(r"^[\d\s.,:;/\-—$€Rp%!()+]+$", clean):
                continue
            if re.search(r"\b\d+\s*s\b|left to be|reward in|rewarded|tersisa|to be rewarded", clean_lower):
                continue
            if any(iw == clean_lower or clean_lower.startswith(iw + " ") for iw in ignore_words):
                continue
            if any(p in clean_lower for p in ("google play", "play store", "ad 1 of", "ad 2 of", "ad 3 of", "iklan 1 dari")):
                continue
            candidates.append(clean)

        title = candidates[0] if candidates else ""
        if not title:
            for text, *_ in entries:
                t_clean = text.strip()
                if len(t_clean) >= 3 and not re.match(r"^[\d\s.,:;/\-—$€Rp%!()+]+$", t_clean):
                    if not any(t_clean.lower().startswith(iw) for iw in ("ad 1", "ad 2", "iklan 1")):
                        title = t_clean
                        break

        if not title:
            title = network

        act_lower = app.activity.lower()
        if matched_high:
            tier = "HIGH_TIER"
            matched_str = f"HIGH:[{','.join(matched_high[:3])}]"
        elif matched_cheap:
            tier = "CHEAP"
            matched_str = f"CHEAP:[{','.join(matched_cheap[:3])}]"
        elif "unity3d" in act_lower or "mbridge" in act_lower:
            tier = "CHEAP"
            matched_str = f"DEFAULT_CHEAP:({network})"
        else:
            tier = "HIGH_TIER"
            matched_str = f"DEFAULT_HIGH:({network})"

        return network, title, matched_str, tier

    def classify_ad_quality(self, app: ForegroundApp) -> str:
        network, title, matched_str, tier = self.analyze_ad_screen(app)
        self.current_ad_network = network
        self.current_ad_title = title
        self.current_ad_match = matched_str
        self.current_ad_tier = tier
        return tier

    def try_close_ad(self, app: ForegroundApp) -> None:
        now = time.time()
        if self.ad_start_ts is None or self.ad_activity != app.activity:
            self.ad_start_ts = now
            self.ad_activity = app.activity
            self.ad_title_confirmed = False
            network, title, matched_str, tier = self.analyze_ad_screen(app)
            self.current_ad_network = network
            self.current_ad_title = title
            self.current_ad_match = matched_str
            self.current_ad_tier = tier
            short_act = app.activity.split(".")[-1]
            self.log(f"IKLAN TERBUKA: Asal: {network} | Iklan/App: \"{title}\" | Match: {matched_str} | Kategori: {tier} | Act: {short_act}")
            return
        elapsed = now - self.ad_start_ts
        if now - self.last_ad_check_ts < 2:
            return
        self.last_ad_check_ts = now

        # Perbarui judul & klasifikasi iklan setelah video merender (detik ke-3)
        if elapsed >= 3.0 and not self.ad_title_confirmed:
            self.ad_title_confirmed = True
            network, title, matched_str, tier = self.analyze_ad_screen(app)
            if title and title != network:
                self.current_ad_title = title
            self.current_ad_network = network
            self.current_ad_match = matched_str
            self.current_ad_tier = tier

        target_watch = 5.0 if self.current_ad_tier == "CHEAP" else MIN_AD_WATCH_SECONDS
        mode_label = "IKLAN MURAH (Fast Skip 5s)" if self.current_ad_tier == "CHEAP" else f"IKLAN MAHAL (Retensi {MIN_AD_WATCH_SECONDS:.0f}s)"
        short_act = app.activity.split(".")[-1]
        self.log(f"IKLAN DITONTON [{mode_label}]: Asal: {self.current_ad_network} | Iklan: \"{self.current_ad_title}\" | Match: {self.current_ad_match} | Act: {short_act} | durasi {elapsed:.0f}s / target {target_watch:.0f}s")

        # 0) OVERTIME WATCHDOG: jika iklan melebihi target + 20s (misal > 80s), paksa restart game!
        if elapsed > (target_watch + 20):
            self.log(f"IKLAN STUCK OVERTIME ({elapsed:.0f}s > {target_watch:.0f}s+20) -> RESTART GAME")
            self.launch_game(f"iklan overtime {elapsed:.0f}s", hard_restart=True)
            return

        # Jika iklan mahal/slot: tonton utuh. Jika iklan murah (shopee/game): lewati cepat di detik ke-5!
        if elapsed < target_watch:
            return

        # 1) Popup "Confirm to Close" -> klik Continue
        keep_watching = self.find_continue_on_close_confirm()
        if keep_watching and now - self.last_ad_close_tap_ts >= 2.5:
            label, x, y, src = keep_watching
            self.last_ad_close_tap_ts = now
            self.log(f"POPUP CONFIRM TO CLOSE: klik '{label}' di ({x},{y}) via {src} | durasi {elapsed:.0f}s")
            self.tap(x, y)
            return

        # 2) UI Automator Close view (Meta / Kwai / Unity native X / close view di top 18%)
        root = self.dump_ui()
        if root is not None and now - self.last_ad_close_tap_ts >= 2.0:
            w, h = self.screen_size()
            for node in root.iter("node"):
                b = self.bounds_center(node.get("bounds", ""))
                if not b:
                    continue
                cx, cy, x1, y1, x2, y2 = b
                if cy > int(h * 0.18):
                    continue
                desc = (node.get("content-desc") or node.get("resource-id") or node.get("text") or "").lower()
                if any(k in desc for k in ("close", "tutup", "skip", "dismiss", "x")) or (node.get("clickable") == "true" and cy < int(h * 0.12)):
                    self.last_ad_close_tap_ts = now
                    self.log(f"UI AUTOMATOR CLOSE: klik '{desc}' di ({cx},{cy}) | durasi {elapsed:.0f}s")
                    self.tap(cx, cy)
                    return

        # 3) Close button via OCR (X, close, skip, lewati)
        found = self.find_close_button()
        if found and now - self.last_ad_close_tap_ts >= 2.0:
            label, x, y, src = found
            self.last_ad_close_tap_ts = now
            self.log(f"TUTUP IKLAN: '{label}' di ({x},{y}) via {src} | durasi {elapsed:.0f}s")
            self.tap(x, y)
            return

        # 4) Hough circle + contour di pojok kanan atas
        top_corner = self.find_ad_top_corner_button()
        if top_corner and now - self.last_top_right_arrow_tap_ts >= 2.5:
            kind, label, x, y = top_corner
            self.last_top_right_arrow_tap_ts = now
            self.last_ad_close_tap_ts = now
            self.log(f"MENEMUKAN TOMBOL SELESAI IKLAN: {kind} '{label}' di ({x},{y}) | durasi {elapsed:.0f}s")
            self.tap(x, y)
            return

        # 5) Arrow icon HSV di kanan atas
        arrow = self.find_top_right_arrow_button()
        if arrow and now - self.last_top_right_arrow_tap_ts >= 2.5:
            label, x, y, src = arrow
            self.last_top_right_arrow_tap_ts = now
            self.last_ad_close_tap_ts = now
            self.log(f"IKON ARAH KANAN ATAS: klik '{label}' di ({x},{y}) via {src} | durasi {elapsed:.0f}s")
            self.tap(x, y)
            return

        # 6) DIRECT CORNER TAP + BACK FALLBACK (Khusus Meta Audience Network & rewarded video):
        # Jika durasi iklan sudah terpenuhi (target_watch + 3s), tap koordinat paten X pojok atas & tekan BACK
        if elapsed >= (target_watch + 3) and now - self.last_ad_close_tap_ts >= 2.0:
            self.last_ad_close_tap_ts = now
            w, h = self.screen_size()
            meta_top_right_x = int(w * 0.92)  # ≈ 662 pada 720
            meta_top_right_y = int(h * 0.055) # ≈ 90 pada 1640
            self.log(f"FALLBACK CLOSE ({elapsed:.0f}s >= {target_watch:.0f}s+3): tap pojok kanan atas ({meta_top_right_x},{meta_top_right_y}) & BACK")
            self.tap(meta_top_right_x, meta_top_right_y)
            time.sleep(0.3)
            self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
            return

        # 7) Iklan stuck overtime (> target_watch + 18s) -> restart game
        if elapsed > (target_watch + 18):
            self.log(f"IKLAN STUCK OVERTIME ({elapsed:.0f}s > {target_watch:.0f}s+18) -> restart game")
            self.launch_game(f"iklan stuck {elapsed:.0f}s", hard_restart=True)
            return

    # ===================== SALDO =====================

    def parse_rupiah(self, text: str):
        low = text.lower()
        # Abaikan debug overlay pointer location
        if any(ign in low for ign in ("size:", "dx:", "dy:", "prs:", "xv:", "yv:", "p:")):
            return None
        if "rp" not in low:
            return None
        m = re.search(r"rp\s*([0-9][0-9.,]*)", text, re.I)
        if not m:
            return None
        raw = m.group(1)
        try:
            if "," in raw and "." in raw:
                return float(raw.replace(".", "").replace(",", "."))
            elif "," in raw:
                return float(raw.replace(",", "."))
            return float(raw)
        except Exception:
            return None

    @staticmethod
    def rupiah(v: float) -> str:
        s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"Rp {s}"

    def get_current_saldo(self) -> Optional[float]:
        w, h = self.screen_size()
        entries = self.ocr_screen("get_saldo")
        candidates = []
        for text, x, y, bbox in entries:
            if y > int(h * 0.28):
                continue
            val = self.parse_rupiah(text)
            if val is not None and val > 10.0:
                candidates.append((y, val, text.strip()))
        if not candidates:
            return None
        candidates.sort(key=lambda c: c[0])
        return candidates[0][1]

    def record_verified_reward(self, delta: float, pre: float, post: float, action: str, mode: str, network: str, ad_title: str = "") -> None:
        try:
            history = []
            if os.path.exists(REWARD_HISTORY_FILE):
                try:
                    with open(REWARD_HISTORY_FILE, "r") as f:
                        history = json.load(f)
                except Exception:
                    history = []

            now_ts = time.time()
            ad_note = f"Hadiah riil selisih saldo (+Rp {delta:,.2f}) mode {mode} jaringan {network}"
            if ad_title and ad_title != "-":
                ad_note += f" [Iklan: {ad_title}]"
            new_entry = {
                "timestamp": now_ts,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB"),
                "amount": delta,
                "amount_display": f"Rp {delta:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "pre_saldo": pre,
                "post_saldo": post,
                "is_dobel": "dobel" in mode.lower(),
                "action": action,
                "network": network,
                "ad_title": ad_title,
                "note": ad_note,
            }
            history.append(new_entry)
            with open(REWARD_HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as exc:
            self.log(f"Gagal simpan verified reward: {exc}")

    def verify_reward_payout(self) -> None:
        current_saldo = self.get_current_saldo()
        if current_saldo is None:
            time.sleep(1.0)
            current_saldo = self.get_current_saldo()
        if current_saldo is None:
            return

        if self.pre_ad_saldo is not None:
            delta = round(current_saldo - self.pre_ad_saldo, 2)
            mode_str = "DOBEL (2x)" if self.was_dobel_clicked else "SINGLE (1x)"
            action_str = "CLAIMED_DOBEL" if self.was_dobel_clicked else "CLAIMED_SINGLE"
            ad_net = getattr(self, "current_ad_network", "Unknown Network") or "Unknown Network"
            ad_title = getattr(self, "current_ad_title", "-") or "-"

            if delta > 0.0:
                self.log(f"[HADIAH IKLAN TERVERIFIKASI] +Rp {delta:,.2f} | Saldo: Rp {self.pre_ad_saldo:,.2f} -> Rp {current_saldo:,.2f} | Mode: {mode_str} | Asal: {ad_net} | Iklan: \"{ad_title}\"")
                self.record_verified_reward(delta, self.pre_ad_saldo, current_saldo, action_str, mode_str, ad_net, ad_title)
                self.send_telegram(f"[{TARGET_NAME}] Hadiah Terverifikasi: +Rp {delta:,.2f} ({mode_str})\nSaldo: Rp {self.pre_ad_saldo:,.2f} -> Rp {current_saldo:,.2f}\nAsal: {ad_net}\nIklan: {ad_title}")
            else:
                self.log(f"[INFO SALDO] Saldo: Rp {current_saldo:,.2f} (delta=0) setelah nonton iklan {ad_net} ({ad_title})")

        self.pre_ad_saldo = current_saldo
        self.pending_ad_verification = False
        self.was_dobel_clicked = False

    def check_saldo(self, reason: str) -> None:
        w, h = self.screen_size()
        entries = self.ocr_screen("saldo")
        candidates = []
        for text, x, y, bbox in entries:
            if y > int(h * 0.28):
                continue
            val = self.parse_rupiah(text)
            if val is not None and val > 10.0:
                candidates.append((y, val, text.strip()))
        if not candidates:
            return
        candidates.sort(key=lambda c: c[0])
        _y, val, raw = candidates[0]
        display = self.rupiah(val)
        self.log(f"SALDO: {display} (raw='{raw}') | reason={reason}")

        state = {
            "saldo_value": val,
            "saldo_display": display,
            "raw_text": raw,
            "timestamp": time.time(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB"),
            "reason": reason,
        }
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

        # Lapor ke Telegram hanya jika nominal berubah atau pertama kali
        if self.last_reported_saldo is None or abs(val - self.last_reported_saldo) >= 0.01:
            old_disp = f" (sebelumnya {self.rupiah(self.last_reported_saldo)})" if self.last_reported_saldo is not None else ""
            self.last_reported_saldo = val
            self.send_telegram(f"[{TARGET_NAME}] Saldo Terkini: {display}{old_disp} | {reason}")

    def send_telegram(self, msg: str) -> None:
        if not os.path.exists(TELEGRAM_SENDER):
            return
        try:
            r = subprocess.run(
                ["/opt/homebrew/bin/python3", TELEGRAM_SENDER, msg],
                capture_output=True, text=True, timeout=15,
            )
            stdout = (r.stdout or "").strip()
            if stdout:
                self.log(f"TELEGRAM STDOUT: {stdout}")
        except Exception as exc:
            self.log(f"TELEGRAM ERROR: {exc}")

    # ===================== REWARD / DOBEL / FILTER HADIAH =====================

    def record_reward_history(self, amount: float, action: str, note: str = "") -> None:
        """Kelola riwayat reward: simpan hanya reward Kwai & Meta, bersihkan riwayat kecil."""
        try:
            history = []
            if os.path.exists(REWARD_HISTORY_FILE):
                try:
                    with open(REWARD_HISTORY_FILE, "r") as f:
                        history = json.load(f)
                except Exception:
                    history = []

            # Hapus riwayat selain Kwai Ads dan Meta Audience Network (atau nominal besar >= 50)
            allowed_nets = ("kwai", "meta", "alliance")
            history = [
                entry for entry in history
                if (any(k in (entry.get("network") or "").lower() or k in (entry.get("note") or "").lower() for k in allowed_nets)
                    or entry.get("amount", 0) >= 50.0)
            ]

            now_ts = time.time()
            ad_net = getattr(self, "current_ad_network", "Meta Audience Network")

            # Deduplikasi dalam 15 detik terakhir untuk nominal yang sama
            is_dup = any(abs(now_ts - e.get("timestamp", 0)) < 15 and abs(amount - e.get("amount", 0)) < 0.1 for e in history[-5:])

            if not is_dup and (amount >= MIN_REWARD_THRESHOLD or action == "CLAIMED_DOBEL"):
                new_entry = {
                    "timestamp": now_ts,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB"),
                    "amount": round(amount, 2),
                    "amount_display": f"Rp {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "action": action,
                    "note": note or f"Reward iklan {ad_net} ditonton & digandakan",
                    "network": ad_net,
                }
                history.append(new_entry)

            with open(REWARD_HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as exc:
            self.log(f"Gagal simpan reward history: {exc}")

    def find_reward_offer(self):
        """Deteksi tombol DOBEL, tombol NOW NOT/NANTI, serta nominal Rp reward di popup."""
        w, h = self.screen_size()
        entries = self.ocr_screen("reward_offer")
        
        dobel = None
        not_now = None
        reward_candidates = []
        for text, x, y, _bbox in entries:
            n = self.norm(text)
            n_clean = n.replace(" ", "")
            if any(sw in n for sw in STORE_WORDS):
                continue
            
            val = self.parse_rupiah(text)
            if val is not None and val > 0 and y > 300:
                reward_candidates.append((y, val, text, x, y))
                
            if "dobel" in n_clean or "double" in n_clean or "2x" in n_clean or "x2" in n_clean:
                dobel = (text, x, y)
                continue
                
            if not_now is None and any(k in n_clean for k in ("notnow", "nownot", "nanti", "tidak", "lewati", "skip", "ambil", "dapat", "terima")):
                not_now = (text, x, y)

        reward_rp = None
        if reward_candidates and dobel:
            target_y = dobel[2]
            above = [r for r in reward_candidates if r[0] < target_y and (target_y - r[0]) < 500]
            if above:
                above.sort(key=lambda item: abs(target_y - item[0]))
                reward_rp = above[0][1]
            else:
                reward_candidates.sort(key=lambda item: abs(target_y - item[0]))
                reward_rp = reward_candidates[0][1]

        return dobel, not_now, reward_rp

    # ===================== REWARD / DOBEL BUTTON =====================

    def reward_score(self, label: str) -> int:
        n = self.norm(label).replace(" ", "")
        if "dobel" in n or "double" in n or "2x" in n or "x2" in n:
            return 0
        if any(k in n for k in ("claim", "klaim", "watch", "tonton", "reward", "bonus", "gratis", "buka")):
            return 1
        if any(k in n for k in ("ambil", "get", "collect", "dapat")):
            return 2
        if any(k in n for k in ("notnow", "nownot", "nanti", "tidak", "lanjut", "next", "continue")):
            return 3
        return 9

    def find_not_now_button(self):
        entries = self.ocr_screen("not_now")
        for text, x, y, _bbox in entries:
            n = self.norm(text).replace(" ", "")
            if any(k in n for k in ("notnow", "nownot", "nanti", "tidak", "lewati", "skip")):
                return text, x, y
        return None

    def find_reward_button(self):
        w, h = self.screen_size()
        candidates = []

        # 1. OCR (game Unity render kanvas grafik tombol DOBEL)
        entries = self.ocr_screen("reward")
        for text, x, y, _bbox in entries:
            n = self.norm(text)
            n_clean = n.replace(" ", "")
            if any(sw in n for sw in STORE_WORDS):
                continue
            # Jika ada DOBEL langsung pilih tanpa ragu
            if "dobel" in n_clean or "double" in n_clean or "2x" in n_clean or "x2" in n_clean:
                return text, x, y, "ocr"
            if any(word in n for word in REWARD_WORDS) and h * 0.18 < y < h * 0.92:
                candidates.append((self.reward_score(text), text, x, y, "ocr"))

        # 2. UI Automator dump
        root = self.dump_ui()
        if root is not None:
            for node in root.iter("node"):
                label = (node.get("text") or node.get("content-desc") or "").strip()
                b = self.bounds_center(node.get("bounds", ""))
                if not label or not b:
                    continue
                n = self.norm(label)
                n_clean = n.replace(" ", "")
                if any(sw in n for sw in STORE_WORDS):
                    continue
                if "dobel" in n_clean or "double" in n_clean:
                    x, y, *_ = b
                    return label, x, y, "ui"
                if any(word in n for word in REWARD_WORDS):
                    x, y, *_ = b
                    if h * 0.18 < y < h * 0.92:
                        candidates.append((self.reward_score(label), label, x, y, "ui"))

        if not candidates:
            return None
        candidates.sort(key=lambda t: (t[0], -t[3]))
        _score, label, x, y, src = candidates[0]
        return label, x, y, src

    def burst_tap_bubble_and_arrows(self, bx: int, by: int) -> None:
        """Spam multi-tap serentak: pecahkan bubble iklan dan sekaligus klik panah puzzle (cepat < 0.3s tanpa timeout)."""
        w, h = self.screen_size()
        b_x = max(10, min(w - 10, bx + random.randint(-6, 6)))
        b_y = max(10, min(h - 10, by + random.randint(-6, 6)))

        arrow1_x = w // 2 + random.randint(-120, 120)
        arrow1_y = int(h * 0.55) + random.randint(-100, 100)
        arrow2_x = w // 2 + random.randint(-120, 120)
        arrow2_y = int(h * 0.55) + random.randint(-100, 100)

        cmd = f"input tap {b_x} {b_y} & input tap {arrow1_x} {arrow1_y} & input tap {arrow2_x} {arrow2_y}"
        markers = [
            (b_x, b_y, "red", 0.6, 75),
            (arrow1_x, arrow1_y, "green", 0.5, 55),
            (arrow2_x, arrow2_y, "green", 0.5, 55),
        ]
        self.show_tap_marker(markers)
        self.adb_out(["shell", f"sh -c '{cmd}'"], timeout=2)

    # ===================== BUBBLE IKLAN (HIJAU/KUNING) =====================

    def find_ad_bubble(self):
        """Deteksi bubble iklan hijau/kuning di layar game."""
        cap = self.capture_png()
        if not cap:
            return None
        png, w, h = cap
        try:
            import cv2
            import numpy as np
        except Exception:
            return None
        img = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return None

        x_min = int(w * 0.05)
        y_min = int(h * 0.15)
        x_max = w - 8
        y_max = int(h * 0.88)
        roi = img[y_min:y_max, x_min:x_max]
        if roi.size == 0:
            return None

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        green = cv2.inRange(hsv, (35, 55, 70), (95, 255, 255))
        yellow = cv2.inRange(hsv, (15, 70, 100), (38, 255, 255))
        mask = cv2.bitwise_or(green, yellow)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.dilate(mask, kernel, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < 600 or area > 30000:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            if bw < 30 or bh < 30 or bw > 220 or bh > 220:
                continue
            aspect = bw / float(bh)
            if aspect < 0.4 or aspect > 2.2:
                continue
            cx = x_min + x + bw // 2
            cy = y_min + y + bh // 2

            pad = 70
            cr_x1 = max(0, cx - pad)
            cr_y1 = max(0, cy - pad)
            cr_x2 = min(w, cx + pad)
            cr_y2 = min(h, cy + pad)
            crop_hsv = cv2.cvtColor(img[cr_y1:cr_y2, cr_x1:cr_x2], cv2.COLOR_BGR2HSV)
            if crop_hsv.size == 0:
                continue
            white_mask = cv2.inRange(crop_hsv, np.array([0, 0, 165]), np.array([179, 85, 255]))
            white_ratio = float(white_mask.mean() / 255.0)
            if white_ratio < 0.06:
                continue

            score = area + white_ratio * 5000
            candidates.append((score, cx, cy, area, bw, bh))

        if not candidates:
            return None
        candidates.sort(reverse=True)
        _score, cx, cy, area, bw, bh = candidates[0]
        return int(cx), int(cy), f"ad-bubble area={int(area)} size={bw}x{bh}"

    # ===================== LICENSE ERROR =====================

    def handle_license_error(self) -> bool:
        root = self.dump_ui()
        if root is not None:
            for node in root.iter("node"):
                label = (node.get("text") or node.get("content-desc") or "").strip()
                b = self.bounds_center(node.get("bounds", ""))
                if label.lower() in ("close", "tutup") and b:
                    x, y, *_ = b
                    self.log(f"LICENSE ERROR: klik '{label}' di ({x},{y})")
                    self.tap(x, y)
                    time.sleep(0.7)
                    self.launch_game("license error close")
                    return True
        self.log("LICENSE ERROR: tutup dengan BACK lalu launch ulang")
        self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
        time.sleep(0.7)
        self.launch_game("license error")
        return True

    # ===================== GAMEPLAY =====================

    def handle_game_screen(self) -> None:
        now = time.time()
        self.ad_start_ts = None
        self.ad_title_confirmed = False

        # Cek saldo periodik setiap 45 detik
        if now - self.last_saldo_check_ts > 45:
            self.last_saldo_check_ts = now
            self.check_saldo("pengecekan periodik")

        # Bersihkan cache berkala tiap 10 menit
        if now - self.last_cache_clear_ts > 600:
            self.last_cache_clear_ts = now
            self.clear_ad_cache()

        # 1. Deteksi popup reward cerdas (DOBEL SELALU DIKLIK, TIDAK PERNAH KLIK NOW NOT)
        dobel, not_now, reward_rp = self.find_reward_offer()
        if dobel:
            label, dx, dy = dobel
            # Beri jeda lelang 3.5 detik antar-klik agar SDK TopOn selesai buffering video tanpa interupsi spam tap
            if now - self.last_reward_tap_ts < 3.5:
                return
            self.last_reward_tap_ts = now

            s = self.get_current_saldo()
            if s is not None:
                self.pre_ad_saldo = s
            self.was_dobel_clicked = True
            self.pending_ad_verification = True
            self.dobel_consecutive_clicks += 1

            # Titik sentuh presisi di tengah tombol horizontal (x=360)
            tap_x = 360
            tap_y = dy

            # Sesuai instruksi: Jika sudah 15x klik dobel iklan tidak terbuka -> klaim saldo via NOT NOW / AMBIL & restart
            if self.dobel_consecutive_clicks >= 15:
                self.log(f"DOBEL TERTUNDA ({self.dobel_consecutive_clicks}x) -> KLAIM SALDO via NOT NOW / AMBIL & RESTART GAME")
                if not_now:
                    _, nx, ny = not_now
                    self.tap(nx, ny)
                else:
                    self.tap(360, 1216)
                time.sleep(2.0)
                self.launch_game("restart setelah klaim saldo dobel macet 15x", hard_restart=True)
                self.dobel_consecutive_clicks = 0
                return



            rp_info = f" Rp {reward_rp:.2f}" if reward_rp else ""
            self.log(f"FOKUS IKLAN DOBEL{rp_info}! -> KLIK TENGAH DOBEL di ({tap_x},{tap_y}) [attempt {self.dobel_consecutive_clicks}] via ocr")
            self.tap(tap_x, tap_y)
            return
        else:
            self.dobel_consecutive_clicks = 0

        # 2. Cari tombol reward umum lainnya (termasuk BUKA / PETI IKLAN)
        if now - self.last_reward_tap_ts < 3.5:
            return
        btn = self.find_reward_button()
        if btn:
            label, x, y, src = btn
            n = self.norm(label).replace(" ", "")
            if "buka" in n:
                if now < self.buka_ad_cooldown_until:
                    remaining = int(self.buka_ad_cooldown_until - now)
                    self.log(f"IKLAN BELUM TERSEDIA: tombol BUKA dalam cooldown ({remaining}s tersisa) -> tutup popup, tidak retry")
                    not_now_btn = self.find_not_now_button()
                    if not_now_btn:
                        _, nx, ny = not_now_btn
                        self.tap(nx, ny)
                    self.buka_consecutive_clicks = 0
                    self.pending_ad_verification = False
                    return

                self.buka_consecutive_clicks += 1
                if self.buka_consecutive_clicks == 1:
                    wait_sec = 5.0
                elif self.buka_consecutive_clicks == 2:
                    wait_sec = 8.0
                else:
                    wait_sec = 12.0
                if self.buka_consecutive_clicks >= MAX_BUKA_AD_ATTEMPTS:
                    self.buka_ad_cooldown_until = now + BUKA_AD_COOLDOWN_SECONDS
                    self.log(
                        f"IKLAN GAGAL DIMUAT ({self.buka_consecutive_clicks}x): aplikasi tidak membuka aktivitas iklan "
                        f"-> cooldown {BUKA_AD_COOLDOWN_SECONDS // 60} menit, tutup popup tanpa restart"
                    )
                    not_now_btn = self.find_not_now_button()
                    if not_now_btn:
                        _, nx, ny = not_now_btn
                        self.tap(nx, ny)
                    self.buka_consecutive_clicks = 0
                    self.pending_ad_verification = False
                    return

            else:
                self.buka_consecutive_clicks = 0
                wait_sec = 2.0

            s = self.get_current_saldo()
            if s is not None:
                self.pre_ad_saldo = s
            self.was_dobel_clicked = False
            self.pending_ad_verification = True
            # Beri jeda 4.5 detik agar SDK TopOn selesai lelang & buffering tanpa interupsi
            self.last_reward_tap_ts = now + wait_sec
            self.log(f"FOKUS BUKA IKLAN: '{label}' di ({x},{y}) [attempt {self.buka_consecutive_clicks}] via {src} -> tunggu {wait_sec}s hingga iklan muncul")
            self.tap(x, y)
            return
        else:
            self.buka_consecutive_clicks = 0

        # 3. Cari bubble iklan (hijau/kuning) untuk di-tap brutal BARENGAN dengan klik panah puzzle (4X LEBIH CEPAT: 0.15s)
        if now - self.last_bubble_tap_ts > 0.15:
            bubble = self.find_ad_bubble()
            if bubble:
                bx, by, info = bubble
                self.last_bubble_tap_ts = now
                self.log(f"BUBBLE IKLAN + PANAH (4X CEPAT): {info} -> TAP SERENTAK bubble ({bx},{by}) & 5 panah")
                self.burst_tap_bubble_and_arrows(bx, by)
                return

        # 4. Gameplay aktif super cepat (4X LEBIH CEPAT: 0.12s + 5 panah serentak):
        if now - self.last_gameplay_tap_ts > 0.12:
            self.last_gameplay_tap_ts = now
            w, h = self.screen_size()
            arrow_pts = [
                (w // 2 + random.randint(-150, 150), int(h * 0.55) + random.randint(-130, 130))
                for _ in range(5)
            ]
            tap_cmds = " & ".join(f"input tap {x} {y}" for x, y in arrow_pts)
            self.adb_out(["shell", f"sh -c '{tap_cmds}'"], timeout=2)

    # ===================== MAIN STEP =====================

    def step(self) -> None:
        app = self.foreground()
        if not app:
            self.launch_game("foreground tidak terbaca")
            return
        fg_key = f"{app.package}/{app.activity}"
        if fg_key != self.last_fg:
            self.last_fg = fg_key
            self.log(f"FOREGROUND: {fg_key}")

        # Jika bukan game kita -> kembali ke game
        if app.package != TARGET_PACKAGE:
            name = BLOCKED_PACKAGES.get(app.package, "aplikasi lain")
            now = time.time()
            if now - self.last_external_ts > 2:
                self.last_external_ts = now
                self.log(f"KELUAR DARI GAME ke {name} ({app.package}) -> kembali ke game")
                self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
                time.sleep(0.7)
                after = self.foreground()
                if not after or after.package != TARGET_PACKAGE:
                    self.launch_game(f"foreground {app.package}")
            return

        # License error
        if "license" in app.activity.lower():
            self.handle_license_error()
            return

        # Iklan terbuka -> tutup
        if self.is_ad(app):
            self.was_in_ad = True
            self.try_close_ad(app)
            return

        # Kembali dari iklan ke game -> jalankan verifikasi selisih saldo!
        if self.was_in_ad:
            self.was_in_ad = False
            self.log("KEMBALI DARI IKLAN KE GAME -> Verifikasi selisih saldo...")
            time.sleep(2.0)
            self.verify_reward_payout()

        # Verifikasi masih di game
        if not self.verify_still_in_game():
            return

        # Handle layar game (cari DOBEL, bubble, dll)
        self.handle_game_screen()

    # ===================== RUN =====================

    def run(self) -> None:
        self.log("=" * 50)
        self.log(f"  {TARGET_NAME.upper()} GUARDIAN BOT")
        self.log("=" * 50)
        self.log(f"Bot aktif untuk {TARGET_NAME} ({TARGET_PACKAGE})")
        self.log(f"Log: {LOG_FILE}")
        if self.serial:
            self.log(f"Device: {self.serial}")
        self.launch_game("start bot")
        while True:
            try:
                self.step()
            except BaseException as exc:
                self.log(f"LOOP ERROR/RECOVER: {type(exc).__name__}: {exc}")
                time.sleep(1.0)
            time.sleep(self.interval)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--serial", default="")
    p.add_argument("--interval", type=float, default=0.08)
    args = p.parse_args()
    Bot(serial=args.serial, interval=args.interval).run()


if __name__ == "__main__":
    main()
