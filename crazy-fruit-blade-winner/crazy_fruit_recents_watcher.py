#!/usr/bin/env python3
"""
Crazy Fruit Blade Winner - Recent Apps Watcher Bot

Fungsi:
- Memantau foreground app di HP Android melalui ADB.
- Jika terdeteksi di luar game Crazy Fruit Blade Winner (misal Chrome, Play Store,
  Home Screen / Launcher, atau aplikasi lain), bot akan:
  1. Membuka riwayat aplikasi (Recent Apps).
  2. Memilih dan membuka kartu riwayat Crazy Fruit Blade Winner.
  3. Membawa task game kembali ke layar depan tanpa mereset progress/iklan yang sedang berjalan.
  4. Jika aplikasi tertutup total, membuka ulang game secara otomatis.
- Deteksi Halaman Iklan:
  Mendeteksi saat halaman iklan terbuka, melacak durasi tayang iklan secara realtime
  (dalam detik dan menit), dan mencatat saat iklan selesai ditutup dan kembali ke game utama.
"""

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional, Tuple
import cv2
import numpy as np

TARGET_PACKAGE = "com.starlightgame.crazyfruitbladewinner"
TARGET_ACTIVITY = "com.google.firebase.MessagingUnityPlayerActivity"
RECENTS_PACKAGE = "com.android.quickstep"

DEFAULT_ADB_BIN = "/Users/macbookair/Library/Android/sdk/platform-tools/adb"
TAP_MARKER_BIN = "/Users/macbookair/scrcpy_tap_marker"
OCR_HELPER_BIN = "/Users/macbookair/ocr_helper"
LOG_FILE = os.path.expanduser("~/crazy_fruit_recents_watcher.log")

# Kata kunci activity iklan yang umum
AD_ACTIVITY_KEYWORDS = (
    "ads",
    "adplayer",
    "advert",
    "adview",
    "rewardvideo",
    "rewarded",
    "reward",
    "applovin",
    "unity3d.ads",
    "unityads",
    "mbridge",
    "mintegral",
    "vungle",
    "ironsource",
    "chartboost",
    "adcolony",
    "audience",
    "facebook.ads",
    "fullscreenwebviewdisplay",
    "webviewdisplay",
    "kwai",
    "alliance",
    "adcommon",
    "emptyshell",
    "pangle",
    "bytedance",
    "ksad",
    "moloco",
    "thinkup",
    "smartdigimkt",
    "gms.ads",
)


def format_duration(seconds: float) -> str:
    """Format durasi ke representasi ramah detik dan menit."""
    total_sec = max(0, int(round(seconds)))
    if total_sec < 60:
        return f"{total_sec} detik"
    mins = total_sec // 60
    rem_sec = total_sec % 60
    if rem_sec == 0:
        return f"{mins} menit ({total_sec} detik)"
    return f"{mins} menit {rem_sec} detik ({total_sec} detik)"


def friendly_act_name(act: str) -> str:
    """Menyederhanakan nama activity dan mencantumkan SDK iklan jika terdeteksi."""
    simple_name = act.split(".")[-1]
    act_lower = act.lower()
    sdk = ""
    if "kwai" in act_lower:
        sdk = "Kwai Ads"
    elif "applovin" in act_lower:
        sdk = "AppLovin"
    elif "unity3d" in act_lower or "unityads" in act_lower:
        sdk = "Unity Ads"
    elif "facebook" in act_lower or "audience" in act_lower:
        sdk = "Meta / FB Ads"
    elif "vungle" in act_lower:
        sdk = "Vungle"
    elif "ironsource" in act_lower:
        sdk = "IronSource"
    elif "moloco" in act_lower:
        sdk = "Moloco"
    elif "bytedance" in act_lower or "pangle" in act_lower:
        sdk = "Pangle / TikTok"
    elif "google" in act_lower or "gms.ads" in act_lower:
        sdk = "Google AdMob"
    elif "thinkup" in act_lower:
        sdk = "ThinkUp Ads"
    elif "mbridge" in act_lower or "mintegral" in act_lower:
        sdk = "Mintegral"

    if sdk:
        return f"{simple_name} [{sdk}]"
    return simple_name


