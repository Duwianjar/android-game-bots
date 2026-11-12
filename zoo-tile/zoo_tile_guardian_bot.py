#!/usr/bin/env python3
"""
Zoo Tile Guardian & Match-3 Auto Player Bot
Game: Tangkap Hewan Lucu: Permainan Tile (Zoo Tile: Win Mega Rewards!)
Package: com.zoo.tile.cute.animal.elephant.mouse.fox
Activity: com.google.firebase.MessagingUnityPlayerActivity

Fitur Utama:
1. Auto Reopen (Guardian): Memantau status foreground real-time. Jika keluar ke
   Chrome, Google Play Store, atau launcher, aplikasi redirect ditutup dan Zoo Tile
   segera dibuka kembali.
2. Smart Ad Handling: Mendeteksi iklan bawaan game (Vungle, MBridge, Pangle/Bytedance,
   Fyber/Inneractive, AppLovin, AdMob). Mendeteksi tombol tutup/skip (X, >>, Close, Tutup)
   secara dinamis via UIAutomator, OCR, dan Computer Vision tanpa salah klik banner.
3. Auto Match-3 Gameplay: Mendeteksi ubin hewan di area bermain via multi-threshold CV,
   mengelompokkan ubin dengan ikon hewan yang sama, dan mengetuk 3 ubin yang sama berturut-turut
   agar cocok (match-3) dan langsung hilang dari tray bawah. Otomatis mengetuk tombol Klaim/Lanjut
   saat menyelesaikan level.
"""

from __future__ import annotations

import argparse
import io
import math
import os
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

import cv2
import numpy as np

TARGET_PACKAGE = "com.zoo.tile.cute.animal.elephant.mouse.fox"
TARGET_ACTIVITY = "com.google.firebase.MessagingUnityPlayerActivity"
TARGET_NAME = "Zoo Tile"

BLOCKED_PACKAGES = {
    "com.android.chrome": "Chrome",
    "com.chrome.beta": "Chrome Beta",
    "com.chrome.dev": "Chrome Dev",
    "com.google.android.apps.chrome": "Chrome",
    "com.android.vending": "Google Play Store",
    "com.transsion.phoenix": "Phoenix Browser",
    "com.transsion.palmpay": "PalmPay / PalmStore",
    "com.opera.browser": "Opera Browser",
    "com.opera.mini.native": "Opera Mini",
    "com.sec.android.app.sbrowser": "Samsung Browser",
    "com.gems.adventure.journey": "Gems Adventure Ad",
}

LOG_FILE = os.path.expanduser("~/zoo_tile_guardian_bot.log")
OCR_HELPER = "/Users/macbookair/ocr_helper"

DEFAULT_INTERVAL = 0.05
LAUNCH_COOLDOWN = 2.0

AD_ACTIVITY_KEYWORDS = (
    "ads",
    "adplayer",
    "advert",
    "rewardvideo",
    "rewarded",
    "mbridge",
    "mintegral",
    "applovin",
    "vungle",
    "ironsource",
    "chartboost",
    "adcolony",
    "gms.ads",
    "fullscreenwebviewdisplay",
    "webviewdisplay",
    "kwai",
    "alliance",
    "adcommon",
    "pangle",
    "bytedance",
    "ksad",
    "ttrewardexpressvideoactivity",
    "inneractive",
    "fyber",
)

# Koordinat cadangan tombol tutup iklan yang terbukti pada perangkat 720x1640
AD_KNOWN_CLOSE_COORDS = [
    (653, 199),  # AppLovin / Unity top-right
    (670, 204),  # Vungle / Express top-right
    (662, 110),  # MBridge endcard top-right
    (675, 135),  # MBridge circle top-right
    (626, 146),  # Fyber / Inneractive top-right skip
    (665, 130),  # Pangle top-right
]

# Area bermain papan ubin (Zoo Tile 720x1640)
BOARD_X_MIN = 20
BOARD_X_MAX = 700
BOARD_Y_MIN = 350
BOARD_Y_MAX = 1250

# Area nampan bawah (tray tempat ubin berkumpul, max 7 ubin)
TRAY_Y_MIN = 1300
TRAY_Y_MAX = 1420

# Tombol bantuan / booster
BOOSTER_UNDO = (200, 1490)
BOOSTER_WAND = (400, 1490)
BOOSTER_SHUFFLE = (580, 1490)


@dataclass
class ForegroundApp:
    package: str
    activity: str = ""
    source: str = ""


@dataclass
class BoardTile:
    cx: int
    cy: int
    w: int
    h: int
    group_id: int = -1


