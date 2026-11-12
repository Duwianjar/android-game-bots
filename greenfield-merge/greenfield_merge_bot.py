#!/usr/bin/env python3
"""
Greenfield Merge Guardian & Auto-Ad Bot

Alur kerja:
1. Menjaga Greenfield Merge tetap di foreground. Jika keluar ke Chrome atau Play Store, tutup app tersebut dan kembali ke game.
2. Ketika berada di game:
   - Jika muncul Halaman Tarik Dana / Dompet: klik icon '<' di pojok kiri atas (60, 135) untuk kembali ke permainan.
   - Jika muncul Pop-up Tarik Dana / Saldo Belum Cukup: klik tombol 'X' atau 'Konfirmasi' pada pop-up tersebut.
   - Jika ada pop-up hadiah (DAPATKAN / KLAIM / DOBEL / BUKA / GRATIS / LIHAT IKLAN), tekan tombol tersebut untuk memicu iklan berhadiah.
   - Jika di papan permainan, lakukan tap bebas/acak & gestur merge pada area item untuk memicu kemunculan iklan/hadiah.
3. Ketika iklan tayang:
   - Pantau durasi iklan (minimal 28 detik).
   - Deteksi tombol tutup iklan (X, Tutup, Skip, ikon pojok atas) via OCR, CV visual, dan UI tree.
   - Tekan tombol tutup atau gunakan fallback tombol BACK jika iklan selesai tetapi belum tertutup.
"""

from __future__ import annotations

import argparse
import os
import random
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

TARGET_PACKAGE = "com.xteleremobilecompanyltd.GreenfieldMerge"
TARGET_ACTIVITY = ".SplashActivity"
TARGET_NAME = "Greenfield Merge"

BLOCKED_PACKAGES = {
    "com.android.chrome": "Chrome",
    "com.chrome.beta": "Chrome Beta",
    "com.chrome.dev": "Chrome Dev",
    "com.google.android.apps.chrome": "Chrome",
    "com.android.vending": "Play Store",
}

LOG_FILE = os.path.expanduser("~/greenfield_merge_bot.log")
DEFAULT_INTERVAL = 0.35
OCR_HELPER = "/Users/macbookair/ocr_helper"
TAP_MARKER = "/Users/macbookair/scrcpy_tap_marker"

AD_CLOSE_MIN_SECONDS = 28.0
AD_CLOSE_CHECK_INTERVAL = 0.8
AD_STUCK_RESTART_SECONDS = 120.0

AD_ACTIVITY_KEYWORDS = (
    "ads",
    "adplayer",
    "fullscreenwebviewdisplay",
    "advert",
    "rewardvideo",
    "rewarded",
    "mbridge",
    "mintegral",
    "applovin",
    "vungle",
    "ironsource",
    "unity3d.ads",
    "bytedance",
    "kwai",
    "adactivity",
    "interstitial",
    "adview",
)


@dataclass
class ForegroundApp:
    package: str
    activity: str = ""
    source: str = ""


