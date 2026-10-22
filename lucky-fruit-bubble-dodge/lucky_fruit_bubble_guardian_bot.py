#!/usr/bin/env python3
"""
Lucky Fruit Bubble Dodge Guardian Bot (v2 - Moving Bubble Edition)

Fitur utama:
- Deteksi foreground, buka game jika belum aktif
- Tutup Chrome/Play Store/app lain yang terbuka karena iklan
- Deteksi & klik tombol DOBEL/AMBIL reward
- Deteksi & tutup iklan (UI dump, OCR, arrow kanan atas)
- Deteksi popup "Confirm to Close" -> klik Continue
- Deteksi gelembung bergerak (moving bubble) via frame diff - TAP BATCH PRESISI
- Deteksi gelembung hijau statis (cash bubble)
- Tap marker visual via scrcpy_tap_marker
- Monkey burst tap (cepat, 1 proses JVM)
- Cek saldo OCR periodik
- Fallback meriam

Target game:
  App     : Lucky Fruit Bubble Dodge
  Package : com.newgameclick.luckyfruitbubbledodge
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

TARGET_PACKAGE = "com.newgameclick.luckyfruitbubbledodge"
TARGET_NAME = "Lucky Fruit Bubble Dodge"
LOG_FILE = os.path.expanduser("~/lucky_fruit_bubble_guardian_bot.log")
STATE_FILE = os.path.expanduser("~/lucky_fruit_bubble_saldo_state.json")
OCR_HELPER = "/Users/macbookair/ocr_helper"
TAP_MARKER = "/Users/macbookair/scrcpy_tap_marker"
TELEGRAM_SENDER = "/Users/macbookair/telegram_sender.py"

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

BUBBLE_CHECK_INTERVAL = 0.0
BUBBLE_TIMEOUT_SECONDS = 16.0
BUBBLE_TAP_COOLDOWN = 0.0
POST_AD_SEARCH_COOLDOWN_SECONDS = 600.0  # Maksimal 1x setiap 10 menit
ENABLE_POST_AD_INFO_SEARCH = True
REWARD_OPEN_RETRY_SECONDS = 8.0
REWARD_OPEN_MAX_ATTEMPTS = 3


@dataclass
class ForegroundApp:
    package: str
    activity: str = ""
    raw: str = ""


class Bot:
    def __init__(self, serial: str = "", interval: float = 0.24):
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
        self.last_open_store_tap_ts = 0.0
        self.last_top_right_arrow_tap_ts = 0.0
        self.last_reward_tap_ts = 0.0
        self.reward_open_attempts = 0
        self.reward_open_last_ts = 0.0
        self.last_saldo_check_ts = 0.0
        self.last_external_ts = 0.0
        self.last_gameplay_tap_ts = 0.0
        self.last_post_ad_search_ts = 0.0
        # Moving bubble state
        self.bubble_watch_active = False
        self.bubble_watch_start_ts = 0.0
        self.last_bubble_check_ts = 0.0
        self.last_bubble_tap_ts = 0.0
        self.last_bubble_restart_ts = 0.0
        self.prev_bubble_detection: Optional[Tuple[float, int, int]] = None
        self.last_bubble_pair_velocity: Optional[Tuple[float, float]] = None
        self.last_bubble_screen_size: Tuple[int, int] = (720, 1600)
        self._cached_bubble_frame = None
        self._cached_bubble_ts = 0.0

    def log(self, msg: str) -> None:
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line, flush=True)
        if os.environ.get("LUCKY_FRUIT_NO_FILE_LOG") == "1":
            return
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

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
            self.log(f"ADB error/interrupt: {' '.join(args)} | {type(exc).__name__}: {exc}")
            return ""

    def adb_bytes(self, args: list[str], timeout: int = 10) -> bytes:
        try:
            r = subprocess.run(self.adb_cmd(args), capture_output=True, timeout=timeout)
            return r.stdout or b""
        except BaseException as exc:
            self.log(f"ADB bytes error/interrupt: {' '.join(args)} | {type(exc).__name__}: {exc}")
            return b""

    def tap(self, x: int, y: int) -> None:
        self.show_tap_marker([(int(x), int(y), "blue", 1.3, 58)])
        self.log(f"TAP ({x},{y})")
        self.adb_out(["shell", "input", "tap", str(int(x)), str(int(y))], timeout=4)

    # -- Tap Marker Visual --

    def show_tap_marker(self, specs: list) -> None:
        if not os.path.exists(TAP_MARKER) or os.environ.get("LUCKY_FRUIT_DISABLE_MARKER") == "1":
            return
        args: list[str] = []
        for x, y, color, duration, diameter in specs[:220]:
            args += [str(int(x)), str(int(y)), color, str(float(duration)), str(int(diameter))]
        try:
            subprocess.Popen([TAP_MARKER, *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            preview = ", ".join(f"({x},{y},{color})" for x, y, color, _, _ in specs[:8])
            self.log(f"MARKER DIBUAT: {len(specs)} titik | {preview}")
        except Exception:
            self.log("MARKER GAGAL DIBUAT")

    # -- Monkey Burst Tap --

    def monkey_burst(self, points: list, delay_ms: int = 3, timeout: int = 6) -> None:
        if not points:
            return
        script_lines = [
            "type= raw events",
            "count= 1",
            "speed= 1.0",
            "start data >>",
        ]
        for x, y in points:
            script_lines.append(f"DispatchPointer(0, 0, 0, {int(x)}, {int(y)}, 0, 0, 0, 0, 0, 0, 0)")
            script_lines.append(f"DispatchPointer(0, 0, 1, {int(x)}, {int(y)}, 0, 0, 0, 0, 0, 0, 0)")
            if delay_ms > 0:
                script_lines.append(f"UserWait({delay_ms})")
        script_content = chr(10).join(script_lines) + chr(10)

        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += ["shell", "cat > /data/local/tmp/burst_tap.txt && monkey -f /data/local/tmp/burst_tap.txt 1"]
        try:
            subprocess.run(cmd, input=script_content, text=True, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            self.log("ADB timeout saat monkey burst tap")
        except Exception as exc:
            self.log(f"Monkey burst error: {exc}")

    def tap_many(self, points: list, timeout: int = 10, color: str = "orange") -> None:
        if not points:
            return
        unique_points = []
        for x, y in points:
            point = (int(x), int(y))
            if point not in unique_points:
                unique_points.append(point)
        marker_diam = 22 if color == "red" else 34
        marker_dur = 1.2 if color == "red" else 1.8
        self.show_tap_marker([(x, y, color, marker_dur, marker_diam) for x, y in unique_points[:220]])
        # Untuk tap gelembung (marker merah) harus sangat cepat/brutal.
        delay_ms = 0 if color == "red" else 3
        self.monkey_burst(unique_points, delay_ms=delay_ms, timeout=timeout)

    def tap_bubble_until_ad(self, points: list) -> bool:
        if not points:
            return False
        batch = points[:800]
        self.log(f"TAP BATCH GELEMBUNG SUPER BRUTAL: {len(batch)} titik presisi cepat")
        self.tap_many(batch, timeout=8, color="red")
        self.last_reward_tap_ts = 0.0
        # Cek cepat; kalau belum buka iklan, tembak wave kedua.
        time.sleep(0.30)
        app = self.foreground()
        if app and (self.is_ad(app) or app.package != TARGET_PACKAGE):
            self.log(f"STOP TAP GELEMBUNG: foreground berubah ({app.package}/{app.activity})")
            return True

        second_wave = list(reversed(points[:700]))
        if second_wave:
            self.log(f"TAP GELEMBUNG WAVE 2 BRUTAL: {len(second_wave)} titik tambahan")
            self.tap_many(second_wave, timeout=7, color="red")

        # Triple-check: catch slow ads.
        time.sleep(0.30)
        app = self.foreground()
        if app and (self.is_ad(app) or app.package != TARGET_PACKAGE):
            self.log(f"STOP TAP GELEMBUNG (check2): foreground berubah ({app.package}/{app.activity})")
            return True
        time.sleep(0.30)
        app = self.foreground()
        if app and (self.is_ad(app) or app.package != TARGET_PACKAGE):
            self.log(f"STOP TAP GELEMBUNG (check3): foreground berubah ({app.package}/{app.activity})")
            return True
        return False

    # -- Foreground Detection --

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
        """Verifikasi cepat bahwa foreground masih game target. Panggil sebelum aksi gameplay."""
        app = self.foreground()
        if not app:
            self.launch_game("verifikasi: foreground tidak terbaca")
            return False
        if app.package != TARGET_PACKAGE:
            name = BLOCKED_PACKAGES.get(app.package, "aplikasi lain")
            self.log(f"VERIFIKASI GAGAL: ternyata di {name} ({app.package}) -> kembali ke game")
            self.adb_out(["shell", "am", "force-stop", app.package], timeout=3)
            time.sleep(0.3)
            self.launch_game(f"verifikasi: keluar ke {app.package}")
            return False
        return True

    def screen_size(self) -> Tuple[int, int]:
        out = self.adb_out(["shell", "wm", "size"], timeout=4)
        m = re.search(r"(\d+)x(\d+)", out)
        return (int(m.group(1)), int(m.group(2))) if m else (720, 1600)

    def launch_game(self, reason: str = "", hard_restart: bool = False) -> None:
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

    def is_ad(self, app: ForegroundApp) -> bool:
        if app.package != TARGET_PACKAGE:
            return False
        low = f"{app.package}/{app.activity}".lower()
        return any(k in low for k in AD_KEYWORDS)

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

    def dump_ui(self):
        self.adb_out(["shell", "uiautomator", "dump", "/sdcard/luckyfruit_ui.xml"], timeout=5)
        xml = self.adb_out(["shell", "cat", "/sdcard/luckyfruit_ui.xml"], timeout=5)
        if "<hierarchy" not in xml:
            return None
        try:
            return ET.fromstring(xml)
        except Exception:
            return None

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

    # -- OCR --

    def ocr_screen(self, prefix: str) -> list:
        if not os.path.exists(OCR_HELPER):
            return []
        cap = self.capture_png()
        if not cap:
            return []
        png, w, h = cap
        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
        path = f"/tmp/luckyfruit_{prefix}_{safe_serial}.png"
        try:
            with open(path, "wb") as f:
                f.write(png)
            r = subprocess.run([OCR_HELPER, path], capture_output=True, text=True, timeout=10)
        except Exception:
            return []
        entries = []
        for line in (r.stdout or "").splitlines():
            text, _, bbox = line.partition("|")
            if not text.strip() or not bbox.strip():
                continue
            try:
                bx, by, bw, bh = [float(x) for x in bbox.split(",")]
                x = int((bx + bw / 2) * w)
                y = int((1 - by - bh / 2) * h)
            except Exception:
                x, y = w // 2, h // 2
            entries.append((text.strip(), x, y, bbox.strip()))
        return entries

    # -- Confirm to Close popup --

    def find_continue_on_close_confirm(self):
        confirm_words = (
            "confirm to close", "not be rewarded", "will not be rewarded",
            "after closing", "closing the window",
        )
        continue_words = ("continue", "lanjut", "lanjutkan")

        root = self.dump_ui()
        if root is not None:
            labels = []
            candidates = []
            for node in root.iter("node"):
                label = (node.get("text") or node.get("content-desc") or "").strip()
                b = self.bounds_center(node.get("bounds", ""))
                if not label:
                    continue
                n = self.norm(label)
                labels.append(n)
                if b and any(word == n or word in n for word in continue_words):
                    x, y, *_ = b
                    candidates.append((label, x, y, "ui"))
            if any(any(word in label for word in confirm_words) for label in labels) and candidates:
                return sorted(candidates, key=lambda c: (-c[1], c[2]))[0]

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

    # -- Top right arrow button --

    def find_top_right_arrow_button(self):
        cap = self.capture_png()
        if not cap:
            return None
        png, w, h = cap
        try:
            import cv2
            import numpy as np
            img = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            return None
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

    # -- Close button detection --

    def find_close_button(self):
        w, h = self.screen_size()
        root = self.dump_ui()
        if root is not None:
            for node in root.iter("node"):
                label = (node.get("text") or node.get("content-desc") or "").strip()
                b = self.bounds_center(node.get("bounds", ""))
                if not label or not b:
                    continue
                n = self.norm(label)
                raw = label.strip().lower()
                if raw not in CLOSE_WORDS and not any(t in n for t in ("close", "tutup", "skip", "lewati")):
                    continue
                x, y, *_ = b
                if y > h * 0.88:
                    continue
                is_store = raw in {"play", "google play", "buka toko", "open store", "store", "install", "instal"}
                if is_store:
                    continue
                return label, x, y, "ui"

        entries = self.ocr_screen("close")
        for text, x, y, bbox in entries:
            n = self.norm(text)
            if any(sw in n for sw in STORE_WORDS):
                continue
            if n in ("x", "\u00d7") or any(t in n for t in ("close", "tutup", "skip", "lewati")):
                return text, x, y, "ocr"
        return None

    # -- Ad handling --

    def try_close_ad(self, app: ForegroundApp) -> None:
        now = time.time()
        if self.ad_start_ts is None or self.ad_activity != app.activity:
            self.ad_start_ts = now
            self.ad_activity = app.activity
            self.log(f"IKLAN TERBUKA: {app.activity}")
            return
        elapsed = now - self.ad_start_ts
        if now - self.last_ad_check_ts < 2:
            return
        self.last_ad_check_ts = now
        self.log(f"IKLAN CHECK: {elapsed:.0f}s activity={app.activity}")
        if elapsed < 5:
            return
        keep_watching = self.find_continue_on_close_confirm()
        if keep_watching and now - self.last_ad_close_tap_ts >= 2.5:
            label, x, y, src = keep_watching
            self.last_ad_close_tap_ts = now
            self.log(f"POPUP CONFIRM TO CLOSE: klik '{label}' di ({x},{y}) via {src} | durasi {elapsed:.0f}s")
            self.tap(x, y)
            return
        top_right_arrow = self.find_top_right_arrow_button()
        if top_right_arrow and now - self.last_top_right_arrow_tap_ts >= 12:
            label, x, y, src = top_right_arrow
            self.last_top_right_arrow_tap_ts = now
            self.last_ad_close_tap_ts = now
            self.log(f"IKON ARAH KANAN ATAS: klik '{label}' di ({x},{y}) via {src} | durasi {elapsed:.0f}s")
            self.tap(x, y)
            return
        found = self.find_close_button()
        if found and now - self.last_ad_close_tap_ts >= 2.5:
            label, x, y, src = found
            self.last_ad_close_tap_ts = now
            self.log(f"TUTUP IKLAN: '{label}' di ({x},{y}) via {src} | durasi {elapsed:.0f}s")
            self.tap(x, y)
            return
        if elapsed > 12 and now - self.last_ad_close_tap_ts >= 4:
            self.last_ad_close_tap_ts = now
            self.log(f"FALLBACK TUTUP IKLAN CEPAT: BACK karena durasi {elapsed:.0f}s")
            self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
        if elapsed > 30:
            # Track stuck ad repetition
            act_key = app.activity.lower()
            if self.ad_stuck_activity == act_key:
                self.ad_stuck_count += 1
            else:
                self.ad_stuck_count = 1
                self.ad_stuck_activity = act_key
            if self.ad_stuck_count >= 3:
                self.log(f"IKLAN STUCK BERULANG {self.ad_stuck_count}x: {app.activity} -> HARD RESTART game")
                self.ad_stuck_count = 0
                self.ad_stuck_activity = ""
                self.launch_game(f"iklan stuck berulang {self.ad_stuck_count}x {elapsed:.0f}s", hard_restart=True)
            else:
                self.log(f"IKLAN STUCK #{self.ad_stuck_count}: {app.activity} -> restart game")
                self.launch_game(f"iklan stuck {elapsed:.0f}s")

    # -- Saldo --

    def parse_rupiah(self, text: str):
        s = text.replace(" ", "")
        if "rp" not in s.lower() and not re.search(r"\d+[,.]\d{1,2}", s):
            return None
        m = re.search(r"(?:rp)?([0-9][0-9.,]*)", s, re.I)
        if not m:
            return None
        raw = m.group(1)
        try:
            if "," in raw:
                return float(raw.replace(".", "").replace(",", "."))
            return float(raw)
        except Exception:
            return None

    @staticmethod
    def rupiah(v: float) -> str:
        s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"Rp {s}"

    def check_saldo(self, reason: str) -> None:
        entries = self.ocr_screen("saldo")
        candidates = []
        for text, x, y, _ in entries:
            val = self.parse_rupiah(text)
            if val is not None:
                candidates.append((y, x, val, text))
        if not candidates:
            self.log("SALDO: belum terdeteksi OCR")
            return
        candidates.sort(key=lambda t: (t[0], t[1]))
        _y, _x, val, raw = candidates[0]
        state = {}
        try:
            if os.path.exists(STATE_FILE):
                state = json.load(open(STATE_FILE, "r", encoding="utf-8"))
        except Exception:
            state = {}
        prev = state.get("saldo_value")
        diff = val - float(prev) if isinstance(prev, (int, float)) else None
        state = {"saldo_value": val, "saldo_display": self.rupiah(val), "raw_text": raw, "time": datetime.now().isoformat(), "reason": reason}
        try:
            json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        except Exception:
            pass
        self.log(f"SALDO TERDETEKSI: {self.rupiah(val)} | raw='{raw}' | diff={self.rupiah(diff) if diff is not None else '-'} | {reason}")

    # -- Moving Bubble Detection (frame diff) --

    def find_moving_bubble(self):
        """Cari objek bulat/gelembung yang bergerak dari dua screenshot berurutan."""
        try:
            import cv2
            import numpy as np
        except Exception:
            return None

        cached_img = self._cached_bubble_frame
        cached_ts = self._cached_bubble_ts
        now_pre = time.time()
        if cached_img is not None and (now_pre - cached_ts < 2.8):
            img1 = cached_img
        else:
            first_res = self.capture_png()
            if not first_res:
                return None
            first_png, width, height = first_res
            self.last_bubble_screen_size = (width, height)
            time.sleep(0.10)
            img1 = cv2.imdecode(np.frombuffer(first_png, dtype=np.uint8), cv2.IMREAD_COLOR)

        second = self.capture_png()
        if not second:
            return None
        second_png, width, height = second
        self.last_bubble_screen_size = (width, height)
        second_ts = time.time()

        img2 = cv2.imdecode(np.frombuffer(second_png, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img1 is None or img2 is None or img1.shape != img2.shape:
            return None
        self._cached_bubble_frame = img2
        self._cached_bubble_ts = second_ts

        diff = cv2.absdiff(img1, img2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 24, 255, cv2.THRESH_BINARY)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.dilate(mask, kernel, iterations=2)

        # Eksklusi zona statis: saldo/bar atas dan meriam bawah
        mask[:int(height * 0.16), :] = 0
        mask[int(height * 0.86), :] = 0

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if area < 350 or area > 24000:
                continue
            if w < 28 or h < 28 or w > 180 or h > 180:
                continue
            aspect = w / float(h)
            if aspect < 0.55 or aspect > 1.8:
                continue

            center_x = x + w // 2
            center_y = y + h // 2
            if center_y < int(height * 0.16) or center_y > int(height * 0.86):
                continue
            if center_x < 30 or center_x > width - 30:
                continue

            rx1 = max(0, x - 18)
            ry1 = max(0, y - 18)
            rx2 = min(width, x + w + 18)
            ry2 = min(height, y + h + 18)
            roi1 = img1[ry1:ry2, rx1:rx2]
            roi2 = img2[ry1:ry2, rx1:rx2]
            if roi1.size == 0 or roi2.size == 0:
                continue
            hsv1 = cv2.cvtColor(roi1, cv2.COLOR_BGR2HSV)
            hsv2 = cv2.cvtColor(roi2, cv2.COLOR_BGR2HSV)

            green1 = cv2.inRange(hsv1, np.array([35, 55, 75]), np.array([90, 255, 255]))
            yellow1 = cv2.inRange(hsv1, np.array([15, 60, 90]), np.array([38, 255, 255]))
            green2 = cv2.inRange(hsv2, np.array([35, 55, 75]), np.array([90, 255, 255]))
            yellow2 = cv2.inRange(hsv2, np.array([15, 60, 90]), np.array([38, 255, 255]))
            money1 = cv2.bitwise_or(green1, yellow1)
            money2 = cv2.bitwise_or(green2, yellow2)

            white1 = cv2.inRange(hsv1, np.array([0, 0, 160]), np.array([179, 85, 255]))
            white2 = cv2.inRange(hsv2, np.array([0, 0, 160]), np.array([179, 85, 255]))
            money_ratio = float(money2.mean() / 255.0)
            white_ratio = float(white2.mean() / 255.0)
            sat_mean = float(hsv2[:, :, 1].mean())

            if money_ratio < 0.04 and white_ratio < 0.08:
                continue
            if sat_mean < 15 and money_ratio < 0.06:
                continue

            # Velocity estimation
            vx, vy = 0.0, 0.0
            latest_x, latest_y = center_x, center_y
            prev = self.prev_bubble_detection
            if prev is not None:
                dt = second_ts - prev[0]
                if 0.05 < dt < 4.0:
                    vx = (center_x - prev[1]) / dt
                    vy = (center_y - prev[2]) / dt
            self.last_bubble_pair_velocity = (vx, vy)

            # Prediksi posisi saat tap tiba
            lead_t = 0.12
            pred_x = int(center_x + vx * lead_t)
            pred_y = int(center_y + vy * lead_t)
            pred_x = max(18, min(width - 18, pred_x))
            pred_y = max(int(height * 0.18), min(int(height * 0.84), pred_y))

            score = area + money_ratio * 12000 + white_ratio * 4000
            candidates.append((score, pred_x, pred_y, f"moving-bubble area={int(area)} bbox=({x},{y},{w},{h}) latest=({latest_x},{latest_y}) v=({vx:.0f},{vy:.0f}) money={money_ratio:.2f} white={white_ratio:.2f}"))

        if not candidates:
            return None
        candidates.sort(reverse=True)
        _, x, y, info = candidates[0]
        return int(x), int(y), info

    # -- Static Cash Bubble Detection --

    def find_green_cash_bubble(self):
        cap = self.capture_png()
        if not cap:
            return None
        png, w, h = cap
        try:
            import cv2
            import numpy as np
            img = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            return None
        if img is None:
            return None

        x_min = int(w * 0.10)
        y_min = int(h * 0.20)
        x_max = w - 8
        y_max = int(h * 0.84)
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
            if area < 800 or area > 25000:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            if bw < 35 or bh < 35 or bw > 200 or bh > 200:
                continue
            aspect = bw / float(bh)
            if aspect < 0.45 or aspect > 1.9:
                continue
            cx = x_min + x + bw // 2
            cy = y_min + y + bh // 2
            if cy < int(h * 0.20) or cy > int(h * 0.84):
                continue

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
            if white_ratio < 0.08:
                continue

            score = area + white_ratio * 5000
            candidates.append((score, cx, cy, area, bw, bh))

        if not candidates:
            return None
        candidates.sort(reverse=True)
        _score, cx, cy, area, bw, bh = candidates[0]
        return int(cx), int(cy), f"cash-bubble area={int(area)} size={bw}x{bh}"

    # -- Build burst tap points --

    def build_bubble_burst_points(self, x: int, y: int, width: int, height: int) -> list:
        """Titik tap brutal: bubble + sweep area aman. Sama brutalnya dengan Magic Ocean."""
        import math
        now = time.time()
        cx, cy = int(x), int(y)
        pair_v = self.last_bubble_pair_velocity or (0.0, -180.0)
        vx, vy = pair_v
        if abs(vx) < 20 and abs(vy) < 20:
            vy = -180.0
        self.prev_bubble_detection = (now, cx, cy)

        points = []
        seen = set()

        def safe(px, py):
            px, py = int(px), int(py)
            if px < 18 or px > width - 18:
                return False
            if py < int(height * 0.20) or py > int(height * 0.84):
                return False
            return True

        def add_p(px, py):
            px, py = int(px), int(py)
            if not safe(px, py):
                return
            pt = (px, py)
            if pt not in seen:
                seen.add(pt)
                points.append(pt)

        # 1) Pusat bubble + prediksi jalur gerak
        centers = [(cx, cy)]
        for lead in (0.06, 0.12, 0.18, 0.26, 0.36, 0.50, 0.66, 0.84, 1.05):
            px = int(cx + vx * lead)
            py = int(cy + vy * lead)
            if abs(px - cx) <= 220 and abs(py - cy) <= 260:
                centers.append((px, py))
        for dy in (-20, -38, -58, -82, -112, -150, -195, -245):
            centers.append((cx, cy + dy))

        for px, py in centers:
            add_p(px, py)
            for dx, dy in (
                (18, 0), (-18, 0), (0, 18), (0, -18),
                (14, 14), (-14, 14), (14, -14), (-14, -14),
            ):
                add_p(px + dx, py + dy)

        # 2) Sweep area aman
        step = 24
        y_start = int(height * 0.20)
        y_end = int(height * 0.84)
        row = 0
        for gy in range(y_start, y_end, step):
            offset = 0 if row % 2 == 0 else step // 2
            for gx in range(24 + offset, width - 20, step):
                add_p(gx, gy)
            row += 1

        # 3) Ring ekstra dan jalur vertikal
        for px, py in centers:
            for radius in (26, 42, 62, 86, 112):
                steps = max(10, int(2 * math.pi * radius / 16))
                for i in range(steps):
                    angle = 2 * math.pi * i / steps
                    add_p(int(px + radius * math.cos(angle)), int(py + radius * math.sin(angle)))

        for dy in range(0, int(height * 0.62), 18):
            add_p(cx, cy - dy)
            add_p(cx - 24, cy - dy)
            add_p(cx + 24, cy - dy)
            add_p(cx - 48, cy - dy)
            add_p(cx + 48, cy - dy)

        # 4) Crosshair rapat
        for offset in range(-150, 151, 18):
            add_p(cx + offset, cy)
            add_p(cx, cy + offset)
            add_p(cx + offset, cy - 36)
            add_p(cx + offset, cy + 36)

        self.log(f"BUILD BURST GELEMBUNG BRUTAL: {len(points)} titik")
        return points[:1400]

    # -- Restart game for bubble search --

    def restart_game_for_bubble_search(self, reason: str) -> None:
        now = time.time()
        if now - self.last_bubble_restart_ts < 5:
            return
        self.last_bubble_restart_ts = now
        self.log(f"RESTART GAME UNTUK CARI GELEMBUNG: {reason}")
        for package in [TARGET_PACKAGE, *BLOCKED_PACKAGES.keys()]:
            self.adb_out(["shell", "am", "force-stop", package], timeout=5)
        time.sleep(0.8)
        self.launch_game("cari gelembung setelah timeout")
        self.bubble_watch_active = True
        self.bubble_watch_start_ts = time.time()
        self.last_bubble_check_ts = 0.0

    # -- Reward buttons --

    def reward_score(self, label: str) -> int:
        n = self.norm(label)
        if any(k in n for k in ("dobel", "double", "x2", "2x")):
            return 0
        if any(k in n for k in ("claim", "klaim", "watch", "tonton", "reward", "bonus", "gratis", "buka")):
            return 1
        if any(k in n for k in ("ambil", "get", "collect", "dapat")):
            return 2
        if any(k in n for k in ("not now", "now not", "nanti", "tidak", "lanjut", "next", "continue")):
            return 3
        return 9

    def find_reward_button(self):
        w, h = self.screen_size()
        root = self.dump_ui()
        candidates = []
        if root is not None:
            for node in root.iter("node"):
                label = (node.get("text") or node.get("content-desc") or "").strip()
                b = self.bounds_center(node.get("bounds", ""))
                if not label or not b:
                    continue
                n = self.norm(label)
                if any(sw in n for sw in STORE_WORDS):
                    continue
                if any(word in n for word in REWARD_WORDS):
                    x, y, *_ = b
                    if h * 0.18 < y < h * 0.92:
                        candidates.append((self.reward_score(label), label, x, y, "ui"))

        entries = self.ocr_screen("reward")
        for text, x, y, _bbox in entries:
            n = self.norm(text)
            if any(sw in n for sw in STORE_WORDS):
                continue
            if any(word in n for word in REWARD_WORDS) and h * 0.18 < y < h * 0.92:
                candidates.append((self.reward_score(text), text, x, y, "ocr"))
        if not candidates:
            return None
        candidates.sort(key=lambda t: (t[0], -t[3]))
        _score, label, x, y, src = candidates[0]
        return label, x, y, src

    # -- License error --

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

    # -- Tap meriam fallback --

    def tap_meriam(self) -> None:
        w, h = self.screen_size()
        x = int(w * 0.50)
        y = int(h * 0.885)
        self.log(f"TAP MERIAM fallback 5x cepat di ({x},{y})")
        self.adb_out([
            "shell",
            f"for i in 1 2 3 4 5; do input tap {int(x)} {int(y)}; sleep 0.02; done",
        ], timeout=3)

    # -- Bubble search update --

    def update_bubble_search(self) -> None:
        now = time.time()
        if now - self.last_bubble_check_ts < BUBBLE_CHECK_INTERVAL:
            return
        self.last_bubble_check_ts = now

        detect_start_ts = time.time()
        found = self.find_moving_bubble()
        detect_ms = int((time.time() - detect_start_ts) * 1000)
        if found:
            x, y, info = found
            mode_label = "MODE CARI" if self.bubble_watch_active else "MODE NORMAL"
            self.log(f"MENEMUKAN GELEMBUNG BERGERAK ({mode_label}): {info} | tap=({x},{y}) | delay_deteksi={detect_ms}ms")
            if now - self.last_bubble_tap_ts >= BUBBLE_TAP_COOLDOWN:
                self.last_bubble_tap_ts = now
                screen_w, screen_h = self.last_bubble_screen_size
                points = self.build_bubble_burst_points(x, y, screen_w, screen_h)
                self.log(f"TAP GELEMBUNG TERFOKUS: {len(points)} titik rapat tepat di badan & jalur ({x},{y})")
                tap_start_ts = time.time()
                opened = self.tap_bubble_until_ad(points)
                tap_ms = int((time.time() - tap_start_ts) * 1000)
                self.log(f"SELESAI TAP GELEMBUNG: durasi_tap={tap_ms}ms opened={opened}")
                if opened:
                    after = self.foreground()
                    activity = after.activity if after else "unknown"
                    self.log(f"BERHASIL BUKA IKLAN SETELAH TAP GELEMBUNG: {activity}")
                    self.bubble_watch_active = False
                    self.prev_bubble_detection = None
            return

        # Fallback: cari cash bubble statis
        static_found = self.find_green_cash_bubble()
        if static_found:
            x, y, info = static_found
            self.log(f"BUBBLE HIJAU TERDETEKSI: {info} -> tap ({x},{y})")
            screen_w, screen_h = self.last_bubble_screen_size
            points = self.build_bubble_burst_points(x, y, screen_w, screen_h)
            self.log(f"TAP GELEMBUNG TERFOKUS: {len(points)} titik rapat tepat di badan & jalur ({x},{y})")
            tap_start_ts = time.time()
            opened = self.tap_bubble_until_ad(points)
            tap_ms = int((time.time() - tap_start_ts) * 1000)
            self.log(f"SELESAI TAP GELEMBUNG: durasi_tap={tap_ms}ms opened={opened}")
            if opened:
                self.bubble_watch_active = False
                self.prev_bubble_detection = None
            return

        if not self.bubble_watch_active:
            return

        elapsed = now - self.bubble_watch_start_ts
        self.log(f"BELUM MENEMUKAN GELEMBUNG BERGERAK | durasi cari {elapsed:.0f}s")
        if elapsed >= BUBBLE_TIMEOUT_SECONDS:
            self.restart_game_for_bubble_search(f"{elapsed:.0f}s tidak menemukan gelembung")

    # -- Safe post-ad routine --

    def run_post_ad_info_search(self) -> None:
        """Buka pencarian informasi umum satu kali per 10 menit setelah iklan.

        Tidak melakukan pendaftaran akun, mengisi formulir, atau membuka aplikasi
        perjudian/slot. Browser ditutup setelah beberapa detik dan game dipulihkan.
        """
        if not ENABLE_POST_AD_INFO_SEARCH:
            return
        now = time.time()
        if now - self.last_post_ad_search_ts < POST_AD_SEARCH_COOLDOWN_SECONDS:
            remaining = int(POST_AD_SEARCH_COOLDOWN_SECONDS - (now - self.last_post_ad_search_ts))
            self.log(f"PASCA-IKLAN: pencarian dilewati; cooldown masih {remaining}s")
            return

        self.last_post_ad_search_ts = now
        query = urllib.parse.quote_plus(f"{TARGET_NAME} official information")
        url = f"https://www.google.com/search?q={query}"
        self.log("PASCA-IKLAN: buka pencarian informasi umum (maksimal 1x/10 menit)")
        try:
            self.adb_out([
                "shell", "am", "start",
                "-a", "android.intent.action.VIEW",
                "-d", url,
                "com.android.chrome",
            ], timeout=8)
            time.sleep(3.0)
        finally:
            self.adb_out(["shell", "am", "force-stop", "com.android.chrome"], timeout=5)
            time.sleep(0.4)
            self.launch_game("selesai pencarian pasca-iklan")
            self.log("PASCA-IKLAN: browser ditutup, kembali ke game")

    def maybe_handle_completed_ad(self, elapsed: float) -> bool:
        """Tandai iklan selesai dan jalankan rutinitas pasca-iklan bila cooldown lewat."""
        if elapsed < 5.0:
            return False
        self.run_post_ad_info_search()
        return True

    # -- Gameplay --

    def gameplay_tap(self) -> None:
        now = time.time()
        if now - self.last_gameplay_tap_ts < 0.23:
            return
        self.last_gameplay_tap_ts = now
        self.update_bubble_search()

    def handle_game_screen(self) -> None:
        now = time.time()
        completed_ad_elapsed = None
        if self.ad_start_ts is not None:
            completed_ad_elapsed = now - self.ad_start_ts
            self.ad_start_ts = None
            self.ad_activity = ""
        if completed_ad_elapsed is not None and self.maybe_handle_completed_ad(completed_ad_elapsed):
            return
        if now - self.last_saldo_check_ts > 20:
            self.last_saldo_check_ts = now
            self.check_saldo("periodic")
        if now - self.last_reward_tap_ts < 4:
            return
        btn = self.find_reward_button()
        if btn:
            label, x, y, src = btn
            score = self.reward_score(label)
            self.log(f"TOMBOL REWARD DITEMUKAN: '{label}' di ({x},{y}) via {src}")

            # Popup "buka" pada game memakai callback JavaScript di dalam APK.
            # Jika callback gagal, popup tetap berada di layar. Jangan spam tap:
            # beri waktu SDK iklan memuat, lalu coba ulang dengan batas aman.
            is_open_button = self.norm(label) == "buka"
            if is_open_button:
                if now - self.reward_open_last_ts < REWARD_OPEN_RETRY_SECONDS:
                    return
                self.reward_open_attempts += 1
                if self.reward_open_attempts > REWARD_OPEN_MAX_ATTEMPTS:
                    self.log(
                        "POPUP BUKA IKLAN MACET setelah "
                        f"{REWARD_OPEN_MAX_ATTEMPTS} percobaan -> buka ulang game "
                        "tanpa menghapus data"
                    )
                    self.reward_open_attempts = 0
                    self.reward_open_last_ts = 0.0
                    self.last_reward_tap_ts = now
                    self.launch_game("callback iklan macet", hard_restart=True)
                    return
                self.reward_open_last_ts = now
                self.last_reward_tap_ts = now
                self.log(
                    f"COBA BUKA IKLAN {self.reward_open_attempts}/"
                    f"{REWARD_OPEN_MAX_ATTEMPTS}: tunggu SDK "
                    f"{REWARD_OPEN_RETRY_SECONDS:.0f}s"
                )
                self.tap(x, y)
                return

            self.reward_open_attempts = 0
            self.reward_open_last_ts = 0.0
            self.last_reward_tap_ts = now
            self.tap(x, y)
            if score == 3:
                self.bubble_watch_active = True
                self.bubble_watch_start_ts = time.time()
                self.last_bubble_check_ts = 0.0
                self.log(f"MODE CARI GELEMBUNG AKTIF: timeout {BUBBLE_TIMEOUT_SECONDS:.0f}s")
        else:
            if self.reward_open_attempts:
                self.log("POPUP BUKA IKLAN sudah hilang/berubah -> reset penghitung retry")
            self.reward_open_attempts = 0
            self.reward_open_last_ts = 0.0
            self.log("GAMEPLAY: tidak ada DOBEL/AMBIL, cari bubble bergerak atau tembak meriam")
            self.gameplay_tap()
            if not self.bubble_watch_active:
                self.tap_meriam()

    # -- Main step --

    def step(self) -> None:
        app = self.foreground()
        if not app:
            self.launch_game("foreground tidak terbaca")
            return
        fg_key = f"{app.package}/{app.activity}"
        if fg_key != self.last_fg:
            self.last_fg = fg_key
            self.log(f"FOREGROUND: {fg_key}")

        if app.package != TARGET_PACKAGE:
            name = BLOCKED_PACKAGES.get(app.package, "aplikasi lain")
            now = time.time()
            if now - self.last_external_ts > 2:
                self.last_external_ts = now
                self.log(f"KELUAR DARI GAME ke {name} ({app.package}) -> kembali ke game")
                self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
                time.sleep(0.7)
                self.launch_game(f"foreground {app.package}")
            return

        if "license" in app.activity.lower():
            self.handle_license_error()
            return

        if self.is_ad(app):
            self.try_close_ad(app)
            return

        if not self.verify_still_in_game():
            return
        self.handle_game_screen()

    def run(self) -> None:
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
            time.sleep(0.25 if self.bubble_watch_active else self.interval)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--serial", default="")
    p.add_argument("--interval", type=float, default=0.24)
    args = p.parse_args()
    Bot(serial=args.serial, interval=args.interval).run()

if __name__ == "__main__":
    main()