class ZooTileBot:
    def __init__(
        self,
        serial: str = "",
        interval: float = DEFAULT_INTERVAL,
        dry_run: bool = False,
        wake: bool = True,
        auto_gameplay: bool = True,
        ad_timeout: float = 75.0,
    ):
        self.serial = serial.strip() or self.detect_device_serial()
        self.interval = max(0.05, interval)
        self.dry_run = dry_run
        self.wake = wake
        self.auto_gameplay = auto_gameplay
        self.ad_timeout = ad_timeout

        self.last_foreground_pkg = ""
        self.last_foreground_act = ""
        self.last_launch_ts = 0.0
        self.last_wake_check_ts = 0.0

        self.ad_start_ts: Optional[float] = None
        self.ad_activity_name = ""
        self.last_ad_log_sec = -1
        self.last_ad_close_attempt_ts = 0.0
        self.ad_close_attempts = 0

        self.total_matches = 0
        self.total_levels_cleared = 0
        self.last_gameplay_ts = 0.0
        self.last_claim_check_ts = 0.0
        self.no_tiles_count = 0
        self.booster_stuck_count = 0
        self.last_target_coords: Optional[Tuple[int, int]] = None
        self.stuck_tile_count = 0

        self.running = True
        self._setup_signals()

    def _setup_signals(self) -> None:
        def handler(sig, frame):
            self.log("Sinyal berhenti diterima. Menutup bot Zoo Tile...")
            self.running = False

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def log(self, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        print(line, flush=True)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def detect_device_serial(self) -> str:
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
            lines = [l.strip() for l in (res.stdout or "").splitlines() if l.strip()]
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    return parts[0]
        except Exception:
            pass
        return ""

    def adb(self, args: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str]:
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def adb_out(self, args: list[str], timeout: int = 10) -> str:
        try:
            res = self.adb(args, timeout=timeout)
            return (res.stdout or "").strip()
        except subprocess.TimeoutExpired:
            return ""
        except FileNotFoundError:
            self.log("ERROR: ADB tidak ditemukan di PATH.")
            sys.exit(1)
        except Exception:
            return ""

    def adb_bytes(self, args: list[str], timeout: int = 10) -> bytes:
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += args
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=timeout)
            return res.stdout or b""
        except Exception:
            return b""

    def tap(self, x: int, y: int, delay: float = 0.15) -> None:
        if self.dry_run:
            self.log(f"[DRY-RUN] Tap ({x}, {y})")
            return
        self.adb(["shell", "input", "tap", str(x), str(y)], timeout=5)
        if delay > 0:
            time.sleep(delay)

    def tap_fast(self, x: int, y: int) -> None:
        """Ketuk 1 koordinat super cepat via Monkey event."""
        if self.dry_run:
            self.log(f"[DRY-RUN] Fast Tap ({x}, {y})")
            return
        events = [
            f"DispatchPointer(0, 0, 0, {int(x)}, {int(y)}, 0, 0, 0, 0, 0, 0, 0)",
            f"DispatchPointer(0, 0, 1, {int(x)}, {int(y)}, 0, 0, 0, 0, 0, 0, 0)",
        ]
        self.monkey_burst(events)

    def monkey_burst(self, script_events: List[str], timeout: int = 6) -> None:
        """Kirim event touch berkecepatan tinggi menggunakan monkey script (satu proses JVM)."""
        if self.dry_run or not script_events:
            return
        header = [
            "type= raw events",
            "count= 1",
            "speed= 1.0",
            "start data >>",
        ]
        content = chr(10).join(header + script_events) + chr(10)
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += ["shell", "cat > /data/local/tmp/burst_tap.txt && monkey -f /data/local/tmp/burst_tap.txt 1"]
        try:
            subprocess.run(cmd, input=content, text=True, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            self.log("ADB timeout saat monkey burst tap")
        except Exception as exc:
            self.log(f"Monkey burst error: {exc}")

    def tap_triplets_burst(
        self,
        triplets: List[List[BoardTile]],
        intra_delay_ms: int = 25,
        inter_delay_ms: int = 100,
    ) -> None:
        """Mengetuk triplet ubin secara berurutan dengan jeda milidetik ultra-cepat."""
        if not triplets:
            return
        events: List[str] = []
        for t_idx, triplet in enumerate(triplets):
            if t_idx > 0 and inter_delay_ms > 0:
                events.append(f"UserWait({inter_delay_ms})")
            for p_idx, tile in enumerate(triplet):
                if p_idx > 0 and intra_delay_ms > 0:
                    events.append(f"UserWait({intra_delay_ms})")
                events.append(f"DispatchPointer(0, 0, 0, {int(tile.cx)}, {int(tile.cy)}, 0, 0, 0, 0, 0, 0, 0)")
                events.append(f"DispatchPointer(0, 0, 1, {int(tile.cx)}, {int(tile.cy)}, 0, 0, 0, 0, 0, 0, 0)")
        self.monkey_burst(events)

    def keyevent(self, keycode: str) -> None:
        if self.dry_run:
            self.log(f"[DRY-RUN] Keyevent {keycode}")
            return
        self.adb(["shell", "input", "keyevent", keycode], timeout=5)

    def has_device(self) -> bool:
        out = self.adb_out(["devices"], timeout=6)
        devices = []
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        if self.serial:
            return self.serial in devices
        if not devices:
            return False
        self.serial = devices[0]
        return True

    def check_and_wake_screen(self) -> None:
        if not self.wake:
            return
        now = time.time()
        if now - self.last_wake_check_ts < 6.0:
            return
        self.last_wake_check_ts = now
        pwr = self.adb_out(["shell", "dumpsys", "power"], timeout=5)
        if "mWakefulness=Asleep" in pwr or "Display Power: state=OFF" in pwr:
            self.log("Layar HP mati/tidur. Mengirim sinyal bangun (WAKEUP)...")
            self.keyevent("KEYCODE_WAKEUP")
            time.sleep(0.3)
            self.keyevent("KEYCODE_MENU")

    @staticmethod
    def parse_app(text: str) -> Optional[ForegroundApp]:
        anr = re.search(r"Application Not Responding:\s*([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)", text)
        if anr:
            return ForegroundApp(anr.group(1), "Application Not Responding", text.strip())
        for pat in (
            r"u\d+\s+([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)/([^\s}\]]+)",
            r"\s([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)/([a-zA-Z0-9_.$]+)",
        ):
            m = re.search(pat, text)
            if m:
                return ForegroundApp(m.group(1), m.group(2), text.strip())
        return None

    def get_foreground_app(self) -> Optional[ForegroundApp]:
        out = self.adb_out(["shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"], timeout=4)
        for line in out.splitlines():
            if "mCurrentFocus" in line or "mFocusedApp" in line:
                app = self.parse_app(line)
                if app and app.package:
                    return app
        return None

    def is_game_ad(self, app: ForegroundApp) -> bool:
        if app.package == TARGET_PACKAGE:
            act = app.activity.lower()
            if any(k in act for k in AD_ACTIVITY_KEYWORDS):
                return True
            if act and "messagingunityplayeractivity" not in act and "unityplayeractivity" not in act:
                return True
            return False
        if app.package == "com.google.android.gms" and "adactivity" in app.activity.lower():
            return True
        return False

    def launch_game(self, reason: str = "") -> None:
        now = time.time()
        if now - self.last_launch_ts < LAUNCH_COOLDOWN:
            return
        self.last_launch_ts = now
        reason_str = f" ({reason})" if reason else ""
        self.log(f"Membuka kembali {TARGET_NAME}{reason_str}...")
        if self.dry_run:
            self.log("[DRY-RUN] am start target app")
            return

        res = self.adb_out([
            "shell", "am", "start",
            "-n", f"{TARGET_PACKAGE}/{TARGET_ACTIVITY}",
            "-a", "android.intent.action.MAIN",
            "-c", "android.intent.category.LAUNCHER",
        ], timeout=8)

        if "Error" in res or "does not exist" in res:
            self.adb_out([
                "shell", "monkey", "-p", TARGET_PACKAGE,
                "-c", "android.intent.category.LAUNCHER", "1"
            ], timeout=8)

    def close_blocked_app(self, package: str) -> None:
        name = BLOCKED_PACKAGES.get(package, package)
        self.log(f"Menutup aplikasi redirect: {name} ({package})")
        if self.dry_run:
            self.log(f"[DRY-RUN] force-stop {package}")
            return
        self.adb_out(["shell", "am", "force-stop", package], timeout=6)

    def capture_cv_image(self) -> Optional[np.ndarray]:
        raw = self.adb_bytes(["exec-out", "screencap"], timeout=6)
        if len(raw) >= 16:
            w = int.from_bytes(raw[0:4], "little")
            h = int.from_bytes(raw[4:8], "little")
            expected_len = 16 + w * h * 4
            if len(raw) >= expected_len and w > 0 and h > 0:
                arr = np.frombuffer(raw[16:expected_len], dtype=np.uint8).reshape((h, w, 4))
                return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        png_data = self.adb_bytes(["exec-out", "screencap", "-p"], timeout=6)
        if png_data.startswith(b"\x89PNG"):
            return cv2.imdecode(np.frombuffer(png_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        return None

    # =========================================================================
    # SMART AD HANDLING (STRICT 30s NO-TAP FOR SLOT ADS)
    # =========================================================================
    def find_ad_finish_button_by_ui(self) -> Optional[Tuple[str, str, int, int]]:
        raw_xml = self.adb_out(["shell", "uiautomator", "dump", "/data/local/tmp/ad_ui.xml"], timeout=6)
        if "dumped to" not in raw_xml:
            return None
        xml_data = self.adb_bytes(["shell", "cat", "/data/local/tmp/ad_ui.xml"], timeout=6)
        if not xml_data.startswith(b"<?xml"):
            return None

        try:
            root = ET.fromstring(xml_data)
        except Exception:
            return None

        finish_words = {"x", "×", "close", "tutup", "skip", "lewati", "next", "lanjut", ">", ">>", ">|", "»", "›"}
        bad_words = {"!", "¡", "i", "info", "feedback", "laporkan", "ad choices", "adchoices", "privacy"}

        for node in root.iter("node"):
            bounds = node.attrib.get("bounds", "")
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
            if not m:
                continue
            x1, y1, x2, y2 = map(int, m.groups())
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # DILARANG PERNAH KLIK DI POJOK KIRI ATAS (AREA TOMBOL ! / INFO)
            if cx <= 150 and cy <= 250:
                continue

            text = (node.attrib.get("text") or "").strip()
            desc = (node.attrib.get("content-desc") or "").strip()
            label = text or desc

            clickable = node.attrib.get("clickable", "false").lower() == "true"
            w, h = x2 - x1, y2 - y1

            # 1. Validasi teks/deskripsi tombol jika ada
            if label:
                raw = label.lower()
                if any(bad in raw for bad in bad_words):
                    continue

                if raw in finish_words or any(w in raw for w in ("close", "tutup", "skip", "lewati", "next", "lanjut", ">", ">>", ">|", "»", "›")):
                    # Tombol skip / X / > harus berada di area atas kanan (cy <= 280 dan cx >= 480)
                    if cy <= 280 and cx >= 480:
                        kind = "SKIP" if any(s in raw for s in (">", "skip", "lewati", "next", "»", "›")) else "X"
                        return kind, label, cx, cy

            # 2. Tombol clickable tanpa teks di pojok kanan atas (icon chevron > atau X)
            # Khusus node yang memang clickable="true" di area cy <= 220 dan cx >= 520
            if clickable and 25 <= w <= 110 and 25 <= h <= 110:
                if cx >= 520 and cy <= 220:
                    return ">", "Clickable_TR_Icon", cx, cy

        return None

    def find_ad_finish_button_by_cv(self, img: np.ndarray) -> Optional[Tuple[str, str, int, int]]:
        """Deteksi ikon tombol >, >>, dan X di pojok kanan atas menggunakan computer vision template matching."""
        try:
            # Area pojok kanan atas: x 500..710, y 50..220
            roi = img[50:220, 500:710]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            # 1. Chevron '>' (size 28x28)
            t_gt = np.zeros((28, 28), dtype=np.uint8)
            pts = np.array([[7, 4], [21, 14], [7, 24]], dtype=np.int32)
            cv2.polylines(t_gt, [pts], False, 255, 3)

            # 2. Double chevron '>>'
            t_gg = np.zeros((28, 36), dtype=np.uint8)
            pts1 = np.array([[5, 4], [16, 14], [5, 24]], dtype=np.int32)
            pts2 = np.array([[18, 4], [29, 14], [18, 24]], dtype=np.int32)
            cv2.polylines(t_gg, [pts1], False, 255, 3)
            cv2.polylines(t_gg, [pts2], False, 255, 3)

            # 3. 'X' cross (size 28x28)
            t_x = np.zeros((28, 28), dtype=np.uint8)
            cv2.line(t_x, (5, 5), (23, 23), 255, 3)
            cv2.line(t_x, (5, 23), (23, 5), 255, 3)

            best_match = None
            best_score = 0.72

            for t_name, t_mat in [('>', t_gt), ('>>', t_gg), ('X', t_x)]:
                res = cv2.matchTemplate(gray, t_mat, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                if max_val > best_score:
                    best_score = max_val
                    th, tw = t_mat.shape
                    cx = 500 + max_loc[0] + tw // 2
                    cy = 50 + max_loc[1] + th // 2
                    best_match = (t_name, f"CV_Template_{t_name}_{best_score:.2f}", cx, cy)

            return best_match
        except Exception:
            return None

    def find_ad_finish_button_by_ocr(self, img: np.ndarray) -> Optional[Tuple[str, str, int, int]]:
        if not os.path.exists(OCR_HELPER):
            return None
        tmp_path = f"/tmp/ad_ocr_{self.serial or 'dev'}.png"
        try:
            cv2.imwrite(tmp_path, img)
            res = subprocess.run([OCR_HELPER, tmp_path], capture_output=True, text=True, timeout=8)
            h, w, _ = img.shape
            bad_words = {"!", "¡", "info", "feedback", "laporkan"}
            for line in (res.stdout or "").splitlines():
                text, _, bbox = line.partition("|")
                label = text.strip()
                if not label or not bbox:
                    continue
                raw = label.lower()
                bx, by, bw, bh = [float(p) for p in bbox.split(",")]
                cx = int((bx + bw / 2) * w)
                cy = int((1 - by - bh / 2) * h)

                # DILARANG KLIK TOMBOL ! / INFO DI POJOK KIRI ATAS
                if cx <= 150 and cy <= 250:
                    continue
                if any(bad in raw for bad in bad_words):
                    continue

                kind = None
                if raw in {"x", "×", "close", "tutup"} or any(w in raw for w in ("close", "tutup")):
                    kind = "X"
                elif raw in {">", ">>", ">|", "»", "›", "skip", "lewati", "next", "lanjut"} or any(w in raw for w in ("skip", "lewati", ">")):
                    kind = "SKIP"
                if not kind:
                    continue
                # Hanya valid jika di pojok kanan atas (cy <= 280 dan cx >= 480)
                if cy <= 280 and cx >= 480:
                    return kind, label, cx, cy
        except Exception:
            pass
        return None

    def is_slot_or_ad_screen(self, img: np.ndarray) -> bool:
        """Deteksi apakah layar menampilkan iklan slot/video overlay agar tidak dimainkan sebagai papan puzzle."""
        if not os.path.exists(OCR_HELPER):
            return False
        tmp_path = f"/tmp/slot_chk_{self.serial or 'dev'}.png"
        try:
            cv2.imwrite(tmp_path, img)
            res = subprocess.run([OCR_HELPER, tmp_path], capture_output=True, text=True, timeout=6)
            full_text = (res.stdout or "").lower()
            slot_words = (
                "toto", "slot", "freespin", "scatter", "jackpot", "pragmatic",
                "pg soft", "pocket games", "hoki", "wede", "taruhan", "casino",
                "maxwin", "situs", "daftar", "deposit", "bonus new", "sensational",
                "game online", "download", "install", "unduh", "pasang", "play now", "mainkan sekarang", "lihat sekarang", "mintegral", "applovin", "mahjong", "ways",
            )
            return any(w in full_text for w in slot_words)
        except Exception:
            return False

    def is_real_gameplay_board(self, img: np.ndarray) -> bool:
        """Pastikan layar benar-benar papan gameplay (memiliki header Tarik & Tingkat)."""
        header = img[0:450, :]
        if not os.path.exists(OCR_HELPER):
            return True
        tmp_path = f"/tmp/board_hdr_{self.serial or 'dev'}.png"
        try:
            cv2.imwrite(tmp_path, header)
            res = subprocess.run([OCR_HELPER, tmp_path], capture_output=True, text=True, timeout=6)
            txt = (res.stdout or "").lower()
            return ("tarik" in txt or "rp" in txt) and ("tingkat" in txt or "level" in txt)
        except Exception:
            return False

    def handle_ad(self, app: ForegroundApp) -> None:
        now = time.time()
        if self.ad_start_ts is None:
            self.ad_start_ts = now
            self.ad_activity_name = app.activity
            self.last_ad_log_sec = -1
            self.ad_close_attempts = 0
            self.log(f"Iklan reward terdeteksi tayang: {app.activity}")
        elif app.activity and self.ad_activity_name != app.activity:
            # Update nama activity tanpa mereset timer ad_start_ts
            self.ad_activity_name = app.activity

        duration = now - self.ad_start_ts
        ad_sec = int(duration)

        if ad_sec > 0 and ad_sec % 5 == 0 and ad_sec != self.last_ad_log_sec:
            self.last_ad_log_sec = ad_sec
            if duration < 30.0:
                self.log(f"Menonton iklan ({ad_sec}s/30s) - Menunggu 30 detik tanpa sentuh layar agar tidak ke Chrome/Play Store...")
            else:
                self.log(f"Iklan sudah berjalan {ad_sec}s (>= 30s). Mulai mencari tombol penutup (>>, >, >|, X)...")

        # =====================================================================
        # ATURAN KETAT DARI PENGGUNA:
        # SEBELUM 30 DETIK PENUH, JANGAN KLIK ATAU CARI TOMBOL APAPUN DI LAYAR!
        # =====================================================================
        if duration < 30.0:
            return

        # =====================================================================
        # SETELAH 30 DETIK PENUH: BARU MULAI DETEKSI TOMBOL >>, >, >|, DAN X!
        # =====================================================================

        # 1. Periksa tombol penutup resmi via UI Automator di pojok kanan atas
        ui_btn = self.find_ad_finish_button_by_ui()
        if ui_btn:
            kind, label, bx, by = ui_btn
            self.log(f"Menemukan tombol penutup iklan ({kind} '{label}') via UI di ({bx}, {by}). Mengetuk...")
            self.tap_fast(bx, by)
            time.sleep(0.5)
            return

        # 2. Periksa tombol penutup visual (CV Template Matching untuk >, >>, X)
        img = self.capture_cv_image()
        if img is not None:
            cv_btn = self.find_ad_finish_button_by_cv(img)
            if cv_btn:
                kind, label, bx, by = cv_btn
                self.log(f"Menemukan tombol penutup iklan ({kind} '{label}') via Computer Vision di ({bx}, {by}). Mengetuk...")
                self.tap_fast(bx, by)
                time.sleep(0.5)
                return

            ocr_btn = self.find_ad_finish_button_by_ocr(img)
            if ocr_btn:
                kind, label, bx, by = ocr_btn
                self.log(f"Menemukan tombol penutup iklan ({kind} '{label}') via OCR di ({bx}, {by}). Mengetuk...")
                self.tap_fast(bx, by)
                time.sleep(0.5)
                return

        # 3. Mengirim tombol BACK setelah >= 33 detik (sangat efektif menutup iklan reward yang selesai)
        if duration >= 33.0 and (now - self.last_ad_close_attempt_ts >= 2.5):
            self.last_ad_close_attempt_ts = now
            self.log(f"Iklan durasi {ad_sec}s (>= 33s). Mengirim tombol BACK untuk menutup iklan...")
            self.keyevent("KEYCODE_BACK")
            time.sleep(0.5)
            return

        # 4. Fallback koordinat penutup aman di pojok kanan atas
        if now - self.last_ad_close_attempt_ts >= 2.5:
            self.last_ad_close_attempt_ts = now
            self.ad_close_attempts += 1
            verified_coords = [(660, 110), (653, 199), (670, 204), (675, 135), (626, 146), (665, 130)]
            coord_idx = (self.ad_close_attempts - 1) % len(verified_coords)
            kx, ky = verified_coords[coord_idx]
            self.log(f"Iklan berjalan {ad_sec}s (>= 30s). Mencoba koordinat penutup aman ({kx}, {ky})...")
            self.tap_fast(kx, ky)

        # 5. Stuck recovery jika > ad_timeout
        if duration >= self.ad_timeout:
            self.log(f"Iklan macet ({ad_sec}s >= {int(self.ad_timeout)}s). Membuka ulang game Zoo Tile...")
            self.launch_game(reason="iklan macet melebihi batas waktu")
            self.ad_start_ts = None
            self.ad_activity_name = ""

    # LOGIKA GAMEPLAY MATCH-3
    # =========================================================================
    def check_and_tap_popups(self, img: np.ndarray) -> bool:
        now = time.time()
        if now - self.last_claim_check_ts < 0.6:
            return False
        self.last_claim_check_ts = now

        if not os.path.exists(OCR_HELPER):
            return False

        tmp_path = f"/tmp/zoo_popup_{self.serial or 'dev'}.png"
        try:
            cv2.imwrite(tmp_path, img)
            res = subprocess.run([OCR_HELPER, tmp_path], capture_output=True, text=True, timeout=8)
            h, w, _ = img.shape
            popup_targets = {"klaim", "claim", "clalm", "lanjut", "next", "buka", "selesai", "terima", "ok", "gratis", "ambil", "hidupkan"}
            for line in (res.stdout or "").splitlines():
                text, _, bbox = line.partition("|")
                label = text.strip()
                if not label or not bbox:
                    continue
                raw = label.lower()
                if raw in popup_targets or any(t in raw for t in popup_targets):
                    bx, by, bw, bh = [float(p) for p in bbox.split(",")]
                    cx = int((bx + bw / 2) * w)
                    cy = int((1 - by - bh / 2) * h)
                    if 500 <= cy <= 1350:
                        self.log(f"POPUP DETEKSI: '{label}' di ({cx}, {cy}). Mengetuk...")
                        self.tap_fast(cx, cy)
                        if any(k in raw for k in ("klaim", "claim", "clalm", "selesai")):
                            self.total_levels_cleared += 1

                        # SETELAH KLIK KLAIM / GRATIS: WAJIB TUNGGU 30 DETIK TANPA MENYENTUH APAPUN!
                        self.ad_start_ts = time.time()
                        self.ad_activity_name = f"AdAfter_{label}"
                        self.last_ad_log_sec = -1
                        self.ad_close_attempts = 0
                        self.log(f"IKLAN DIMULAI SETELAH '{label}': Wajib menunggu 30 detik tanpa sentuh layar...")
                        time.sleep(1.0)
                        return True
        except Exception:
            pass
        return False

    def scan_board_and_tray(self, img: np.ndarray) -> Tuple[List[BoardTile], int]:
        board_roi = img[BOARD_Y_MIN:BOARD_Y_MAX, BOARD_X_MIN:BOARD_X_MAX]
        gray_b = cv2.cvtColor(board_roi, cv2.COLOR_BGR2GRAY)

        # Multi-threshold detection agar ubin berbayang/lapisan bawah terdeteksi optimal
        best_board_tiles: List[BoardTile] = []
        for thresh_val in [205, 185, 165]:
            thresh = (gray_b > thresh_val).astype(np.uint8)
            cnts, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            raw_board = []
            for c in cnts:
                x, y, w, h = cv2.boundingRect(c)
                if 65 <= w <= 105 and 65 <= h <= 105:
                    cx = BOARD_X_MIN + x + w // 2
                    cy = BOARD_Y_MIN + y + h // 2
                    raw_board.append(BoardTile(cx=cx, cy=cy, w=w, h=h))

            # Deduplikasi ubin pada threshold ini
            current_tiles: List[BoardTile] = []
            for t in raw_board:
                if not any(abs(t.cx - u.cx) < 15 and abs(t.cy - u.cy) < 15 for u in current_tiles):
                    current_tiles.append(t)

            if len(current_tiles) > len(best_board_tiles):
                best_board_tiles = current_tiles

        # Tray detection: gunakan thresh 190 agar slot kayu kosong tidak terhitung ubin
        tray_roi = img[TRAY_Y_MIN:TRAY_Y_MAX, BOARD_X_MIN:BOARD_X_MAX]
        gray_t = cv2.cvtColor(tray_roi, cv2.COLOR_BGR2GRAY)
        thresh_t = (gray_t > 190).astype(np.uint8)
        cnts_t, _ = cv2.findContours(thresh_t, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        raw_tray = []
        for c in cnts_t:
            x, y, w, h = cv2.boundingRect(c)
            if 40 <= w <= 100 and 40 <= h <= 100:
                cx = BOARD_X_MIN + x + w // 2
                cy = TRAY_Y_MIN + y + h // 2
                raw_tray.append((cx, cy))

        tray_tiles = []
        for cx, cy in sorted(raw_tray, key=lambda p: p[0]):
            if not any(abs(cx - ux) < 25 for ux, uy in tray_tiles):
                tray_tiles.append((cx, cy))

        return best_board_tiles, len(tray_tiles)

    def cluster_tiles_by_animal(self, img: np.ndarray, tiles: List[BoardTile]) -> dict[int, List[BoardTile]]:
        icons = []
        for t in tiles:
            icon = img[t.cy - 23 : t.cy + 23, t.cx - 23 : t.cx + 23]
            icons.append(icon)

        clusters: dict[int, List[int]] = {}
        for i, icon in enumerate(icons):
            matched = False
            for cid, indices in clusters.items():
                rep = icons[indices[0]]
                score = cv2.matchTemplate(icon, rep, cv2.TM_CCOEFF_NORMED)[0, 0]
                if score >= 0.78:
                    clusters[cid].append(i)
                    tiles[i].group_id = cid
                    matched = True
                    break
            if not matched:
                new_cid = len(clusters)
                clusters[new_cid] = [i]
                tiles[i].group_id = new_cid

        result_groups: dict[int, List[BoardTile]] = {}
        for cid, indices in clusters.items():
            result_groups[cid] = [tiles[idx] for idx in indices]

        return result_groups

    def play_gameplay_step(self, img: np.ndarray) -> bool:
        board_tiles, tray_count = self.scan_board_and_tray(img)

        # Jika nampan berisiko penuh (>= 5) atau ubin macet, periksa popup (misal tombol Gratis)
        if not board_tiles or tray_count >= 5 or self.stuck_tile_count >= 2:
            if self.check_and_tap_popups(img):
                self.no_tiles_count = 0
                self.stuck_tile_count = 0
                return True

        if not board_tiles:
            self.no_tiles_count += 1
            if self.no_tiles_count >= 2:
                self.no_tiles_count = 0
                if self.is_slot_or_ad_screen(img):
                    fake_ad_app = ForegroundApp(package=TARGET_PACKAGE, activity="SlotAdOverlay")
                    self.handle_ad(fake_ad_app)
                    return False
                self.check_and_tap_popups(img)
            return False

        self.no_tiles_count = 0

        # Validasi keamanan saat ubin sedikit: jika bukan papan gameplay dan ada kata iklan, anggap iklan
        if len(board_tiles) <= 8:
            if not self.is_real_gameplay_board(img):
                if self.is_slot_or_ad_screen(img):
                    fake_ad_app = ForegroundApp(package=TARGET_PACKAGE, activity="AdEndCardOverlay")
                    self.handle_ad(fake_ad_app)
                return False

        groups = self.cluster_tiles_by_animal(img, board_tiles)

        # 1. Prioritaskan kelompok dengan >= 3 ubin yang sama (triplet) via Monkey Burst
        all_triplets: List[List[BoardTile]] = []
        for cid, tile_list in groups.items():
            if len(tile_list) >= 3:
                all_triplets.append(tile_list[:3])

        if all_triplets:
            self.booster_stuck_count = 0
            self.stuck_tile_count = 0
            max_triplets = 2 if tray_count == 0 else 1
            selected = all_triplets[:max_triplets]
            t_count = len(selected)
            tiles_total = sum(len(t) for t in selected)
            info = ", ".join(f"Grup #{t[0].group_id} [{len(t)} ubin]" for t in selected)
            self.log(f"MATCH-3 BURST: Mengetuk {t_count} triplet ({tiles_total} ubin, {info}) super cepat | Papan: {len(board_tiles)}, Tray: {tray_count}/7")
            self.tap_triplets_burst(selected, intra_delay_ms=25, inter_delay_ms=100)
            self.total_matches += t_count
            time.sleep(0.06)
            return True

        # 2. Jika ada pasangan (pair = 2 ubin identik) dan nampan aman (tray_count <= 4)
        pairs: List[List[BoardTile]] = [t_list[:2] for t_list in groups.values() if len(t_list) >= 2]
        if pairs and tray_count <= 4:
            self.booster_stuck_count = 0
            self.stuck_tile_count = 0
            pair = pairs[0]
            self.log(f"MATCH-2 PAIR: Mengetuk 2 hewan identik (Grup #{pair[0].group_id}) cepat di [({pair[0].cx},{pair[0].cy}), ({pair[1].cx},{pair[1].cy})] | Tray: {tray_count}/7")
            self.tap_triplets_burst([pair], intra_delay_ms=25)
            time.sleep(0.06)
            return True

        # 3. Jika tidak ada triplet/pair dan nampan masih aman (<= 5 ubin), ambil 1 ubin pembuka
        if tray_count <= 5 and board_tiles:
            self.booster_stuck_count = 0
            largest_group = max(groups.values(), key=len)
            target_tile = largest_group[0]

            # Deteksi jika ubin yang sama diketuk berulang kali tanpa perubahan (misal ada popup modal Gratis)
            if self.last_target_coords and abs(self.last_target_coords[0] - target_tile.cx) < 10 and abs(self.last_target_coords[1] - target_tile.cy) < 10:
                self.stuck_tile_count += 1
                if self.stuck_tile_count >= 2:
                    self.log(f"Ubin di ({target_tile.cx}, {target_tile.cy}) tidak berubah ({self.stuck_tile_count}x). Memeriksa popup/modal Gratis...")
                    if self.check_and_tap_popups(img):
                        self.stuck_tile_count = 0
                        return True
                    self.log(f"BOOSTER ACTIVATED: Mengacak ubin (Shuffle) di ({BOOSTER_SHUFFLE[0]}, {BOOSTER_SHUFFLE[1]})...")
                    self.tap_fast(BOOSTER_SHUFFLE[0], BOOSTER_SHUFFLE[1])
                    self.stuck_tile_count = 0
                    time.sleep(0.3)
                    return True
            else:
                self.stuck_tile_count = 0

            self.last_target_coords = (target_tile.cx, target_tile.cy)
            self.log(f"STRATEGI: Mengambil 1 ubin pembuka di ({target_tile.cx}, {target_tile.cy}) untuk membuka ubin berikutnya...")
            self.tap_fast(target_tile.cx, target_tile.cy)
            time.sleep(0.06)
            return True

        # 4. Jika nampan berisiko penuh (>= 6 ubin): Gunakan booster
        self.booster_stuck_count += 1
        if self.booster_stuck_count <= 2:
            self.log(f"BOOSTER ACTIVATED: Mengacak ubin (Shuffle) & Wand di ({BOOSTER_SHUFFLE[0]}, {BOOSTER_SHUFFLE[1]})...")
            self.tap_fast(BOOSTER_SHUFFLE[0], BOOSTER_SHUFFLE[1])
            time.sleep(0.2)
            self.tap_fast(BOOSTER_WAND[0], BOOSTER_WAND[1])
            return True

        # Jika booster sudah diketuk 2 kali, paksa ambil 1 ubin agar permainan tidak macet
        self.booster_stuck_count = 0
        if board_tiles:
            largest_group = max(groups.values(), key=len)
            target_tile = largest_group[0]
            self.log(f"PAKSA JALAN: Mengambil ubin di ({target_tile.cx}, {target_tile.cy}) agar bot tidak macet...")
            self.tap_fast(target_tile.cx, target_tile.cy)
            time.sleep(0.1)
            return True

        return False

    def step(self) -> None:
        self.check_and_wake_screen()
        app = self.get_foreground_app()

        if not app or not app.package:
            return

        current_pkg = app.package
        current_act = app.activity

        if current_pkg != self.last_foreground_pkg or current_act != self.last_foreground_act:
            self.last_foreground_pkg = current_pkg
            self.last_foreground_act = current_act
            self.log(f"Foreground: {current_pkg} / {current_act}")

        # Game Zoo Tile aktif
        if current_pkg == TARGET_PACKAGE:
            # Jika sedang dalam periode tunggu iklan 30 detik (setelah klaim/gratis atau saat iklan aktif)
            if self.ad_start_ts is not None:
                duration = time.time() - self.ad_start_ts
                if duration < 30.0:
                    # WAJIB TUNGGU 30 DETIK TANPA MENYENTUH LAYAR!
                    fake_ad_app = ForegroundApp(package=TARGET_PACKAGE, activity=self.ad_activity_name or "PostAdWait")
                    self.handle_ad(fake_ad_app)
                    return

                # Durasi sudah >= 30 detik: jika masih di activity iklan, proses penutupannya
                if self.is_game_ad(app):
                    self.handle_ad(app)
                    return

                img = self.capture_cv_image()
                if img is not None:
                    if self.is_slot_or_ad_screen(img) or not self.is_real_gameplay_board(img):
                        fake_ad_app = ForegroundApp(package=TARGET_PACKAGE, activity="AdEndCardOverlay")
                        self.handle_ad(fake_ad_app)
                        return

                self.log(f"Iklan selesai setelah {duration:.1f} detik. Kembali ke gameplay Zoo Tile.")
                self.ad_start_ts = None
                self.ad_activity_name = ""

            if self.is_game_ad(app):
                self.handle_ad(app)
                return

            # Walaupun activity terbaca UnityPlayer, periksa apakah layar menampilkan iklan slot
            img = self.capture_cv_image()
            if img is not None and self.is_slot_or_ad_screen(img):
                fake_ad_app = ForegroundApp(package=TARGET_PACKAGE, activity="SlotAdOverlay")
                self.handle_ad(fake_ad_app)
                return

            if self.auto_gameplay:
                if img is not None:
                    self.play_gameplay_step(img)
            return

        # Iklan di package lain
        if self.is_game_ad(app):
            self.handle_ad(app)
            return

        if self.ad_start_ts is not None:
            self.ad_start_ts = None
            self.ad_activity_name = ""

        # Aplikasi redirect terlarang
        if current_pkg in BLOCKED_PACKAGES:
            self.close_blocked_app(current_pkg)
            self.last_launch_ts = 0.0
            time.sleep(0.2)
            self.launch_game(reason=f"keluar ke {BLOCKED_PACKAGES[current_pkg]}")
        else:
            self.launch_game(reason=f"foreground berpindah ke {current_pkg}")

    def run(self, once: bool = False) -> int:
        self.log("=" * 60)
        self.log("  ZOO TILE GUARDIAN & MATCH-3 BOT (v2.1)")
        self.log("=" * 60)
        self.log(f"Target App   : {TARGET_NAME}")
        self.log(f"Package      : {TARGET_PACKAGE}")
        self.log(f"Activity     : {TARGET_ACTIVITY}")
        self.log(f"Device       : {self.serial or 'Auto-detect'}")
        self.log(f"Auto Gameplay: {'Aktif (Auto Match-3)' if self.auto_gameplay else 'Nonaktif (Guardian Only)'}")
        self.log(f"Interval     : {self.interval} detik")
        self.log(f"Log File     : {LOG_FILE}")
        self.log("=" * 60)

        if not self.has_device():
            self.log("ERROR: Device Android tidak terdeteksi via ADB. Pastikan kabel USB & USB debugging aktif.")
            return 2

        self.log("Bot aktif memantau aplikasi & memainkan level...")

        try:
            while self.running:
                self.step()
                if once:
                    break
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.log("Bot dihentikan oleh pengguna.")
        except Exception as exc:
            self.log(f"Terjadi kesalahan: {exc}")
            return 1

        self.log(f"Bot penjaga telah selesai. Total matches: {self.total_matches}, Levels cleared: {self.total_levels_cleared}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bot Penjaga & Auto-Player Match-3 Zoo Tile")
    parser.add_argument("--serial", "-s", default="", help="Serial ADB jika terhubung lebih dari 1 device")
    parser.add_argument("--interval", "-i", type=float, default=DEFAULT_INTERVAL, help=f"Interval cek detik (default: {DEFAULT_INTERVAL})")
    parser.add_argument("--once", action="store_true", help="Jalankan satu kali pengecekan lalu selesai")
    parser.add_argument("--dry-run", action="store_true", help="Simulasi tanpa mengeksekusi klik")
    parser.add_argument("--no-wake", action="store_true", help="Jangan otomatis bangunkan layar jika layar mati")
    parser.add_argument("--no-gameplay", action="store_true", help="Hanya jalankan guardian tanpa auto match-3")
    parser.add_argument("--ad-timeout", type=float, default=75.0, help="Batas detik sebelum iklan macet dipulihkan")

    args = parser.parse_args()
    bot = ZooTileBot(
        serial=args.serial,
        interval=args.interval,
        dry_run=args.dry_run,
        wake=not args.no_wake,
        auto_gameplay=not args.no_gameplay,
        ad_timeout=args.ad_timeout,
    )
    return bot.run(once=args.once)


if __name__ == "__main__":
    sys.exit(main())