class CrazyFruitRecentsWatcher:
    def __init__(self, serial: str = "", interval: float = 0.6):
        self.serial = serial.strip()
        self.interval = interval
        self.adb_bin = self._find_adb()
        self.last_foreground_pkg = ""
        self.last_foreground_act = ""
        self.last_heartbeat_ts = 0.0
        self.last_recovery_ts = 0.0

        # State pelacakan iklan
        self.ad_active: bool = False
        self.ad_start_ts: Optional[float] = None
        self.current_ad_activity: str = ""
        self.last_ad_log_ts: float = 0.0

        # State pelacakan tombol pojok iklan & visual marker di scrcpy
        self.active_marker_proc: Optional[subprocess.Popen] = None
        self.last_marker_coord: Optional[Tuple[int, int]] = None
        self.last_marker_type: str = ""
        self.last_marker_pos: str = ""
        self.last_marker_start_ts: float = 0.0
        self.last_btn_log_ts: float = 0.0
        self.last_ad_screencap_ts: float = 0.0
        self.last_detected_btn: Optional[dict] = None

    def _find_adb(self) -> str:
        if os.path.exists(DEFAULT_ADB_BIN) and os.access(DEFAULT_ADB_BIN, os.X_OK):
            return DEFAULT_ADB_BIN
        which_adb = subprocess.run(["which", "adb"], capture_output=True, text=True)
        if which_adb.returncode == 0 and which_adb.stdout.strip():
            return which_adb.stdout.strip()
        return "adb"

    def log(self, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        print(line, flush=True)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def adb_cmd(self, args: list[str], timeout: int = 8) -> subprocess.CompletedProcess[str]:
        cmd = [self.adb_bin]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def adb_out(self, args: list[str], timeout: int = 8) -> str:
        try:
            res = self.adb_cmd(args, timeout=timeout)
            return (res.stdout or "").strip()
        except subprocess.TimeoutExpired:
            self.log(f"ADB timeout: {' '.join(args)}")
            return ""
        except Exception as e:
            self.log(f"ADB error: {e}")
            return ""

    def show_marker(self, x: int, y: int, color: str = "cyan") -> None:
        if os.path.exists(TAP_MARKER_BIN) and os.access(TAP_MARKER_BIN, os.X_OK):
            try:
                subprocess.Popen(
                    [TAP_MARKER_BIN, str(int(x)), str(int(y)), color, "1.0", "50"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass

    def tap(self, x: int, y: int, color: str = "cyan") -> None:
        self.show_marker(x, y, color=color)
        self.adb_out(["shell", "input", "tap", str(int(x)), str(int(y))], timeout=5)

    def clear_ad_marker(self) -> None:
        """Menghilangkan visual marker penanda warna di jendela scrcpy."""
        if self.active_marker_proc is not None:
            try:
                self.active_marker_proc.terminate()
                self.active_marker_proc.wait(timeout=0.2)
            except Exception:
                pass
            self.active_marker_proc = None
        self.last_marker_coord = None
        self.last_marker_type = ""
        self.last_marker_pos = ""
        self.last_marker_start_ts = 0.0

    def update_ad_marker(self, btn: Optional[dict], now: float) -> None:
        """
        Memperbarui atau mematikan visual marker di scrcpy berdasarkan tombol iklan yang terdeteksi.
        """
        if btn is not None:
            pos = btn["pos"]
            btype = btn["type"]
            bx = btn["x"]
            by = btn["y"]

            is_new = (
                self.last_marker_coord is None
                or self.last_marker_type != btype
                or self.last_marker_pos != pos
                or abs(self.last_marker_coord[0] - bx) > 25
                or abs(self.last_marker_coord[1] - by) > 25
            )

            if is_new or now - self.last_btn_log_ts >= 4.0:
                self.log(
                    f"[IKLAN][TOMBOL] Ditemukan tombol '{btype}' di {pos} "
                    f"koordinat ({bx}, {by}) | Visual marker (kuning) AKTIF di scrcpy"
                )
                self.last_btn_log_ts = now

            if is_new or now - self.last_marker_start_ts >= 2.0:
                if self.active_marker_proc is not None:
                    try:
                        self.active_marker_proc.terminate()
                    except Exception:
                        pass
                if os.path.exists(TAP_MARKER_BIN) and os.access(TAP_MARKER_BIN, os.X_OK):
                    try:
                        self.active_marker_proc = subprocess.Popen(
                            [TAP_MARKER_BIN, str(int(bx)), str(int(by)), "yellow", "3.5", "65"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    except Exception:
                        self.active_marker_proc = None
                self.last_marker_coord = (bx, by)
                self.last_marker_type = btype
                self.last_marker_pos = pos
                self.last_marker_start_ts = now
        else:
            if self.last_marker_coord is not None:
                self.log("[IKLAN][TOMBOL] Tombol tidak lagi terdeteksi | Visual marker DIHILANGKAN")
                self.clear_ad_marker()

    def detect_ad_corner_button(self, img: np.ndarray) -> Optional[dict]:
        """
        Mendeteksi tombol 'X', '>', atau '>|' di Pojok Kanan Atas dan Pojok Kiri Atas layar.
        Area pojok atas dibatasi secara spesifik (x: w-160..w-5, y: 50..180) agar tidak
        keliru mendeteksi teks isi halaman iklan atau status bar jam.
        """
        if img is None:
            return None
        h, w = img.shape[:2]

        corners = [
            ("POJOK KANAN ATAS", max(0, w - 160), 50, min(w, w - 5), 180),
            ("POJOK KIRI ATAS", 5, 50, min(w, 160), 180),
        ]

        for pos_name, x1, y1, x2, y2 in corners:
            crop = img[y1:y2, x1:x2]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            candidates = []

            # 1. Deteksi lingkaran tombol (HoughCircles)
            circles = cv2.HoughCircles(
                gray,
                cv2.HOUGH_GRADIENT,
                dp=1.2,
                minDist=25,
                param1=50,
                param2=20,
                minRadius=14,
                maxRadius=38,
            )
            if circles is not None:
                for c in circles[0]:
                    cx, cy, r = int(c[0]), int(c[1]), int(c[2])
                    candidates.append((cx, cy, int(r * 1.3)))

            # 2. Deteksi kontur tombol (kotak / silang / panah)
            for thresh_val in [180, 110]:
                _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
                cnts, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                for c in cnts:
                    area = cv2.contourArea(c)
                    if 50 < area < 3000:
                        bx, by, bw, bh = cv2.boundingRect(c)
                        if 0.70 < bw / float(bh) < 1.45 and 18 <= max(bw, bh) <= 70:
                            candidates.append((bx + bw // 2, by + bh // 2, max(bw, bh)))

            best_btn = None
            best_score = 0.0

            for cx, cy, sz in candidates:
                rad = max(12, sz // 2 + 3)
                rx1, ry1 = max(0, cx - rad), max(0, cy - rad)
                rx2, ry2 = min(crop.shape[1], cx + rad), min(crop.shape[0], cy + rad)
                roi = gray[ry1:ry2, rx1:rx2]
                if roi.shape[0] < 14 or roi.shape[1] < 14:
                    continue

                if np.mean(roi) < 128:
                    roi_inv = cv2.bitwise_not(roi)
                else:
                    roi_inv = roi
                _, bin_roi = cv2.threshold(roi_inv, 160, 255, cv2.THRESH_BINARY_INV)
                rh, rw = bin_roi.shape

                # Template X (diagonal simetris)
                d1 = np.zeros((rh, rw), dtype=np.uint8)
                cv2.line(d1, (int(rw * 0.15), int(rh * 0.15)), (int(rw * 0.85), int(rh * 0.85)), 255, max(2, int(rw * 0.12)))
                d2 = np.zeros((rh, rw), dtype=np.uint8)
                cv2.line(d2, (int(rw * 0.85), int(rh * 0.15)), (int(rw * 0.15), int(rh * 0.85)), 255, max(2, int(rw * 0.12)))
                s1 = float(np.max(cv2.matchTemplate(bin_roi, d1, cv2.TM_CCOEFF_NORMED)))
                s2 = float(np.max(cv2.matchTemplate(bin_roi, d2, cv2.TM_CCOEFF_NORMED)))
                score_x = min(s1, s2)

                # Template > (chevron kanan)
                arr = np.zeros((rh, rw), dtype=np.uint8)
                cv2.line(arr, (int(rw * 0.25), int(rh * 0.18)), (int(rw * 0.75), int(rh * 0.5)), 255, max(2, int(rw * 0.12)))
                cv2.line(arr, (int(rw * 0.75), int(rh * 0.5)), (int(rw * 0.25), int(rh * 0.82)), 255, max(2, int(rw * 0.12)))
                score_arr = float(np.max(cv2.matchTemplate(bin_roi, arr, cv2.TM_CCOEFF_NORMED)))

                # Template >| (skip)
                skp = np.zeros((rh, rw), dtype=np.uint8)
                cv2.line(skp, (int(rw * 0.15), int(rh * 0.18)), (int(rw * 0.55), int(rh * 0.5)), 255, max(2, int(rw * 0.10)))
                cv2.line(skp, (int(rw * 0.55), int(rh * 0.5)), (int(rw * 0.15), int(rh * 0.82)), 255, max(2, int(rw * 0.10)))
                cv2.line(skp, (int(rw * 0.75), int(rh * 0.18)), (int(rw * 0.75), int(rh * 0.82)), 255, max(2, int(rw * 0.10)))
                score_skp = float(np.max(cv2.matchTemplate(bin_roi, skp, cv2.TM_CCOEFF_NORMED)))

                btn_type = None
                conf = 0.0
                if score_x >= 0.28:
                    btn_type = "X"
                    conf = score_x
                elif score_skp >= 0.35:
                    btn_type = ">|"
                    conf = score_skp
                elif score_arr >= 0.28:
                    btn_type = ">"
                    conf = score_arr

                if btn_type and conf > best_score:
                    best_score = conf
                    best_btn = {
                        "pos": pos_name,
                        "type": btn_type,
                        "x": x1 + cx,
                        "y": y1 + cy,
                        "confidence": conf,
                    }

            if best_btn:
                return best_btn

        return None

    def ensure_screen_on(self) -> None:
        pwr = self.adb_out(["shell", "dumpsys", "power"], timeout=5)
        if "Display Power: state=OFF" in pwr:
            self.log("Layar terdeteksi MATI. Menyalakan layar...")
            self.adb_out(["shell", "input", "keyevent", "224"], timeout=5)  # KEYCODE_WAKEUP
            time.sleep(0.3)
            self.adb_out(["shell", "input", "keyevent", "82"], timeout=5)   # KEYCODE_MENU (unlock)

    def is_ad_activity(self, pkg: str, act: str) -> bool:
        """
        Menentukan apakah activity yang sedang aktif merupakan halaman iklan.
        Dalam game ini, activity selain MessagingUnityPlayerActivity adalah halaman iklan.
        """
        if pkg != TARGET_PACKAGE:
            return False
        if not act:
            return False
        # Activity gameplay utama
        if act == TARGET_ACTIVITY:
            return False
        act_lower = act.lower()
        if any(keyword in act_lower for keyword in AD_ACTIVITY_KEYWORDS):
            return True
        # Semua sub-activity lain dalam APK ini merupakan ad/web viewer
        return True

    def get_foreground_app(self) -> Tuple[str, str]:
        """
        Mengambil package dan activity dari dumpsys window atau dumpsys activity.
        """
        win = self.adb_out(["shell", "dumpsys", "window"], timeout=5)
        pkg = ""
        act = ""

        m_focus = re.search(r'mCurrentFocus=Window\{[^ ]+ [^ ]+ ([^/\s]+)/([^}\s]+)\}', win)
        if m_focus:
            pkg, act = m_focus.group(1), m_focus.group(2)
            return pkg, act

        m_app = re.search(r'mFocusedApp=.*Token\{.*ActivityRecord\{[^ ]+ [^ ]+ ([^/\s]+)/([^}\s]+)', win)
        if m_app:
            pkg, act = m_app.group(1), m_app.group(2)
            return pkg, act

        # Fallback dumpsys activity
        act_dump = self.adb_out(["shell", "dumpsys", "activity", "activities"], timeout=5)
        m_resumed = re.search(r'mResumedActivity: ActivityRecord\{[^ ]+ [^ ]+ ([^/\s]+)/([^}\s]+)', act_dump)
        if m_resumed:
            pkg, act = m_resumed.group(1), m_resumed.group(2)
            return pkg, act

        return "", ""

    def inspect_recents(self) -> Tuple[Optional[int], Optional[str]]:
        """
        Memeriksa urutan task di dumpsys activity recents.
        Mengembalikan (target_index, target_task_id) jika ditemukan.
        """
        out = self.adb_out(["shell", "dumpsys", "activity", "recents"], timeout=5)
        if not out:
            return None, None

        # Cari Visible recent tasks
        vis_match = re.search(r'Visible recent tasks.*?(?=\n\s*\n|\Z)', out, re.DOTALL)
        if vis_match:
            tasks = re.findall(
                r'RecentTaskInfo #(\d+):\s+id=(\d+).*?cmp=([^/\s]+)',
                vis_match.group(0),
                re.DOTALL,
            )
            for idx_str, tid, pkg in tasks:
                if pkg == TARGET_PACKAGE:
                    return int(idx_str), tid

        # Fallback cari di Recent tasks
        recent_tasks = re.findall(
            r'\* Recent #(\d+):\s+TaskRecord\{[^ ]+ #(\d+) A=([^ ]+)',
            out,
        )
        for idx_str, tid, pkg in recent_tasks:
            if pkg == TARGET_PACKAGE:
                return int(idx_str), tid

        return None, None

    def recover_to_target(self, current_pkg: str, current_act: str) -> bool:
        """
        Membuka riwayat aplikasi dan memilih Crazy Fruit Blade Winner untuk kembali ke game.
        """
        self.clear_ad_marker()
        self.log(f"TERDETEKSI DI LUAR GAME: {current_pkg}/{current_act}")

        # 1. Cek posisi game di riwayat aplikasi
        target_idx, target_tid = self.inspect_recents()
        if target_idx is not None:
            self.log(f"Posisi game di riwayat aplikasi: index #{target_idx} (Task ID: {target_tid})")
        else:
            self.log("Game belum ada di riwayat (kemungkinan aplikasi tertutup/dihentikan).")

        # 2. Tangani sesuai konteks aplikasi saat ini
        if current_pkg == RECENTS_PACKAGE:
            # Layar Recents sudah terbuka
            if target_idx == 0 or target_idx is None:
                self.log("Layar riwayat aktif. Mengetuk kartu Crazy Fruit Blade Winner di tengah (360, 750)...")
                self.tap(360, 750, color="green")
            elif target_idx == 1:
                self.log("Layar riwayat aktif. Mengetuk kartu Crazy Fruit Blade Winner di kiri (40, 700)...")
                self.tap(40, 700, color="green")
            else:
                self.log(f"Layar riwayat aktif. Membawa task game #{target_tid} ke depan...")
                self.adb_out(["shell", "am", "start", "-n", f"{TARGET_PACKAGE}/{TARGET_ACTIVITY}"], timeout=5)

        elif target_idx == 1:
            # Berada di app lain (misal Chrome, Play Store) dan game adalah aplikasi tepat sebelumnya
            # Gunakan Quick Switch riwayat (double APP_SWITCH 187x2)
            self.log("Membuka riwayat aplikasi dan beralih ke game (Quick Switch 187x2)...")
            self.adb_out(["shell", "input keyevent 187 && input keyevent 187"], timeout=5)

        elif target_idx == 0:
            # Berada di Home screen / launcher, kartu game ada di urutan #0 di riwayat
            self.log("Membuka riwayat aplikasi (Recents / keyevent 187)...")
            self.adb_out(["shell", "input", "keyevent", "187"], timeout=5)
            time.sleep(0.35)
            self.log("Mengetuk kartu Crazy Fruit Blade Winner di posisi tengah (360, 750)...")
            self.tap(360, 750, color="green")

        elif target_idx is not None and target_idx >= 2:
            self.log(f"Game di urutan riwayat #{target_idx}. Membawa task #{target_tid} ke depan...")
            self.adb_out(["shell", "am", "start", "-n", f"{TARGET_PACKAGE}/{TARGET_ACTIVITY}"], timeout=5)

        else:
            # Game tidak ada di recents sama sekali -> buka game baru
            self.log("Game tidak ditemukan di riwayat. Membuka game dari launcher...")
            self.adb_out([
                "shell", "monkey", "-p", TARGET_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"
            ], timeout=6)

        # 3. Verifikasi apakah sudah kembali ke game
        time.sleep(0.8)
        new_pkg, new_act = self.get_foreground_app()
        if new_pkg == TARGET_PACKAGE:
            self.log(f"BERHASIL KEMBALI KE GAME: {new_pkg}/{friendly_act_name(new_act)}")
            return True

        # 4. Fallback jika masih belum kembali
        self.log(f"Masih berada di {new_pkg}, menjalankan am start langsung ke game...")
        self.adb_out([
            "shell", "am", "start", "-n", f"{TARGET_PACKAGE}/{TARGET_ACTIVITY}"
        ], timeout=5)
        time.sleep(1.0)

        new_pkg2, new_act2 = self.get_foreground_app()
        if new_pkg2 == TARGET_PACKAGE:
            self.log(f"BERHASIL KEMBALI KE GAME (via am start): {new_pkg2}/{friendly_act_name(new_act2)}")
            return True
        else:
            self.log(f"Aplikasi aktif saat ini: {new_pkg2}/{new_act2}. Akan dicek kembali pada loop berikutnya.")
            return False

    def handle_in_game(self, act: str, now: float) -> None:
        """
        Menangani status saat aplikasi Crazy Fruit Blade Winner sedang aktif di layar.
        Mendeteksi pembukaan, penutupan, dan durasi halaman iklan.
        """
        is_ad = self.is_ad_activity(TARGET_PACKAGE, act)

        if is_ad:
            friendly_name = friendly_act_name(act)

            if not self.ad_active:
                # Iklan baru saja terbuka
                self.ad_active = True
                self.ad_start_ts = now
                self.current_ad_activity = act
                self.last_ad_log_ts = now
                self.log(f"[IKLAN] Halaman iklan TERBUKA: {friendly_name}")
                self.log("[IKLAN] Mulai pelacakan durasi iklan...")
            else:
                # Iklan sedang berjalan
                durasi = now - (self.ad_start_ts or now)

                # Jika ada perpindahan SDK iklan (mediation chaining)
                if act != self.current_ad_activity:
                    self.log(
                        f"[IKLAN] Halaman iklan berganti ke: {friendly_name} | "
                        f"Total durasi iklan berjalan: {format_duration(durasi)}"
                    )
                    self.current_ad_activity = act

                # Catat pembaruan durasi setiap 5 detik
                if now - self.last_ad_log_ts >= 5.0:
                    self.log(
                        f"[IKLAN] Halaman iklan sedang aktif: {friendly_name} | "
                        f"Sudah tayang: {format_duration(durasi)}"
                    )
                    self.last_ad_log_ts = now

                # Pengecekan tombol di pojok atas layar setiap ~0.7 detik
                if now - self.last_ad_screencap_ts >= 0.7:
                    self.last_ad_screencap_ts = now
                    try:
                        raw_cap = subprocess.run(
                            [self.adb_bin] + (["-s", self.serial] if self.serial else []) + ["exec-out", "screencap", "-p"],
                            capture_output=True,
                            timeout=3,
                        ).stdout
                        if raw_cap:
                            img = cv2.imdecode(np.frombuffer(raw_cap, np.uint8), cv2.IMREAD_COLOR)
                            btn_detected = self.detect_ad_corner_button(img)
                            self.update_ad_marker(btn_detected, now)
                    except Exception:
                        pass

        else:
            # Berada di layar game utama (bukan iklan)
            if self.ad_active:
                # Iklan baru saja ditutup / selesai
                self.clear_ad_marker()
                durasi = now - (self.ad_start_ts or now)
                self.log(
                    f"[IKLAN] Halaman iklan SELESAI / DITUTUP. "
                    f"Total durasi iklan: {format_duration(durasi)}. "
                    f"Kembali ke game utama."
                )
                self.ad_active = False
                self.ad_start_ts = None
                self.current_ad_activity = ""

            # Heartbeat reguler game utama
            if (TARGET_PACKAGE != self.last_foreground_pkg or
                    act != self.last_foreground_act or
                    now - self.last_heartbeat_ts >= 15.0):
                self.log(f"Game utama aktif (Gameplay): {act}")
                self.last_heartbeat_ts = now

    def run(self) -> None:
        self.log("=" * 60)
        self.log("CRAZY FRUIT BLADE WINNER - RECENT APPS WATCHER BOT AKTIF")
        self.log(f"Target: {TARGET_PACKAGE}")
        self.log(f"ADB Binary: {self.adb_bin}")
        if self.serial:
            self.log(f"Device Serial: {self.serial}")
        self.log(f"Log File: {LOG_FILE}")
        self.log("Tekan Ctrl+C untuk menghentikan bot.")
        self.log("=" * 60)

        dev_out = self.adb_out(["devices"], timeout=5)
        if not any(line.endswith("\tdevice") for line in dev_out.splitlines()):
            self.log("PERINGATAN: Perangkat ADB belum terhubung!")

        while True:
            try:
                now = time.time()
                self.ensure_screen_on()

                pkg, act = self.get_foreground_app()
                if not pkg:
                    time.sleep(self.interval)
                    continue

                if pkg == TARGET_PACKAGE:
                    # Sedang berada di dalam game (baik gameplay utama maupun halaman iklan)
                    self.handle_in_game(act, now)
                    self.last_foreground_pkg = pkg
                    self.last_foreground_act = act
                    time.sleep(self.interval)
                    continue

                # Jika berada di luar game:
                # Beri debounce minimal 1.5 detik antar pemulihan agar transisi stabil
                if now - self.last_recovery_ts >= 1.5:
                    self.recover_to_target(pkg, act)
                    self.last_recovery_ts = time.time()
                    self.last_foreground_pkg, self.last_foreground_act = self.get_foreground_app()

                time.sleep(self.interval)

            except KeyboardInterrupt:
                self.log("Bot dihentikan oleh pengguna (Ctrl+C).")
                break
            except Exception as exc:
                self.log(f"Error pada loop utama: {exc}")
                time.sleep(1.0)


def main():
    parser = argparse.ArgumentParser(description="Crazy Fruit Blade Winner Recent Apps Watcher")
    parser.add_argument("--serial", default="", help="Nomor serial perangkat ADB")
    parser.add_argument("--interval", type=float, default=0.6, help="Interval pengecekan (detik)")
    args = parser.parse_args()

    watcher = CrazyFruitRecentsWatcher(serial=args.serial, interval=args.interval)
    watcher.run()


if __name__ == "__main__":
    main()