class GreenfieldMergeBot:
    def __init__(self, serial: str = "", interval: float = DEFAULT_INTERVAL, dry_run: bool = False):
        self.serial = serial.strip() or self.detect_device_serial()
        self.interval = interval
        self.dry_run = dry_run

        self.last_foreground = ""
        self.last_action = ""
        self.last_launch_ts = 0.0

        self.ad_start_ts: Optional[float] = None
        self.ad_activity = ""
        self.last_ad_close_check_ts = 0.0
        self.last_ad_close_tap_ts = 0.0
        self.ad_close_same_btn_count = 0
        self.ad_close_last_btn_key = ""

        self.last_board_tap_ts = 0.0
        self.last_reward_check_ts = 0.0
        self.last_reward_tap_ts = 0.0
        self.last_tarik_dana_check_ts = 0.0

        self._screen_width = 720
        self._screen_height = 1640
        self._update_screen_size()

    def log(self, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        print(line, flush=True)

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

    def _update_screen_size(self) -> None:
        res = self.adb_out(["shell", "wm", "size"], timeout=5)
        m = re.search(r"Physical size:\s*(\d+)x(\d+)", res)
        if m:
            self._screen_width = int(m.group(1))
            self._screen_height = int(m.group(2))

    def adb(self, args: list[str], timeout: int = 12) -> subprocess.CompletedProcess[str]:
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def adb_out(self, args: list[str], timeout: int = 12) -> str:
        try:
            res = self.adb(args, timeout=timeout)
            return (res.stdout or "").strip()
        except subprocess.TimeoutExpired:
            return ""
        except FileNotFoundError:
            self.log("ADB tidak ditemukan di PATH.")
            sys.exit(1)
        except Exception:
            return ""

    def adb_bytes(self, args: list[str], timeout: int = 12) -> bytes:
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += args
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=timeout)
            return res.stdout or b""
        except Exception:
            return b""

    def show_tap_marker(self, x: int, y: int, color: str = "blue", duration: float = 1.0, diameter: int = 50) -> None:
        if not os.path.exists(TAP_MARKER):
            return
        try:
            subprocess.Popen(
                [TAP_MARKER, str(int(x)), str(int(y)), color, str(float(duration)), str(int(diameter))],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def tap(self, x: int, y: int, color: str = "blue") -> None:
        self.show_tap_marker(x, y, color=color)
        if self.dry_run:
            self.log(f"[DRY-RUN] tap ({x}, {y})")
            return
        self.adb_out(["shell", "input", "tap", str(int(x)), str(int(y))], timeout=4)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 250) -> None:
        if self.dry_run:
            return
        self.adb_out([
            "shell", "input", "swipe",
            str(int(x1)), str(int(y1)),
            str(int(x2)), str(int(y2)),
            str(int(duration_ms))
        ], timeout=4)

    def capture_screenshot(self) -> Optional[Tuple[bytes, int, int]]:
        png_data = self.adb_bytes(["exec-out", "screencap", "-p"], timeout=8)
        if len(png_data) < 1000:
            return None
        try:
            from PIL import Image
            from io import BytesIO

            image = Image.open(BytesIO(png_data))
            return png_data, image.width, image.height
        except Exception:
            return png_data, self._screen_width, self._screen_height

    def dump_ui_tree(self) -> Optional[ET.Element]:
        self.adb_out(["shell", "rm", "-f", "/sdcard/gf_ui.xml"], timeout=2)
        res = self.adb_out(["shell", "uiautomator", "dump", "--compressed", "/sdcard/gf_ui.xml"], timeout=3)
        if "dumped to" not in res:
            return None
        xml_text = self.adb_out(["shell", "cat", "/sdcard/gf_ui.xml"], timeout=3)
        if "<hierarchy" not in xml_text:
            return None
        try:
            return ET.fromstring(xml_text)
        except Exception:
            return None

    @staticmethod
    def parse_bounds(bounds: str) -> Optional[Tuple[int, int]]:
        nums = [int(n) for n in re.findall(r"\d+", bounds)]
        if len(nums) == 4:
            return (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2
        return None

    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    def ocr_screen(self, prefix: str = "gf") -> list[Tuple[str, str, int, int]]:
        if not os.path.exists(OCR_HELPER):
            return []
        screenshot = self.capture_screenshot()
        if not screenshot:
            return []
        png_data, width, height = screenshot
        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
        screenshot_path = f"/tmp/gf_{prefix}_{safe_serial}.png"
        try:
            with open(screenshot_path, "wb") as f:
                f.write(png_data)
            res = subprocess.run([OCR_HELPER, screenshot_path], capture_output=True, text=True, timeout=8)
        except Exception:
            return []
        finally:
            try:
                if os.path.exists(screenshot_path):
                    os.remove(screenshot_path)
            except Exception:
                pass

        entries: list[Tuple[str, str, int, int]] = []
        for line in (res.stdout or "").splitlines():
            text, _, bbox = line.partition("|")
            text = text.strip()
            bbox = bbox.strip()
            if not text or not bbox:
                continue
            try:
                bx, by, bw, bh = [float(p) for p in bbox.split(",")]
                cx = int((bx + bw / 2) * width)
                cy = int((1 - by - bh / 2) * height)
                entries.append((text, bbox, cx, cy))
            except Exception:
                continue
        return entries

    def get_foreground_app(self) -> Optional[ForegroundApp]:
        checks = [
            (["shell", "dumpsys", "window", "displays"], ("mCurrentFocus",)),
            (["shell", "dumpsys", "activity", "activities"], ("topResumedActivity", "mResumedActivity")),
        ]
        for args, keywords in checks:
            out = self.adb_out(args, timeout=8)
            for line in out.splitlines():
                if any(k in line for k in keywords):
                    m = re.search(r"([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.$]+)", line)
                    if m:
                        return ForegroundApp(package=m.group(1), activity=m.group(2), source=line.strip())
        return None

    def has_top_menarik(self) -> bool:
        """Deteksi apakah tombol 'Menarik' atau Saldo 'RP' ada di bagian atas layar."""
        entries = self.ocr_screen("check_menarik")
        for text, _bbox, cx, cy in entries:
            norm = self.normalize_text(text)
            if cy < int(self._screen_height * 0.22):
                if any(w in norm for w in ("menarik", "menarlk", "tarik", "saldo", "level")):
                    return True
                if "rp" in norm and len(norm) > 2:
                    return True
        return False

    def is_game_ad(self, app: Optional[ForegroundApp]) -> bool:
        if not app:
            return False
        act = (app.activity or "").lower()
        if "splashactivity" in act:
            return False
        if any(keyword in act for keyword in AD_ACTIVITY_KEYWORDS):
            return True
        if app.package == TARGET_PACKAGE:
            if "fullscreenwebviewdisplay" in act:
                return True
            # Halaman tarik dana bukan iklan, ditangani terpisah oleh handle_tarik_dana
            return False
        return False

    def launch_game(self, reason: str = "") -> None:
        now = time.time()
        if now - self.last_launch_ts < 3.0:
            return
        self.last_launch_ts = now
        self.log(f"Membuka game {TARGET_NAME} ({reason})...")
        self.adb_out([
            "shell", "am", "start",
            "-n", f"{TARGET_PACKAGE}/{TARGET_ACTIVITY}"
        ], timeout=8)

    def close_blocked_app_and_return(self, package: str) -> None:
        self.log(f"Menutup aplikasi redirect: {package}")
        self.adb_out(["shell", "am", "force-stop", package], timeout=5)
        time.sleep(0.5)
        self.launch_game(reason=f"keluar dari {package}")

    # --- PENDETEKSI HALAMAN & POPUP TARIK DANA ---

    def handle_tarik_dana_page_and_popup(self) -> bool:
        """Menutup halaman Tarik Dana (icon < di pojok kiri atas) atau popup Tarik Dana (icon X)."""
        now = time.time()
        if now - self.last_tarik_dana_check_ts < 1.0:
            return False
        self.last_tarik_dana_check_ts = now

        entries = self.ocr_screen("tarik_dana_check")
        is_tarik_page = False
        is_tarik_popup = False
        konfirmasi_point = None

        for text, _bbox, cx, cy in entries:
            norm = self.normalize_text(text)

            # 1. Judul Tarik Dana di header atas
            if ("tarikdana" in norm or "saldouangtunai" in norm or "pilihjumlah" in norm) and cy < int(self._screen_height * 0.30):
                is_tarik_page = True

            # 2. Pop-up dialog saldo belum cukup / penarikan
            if any(k in norm for k in ("saldotunaimencapai", "bisaditarik", "namunmasihkurang", "petunjukpenarikan")):
                is_tarik_popup = True

            if "konfirmasi" in norm and 500 <= cy <= 1300:
                konfirmasi_point = (cx, cy)

        # Kasus A: Pop-up dialog di atas halaman tarik dana
        if is_tarik_popup:
            if konfirmasi_point:
                kx, ky = konfirmasi_point
                self.log(f"[POPUP TARIK DANA]: Menutup dialog dengan klik 'Konfirmasi' di ({kx}, {ky})...")
                self.tap(kx, ky, color="yellow")
                time.sleep(0.6)
                return True
            else:
                # Tap X pojok kanan atas dialog
                self.log("[POPUP TARIK DANA]: Menutup dialog pop-up...")
                self.tap(635, 136, color="yellow")
                time.sleep(0.6)
                return True

        # Kasus B: Halaman penuh Tarik Dana -> Klik icon '<' di pojok kiri atas
        if is_tarik_page:
            tap_x = 60
            tap_y = 135
            self.log(f"[HALAMAN TARIK DANA]: Terdeteksi -> Klik icon '<' di pojok kiri atas ({tap_x}, {tap_y}) untuk kembali ke game...")
            self.tap(tap_x, tap_y, color="green")
            time.sleep(0.8)
            return True

        return False

    # --- PENDETEKSI TOMBOL TUTUP IKLAN ---

    def find_ad_finish_button_by_ui(self) -> Optional[Tuple[str, str, int, int]]:
        root = self.dump_ui_tree()
        if root is None:
            return None

        finish_words = {"x", "×", "close", "tutup", "skip", "lewati", "next", "lanjut", ">", "›", "»"}
        screen_w = self._screen_width
        screen_h = self._screen_height

        for node in root.iter("node"):
            text = (node.get("text") or "").strip()
            desc = (node.get("content-desc") or "").strip()
            label = text or desc
            if not label:
                continue
            norm = self.normalize_text(label)
            raw = label.strip().lower()

            if raw not in finish_words and norm not in finish_words and not any(token in norm for token in ("close", "tutup", "skip", "lewati")):
                continue

            center = self.parse_bounds(node.get("bounds", ""))
            if not center:
                continue
            x, y = center
            if y > screen_h * 0.88:
                continue
            kind = "X" if raw in {"x", "×", "close", "tutup"} else "NEXT"
            return kind, label, x, y

        candidates = []
        for node in root.iter("node"):
            klass = (node.get("class") or "").lower()
            if "imageview" not in klass and "button" not in klass:
                continue
            bounds = node.get("bounds", "")
            match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
            if not match:
                continue
            x1, y1, x2, y2 = map(int, match.groups())
            w = x2 - x1
            h = y2 - y1
            if w < 16 or h < 16 or w > 85 or h > 85:
                continue
            x = (x1 + x2) // 2
            y = (y1 + y2) // 2
            if y < screen_h * 0.20 and (x < screen_w * 0.25 or x > screen_w * 0.75):
                candidates.append((x, y, bounds))

        if candidates:
            x, y, bounds = candidates[0]
            return "X", f"UI icon {bounds}", x, y
        return None

    def find_ad_finish_button_by_ocr(self, png_data: bytes, width: int, height: int) -> Optional[Tuple[str, str, int, int]]:
        if not os.path.exists(OCR_HELPER):
            return None
        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
        screenshot_path = f"/tmp/gf_ocr_close_{safe_serial}.png"
        try:
            with open(screenshot_path, "wb") as f:
                f.write(png_data)
            res = subprocess.run([OCR_HELPER, screenshot_path], capture_output=True, text=True, timeout=8)
        except Exception:
            return None
        finally:
            try:
                if os.path.exists(screenshot_path):
                    os.remove(screenshot_path)
            except Exception:
                pass

        finish_labels = {
            "x": "X", "close": "X", "tutup": "X",
            "skip": "NEXT", "lewati": "NEXT", "next": "NEXT", "lanjut": "NEXT"
        }
        for line in (res.stdout or "").splitlines():
            text, _, bbox = line.partition("|")
            label = text.strip()
            if not label or not bbox:
                continue
            norm = self.normalize_text(label)
            raw = label.strip().lower()
            if any(k in norm for k in ("menarik", "tarik", "saldo", "level", "rp")):
                continue

            kind = None
            if raw in {">", "›", "»", "→"}:
                kind = "NEXT"
            elif norm in finish_labels:
                kind = finish_labels[norm]
            elif any(token in norm for token in ("close", "tutup")):
                kind = "X"
            elif any(token in norm for token in ("skip", "lewati", "next", "lanjut")):
                kind = "NEXT"

            if not kind:
                continue
            try:
                bx, by, bw, bh = [float(p) for p in bbox.split(",")]
                cx = int((bx + bw / 2) * width)
                cy = int((1 - by - bh / 2) * height)
                if cy > height * 0.88:
                    continue
                if cy < height * 0.25 or cx > width * 0.70 or cx < width * 0.30:
                    return kind, label, cx, cy
            except Exception:
                continue
        return None

    def find_ad_finish_button_by_cv(self, png_data: bytes, width: int, height: int) -> Optional[Tuple[str, str, int, int]]:
        try:
            import cv2
            import numpy as np
        except Exception:
            return None

        arr = np.frombuffer(png_data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        search_areas = [
            (int(width * 0.70), 0, width, int(height * 0.15)),      # Kanan atas
            (0, 0, int(width * 0.30), int(height * 0.15)),          # Kiri atas
        ]

        for ax1, ay1, ax2, ay2 in search_areas:
            roi = img[ay1:ay2, ax1:ax2]
            if roi.size == 0:
                continue
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 80, 180)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w < 14 or h < 14 or w > 85 or h > 85:
                    continue
                aspect = w / float(h)
                if aspect < 0.5 or aspect > 2.0:
                    continue

                abs_x = ax1 + x + w // 2
                abs_y = ay1 + y + h // 2
                if abs_y < 50:
                    continue
                return "X", "OpenCV corner icon", abs_x, abs_y
        return None

    def find_ad_finish_button(self) -> Optional[Tuple[str, str, int, int, str]]:
        if self.has_top_menarik():
            return None

        screenshot = self.capture_screenshot()
        if screenshot:
            png_data, width, height = screenshot
            ocr_found = self.find_ad_finish_button_by_ocr(png_data, width, height)
            if ocr_found:
                kind, label, x, y = ocr_found
                return kind, label, x, y, "ocr"

            cv_found = self.find_ad_finish_button_by_cv(png_data, width, height)
            if cv_found:
                kind, label, x, y = cv_found
                return kind, label, x, y, "cv"

        ui_found = self.find_ad_finish_button_by_ui()
        if ui_found:
            kind, label, x, y = ui_found
            return kind, label, x, y, "ui"

        return None

    def try_finish_ad(self, app: Optional[ForegroundApp]) -> None:
        if not app or not self.is_game_ad(app):
            return

        now = time.time()
        if self.ad_start_ts is None:
            self.ad_start_ts = now
            self.ad_activity = app.activity
            self.log(f"IKLAN DIMULAI: {app.package}/{app.activity}")

        elapsed = now - self.ad_start_ts

        if elapsed < AD_CLOSE_MIN_SECONDS:
            if int(elapsed) % 6 == 0 and int(elapsed) > 0:
                self.log(f"Iklan tayang: {int(elapsed)}s / {int(AD_CLOSE_MIN_SECONDS)}s...")
            return

        if now - self.last_ad_close_check_ts < AD_CLOSE_CHECK_INTERVAL:
            return
        self.last_ad_close_check_ts = now

        found = self.find_ad_finish_button()
        if found:
            kind, label, x, y, source = found
            self.log(f"TOMBOL TUTUP IKLAN [{kind} via {source}]: '{label}' di ({x}, {y}) -> Klik Tutup!")
            self.tap(x, y, color="red")
            self.last_ad_close_tap_ts = now
            time.sleep(1.2)
            return

        # Fallback tombol BACK jika iklan sudah berjalan > 35 detik dan tombol tutup belum terdeteksi
        if elapsed >= (AD_CLOSE_MIN_SECONDS + 6.0):
            if now - self.last_ad_close_tap_ts >= 3.5:
                self.last_ad_close_tap_ts = now
                self.log(f"FALLBACK CLOSE: Iklan sudah tayang {int(elapsed)}s, mencoba tekan tombol BACK...")
                self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
                time.sleep(1.0)

    # --- PENDETEKSI POP-UP HADIAH / REWARD BUTTON ---

    def find_reward_popup_button(self) -> Optional[Tuple[str, int, int]]:
        entries = self.ocr_screen("popup_reward")
        target_keywords = (
            "dapatkan", "klaim", "claim", "dobel", "buka", "gratis",
            "terima", "lihatiklan", "nonton", "gandakan", "ambil", "super"
        )
        for text, _bbox, cx, cy in entries:
            norm = self.normalize_text(text)
            if 350 <= cy <= (self._screen_height - 180):
                if any(kw in norm for kw in target_keywords):
                    if "menarik" not in norm and "tarik" not in norm:
                        return text, cx, cy
        return None

    # --- KLIK BEBAS AREA PAPAN GAME & GESTUR MERGE (MEMICU IKLAN) ---

    def do_board_random_tap_burst(self, tap_count: int = 15) -> None:
        """Melakukan ketukan bebas pada area papan gambar Greenfield Merge untuk memicu iklan."""
        min_x = int(self._screen_width * 0.16)
        max_x = int(self._screen_width * 0.84)
        min_y = int(self._screen_height * 0.35)
        max_y = int(self._screen_height * 0.78)

        self.log(f"[GAMEPLAY]: Klik bebas {tap_count}x pada area gambar papan untuk memicu iklan...")
        for i in range(tap_count):
            rx = random.randint(min_x, max_x)
            ry = random.randint(min_y, max_y)
            self.tap(rx, ry, color="blue")
            time.sleep(0.08)

            # Sesekali lakukan gestur geser / merge kecil antar petak berdekatan
            if i % 6 == 0:
                dx = rx + random.choice([-80, 80])
                dy = ry + random.choice([-80, 80])
                self.swipe(rx, ry, dx, dy, duration_ms=200)

        self.last_board_tap_ts = time.time()

    # --- STEP UTAMA ---

    def step(self) -> None:
        app = self.get_foreground_app()
        if not app:
            self.launch_game("foreground kosong")
            return

        if app.package != self.last_foreground:
            self.last_foreground = app.package
            self.log(f"Foreground: {app.package}/{app.activity}")

        # 1. Jika terlempar ke Chrome atau Play Store, tutup dan kembali ke game
        if app.package in BLOCKED_PACKAGES:
            self.close_blocked_app_and_return(app.package)
            return

        # 2. Jika bukan paket Greenfield Merge dan bukan app sistem penting, buka kembali game
        if app.package != TARGET_PACKAGE:
            self.launch_game(f"keluar ke {app.package}")
            return

        # 3. Cek apakah ada halaman Tarik Dana atau Pop-up Saldo/Penarikan -> Tutup (icon < di kiri atas atau tombol X)
        if self.handle_tarik_dana_page_and_popup():
            return

        # 4. Jika sedang berada dalam tayangan iklan (ad activity atau FullScreenWebViewDisplay)
        if self.is_game_ad(app):
            self.try_finish_ad(app)
            return

        # 5. Berada di dalam game Greenfield Merge utama
        if self.ad_start_ts is not None:
            self.log(f"IKLAN SELESAI: total durasi {int(time.time() - self.ad_start_ts)}s. Kembali ke permainan.")
            self.ad_start_ts = None
            self.ad_activity = ""
            time.sleep(0.5)

        # 6. Cek apakah ada popup hadiah / klaim / dapatkan yang muncul di layar
        now = time.time()
        if now - self.last_reward_check_ts >= 1.2:
            self.last_reward_check_ts = now
            reward_btn = self.find_reward_popup_button()
            if reward_btn:
                btn_text, bx, by = reward_btn
                self.log(f"POPUP HADIAH TERDETEKSI: Tombol '{btn_text}' di ({bx}, {by}) -> Klik untuk buka iklan!")
                self.tap(bx, by, color="green")
                self.last_reward_tap_ts = now
                time.sleep(1.8)
                return

        # 7. Klik bebas pada area gambar di papan untuk terus memicu iklan
        if now - self.last_board_tap_ts >= 2.0:
            self.do_board_random_tap_burst(tap_count=random.randint(12, 18))

    def run(self) -> None:
        self.log("=" * 60)
        self.log(f"=== BOT GREENFIELD MERGE DIMULAI ({TARGET_PACKAGE}) ===")
        self.log("=" * 60)
        try:
            while True:
                self.step()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.log("Bot Greenfield Merge dihentikan oleh pengguna.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot Greenfield Merge: Auto Klik Papan Bebas + Buka & Selesaikan Iklan")
    parser.add_argument("--serial", "-s", default="", help="Serial ADB device")
    parser.add_argument("--interval", "-i", type=float, default=DEFAULT_INTERVAL, help="Jeda loop (detik)")
    parser.add_argument("--dry-run", action="store_true", help="Simulasi tanpa tap fisik")

    args = parser.parse_args()
    bot = GreenfieldMergeBot(serial=args.serial, interval=args.interval, dry_run=args.dry_run)
    bot.run()


if __name__ == "__main__":
    main()
