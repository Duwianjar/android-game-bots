#!/usr/bin/env python3
"""
Magic Ocean Tile Crush Guardian Bot

Tugas utama:
- Jika game Magic Ocean Tile Crush belum foreground, buka game.
- Jika foreground masuk Chrome atau Play Store, tutup app tersebut lalu kembali ke game.

Target game:
  App     : Magic Ocean Tile Crush
  Package : com.starlightgame.magicoceantilecrush
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

TARGET_PACKAGE = "com.starlightgame.magicoceantilecrush"
TARGET_NAME = "Magic Ocean Tile Crush"

# App yang sering terbuka karena iklan / redirect.
BLOCKED_PACKAGES = {
    "com.android.chrome": "Chrome",
    "com.chrome.beta": "Chrome Beta",
    "com.chrome.dev": "Chrome Dev",
    "com.google.android.apps.chrome": "Chrome",
    "com.android.vending": "Play Store",
    "com.bubble.crush.stick.magicgames": "Bubble Crush redirect",
    "com.starlightgame.woodlandtilematcher": "Woodland Tile Matcher redirect",
}

LOG_FILE = os.path.expanduser("~/magic_ocean_guardian_bot.log")
SALDO_STATE_FILE = os.path.expanduser("~/magic_ocean_saldo_state.json")
TELEGRAM_SENDER = "/Users/macbookair/telegram_sender.py"
DEFAULT_INTERVAL = 0.005
OCR_HELPER = "/Users/macbookair/ocr_helper"
TAP_MARKER = "/Users/macbookair/scrcpy_tap_marker"
DOBEL_CHECK_INTERVAL = 0.01
DOBEL_TAP_RETRY_SECONDS = 0.04
AD_CLOSE_CHECK_INTERVAL = 0.01
# Sebagian iklan TikTok membuka Play Store otomatis dalam 8â10 detik. Coba
# tombol tutup segera setelah kontrol iklan tersedia, bukan setelah durasi video penuh.
AD_CLOSE_MIN_SECONDS = 0.0
AD_TARGET_SECONDS = 5.0
AD_STUCK_RESTART_SECONDS = 120.0
BUBBLE_CHECK_INTERVAL = 0.0
BUBBLE_TIMEOUT_SECONDS = 300.0  # 5 menit (hanya restart jika 5 menit tidak menemukan gelembung)
BUBBLE_TAP_COOLDOWN = 0.0
# Area scan/tap gelembung Magic Ocean:
# mulai dari bawah tombol menu garis-3 kiri atas sampai hampir dasar layar.
BUBBLE_SCAN_TOP_RATIO = 0.235
BUBBLE_SCAN_BOTTOM_RATIO = 0.985
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
    "emptyshell",
    "pangle",
    "bytedance",
    "ksad",
)

# Iklan yang terbukti berulang/tidak menambah hadiah. Kalau activity ini muncul,
# langsung bersihkan semua app dan buka ulang game.
BAD_AD_ACTIVITIES = set()


@dataclass
class ForegroundApp:
    package: str
    activity: str = ""
    source: str = ""


class MagicOceanGuardian:
    def __init__(self, serial: str = "", interval: float = DEFAULT_INTERVAL, dry_run: bool = False):
        self.serial = serial.strip()
        self.interval = interval
        self.dry_run = dry_run
        self.last_foreground = ""
        self.last_action = ""
        self.last_launch_ts = 0.0
        self.last_block_close_ts = 0.0
        self.ad_start_ts: Optional[float] = None
        self.ad_activity = ""
        self.last_ad_log_second = -1
        self.dobel_visible = False
        self.not_now_visible = False
        self.last_dobel_check_ts = 0.0
        self.last_dobel_tap_ts = 0.0
        self.last_buka_tap_ts = 0.0
        self.last_ad_close_check_ts = 0.0
        self.last_ad_close_tap_ts = 0.0
        self.ad_close_same_btn_count = 0
        self.ad_close_last_btn_key = ""
        self.bubble_watch_active = False
        self.bubble_watch_start_ts = 0.0
        self.bubble_search_notified = False
        self.last_bubble_check_ts = 0.0
        self.last_bubble_tap_ts = 0.0
        self.last_bubble_restart_ts = 0.0
        self.last_ad_open_telegram_ts = 0.0
        self.last_ad_stuck_restart_ts = 0.0
        self.pending_dobel_reward_value: Optional[float] = None
        self.pending_dobel_reward_raw = ""
        self.pending_dobel_ts = 0.0
        self.last_dobel_reward_value: Optional[float] = None
        self.last_dobel_reward_raw = ""
        self.last_dobel_ad_activity = ""
        self.last_dobel_ad_ts = 0.0
        self.last_duplicate_dobel_restart_ts = 0.0
        self.last_bad_ad_restart_ts = 0.0
        self.last_wallet_check_ts = 0.0
        self.last_confirm_close_check_ts = 0.0
        self.last_confirm_close_tap_ts = 0.0
        self.prev_bubble_detection: Optional[Tuple[float, int, int]] = None
        self.seeding_slot_routine = False
        self.last_chrome_seed_ts = 0.0
        self.last_tile_tap_ts = 0.0
        self.last_gagal_check_ts = 0.0
        self.last_gagal_tap_ts = 0.0
        self._ocr_cache_ts = 0.0
        self._ocr_cache_entries = None
        self.tile_tap_index = 0
        self.completed_ads_count = 0
        self.pending_slot_seeding_after_ad = False
        self.last_ad_was_slot: bool = False
        self.ad_finished_reported: bool = False
        self.last_tiktok_restart_ts: float = 0.0
        self.last_non_slot_review_files: Optional[Tuple[str, str]] = None
        self.non_slot_review_saved: bool = False
        self._penarikan_cache: Optional[Tuple[float, bool]] = None
        self.current_ad_slot_detected: bool = False
        self.last_ad_slot_check_ts: float = 0.0
        self.last_auto_withdraw_ts: float = 0.0
        self.last_saldo_withdraw_check_ts: float = 0.0

    def log(self, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        print(line, flush=True)
        if os.environ.get("MAGIC_OCEAN_NO_FILE_LOG") == "1":
            return
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def adb(self, args: list[str], timeout: int = 12) -> subprocess.CompletedProcess[str]:
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def adb_out(self, args: list[str], timeout: int = 12) -> str:
        try:
            result = self.adb(args, timeout=timeout)
            return (result.stdout or "").strip()
        except subprocess.TimeoutExpired:
            self.log(f"ADB timeout: {' '.join(args)}")
            return ""
        except FileNotFoundError:
            self.log("ADB tidak ditemukan. Install: brew install android-platform-tools")
            sys.exit(1)
        except Exception as exc:
            self.log(f"ADB error: {exc}")
            return ""

    def adb_bytes(self, args: list[str], timeout: int = 12) -> bytes:
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += args
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout)
            return result.stdout or b""
        except Exception:
            return b""

    def tap(self, x: int, y: int, color: str = "blue") -> None:
        self.show_tap_marker([(int(x), int(y), color, 1.3, 58)])
        self._ocr_cache_entries = None
        self._ocr_cache_ts = 0.0
        if self.dry_run:
            self.log(f"DRY RUN: tap {x},{y}")
            return
        self.adb_out(["shell", "input", "tap", str(x), str(y)], timeout=5)

    def show_tap_marker(self, specs: list[Tuple[int, int, str, float, int]]) -> None:
        if not os.path.exists(TAP_MARKER) or os.environ.get("MAGIC_OCEAN_DISABLE_MARKER") == "1":
            self.log(f"MARKER TIDAK AKTIF: file tidak ada atau disable | specs={len(specs)}")
            return
        args: list[str] = []
        # Batasi supaya marker tetap ringan.
        for x, y, color, duration, diameter in specs[:15]:
            args += [str(int(x)), str(int(y)), color, str(float(duration)), str(int(diameter))]
        try:
            subprocess.Popen([TAP_MARKER, *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            preview = ", ".join(f"({x},{y},{color})" for x, y, color, _, _ in specs[:8])
            self.log(f"MARKER DIBUAT: {len(specs)} titik | {preview}")
        except Exception:
            self.log("MARKER GAGAL DIBUAT")

    def monkey_burst(self, points: list[Tuple[int, int]], delay_ms: int = 0, timeout: int = 6) -> None:
        """Kirim banyak tap berkecepatan tinggi menggunakan monkey script (satu proses JVM, tanpa ANR/lag)."""
        if not points or self.dry_run:
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

    def tap_many(self, points: list[Tuple[int, int]], timeout: int = 10, color: str = "orange", wait: bool = True) -> None:
        """Kirim banyak tap berkecepatan tinggi via monkey script agar tidak membebani sistem."""
        if not points:
            return
        unique_points: list[Tuple[int, int]] = []
        self._ocr_cache_entries = None
        self._ocr_cache_ts = 0.0
        for x, y in points:
            point = (int(x), int(y))
            if point not in unique_points:
                unique_points.append(point)

        marker_diam = 22 if color == "red" else 34
        marker_dur = 1.2 if color == "red" else 1.8
        self.show_tap_marker([(x, y, color, marker_dur, marker_diam) for x, y in unique_points[:220]])

        if self.dry_run:
            self.log(f"DRY RUN: burst tap {unique_points}")
            return

        # Untuk tap gelembung (marker merah) harus sangat cepat/brutal.
        delay_ms = 0 if color == "red" else 1
        self.monkey_burst(unique_points, delay_ms=delay_ms, timeout=timeout)

    def tap_bubble_until_ad(self, points: list[Tuple[int, int]]) -> bool:
        """Tap gelembung SUPER CEPAT & BRUTAL via monkey burst (3x lebih cepat)."""
        if not points:
            return False
        batch = points[:40]
        self.log(f"TAP BATCH GELEMBUNG SUPER BRUTAL: {len(batch)} titik presisi cepat")
        self.tap_many(batch, timeout=6, color="red")
        self.last_dobel_check_ts = 0.0
        # Cek cepat; kalau belum buka iklan, tembak wave kedua dengan jeda ultra singkat.
        time.sleep(0.015)
        app = self.get_foreground_app()
        if app and (self.is_game_ad(app) or app.package != TARGET_PACKAGE):
            self.log(f"STOP TAP GELEMBUNG: foreground berubah ({app.package}/{app.activity})")
            return True

        second_wave = list(reversed(points[:25]))
        if second_wave:
            self.log(f"TAP GELEMBUNG WAVE 2 BRUTAL: {len(second_wave)} titik tambahan")
            self.tap_many(second_wave, timeout=6, color="red")

        # Double-check cepat: catch slow ads.
        time.sleep(0.015)
        app = self.get_foreground_app()
        if app and (self.is_game_ad(app) or app.package != TARGET_PACKAGE):
            self.log(f"STOP TAP GELEMBUNG (check2): foreground berubah ({app.package}/{app.activity})")
            return True
        time.sleep(0.015)
        app = self.get_foreground_app()
        if app and (self.is_game_ad(app) or app.package != TARGET_PACKAGE):
            self.log(f"STOP TAP GELEMBUNG (check3): foreground berubah ({app.package}/{app.activity})")
            return True
        return False

    @staticmethod
    def parse_package_activity(text: str) -> Optional[ForegroundApp]:
        # Contoh:
        # mCurrentFocus=Window{a5c81e3 u0 com.pkg/.MainActivity}
        # ActivityRecord{... u0 com.pkg/com.Activity t123}
        anr_match = re.search(r"Application Not Responding:\s*([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)", text)
        if anr_match:
            return ForegroundApp(package=anr_match.group(1), activity="Application Not Responding", source=text.strip())

        patterns = [
            r"u\d+\s+([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)/([^\s}\]]+)",
            r"\s([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)/([a-zA-Z0-9_.$]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return ForegroundApp(package=match.group(1), activity=match.group(2), source=text.strip())
        return None

    def get_foreground_app(self) -> Optional[ForegroundApp]:
        # Prioritaskan mCurrentFocus/topResumedActivity. Gunakan 'dumpsys window displays'
        # agar tidak membaca dump riwayat 'Last ANR' stale dari dumpsys window.
        checks = [
            (["shell", "dumpsys", "window", "displays"], ("mCurrentFocus",)),
            (["shell", "dumpsys", "activity", "activities"], ("topResumedActivity", "mResumedActivity", "ResumedActivity")),
            (["shell", "dumpsys", "window", "displays"], ("mFocusedApp",)),
        ]
        for args, keywords in checks:
            output = self.adb_out(args, timeout=10)
            in_last_anr = False
            for line in output.splitlines():
                if "Last ANR" in line:
                    in_last_anr = True
                    continue
                if in_last_anr:
                    if not line.startswith(" ") and not line.startswith("	"):
                        in_last_anr = False
                    else:
                        continue
                if any(keyword in line for keyword in keywords):
                    app = self.parse_package_activity(line)
                    if app:
                        return app
        return None

    def has_device(self) -> bool:
        output = self.adb_out(["devices"], timeout=8)
        devices = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        if self.serial:
            ok = self.serial in devices
            if not ok:
                self.log(f"Device serial {self.serial} tidak terhubung. Devices aktif: {devices or '-'}")
            return ok
        if not devices:
            self.log("Tidak ada device ADB aktif. Cek USB debugging dan jalankan: adb devices")
            return False
        if len(devices) > 1:
            self.log(f"Ada lebih dari 1 device: {devices}. Jalankan dengan --serial SERIAL agar jelas.")
            return False
        self.serial = devices[0]
        self.log(f"Device dipakai: {self.serial}")
        return True

    def is_target_installed(self) -> bool:
        output = self.adb_out(["shell", "pm", "path", TARGET_PACKAGE], timeout=8)
        return "package:" in output

    def force_stop(self, package: str) -> None:
        name = BLOCKED_PACKAGES.get(package, package)
        if self.dry_run:
            self.log(f"DRY RUN: force-stop {name} ({package})")
            return
        self.log(f"Menutup {name} ({package})")
        self.adb_out(["shell", "am", "force-stop", package], timeout=8)

    def launch_game(self, reason: str = "") -> None:
        now = time.time()
        # Hindari spam launch terlalu cepat.
        if now - self.last_launch_ts < 3:
            return
        self.last_launch_ts = now
        reason_msg = f" karena {reason}" if reason else ""
        if self.dry_run:
            self.log(f"DRY RUN: buka {TARGET_NAME}{reason_msg}")
            return
        self.log(f"Membuka {TARGET_NAME}{reason_msg}")
        # monkey paling stabil untuk launch activity utama dari manifest.
        self.adb_out([
            "shell", "monkey", "-p", TARGET_PACKAGE,
            "-c", "android.intent.category.LAUNCHER", "1",
        ], timeout=12)

    def close_blocked_app_and_return(self, package: str) -> None:
        if getattr(self, "seeding_slot_routine", False):
            return
        now = time.time()
        if now - self.last_block_close_ts < 2:
            return
        self.last_block_close_ts = now
        self.force_stop(package)
        time.sleep(0.4)
        self.launch_game(reason=f"keluar dari {BLOCKED_PACKAGES.get(package, package)}")

    def restart_game_for_bubble_search(self, reason: str) -> None:
        now = time.time()
        if now - self.last_bubble_restart_ts < 5:
            return
        self.last_bubble_restart_ts = now
        self.log(f"RESTART GAME UNTUK CARI GELEMBUNG: {reason}")
        for package in [TARGET_PACKAGE, *BLOCKED_PACKAGES.keys()]:
            if self.dry_run:
                self.log(f"DRY RUN: force-stop {package}")
            else:
                self.adb_out(["shell", "am", "force-stop", package], timeout=5)
        time.sleep(0.8)
        self.launch_game(reason="cari gelembung setelah timeout")
        self.bubble_watch_active = True
        self.bubble_watch_start_ts = time.time()
        self.bubble_search_notified = False
        self.last_bubble_check_ts = 0.0

    def restart_game_for_stuck_ad(self, reason: str) -> None:
        now = time.time()
        if now - self.last_ad_stuck_restart_ts < 30:
            return
        self.last_ad_stuck_restart_ts = now
        self.log(f"IKLAN STUCK: {reason} -> tutup semua app terkait dan buka ulang game")
        for package in [TARGET_PACKAGE, *BLOCKED_PACKAGES.keys()]:
            if self.dry_run:
                self.log(f"DRY RUN: force-stop {package}")
            else:
                self.adb_out(["shell", "am", "force-stop", package], timeout=8)
        self.ad_start_ts = None
        self.ad_activity = ""
        self.last_ad_log_second = -1
        self.last_ad_close_check_ts = 0.0
        self.last_ad_close_tap_ts = 0.0
        self.dobel_visible = False
        self.not_now_visible = False
        self.bubble_watch_active = False
        self.prev_bubble_detection = None
        time.sleep(0.8)
        self.launch_game(reason="iklan stuck lebih dari 2 menit")

    def clear_apps_and_reopen_game(self, reason: str) -> None:
        self.log(f"BERSIHKAN APP DAN BUKA ULANG GAME: {reason}")
        self.adb_out(["shell", "input", "keyevent", "4"], timeout=3)
        packages = [TARGET_PACKAGE, *BLOCKED_PACKAGES.keys()]
        seen = set()
        for package in packages:
            if package in seen:
                continue
            seen.add(package)
            if self.dry_run:
                self.log(f"DRY RUN: force-stop {package}")
            else:
                self.adb_out(["shell", "am", "force-stop", package], timeout=8)
        self.ad_start_ts = None
        self.ad_activity = ""
        self.last_ad_log_second = -1
        self.last_ad_close_check_ts = 0.0
        self.last_ad_close_tap_ts = 0.0
        self.dobel_visible = False
        self.not_now_visible = False
        self.bubble_watch_active = False
        self.prev_bubble_detection = None
        time.sleep(0.8)
        self.launch_game(reason=reason)

    def is_tiktok_ad(self, app: Optional[ForegroundApp] = None) -> bool:
        """Deteksi apakah tampilan saat ini adalah iklan TikTok."""
        if app:
            pkg = (app.package or "").lower()
            act = (app.activity or "").lower()
            if any(k in pkg for k in ("musically", "trill", "tiktok", "bytedance")):
                return True
            if "tiktok" in act:
                return True

        entries = self.ocr_current_screen("tiktok_check")
        if not entries:
            return False

        raw_text = " " + " ".join(t.lower() for t, _, _, _ in entries) + " "
        clean_text = " " + re.sub(r"[^a-z0-9+]+", " ", raw_text) + " "

        tiktok_patterns = [
            r"\btiktok\b",
            r"\btik\s*tok\b",
            r"\bwarga\s*ti\w*\b",
            r"\bwargo\s*ti\w*\b",
            r"\bgabung\s*bar\w*\b",
            r"\bung\s*barong\b",
            r"\bvideos\b.*\b(live|sh|livel)\b",
            r"\bd\s*tik\s*tok\b",
            r"\bd\s*tiktok\b",
            r"\binstal\s*tiktok\b",
            r"\bdapatkan\s*tiktok\b",
        ]
        for pat in tiktok_patterns:
            if re.search(pat, clean_text):
                return True
        return False

    def close_game_from_recents_and_reopen(self, reason: str) -> None:
        """Tutup game di riwayat buka aplikasi (Recents / Overview) lalu buka game ulang."""
        self.log(f"IKLAN TIKTOK TERDETEKSI ({reason}) -> Tutup game di riwayat buka aplikasi dan buka ulang game.")

        # 1. Buka layar riwayat aplikasi (Recents / Overview)
        self.adb_out(["shell", "input", "keyevent", "187"], timeout=3)
        time.sleep(0.7)

        # 2. Tutup dari riwayat aplikasi (tap tombol hapus semua Infinix di (360, 1420) & swipe ke atas)
        self.adb_out(["shell", "input", "tap", "360", "1420"], timeout=3)
        self.adb_out(["shell", "input", "swipe", "360", "800", "360", "200", "200"], timeout=3)
        time.sleep(0.5)

        # 3. Force stop game dan package terkait untuk memastikan instance bersih
        kill_packages = [
            TARGET_PACKAGE,
            "com.android.vending",
            "com.zhiliaoapp.musically",
            "com.ss.android.ugc.trill",
            *BLOCKED_PACKAGES.keys(),
        ]
        for pkg in set(kill_packages):
            self.adb_out(["shell", "am", "force-stop", pkg], timeout=4)

        # 4. Reset status internal bot
        self.ad_start_ts = None
        self.ad_activity = ""
        self.last_ad_log_second = -1
        self.last_ad_close_check_ts = 0.0
        self.last_ad_close_tap_ts = 0.0
        self.current_ad_slot_detected = False
        self.last_ad_was_slot = False
        self.ad_finished_reported = False
        self.pending_slot_seeding_after_ad = False
        self.last_non_slot_review_files = None
        self.non_slot_review_saved = False
        self.dobel_visible = False
        self.not_now_visible = False
        self.bubble_watch_active = False
        self.prev_bubble_detection = None

        time.sleep(1.0)
        # 5. Buka game ulang dari awal
        self.launch_game(reason=f"buka ulang setelah tutup riwayat (iklan TikTok)")

    def handle_tiktok_ad_if_needed(self, app: Optional[ForegroundApp] = None) -> bool:
        """Jika terdeteksi iklan TikTok, tutup dari riwayat aplikasi lalu buka ulang game."""
        now = time.time()
        if now - getattr(self, "last_tiktok_restart_ts", 0.0) < 4.0:
            return False

        if not self.is_tiktok_ad(app):
            return False

        self.last_tiktok_restart_ts = now
        reason = app.activity if app else "konten TikTok di layar"
        self.close_game_from_recents_and_reopen(reason)
        return True

    def remember_pending_dobel_reward(self, reward_rp: Optional[Tuple[float, str, int, int]]) -> None:
        self.pending_dobel_ts = time.time()
        if reward_rp:
            value, raw_text, _x, _y = reward_rp
            self.pending_dobel_reward_value = float(value)
            self.pending_dobel_reward_raw = raw_text
        else:
            self.pending_dobel_reward_value = None
            self.pending_dobel_reward_raw = ""

    def handle_dobel_ad_opened(self, activity: str) -> bool:
        """Return True hanya kalau DOBEL benar-benar duplikat: iklan sama DAN reward tidak berubah."""
        now = time.time()
        current_reward = self.pending_dobel_reward_value
        current_reward_raw = self.pending_dobel_reward_raw or "-"
        previous_reward = self.last_dobel_reward_value
        previous_reward_raw = self.last_dobel_reward_raw or "-"
        previous_ad = self.last_dobel_ad_activity or "-"
        same_ad = bool(self.last_dobel_ad_activity and self.last_dobel_ad_activity == activity)
        can_compare_reward = current_reward is not None and previous_reward is not None
        same_reward = can_compare_reward and abs(current_reward - previous_reward) < 0.01
        reward_changed = can_compare_reward and not same_reward
        reward_increased = can_compare_reward and current_reward > previous_reward + 0.01

        self.log(
            "CEK DOBEL VS SEBELUMNYA: "
            f"reward_sekarang={current_reward_raw}, reward_sebelumnya={previous_reward_raw}, "
            f"iklan_sekarang={activity}, iklan_sebelumnya={previous_ad}, "
            f"same_reward={same_reward}, reward_changed={reward_changed}, "
            f"reward_increased={reward_increased}, same_ad={same_ad}"
        )

        # Penting: jangan tutup app hanya karena activity iklan sama. Kalau nominal DOBEL berubah/naik,
        # itu reward baru dan iklannya harus tetap dijalankan. Tutup hanya jika iklan sama DAN reward sama.
        if same_ad and same_reward:
            self.log(
                "IKLAN DOBEL SAMA DAN REWARD SAMA: tetap jalankan tonton iklan tanpa restart"
            )

        if same_ad and reward_changed:
            self.log(
                "IKLAN DOBEL SAMA TAPI REWARD BERUBAH/NAIK: "
                f"tetap jalankan iklan | reward sekarang={current_reward_raw}, sebelumnya={previous_reward_raw}"
            )
        elif same_ad and not can_compare_reward:
            self.log(
                "IKLAN DOBEL SAMA TAPI DATA REWARD BELUM LENGKAP: tetap jalankan iklan, jangan tutup app"
            )

        self.last_dobel_reward_value = current_reward
        self.last_dobel_reward_raw = current_reward_raw
        self.last_dobel_ad_activity = activity
        self.last_dobel_ad_ts = now
        self.pending_dobel_reward_value = None
        self.pending_dobel_reward_raw = ""
        return False

    @staticmethod
    def format_duration(seconds: float) -> str:
        total = max(0, int(seconds))
        minutes, sec = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours} jam {minutes} menit {sec} detik"
        if minutes:
            return f"{minutes} menit {sec} detik"
        return f"{sec} detik"

    def is_game_ad(self, app: ForegroundApp) -> bool:
        if not app:
            return False

        activity = (app.activity or "").lower()
        if activity and activity == "application not responding":
            return False

        # Activity SDK iklan sudah definitif. Jangan screenshot/OCR tombol Penarikan
        # setiap loop; logging durasi harus tetap maksimal berselang 3 detik.
        if any(keyword in activity for keyword in AD_ACTIVITY_KEYWORDS):
            return True

        # UnityPlayerActivity dapat berarti halaman game atau playable ad. Hanya
        # kasus ambigu ini yang memerlukan validasi tombol Penarikan.
        if app.package == TARGET_PACKAGE:
            return not self.has_top_right_penarikan()
        return False

    def has_top_right_penarikan(self, screenshot_data: Optional[Tuple[bytes, int, int]] = None) -> bool:
        """Cek apakah ada tombol atau teks 'Penarikan' di kanan atas layar.
        Jika ada, layar ini adalah HALAMAN UTAMA game, bukan halaman iklan, dan tidak boleh diklik."""
        now = time.time()
        cached = getattr(self, "_penarikan_cache", None)
        if cached is not None:
            ts, val = cached
            if now - ts < 0.8:
                return val

        if screenshot_data is None:
            screenshot_data = self.capture_screenshot()
        if not screenshot_data:
            return False

        png_data, width, height = screenshot_data
        try:
            import cv2
            import numpy as np
            arr = np.frombuffer(png_data, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return False

            # Crop area kanan atas tombol Penarikan
            x1, x2 = int(0.48 * width), width
            y1, y2 = int(0.04 * height), int(0.19 * height)
            roi = img[y1:y2, x1:x2]
            if roi.size == 0:
                return False

            # 1. Deteksi teks OCR pada ROI kanan atas (harus mengandung 'penarikan' atau 'tarik')
            has_amount = False
            if os.path.exists(OCR_HELPER):
                safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
                roi_path = f"/tmp/magic_ocean_top_right_penarikan_{safe_serial}.png"
                cv2.imwrite(roi_path, roi)
                res = subprocess.run([OCR_HELPER, roi_path], capture_output=True, text=True, timeout=5)
                for line in (res.stdout or "").splitlines():
                    t, _, _ = line.partition("|")
                    norm = self.normalize_text(t)
                    if any(k in norm for k in ["penarikan", "tarik", "narik"]):
                        self._penarikan_cache = (now, True)
                        return True
                    if "rp" in norm or any(ch.isdigit() for ch in norm):
                        has_amount = True

            # 2. Deteksi warna kuning/oranye tombol Penarikan (hanya jika ada teks saldo/Rp di ROI)
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, (10, 100, 140), (35, 255, 255))
            yellow_ratio = cv2.countNonZero(mask) / float(roi.shape[0] * roi.shape[1])
            if has_amount and yellow_ratio >= 0.16:
                self._penarikan_cache = (now, True)
                return True

            self._penarikan_cache = (now, False)
            return False
        except Exception:
            return False

    @staticmethod
    def get_ad_info(activity: str) -> Tuple[str, str, str]:
        act_lower = (activity or "").lower()
        if "unityplayeractivity" in act_lower:
            network = "Unity Ads / Game Ad"
            ad_type = "Fullscreen Ad"
        elif "applovin" in act_lower:
            network = "AppLovin"
            ad_type = "Fullscreen / Rewarded"
        elif "mbridge" in act_lower or "mintegral" in act_lower:
            network = "Mintegral (MBridge)"
            ad_type = "Rewarded Video" if "reward" in act_lower else "Interstitial"
        elif "unity3d.services" in act_lower or ("unity" in act_lower and "ads" in act_lower):
            network = "Unity Ads"
            ad_type = "FullScreen WebView Display" if "fullscreenwebview" in act_lower else "AdUnit"
        elif "bytedance" in act_lower or "openadsdk" in act_lower or "pangle" in act_lower:
            network = "Pangle (ByteDance)"
            ad_type = "Rewarded / Interstitial"
        elif "kwad" in act_lower or "kwai" in act_lower or "ksad" in act_lower:
            network = "Kwai Ads"
            ad_type = "Rewarded Video"
        elif "gms.ads" in act_lower or "admob" in act_lower or "google" in act_lower:
            network = "Google AdMob"
            ad_type = "AdActivity"
        elif "ironsource" in act_lower:
            network = "ironSource"
            ad_type = "Rewarded / Interstitial"
        elif "vungle" in act_lower:
            network = "Vungle (Liftoff)"
            ad_type = "Fullscreen Ad"
        else:
            network = "Game Ad Network"
            ad_type = "Fullscreen Activity"

        short_id = activity.split(".")[-1] if "." in activity else activity
        return network, ad_type, short_id

    def on_ad_finished(self, activity: str, duration: float) -> None:
        self.completed_ads_count += 1
        self.log(f"Iklan selesai ({activity}), durasi {duration:.1f}s. Total selesai: {self.completed_ads_count}")
        # Siklus injeksi slot hanya dijalankan jika iklan sebelumnya BUKAN slot.
        # Jika iklan terdeteksi sebagai iklan slot, lewati injeksi slot.
        is_slot = getattr(self, "current_ad_slot_detected", False) or getattr(self, "last_ad_was_slot", False)
        if is_slot:
            self.pending_slot_seeding_after_ad = False
            self.log("PASCA-IKLAN: Iklan sebelumnya adalah IKLAN SLOT -> tidak perlu injeksi slot.")
        else:
            self.pending_slot_seeding_after_ad = True
            self.log("PASCA-IKLAN: Iklan sebelumnya BUKAN SLOT -> menunggu tombol DOBEL/BUKA sebelum siklus Google + DAFTAR")

    def adb_type_text(self, text: str) -> None:
        """Ketik teks via ADB input text dengan penanganan karakter khusus seperti * dan @."""
        if not text:
            return
        special = " *?&$()[]{}|;<>`\"'\\"
        if "*" in text:
            parts = text.split("*")
            for i, part in enumerate(parts):
                if part:
                    safe = "".join(("\\" + ch) if ch in special else ch for ch in part)
                    self.adb_out(["shell", "input", "text", safe], timeout=4)
                if i < len(parts) - 1:
                    # KEYCODE_STAR = 17
                    self.adb_out(["shell", "input", "keyevent", "17"], timeout=3)
        else:
            safe = "".join(("\\" + ch) if ch in special else ch for ch in text)
            self.adb_out(["shell", "input", "text", safe], timeout=4)

    def hide_keyboard_if_shown(self) -> None:
        """Tutup virtual keyboard jika sedang aktif agar tidak menutupi form atau mengganggu swipe."""
        try:
            res = self.adb_out(["shell", "dumpsys", "input_method"], timeout=3)
            if "mInputShown=true" in res:
                self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=2)
                time.sleep(0.25)
        except Exception:
            pass

    def match_registration_field(self, text: str) -> Optional[str]:
        """Cocokkan label teks OCR / accessibility dengan jenis field formulir pendaftaran."""
        norm = self.normalize_text(text)
        if not norm or len(norm) < 2:
            return None

        # 1. Konfirmasi Kata Sandi / Password (harus diperiksa SEBELUM password)
        if (
            any(k in norm for k in [
                "konfirmasikatasandi", "konfirmasisandi", "konfirmasipassword",
                "ulangikatasandi", "ulangisandi", "ulangipassword",
                "confirmpassword", "repeatpassword", "ketikulangkatasandi",
                "masukkankembalikatasandi", "verifikasikatasandi"
            ])
            or (("konfirmasi" in norm or "ulangi" in norm or "confirm" in norm or "repeat" in norm)
                and ("sandi" in norm or "password" in norm or "pass" in norm or "pwd" in norm))
        ):
            return "confirm_password"

        # 2. Kata Sandi / Password
        if any(k in norm for k in ["katasandi", "password", "sandi", "katakunci", "passw", "passwd", "pwd"]):
            if not any(neg in norm for neg in ["konfirmasi", "ulangi", "confirm", "repeat", "kembali", "ketikulang"]):
                return "password"

        # 3. Nomor Rekening (harus diperiksa SEBELUM nomor telepon)
        if (
            any(k in norm for k in [
                "nomorrekening", "norekening", "norek", "nomorakun",
                "nomorewallet", "noewallet", "nomordompet", "nodompet",
                "rekeningtujuan", "rekeningbank"
            ])
            or ("rekening" in norm and "nomor" in norm)
        ):
            return "rek"

        # 4. Nama Pemilik Rekening
        if (
            any(k in norm for k in [
                "namarekening", "namapemilik", "namasesuairekening",
                "namapadarekening", "pemilikrekening", "namalengkapsesuai"
            ])
            or ("rekening" in norm and ("nama" in norm or "pemilik" in norm))
        ):
            return "nama_rek"

        # 5. Bank / Metode Pembayaran / E-Wallet
        if (
            any(k in norm for k in [
                "pilihbank", "namabank", "jenisbank", "metodepembayaran",
                "jenisrekening", "akunbank", "ewallet", "pilihpembayaran",
                "pilihmetode", "jenispembayaran"
            ])
            or norm == "bank"
            or ("pilih" in norm and ("bank" in norm or "pembayaran" in norm or "metode" in norm))
        ):
            return "bank"

        # 6. Nomor Telepon / HP / WhatsApp
        if any(k in norm for k in [
            "nomortelepon", "notelepon", "nomorhp", "nohp", "telepon",
            "whatsapp", "nowa", "nomorkontak", "kontak", "nohandphone",
            "handphone", "nomorponsel", "ponsel", "wa"
        ]):
            return "phone"

        # 7. Email / Alamat Email
        if any(k in norm for k in ["email", "alamatemail", "surel", "mail"]) or "@" in norm:
            return "email"

        # 8. Nama Pengguna / Username
        if (
            any(k in norm for k in [
                "namapengguna", "username", "userid", "namaakun",
                "idpengguna", "loginid", "idakun", "pengguna", "user"
            ])
            or norm in ("nama", "user", "id")
        ):
            return "username"

        return None

    def select_ovo_option_if_present(self) -> bool:
        """Cari teks 'OVO' di layar (setelah klik dropdown bank/metode pembayaran), lalu klik."""
        screenshot = self.capture_screenshot()
        if not screenshot:
            return False
        png_data, width, height = screenshot
        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
        screenshot_path = f"/tmp/magic_ocean_bank_drop_{safe_serial}.png"
        try:
            with open(screenshot_path, "wb") as f:
                f.write(png_data)
            result = subprocess.run(
                [OCR_HELPER, screenshot_path],
                capture_output=True,
                text=True,
                timeout=8,
            )
        except Exception:
            return False

        for line in (result.stdout or "").splitlines():
            text, _, bbox = line.partition("|")
            text = text.strip()
            norm = self.normalize_text(text)
            if "ovo" in norm:
                try:
                    bx, by, bw, bh = [float(p) for p in bbox.split(",")]
                    cx = int((bx + bw / 2) * width)
                    cy = int((1 - by - bh / 2) * height)
                    if 180 <= cy <= 1580:
                        self.log(f"Opsi OVO terdeteksi di ({cx},{cy}), memilih OVO!")
                        self.tap(cx, cy, color="green")
                        time.sleep(0.8)
                        return True
                except Exception:
                    pass
        return False

    def get_registration_input_fields(self) -> list[Tuple[str, int, int]]:
        """Baca input form dari accessibility tree Chrome; lebih akurat dari OCR label saja."""
        remote = "/sdcard/magic_ocean_form.xml"
        try:
            self.adb_out(["shell", "uiautomator", "dump", remote], timeout=5)
            xml = self.adb_out(["exec-out", "cat", remote], timeout=5)
            root = ET.fromstring(xml)
        except Exception:
            return []

        fields = []
        # Pada beberapa form Chrome, label berada pada node TextView terpisah
        # sehingga EditText sendiri tidak mempunyai text/content-desc. Simpan
        # semua teks terlebih dahulu agar label terdekat dapat dipasangkan.
        text_nodes = []
        for node in root.iter("node"):
            bounds = node.attrib.get("bounds", "")
            nums = [int(n) for n in re.findall(r"\d+", bounds)]
            text = " ".join(filter(None, (
                node.attrib.get("text", ""),
                node.attrib.get("content-desc", ""),
                node.attrib.get("hint", ""),
                node.attrib.get("resource-id", ""),
            ))).strip()
            if text and len(nums) == 4:
                text_nodes.append((text, nums))

        for node in root.iter("node"):
            klass = node.attrib.get("class", "")
            if "EditText" not in klass and "AutoCompleteTextView" not in klass:
                continue
            label = " ".join(filter(None, (
                node.attrib.get("text", ""), node.attrib.get("content-desc", ""),
                node.attrib.get("hint", ""),
                node.attrib.get("resource-id", ""),
            )))
            bounds = node.attrib.get("bounds", "")
            nums = [int(n) for n in re.findall(r"\d+", bounds)]
            if len(nums) != 4:
                continue
            x1, y1, x2, y2 = nums
            # Cari label yang paling dekat di atas/kiri input ini.
            nearby = []
            for candidate, (tx1, ty1, tx2, ty2) in text_nodes:
                if candidate == label:
                    continue
                vertical_gap = y1 - ty2
                horizontal_gap = min(abs(tx1 - x1), abs(tx2 - x2))
                if -20 <= vertical_gap <= 180 and horizontal_gap <= 260:
                    nearby.append((max(0, vertical_gap) + horizontal_gap * 0.15, candidate))
            if nearby:
                nearby.sort(key=lambda item: item[0])
                label = f"{label} {nearby[0][1]}".strip()
            field_type = self.match_registration_field(label)
            if not field_type:
                continue
            fields.append((field_type, (x1 + x2) // 2, (y1 + y2) // 2))
        return fields

    def fill_registration_form(self, search_label: str = "WEB SLOT") -> None:
        """Isi form dari posisi sekarang, lalu turun perlahan tanpa scroll balik ke atas."""
        self.log(f"[{search_label}]: Memulai pengisian formulir pendaftaran akun...")
        self.hide_keyboard_if_shown()

        field_values = {
            "username": "Wahyu91123",
            "password": "Wahyu123*",
            "confirm_password": "Wahyu123*",
            "email": "wahyu91123@gmail.com",
            "phone": "085157993801",
            "bank": "OVO",
            "rek": "085157993801",
            "nama_rek": "Wahyu",
        }
        all_required = ["username", "password", "confirm_password", "email", "phone", "bank", "rek", "nama_rek"]
        filled_fields: set[str] = set()

        def fill(field_type: str, label: str, tap_x: int, tap_y: int) -> None:
            if field_type in filled_fields:
                return
            val = field_values.get(field_type)
            if not val:
                return
            if field_type == "bank":
                self.log(f"[{search_label}]: FIELD bank ditemukan '{label}' di ({tap_x},{tap_y}); pilih OVO")
                self.tap(tap_x, tap_y, color="yellow")
                time.sleep(0.5)
                if not self.select_ovo_option_if_present():
                    self.adb_type_text(val)
            else:
                self.log(f"[{search_label}]: FIELD {field_type} ditemukan '{label}' di ({tap_x},{tap_y}); isi '{val}'")
                self.tap(tap_x, tap_y, color="yellow")
                time.sleep(0.3)
                self.adb_type_text(val)
            filled_fields.add(field_type)
            time.sleep(0.25)
            # Selalu tutup keyboard setelah mengetik agar layar tidak tertutupi saat scan/swipe berikutnya
            self.hide_keyboard_if_shown()

        def scan_current_viewport() -> None:
            self._ocr_cache_entries = None
            self._ocr_cache_ts = 0.0

            # 1. Coba lewat accessibility input box
            for field_type, x, y in self.get_registration_input_fields():
                fill(field_type, "accessibility", x, y)

            # 2. Coba lewat OCR teks label
            entries = self.ocr_current_screen("reg_form")
            entries.sort(key=lambda item: item[3])  # Urutkan dari atas ke bawah
            for text, _bbox, cx, cy in entries:
                if cy < 160 or cy > 1580:
                    continue
                field_type = self.match_registration_field(text)
                if field_type and field_type not in filled_fields:
                    tap_x = 360 if cx < 250 else cx
                    tap_y = min(cy + 48, 1550)
                    fill(field_type, text, tap_x, tap_y)

        # Mulai dari posisi form saat ini. Jangan menggeser ke atas karena
        # beberapa situs membuka form pada field pertama yang sudah terlihat.
        self.log(f"[{search_label}]: Scan posisi form saat ini, lalu scroll turun sedikit-sedikit...")
        last_filled_count = -1
        unchanged_scans = 0
        # Jarak geser kecil supaya setiap input sempat terlihat dan tidak terlewati.
        for pass_num in range(12):
            scan_current_viewport()
            if len(filled_fields) == len(all_required):
                break
            if len(filled_fields) == last_filled_count:
                unchanged_scans += 1
            else:
                unchanged_scans = 0
            last_filled_count = len(filled_fields)
            # Swipe hanya sekitar 220-260 px: jangan langsung melewati field.
            self.adb_out(["shell", "input", "swipe", "360", "1180", "360", "900", "420"], timeout=4)
            self._ocr_cache_entries = None
            self._ocr_cache_ts = 0.0
            time.sleep(0.55)
            self.hide_keyboard_if_shown()

            # Dua viewport tanpa field baru belum berarti field tidak ada:
            # tetap beri kesempatan beberapa swipe kecil lagi sampai bawah.
            if unchanged_scans >= 3 and pass_num >= 7:
                break

        # Field yang benar-benar tidak ada setelah posisi sekarang sampai bawah.
        for field_type in all_required:
            if field_type not in filled_fields:
                self.log(f"[{search_label}]: FIELD {field_type} tidak ditemukan dari posisi form sampai bawah; lewati.")
        self.log(f"[{search_label}]: Formulir selesai. Field terisi: {sorted(filled_fields)}")

    def find_web_daftar_button(self) -> Optional[Tuple[str, str, int, int]]:
        """Mendeteksi tombol/link DAFTAR, REGISTER, SIGN UP, REGISTRASI pada halaman web yang dibuka."""
        screenshot = self.capture_screenshot()
        if not screenshot:
            return None
        png_data, width, height = screenshot

        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
        screenshot_path = f"/tmp/magic_ocean_web_daftar_{safe_serial}.png"
        try:
            with open(screenshot_path, "wb") as f:
                f.write(png_data)
            result = subprocess.run(
                [OCR_HELPER, screenshot_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            return None

        register_keywords = [
            "daftar", "register", "registrasi", "signup", "sign up",
            "gabung", "buka akun", "buat akun", "klaim bonus", "claim bonus", "join now"
        ]
        exclude_words = ["cara", "mengklik", "syarat", "ketentuan", "panduan", "adalah", "tentang", "about", "hasil"]

        candidates: list[Tuple[int, str, str, int, int]] = []
        for line in (result.stdout or "").splitlines():
            text, _, bbox = line.partition("|")
            text = text.strip()
            bbox = bbox.strip()
            if not text or not bbox:
                continue
            try:
                bx, by, bw, bh = [float(p) for p in bbox.split(",")]
                cx = int((bx + bw / 2) * width)
                cy = int((1 - by - bh / 2) * height)
            except Exception:
                continue

            # Abaikan status bar / URL bar atas (cy < 180) dan navbar Android bawah (cy > 1580)
            if cy < 180 or cy > 1580:
                continue

            words = text.split()
            # Tombol biasanya singkat (1 - 4 kata, <= 25 karakter)
            if len(words) > 4 or len(text) > 25:
                continue

            lower_text = text.lower()
            if any(ex in lower_text for ex in exclude_words):
                continue

            norm = self.normalize_text(text)
            for kw in register_keywords:
                kw_norm = self.normalize_text(kw)
                if kw_norm in norm:
                    # Prioritaskan kata 'daftar' dan 'register' di atas yang lain
                    priority = 0 if ("daftar" in norm or "register" in norm) else 1
                    candidates.append((priority, text, bbox, cx, cy))
                    break

        if not candidates:
            return None

        candidates.sort(key=lambda c: (c[0], c[4]))  # prioritas, lalu y
        _, best_text, best_bbox, best_x, best_y = candidates[0]
        return best_text, best_bbox, best_x, best_y

    def browse_google_and_click_sites(self, query: str, search_label: str = "WEB SLOT 1/2") -> None:
        """Buka Google Search di Chrome, scroll hasil pencarian, klik beberapa situs, dan klik tombol daftar jika ada."""
        import urllib.parse

        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        self.log(f"[{search_label}]: Google Search '{query}'")
        self.adb_out([
            "shell", "am", "start",
            "-a", "android.intent.action.VIEW",
            "-d", url,
            "com.android.chrome"
        ], timeout=6)
        time.sleep(1.8)

        for site_idx in (1, 2):
            if site_idx == 1:
                # Scroll Google hasil pencarian awal
                self.adb_out(["shell", "input", "swipe", "360", "950", "360", "550", "250"], timeout=4)
                time.sleep(0.4)
                tap_x, tap_y = 360, 680
            else:
                # Scroll Google lebih ke bawah untuk mendapatkan situs berbeda
                self.adb_out(["shell", "input", "swipe", "360", "1100", "360", "450", "300"], timeout=4)
                time.sleep(0.4)
                tap_x, tap_y = 360, 780

            self.log(f"[{search_label} - SITUS {site_idx}]: Klik link situs hasil pencarian Google di ({tap_x},{tap_y})")
            self.tap(tap_x, tap_y, color="green")
            time.sleep(2.2)

            # Scroll ke bawah di dalam situs untuk memicu pemuatan aset & tracking
            self.adb_out(["shell", "input", "swipe", "360", "1000", "360", "550", "300"], timeout=4)
            time.sleep(0.6)

            # Cari tombol DAFTAR / REGISTER
            daftar_btn = self.find_web_daftar_button()
            if not daftar_btn:
                # Coba scroll sekali lagi jika tombol ada di posisi lebih bawah
                self.adb_out(["shell", "input", "swipe", "360", "900", "360", "450", "300"], timeout=4)
                time.sleep(0.6)
                daftar_btn = self.find_web_daftar_button()

            if daftar_btn:
                dtext, _dbbox, dx, dy = daftar_btn
                self.log(f"[{search_label} - SITUS {site_idx}]: Menemukan tombol DAFTAR '{dtext}' di ({dx},{dy}) -> KLIK TOMBOL DAFTAR!")
                self.tap(dx, dy, color="green")
                # Waktu muat modal formulir pendaftaran
                time.sleep(1.8)
                # Isi formulir pendaftaran dengan data akun (Wahyu91123, 085157993801, OVO, wahyu91123@gmail.com, Wahyu123*)
                self.fill_registration_form(search_label=f"{search_label} - SITUS {site_idx}")
                time.sleep(0.5)
                # Berhasil klik daftar dan isi form di situs ini, selesai jelajah situs
                break
            else:
                self.log(f"[{search_label} - SITUS {site_idx}]: Tombol DAFTAR tidak terdeteksi di situs ini, selesai jelajah situs.")

            # Jika masih ada situs berikutnya di pencarian ini, kembali ke Google Search
            if site_idx < 2:
                self.log(f"[{search_label}]: Kembali ke halaman pencarian Google...")
                self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
                time.sleep(0.6)
                app = self.get_foreground_app()
                if not app or "chrome" not in app.package:
                    self.adb_out([
                        "shell", "am", "start",
                        "-a", "android.intent.action.VIEW",
                        "-d", url,
                        "com.android.chrome"
                    ], timeout=6)
                    time.sleep(1.2)

    def run_slot_seeding_and_app_routine(self) -> None:
        """Setelah iklan: buka web slot di Chrome, scroll & klik beberapa situs, klik tombol daftar jika ada, buka 1 aplikasi slot acak (rr33, k68, fj99), lalu kembali ke game."""
        self.seeding_slot_routine = True
        self.log("=== MEMULAI SIKLUS INJEKSI SLOT: GOOGLE SEARCH (1/1) + SCROLL SITUS + KLIK DAFTAR + 1 APLIKASI SLOT ACAK ===")
        try:
            import random

            # Kombinasi acak, dua frasa per siklus selalu berbeda.
            keyword_groups = [
                ["toto", "slot", "judi", "casino"],
                ["gacor", "maxwin", "rtp live", "bonus", "rollingan"],
                ["zeus", "pragmatic", "spaceman", "gates of olympus", "mahjong"],
                ["deposit dana", "resmi indonesia", "bonus member", "terpercaya", "hari ini"],
            ]
            slot_keywords = [" ".join(random.sample(group, 1)[0] for group in keyword_groups) for _ in range(8)]
            slot_keywords = list(dict.fromkeys(slot_keywords))
            if len(slot_keywords) < 2:
                slot_keywords += ["slot gacor pragmatic", "judi zeus bonus"]

            # 1. Buka Google Search 1 kali saja (cukup 1/1) & jelajahi situs + tombol daftar
            kw = random.choice(slot_keywords)
            self.browse_google_and_click_sites(kw, search_label="WEB SLOT 1/1")

            # Tutup Chrome setelah kedua web slot dibuka
            self.adb_out(["shell", "am", "force-stop", "com.android.chrome"], timeout=4)
            time.sleep(0.4)

            # 3. Buka salah satu aplikasi slot acak: RR33, K68, atau FJ99
            slot_apps = [
                {"name": "RR33", "pkg": "RR33.COM"},
                {"name": "K68", "pkg": "com.k68.id.xulsfy"},
                {"name": "FJ99", "pkg": "org.chromium.webapk.a1ffa4016fb2cda0c_v2"},
            ]
            chosen_app = random.choice(slot_apps)
            app_name = chosen_app["name"]
            app_pkg = chosen_app["pkg"]
            self.log(f"[APLIKASI SLOT ACAK]: Membuka aplikasi {app_name} ({app_pkg})...")
            self.adb_out([
                "shell", "monkey", "-p", app_pkg,
                "-c", "android.intent.category.LAUNCHER", "1"
            ], timeout=6)
            # Sesi aktif di OS & SDK iklan
            time.sleep(2.2)
            self.adb_out(["shell", "input", "swipe", "360", "900", "360", "650", "250"], timeout=4)
            time.sleep(0.4)
            self.log(f"[APLIKASI SLOT ACAK]: {app_name} selesai dibuka, menutup aplikasi")
            self.adb_out(["shell", "am", "force-stop", app_pkg], timeout=4)

        except Exception as e:
            self.log(f"ERROR SIKLUS SLOT: {e}")
        finally:
            self.seeding_slot_routine = False
            self.log("=== SIKLUS SLOT SELESAI: Kembali ke game Magic Ocean Tile Crush ===")
            self.adb_out([
                "shell", "am", "start",
                "-n", f"{TARGET_PACKAGE}/com.unity3d.player.UnityPlayerActivity"
            ], timeout=6)
            time.sleep(0.8)

    def check_if_current_ad_is_slot(self) -> bool:
        """Cek apakah iklan yang sedang tayang adalah iklan slot atau bukan slot menggunakan regex batas kata (word boundaries)."""
        if getattr(self, "current_ad_slot_detected", False):
            return True

        now = time.time()
        # Periksa berkala tiap 2.5 detik selama iklan berlangsung agar tidak memberatkan CPU
        if now - getattr(self, "last_ad_slot_check_ts", 0.0) < 2.5:
            return getattr(self, "current_ad_slot_detected", False)
        self.last_ad_slot_check_ts = now

        entries = self.ocr_current_screen("ad_classify")
        if not entries:
            return False

        # Gabungkan semua teks OCR di layar menjadi satu string terpisah spasi
        raw_text = " " + " ".join(t.lower() for t, _, _, _ in entries) + " "
        clean_text = " " + re.sub(r"[^a-z0-9+]+", " ", raw_text) + " "

        # Pola kata kunci khusus judi/slot dengan batas kata utuh (...)
        # agar tidak salah mendeteksi kata umum (contoh: 'Fruit Blade Pop Crush' tidak boleh dianggap 'depo')
        slot_regex_patterns = [
            # Slot & variasi kata / composite / OCR typo
            r"\bslot\b", r"\bslots\b", r"\b\w*slot\w*\b", r"\bsiot\b", r"\bstot\b", r"\bs1ot\b", r"\bsl0t\b",
            # Brand & domain slot
            r"\bt9999\b", r"\brr33\b", r"\bk68\b", r"\bfj99\b", r"\b898a\b",
            r"\b\w*777\w*\b", r"\b777\b", r"\b\w*888\w*\b", r"\b888\b", r"\b\w*999\w*\b", r"\b\w*88\b", r"\b\w*99\b",
            r"\bqq\w*\b", r"\bmpoplay\b",
            # Simbol & fitur game slot
            r"\bwild\b",
            r"\bscatter\b",
            r"\bjackpot\b",
            r"\bmaxwin\b",
            r"\bfreespin\b", r"\bfree\s*spin\b", r"\bspin\b",
            r"\brtp\s*live\b", r"\brtp\s*slot\b", r"\brtp\b",
            r"\btumble\b",
            r"\bmultiplier\b",
            r"\bbig\s*win\b", r"\bmega\s*win\b", r"\bsensational\b",
            r"\bbuy\s*spin\b", r"\bbuy\s*freespin\b",
            # Judul game & provider slot
            r"\bgacor\b",
            r"\bpragmatic\b",
            r"\bolympus\b",
            r"\bzeus\b",
            r"\bkakek\s*zeus\b",
            r"\bmahjong\b",
            r"\bstarlight\b",
            r"\bprincess\b",
            r"\bsweet\s*bonanza\b",
            r"\bspaceman\b",
            r"\bpg\s*soft\b", r"\bpgsoft\b",
            r"\bhabanero\b",
            r"\bspadegaming\b",
            r"\bjoker123\b",
            r"\bjudi\b",
            r"\bcasino\b",
            r"\blive\s*casino\b",
            # Transaksi & istilah judi Indonesia
            r"\bdepo\b", r"\bdeposit\b",
            r"\bwede\b", r"\bwd\b",
            r"\btoto\b",
            r"\btogel\b",
            r"\btaruhan\b",
            r"\brollingan\b",
            r"\brungkad\b",
            r"\banti\s*rungkad\b",
            # Slogan & disclaimer khas iklan judi/slot
            r"\bdibayar\s*lunas\b",
            r"\bkemenanga\w*\b",
            r"\bpasti\s*bayar\b",
            r"\bjangan\s*rag\w*\b",
            r"\bbermainlah\s*secara\s*bertanggung\s*jawab\b",
            r"\bbertanggung\s*jawab\b",
            r"\bmenang\s*baru\s*deposit\b",
            r"\bmain\s*gratis\s*dulu\b",
            r"\btanpa\s*deposit\b",
            r"\bakun\s*baru\s*dimanja\b",
            r"\bbonus\s*new\s*member\b", r"\bmember\s*baru\b", r"\bwelcome\s*bonu\w*\b",
            r"\bkecanduan\b",
            r"\b18\+\b", r"\busia\s*18\b",
        ]

        for pat in slot_regex_patterns:
            m = re.search(pat, clean_text)
            if m:
                matched_kw = m.group(0).strip()
                self.current_ad_slot_detected = True
                self.last_ad_was_slot = True
                if getattr(self, "pending_slot_seeding_after_ad", False):
                    self.pending_slot_seeding_after_ad = False
                    self.log(f"DETEKSI IKLAN: teridentifikasi sebagai IKLAN SLOT (kata kunci: '{matched_kw}') -> BATALKAN INJEKSI SLOT")
                else:
                    self.log(f"DETEKSI IKLAN: teridentifikasi sebagai IKLAN SLOT (kata kunci: '{matched_kw}')")
                # Hapus bukti non-slot jika sebelumnya sempat tersimpan karena frame awal belum menampilkan teks slot
                if getattr(self, "last_non_slot_review_files", None):
                    img_f, txt_f = self.last_non_slot_review_files
                    for f in (img_f, txt_f):
                        try:
                            if os.path.exists(f):
                                os.remove(f)
                        except Exception:
                            pass
                    self.last_non_slot_review_files = None
                    self.log("KOREKSI REVIEW: file bukti non-slot dihapus karena iklan ini valid sebagai IKLAN SLOT")
                return True
        return False

    def get_ad_slot_label(self) -> str:
        is_slot = getattr(self, "current_ad_slot_detected", False) or self.check_if_current_ad_is_slot()
        return "IKLAN SLOT" if is_slot else "BUKAN SLOT"

    def save_non_slot_ad_review(self, activity: str) -> None:
        """Simpan bukti iklan non-slot untuk pemeriksaan manual.

        Tidak menekan Report/Block otomatis karena klasifikasi OCR bisa keliru
        dan pelaporan massal dapat salah melaporkan iklan yang sah.
        """
        try:
            screenshot = self.capture_screenshot()
            if not screenshot:
                return
            png_data, _width, _height = screenshot
            review_dir = os.path.expanduser("~/magic_ocean_non_slot_ads")
            os.makedirs(review_dir, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            activity_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", activity or "unknown")
            image_path = os.path.join(review_dir, f"{stamp}_{activity_id}.png")
            text_path = os.path.join(review_dir, f"{stamp}_{activity_id}.txt")
            with open(image_path, "wb") as image_file:
                image_file.write(png_data)
            entries = self.ocr_current_screen("non_slot_review")
            detected_text = " | ".join(text for text, _bbox, _x, _y in entries)
            with open(text_path, "w", encoding="utf-8") as text_file:
                text_file.write(f"activity={activity}\n")
                text_file.write(f"category=BUKAN SLOT\n")
                text_file.write(f"ocr={detected_text}\n")
                text_file.write("action=tidak auto-report/auto-block; review manual\n")
            self.last_non_slot_review_files = (image_path, text_path)
            self.log(
                f"REVIEW IKLAN NON-SLOT: bukti disimpan di {image_path}; "
                "tidak auto-report/auto-block"
            )
        except Exception as exc:
            self.log(f"GAGAL SIMPAN REVIEW IKLAN NON-SLOT: {exc}")

    def detect_ad_report_controls(self) -> None:
        """Deteksi kontrol report secara pasif dan log koordinat untuk tindakan manual."""
        report_words = (
            "adchoices", "why this ad", "about this ad", "report ad",
            "laporkan iklan", "jangan tampilkan", "stop seeing this ad",
            "mengapa iklan ini", "tentang iklan ini",
        )
        try:
            for text, _bbox, x, y in self.ocr_current_screen("ad_report_controls"):
                normalized = self.normalize_text(text)
                if any(self.normalize_text(word) in normalized for word in report_words):
                    self.log(
                        f"KONTROL REPORT TERDETEKSI: '{text}' di ({x},{y}). "
                        "Menunggu tindakan manual; bot tidak menekan Report."
                    )
                    return
            self.log(
                "KONTROL REPORT BELUM TERDETEKSI: buka ikon AdChoices/â/â® secara manual "
                "saat iklan masih tampil."
            )
        except Exception as exc:
            self.log(f"GAGAL DETEKSI KONTROL REPORT: {exc}")

    def is_bad_ad_activity(self, activity: str) -> bool:
        return activity.lower() in BAD_AD_ACTIVITIES

    def handle_bad_ad_if_needed(self, activity: str) -> bool:
        if not self.is_bad_ad_activity(activity):
            return False
        now = time.time()
        if now - self.last_bad_ad_restart_ts < 20:
            return True
        self.last_bad_ad_restart_ts = now
        self.clear_apps_and_reopen_game(
            f"menemukan iklan blacklist/tidak menambah hadiah: {activity}"
        )
        return True

    def update_ad_log(self, app: Optional[ForegroundApp]) -> None:
        if app and self.is_game_ad(app):
            now = time.time()
            elapsed = now - self.ad_start_ts if self.ad_start_ts else 0

            if self.handle_bad_ad_if_needed(app.activity):
                return

            if self.handle_tiktok_ad_if_needed(app):
                return

            if self.ad_start_ts is None or self.ad_activity != app.activity:
                self.ad_start_ts = now
                self.ad_close_same_btn_count = 0
                self.ad_close_last_btn_key = ""
                self.ad_activity = app.activity
                self.last_ad_log_second = 0
                self.current_ad_slot_detected = False
                self.last_ad_was_slot = False
                self.ad_finished_reported = False
                self.last_ad_slot_check_ts = 0.0
                self.last_non_slot_review_files = None
                self.non_slot_review_saved = False
                net, ad_type, short_id = self.get_ad_info(app.activity)
                slot_tag = self.get_ad_slot_label()
                if slot_tag != "BUKAN SLOT":
                    self.current_ad_slot_detected = True
                    self.last_ad_was_slot = True
                target_str = f" | target {int(AD_TARGET_SECONDS)}s"
                self.log(f"IKLAN TERBUKA [DETEKSI: {slot_tag} | NETWORK: {net} | TIPE: {ad_type} | ID: {short_id}]: {app.activity} | durasi {self.format_duration(0)}{target_str}")
                source = "DOBEL" if self.dobel_visible else ("GELEMBUNG" if self.bubble_watch_active else "DETEKSI GAME")
                if source == "DOBEL" and self.handle_dobel_ad_opened(app.activity):
                    return
                self.notify_ad_opened(app.activity, source=source, info="activity iklan baru terdeteksi")
                return

            if elapsed >= AD_STUCK_RESTART_SECONDS:
                self.restart_game_for_stuck_ad(
                    f"{app.activity} terbuka {self.format_duration(elapsed)} tanpa selesai"
                )
                return

            elapsed_second = int(elapsed)
            # Laporan progres maksimal tiap 3 detik; jangan ada jeda lebih panjang.
            if elapsed_second - self.last_ad_log_second >= 3:
                self.last_ad_log_second = elapsed_second
                net, ad_type, short_id = self.get_ad_info(app.activity)
                slot_tag = self.get_ad_slot_label()
                # Skip heavy file/dump review to maintain ultra-fast speed
                pass
                target_str = f" / target {int(AD_TARGET_SECONDS)}s"
                self.log(f"IKLAN DITONTON [DETEKSI: {slot_tag} | NETWORK: {net} | ID: {short_id}]: durasi {self.format_duration(elapsed)}{target_str}")
            return

        if self.ad_start_ts is not None:
            elapsed = time.time() - self.ad_start_ts
            finished_ad = self.ad_activity
            net, ad_type, short_id = self.get_ad_info(finished_ad)
            is_slot = getattr(self, "current_ad_slot_detected", False) or getattr(self, "last_ad_was_slot", False)
            slot_tag = "IKLAN SLOT" if is_slot else "BUKAN SLOT"
            self.log(f"IKLAN SELESAI [DETEKSI: {slot_tag} | NETWORK: {net} | ID: {short_id}]: {finished_ad} | total durasi {self.format_duration(elapsed)}")
            self.ad_start_ts = None
            self.ad_activity = ""
            self.last_ad_log_second = -1
            self.last_ad_close_check_ts = 0.0
            self.last_non_slot_review_files = None
            self.non_slot_review_saved = False
            if not getattr(self, "ad_finished_reported", False):
                self.ad_finished_reported = True
                self.on_ad_finished(finished_ad, elapsed)
            self.current_ad_slot_detected = False

    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    @staticmethod
    def parse_rupiah_value(text: str) -> Optional[float]:
        cleaned = (
            text.replace("R p", "Rp")
            .replace("RP", "Rp")
            .replace("Rp.", "Rp")
            .replace("Rpl", "Rp1")
            .replace("RpI", "Rp1")
        )
        match = re.search(r"Rp\s*([0-9][0-9.,]*)", cleaned, re.I)
        if not match:
            return None
        raw = re.sub(r"[^0-9,.]", "", match.group(1))
        if not raw:
            return None
        # Format Indonesia: 577,11 atau 1.234,56
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif "," in raw:
            raw = raw.replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            return None

    @staticmethod
    def format_rupiah(value: Optional[float]) -> str:
        if value is None:
            return "-"
        return f"Rp {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def load_saldo_state() -> dict:
        try:
            if os.path.exists(SALDO_STATE_FILE):
                with open(SALDO_STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    @staticmethod
    def save_saldo_state(state: dict) -> None:
        try:
            with open(SALDO_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def detect_top_rupiah_balance(self) -> Optional[Tuple[float, str]]:
        """OCR saldo Rp di header atas game."""
        entries = self.ocr_current_screen("saldo")
        candidates: list[Tuple[int, float, str]] = []
        for text, _bbox, _x, y in entries:
            # Header saldo ada di bagian atas layar.
            if y > 260:
                continue
            value = self.parse_rupiah_value(text)
            if value is not None:
                candidates.append((y, value, text))
        if not candidates:
            # Fallback: OCR kadang memecah kata; gabungkan semua text bagian atas.
            top_text = " ".join(text for text, _bbox, _x, y in entries if y <= 260)
            value = self.parse_rupiah_value(top_text)
            if value is not None:
                return value, top_text
            return None
        candidates.sort(key=lambda item: item[0])
        _y, value, raw_text = candidates[0]
        return value, raw_text

    def send_telegram_message(self, message: str) -> None:
        # Telegram dinonaktifkan sepenuhnya agar bot berjalan maksimal tanpa delay jaringan
        return

    def capture_and_report_balance(self, reason: str) -> None:
        detected = self.detect_top_rupiah_balance()
        if not detected:
            self.log("SALDO RP TIDAK TERDETEKSI DI HEADER ATAS")
            return

        now_ts = time.time()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
        current_value, raw_text = detected
        state = self.load_saldo_state()
        prev_value = state.get("saldo_value")
        prev_ts = state.get("timestamp")

        diff_value = None
        elapsed_text = "-"
        if isinstance(prev_value, (int, float)):
            diff_value = current_value - float(prev_value)
        if isinstance(prev_ts, (int, float)):
            elapsed_text = self.format_duration(now_ts - float(prev_ts))

        state = {
            "saldo_value": current_value,
            "saldo_display": self.format_rupiah(current_value),
            "raw_text": raw_text,
            "timestamp": now_ts,
            "time": now_str,
            "reason": reason,
        }
        self.save_saldo_state(state)

        diff_display = "-" if diff_value is None else self.format_rupiah(diff_value)
        prev_display = "-" if prev_value is None else self.format_rupiah(float(prev_value))

        message = (
            "ð° <b>UPDATE SALDO MAGIC OCEAN</b>\n"
            f"ð <b>Waktu:</b> {html.escape(now_str)}\n"
            f"ð <b>Pemicu:</b> {html.escape(reason)}\n"
            f"ð <b>Saldo sebelumnya:</b> {html.escape(prev_display)}\n"
            f"â <b>Saldo sekarang:</b> {html.escape(self.format_rupiah(current_value))}\n"
            f"âï¸ <b>Selisih saldo:</b> {html.escape(diff_display)}\n"
            f"â±ï¸ <b>Jarak dari data sebelumnya:</b> {html.escape(elapsed_text)}\n"
            f"ð <b>OCR:</b> <code>{html.escape(raw_text[:80])}</code>"
        )
        self.log(
            f"SALDO TERDETEKSI: sekarang={self.format_rupiah(current_value)} "
            f"sebelumnya={prev_display} selisih={diff_display} elapsed={elapsed_text}"
        )
        # self.send_telegram_message(message)

    def notify_dobel_found(
        self,
        text: str,
        bbox: str,
        ocr_x: int,
        ocr_y: int,
        tap_x: int,
        tap_y: int,
        reward_rp: Optional[Tuple[float, str, int, int]] = None,
    ) -> None:
        """Notif lengkap saat DOBEL terlihat: saldo header + Rp reward di atas tombol DOBEL."""
        now_ts = time.time()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")

        detected = self.detect_top_rupiah_balance()
        current_display = "-"
        prev_display = "-"
        diff_display = "-"
        elapsed_text = "-"
        raw_balance = "-"

        state = self.load_saldo_state()
        prev_value = state.get("saldo_value")
        prev_ts = state.get("timestamp")
        if isinstance(prev_value, (int, float)):
            prev_display = self.format_rupiah(float(prev_value))
        if isinstance(prev_ts, (int, float)):
            elapsed_text = self.format_duration(now_ts - float(prev_ts))

        if detected:
            current_value, raw_balance = detected
            current_display = self.format_rupiah(current_value)
            if isinstance(prev_value, (int, float)):
                diff_display = self.format_rupiah(current_value - float(prev_value))
            self.save_saldo_state({
                "saldo_value": current_value,
                "saldo_display": current_display,
                "raw_text": raw_balance,
                "timestamp": now_ts,
                "time": now_str,
                "reason": "saat menemukan tombol DOBEL sebelum klik",
            })
        else:
            self.log("SALDO RP TIDAK TERDETEKSI DI HEADER ATAS SAAT DOBEL")

        if reward_rp:
            reward_value, reward_raw, reward_x, reward_y = reward_rp
            reward_display = f"{self.format_rupiah(reward_value)} | OCR: {reward_raw} | pos=({reward_x},{reward_y})"
        else:
            reward_display = "-"

        message = (
            "<b>MAGIC OCEAN: TOMBOL DOBEL TERDETEKSI</b>\n"
            f"<b>Waktu:</b> {html.escape(now_str)}\n"
            f"<b>Reward Rp di atas DOBEL:</b> {html.escape(reward_display)}\n"
            f"<b>Saldo sebelumnya:</b> {html.escape(prev_display)}\n"
            f"<b>Saldo sekarang:</b> {html.escape(current_display)}\n"
            f"<b>Selisih saldo:</b> {html.escape(diff_display)}\n"
            f"<b>Jarak dari data sebelumnya:</b> {html.escape(elapsed_text)}\n"
            f"<b>Tombol:</b> <code>{html.escape(text)}</code> bbox=<code>{html.escape(bbox)}</code>\n"
            f"<b>OCR/Tap:</b> ({ocr_x},{ocr_y}) -> ({tap_x},{tap_y})\n"
            f"<b>OCR saldo:</b> <code>{html.escape(str(raw_balance)[:80])}</code>"
        )
        self.log(
            f"TELEGRAM NOTIF: DOBEL | reward={reward_display} | "
            f"saldo={current_display} prev={prev_display} diff={diff_display}"
        )
        # self.send_telegram_message(message)

    def notify_ad_opened(self, activity: str, source: str = "IKLAN", info: str = "") -> None:
        now = time.time()
        # Anti spam jika activity berulang.
        if now - self.last_ad_open_telegram_ts < 8:
            return
        self.last_ad_open_telegram_ts = now
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
        search_elapsed = "-"
        if self.bubble_watch_start_ts and self.bubble_watch_active:
            search_elapsed = self.format_duration(now - self.bubble_watch_start_ts)
        message = (
            "<b>MAGIC OCEAN: IKLAN TERBUKA</b>\n"
            f"<b>Waktu:</b> {html.escape(now_str)}\n"
            f"<b>Sumber:</b> {html.escape(source)}\n"
            f"<b>Activity iklan:</b> <code>{html.escape(activity)}</code>\n"
            f"<b>Lama cari gelembung:</b> {html.escape(search_elapsed)}\n"
            f"<b>Info:</b> {html.escape(info[:160])}"
        )
        # self.log(f"TELEGRAM NOTIF: iklan terbuka | source={source} | {activity}")
        # self.send_telegram_message(message)

    def notify_bubble_search_once(self, reason: str) -> None:
        if self.bubble_search_notified:
            return
        self.bubble_search_notified = True
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
        message = (
            "ð <b>MAGIC OCEAN: MULAI CARI GELEMBUNG</b>\n"
            f"ð <b>Waktu:</b> {html.escape(now_str)}\n"
            f"ð <b>Pemicu:</b> {html.escape(reason)}\n"
            f"â³ <b>Timeout:</b> {html.escape(self.format_duration(BUBBLE_TIMEOUT_SECONDS))}\n"
            "ð¯ <i>Bot mulai scan cash-bubble dan akan brutal tap jika ketemu.</i>"
        )
        # self.log(f"TELEGRAM NOTIF: mulai cari gelembung | {reason}")
        # self.send_telegram_message(message)

    @staticmethod
    def parse_bounds(bounds: str) -> Optional[Tuple[int, int]]:
        match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
        if not match:
            return None
        x1, y1, x2, y2 = map(int, match.groups())
        if x2 <= x1 or y2 <= y1 or (x2 - x1 < 12) or (y2 - y1 < 12):
            return None
        if x1 < 15 and y1 < 15 and x2 < 30 and y2 < 30:
            return None
        return (x1 + x2) // 2, (y1 + y2) // 2

    def get_screen_size(self) -> Tuple[int, int]:
        output = self.adb_out(["shell", "wm", "size"], timeout=5)
        match = re.search(r"(\d+)x(\d+)", output)
        if match:
            return int(match.group(1)), int(match.group(2))
        return 720, 1640

    def capture_screenshot(self) -> Optional[Tuple[bytes, int, int]]:
        png_data = self.adb_bytes(["exec-out", "screencap", "-p"], timeout=8)
        if len(png_data) < 1000:
            return None
        # Parse PNG dimensions directly from IHDR chunk (zero CPU/PIL overhead)
        if len(png_data) >= 24 and png_data.startswith(bytes([0x89, 0x50, 0x4e, 0x47])):
            import struct
            width, height = struct.unpack(">II", png_data[16:24])
            return png_data, width, height
        width, height = getattr(self, "_screen_size_cache", None) or self.get_screen_size()
        self._screen_size_cache = (width, height)
        return png_data, width, height

    def dump_ui_tree(self) -> Optional[ET.Element]:
        # Hapus file lama terlebih dahulu agar tidak membaca XML basi (seperti 'Tutup sheet' Play Store)
        self.adb_out(["shell", "rm", "-f", "/sdcard/magic_ocean_ui.xml"], timeout=3)
        dump_res = self.adb_out(["shell", "uiautomator", "dump", "/sdcard/magic_ocean_ui.xml"], timeout=4)
        if "dumped to" not in dump_res:
            return None
        xml_text = self.adb_out(["shell", "cat", "/sdcard/magic_ocean_ui.xml"], timeout=4)
        if "<hierarchy" not in xml_text:
            return None
        try:
            return ET.fromstring(xml_text)
        except ET.ParseError:
            return None

    def find_ad_finish_button_by_ui(self) -> Optional[Tuple[str, str, int, int]]:
        root = self.dump_ui_tree()
        if root is None:
            return None

        finish_words = {
            "x",
            "Ã",
            "close",
            "tutup",
            "skip",
            "lewati",
            "next",
            "lanjut",
            ">",
            "âº",
            "Â»",
        }
        screen_w, screen_h = self.get_screen_size()
        # Simpan kontrol non-prioritas (mis. "Tutup sheet" di tengah layar)
        # agar tidak mengalahkan tombol Close video/X di sisi kanan.
        finish_fallback = None
        store_fallback = None
        for node in root.iter("node"):
            text = (node.get("text") or "").strip()
            desc = (node.get("content-desc") or "").strip()
            label = text or desc
            if not label:
                continue
            norm = self.normalize_text(label)
            raw = label.strip().lower()
            is_store = raw in {"play", "google play", "buka toko", "open store", "store", "install", "instal"}
            is_finish = (
                raw in finish_words or norm in finish_words
                or any(token in norm for token in ("close", "tutup", "skip", "lewati"))
            )
            if not is_finish and not is_store:
                continue
            center = self.parse_bounds(node.get("bounds", ""))
            if not center:
                continue
            x, y = center
            # Hindari tombol navigasi Android bawah; tombol close/next iklan biasanya tepi atas/kanan.
            if y > screen_h * 0.88:
                continue
            is_corner = y < screen_h * 0.30 and (x < screen_w * 0.35 or x > screen_w * 0.65)
            if is_store:
                # Google Play di kiri atas adalah jalan keluar cadangan untuk iklan TikTok.
                # Jangan gunakan jika ada X/Close video yang dapat menutup iklan langsung.
                if is_corner and store_fallback is None:
                    store_fallback = ("PLAY/STORE", label, x, y)
                continue
            if x > screen_w * 0.65 or y < screen_h * 0.30 or raw in {"close", "tutup", "skip", "lewati", "next", "lanjut"}:
                kind = "X" if raw in {"x", "Ã", "close", "tutup"} or "close" in norm or "tutup" in norm else "PANAH_KANAN/NEXT"
                candidate = (kind, label, x, y)
                # "Close video"/X di tepi adalah penutup iklan sebenarnya. Node
                # "Tutup sheet" di tengah sering berasal dari overlay Play Store.
                if x > screen_w * 0.65 or x < screen_w * 0.35 or "video" in norm:
                    return candidate
                if finish_fallback is None:
                    finish_fallback = candidate
        return finish_fallback or store_fallback

        # Kwai/Alliance sering menaruh tombol X sebagai ImageView tanpa text/content-desc.
        image_candidates = []
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
            if w < 18 or h < 18 or w > 70 or h > 70:
                continue
            x = (x1 + x2) // 2
            y = (y1 + y2) // 2
            if x < screen_w * 0.72 or y < screen_h * 0.18 or y > screen_h * 0.70:
                continue
            score = x + (screen_h * 0.70 - y) * 0.2
            image_candidates.append((score, x, y, bounds))
        if image_candidates:
            image_candidates.sort(reverse=True)
            _score, x, y, bounds = image_candidates[0]
            return "X", f"kwai image close {bounds}", x, y
        return None

    def find_ad_finish_button_by_ocr(self, png_data: bytes, width: int, height: int) -> Optional[Tuple[str, str, int, int]]:
        if not os.path.exists(OCR_HELPER):
            return None

        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
        screenshot_path = f"/tmp/magic_ocean_ad_close_{safe_serial}.png"
        try:
            with open(screenshot_path, "wb") as f:
                f.write(png_data)
            result = subprocess.run(
                [OCR_HELPER, screenshot_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            return None

        finish_labels = {
            "x": "X",
            "close": "X",
            "tutup": "X",
            "skip": "PANAH_KANAN/NEXT",
            "lewati": "PANAH_KANAN/NEXT",
            "next": "PANAH_KANAN/NEXT",
            "lanjut": "PANAH_KANAN/NEXT",
        }
        arrow_chars = {">", "âº", "Â»", "â"}
        store_fallback = None
        for line in (result.stdout or "").splitlines():
            text, _, bbox = line.partition("|")
            label = text.strip()
            if not label or not bbox:
                continue
            norm = self.normalize_text(label)
            raw = label.strip().lower()
            if any(k in norm for k in ("penarikan", "tarik", "saldo")) or norm.startswith("rp"):
                continue
            kind = None
            if raw in arrow_chars:
                kind = "PANAH_KANAN/NEXT"
            elif norm in finish_labels:
                kind = finish_labels[norm]
            elif any(token in norm for token in ("close", "tutup")):
                kind = "X"
            elif any(token in norm for token in ("skip", "lewati", "next", "lanjut")):
                kind = "PANAH_KANAN/NEXT"
            elif any(token in norm for token in ("googleplay", "bukatoko", "bukotoko", "openstore")):
                kind = "PLAY/STORE"
            if not kind:
                continue

            try:
                bx, by, bw, bh = [float(part) for part in bbox.split(",")]
            except ValueError:
                continue
            x = int((bx + bw / 2) * width)
            y = int((1 - by - bh / 2) * height)
            # Conservative: icon/text harus di tepi atas atau sisi kanan, bukan area tombol install.
            if y > height * 0.88:
                continue
            is_corner = y < height * 0.32 and (x < width * 0.38 or x > width * 0.62)
            if kind == "PLAY/STORE":
                if is_corner and store_fallback is None:
                    store_fallback = (kind, label, x, y)
                continue
            # Tulisan Close/Tutup kadang berupa tombol teks di tengah/bawah iklan.
            # Klik selama masih bukan area navigation bar bawah.
            if x >= int(width * 0.48) and int(height * 0.04) <= y <= int(height * 0.20):
                if self.has_top_right_penarikan():
                    continue
            if kind == "X" and any(token in norm for token in ("close", "tutup")) and y < height * 0.86:
                return kind, label, x, y
            if x > width * 0.60 or y < height * 0.30:
                return kind, label, x, y
        return store_fallback

    def find_ad_top_corner_button_by_image(self, png_data: bytes, width: int, height: int) -> Optional[Tuple[str, str, int, int]]:
        """Prioritas tombol iklan di pojok atas (MBridge sering pakai lingkaran gelap dengan panah >).

        Ini memperbaiki kasus bot salah klik ikon panah/gesture di tengah iklan.
        """
        try:
            import cv2
            import numpy as np
        except Exception:
            return None

        img = cv2.imdecode(np.frombuffer(png_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return None

        # Jalur khusus MBridge: tombol asli adalah lingkaran gelap di kanan atas
        # dengan panah putih. Kontur biasa sering menyatu dengan header iklan,
        # jadi pakai Hough circle dan tap sedikit di bawah center.
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
                        if abs_x < width * 0.88:
                            continue
                        if abs_y < max(78, int(height * 0.045)) or abs_y > height * 0.14:
                            continue
                        patch = gray[
                            max(0, cy - r): min(gray.shape[0], cy + r),
                            max(0, cx - r): min(gray.shape[1], cx + r),
                        ]
                        if patch.size == 0:
                            continue
                        patch_y, patch_x = np.ogrid[:patch.shape[0], :patch.shape[1]]
                        patch_mask = (
                            (patch_x - (patch.shape[1] - 1) / 2) ** 2
                            + (patch_y - (patch.shape[0] - 1) / 2) ** 2
                            <= r * r
                        )
                        white_ratio = float(((patch > 180) & patch_mask).sum()) / max(1, int(patch_mask.sum()))
                        # Lingkaran dekorasi bisa terlihat seperti tombol, tetapi
                        # tombol X/panah memiliki tanda putih yang jelas di dalamnya.
                        if white_ratio < 0.03:
                            continue
                        mean_gray = float(patch[patch_mask].mean())
                        # Lingkaran close/next gelap; hindari lingkaran terang UI/game.
                        if not (45 <= mean_gray <= 135):
                            continue
                        # Klik tepat di pusat lingkaran yang terdeteksi; jangan
                        # menggeser ke bawah karena hitbox X tiap iklan berbeda.
                        tap_x = abs_x
                        tap_y = abs_y
                        score = (
                            (abs_x / width) * 3000
                            + white_ratio * 1500
                            + r * 40
                            - abs(abs_y - 115) * 8
                            - mean_gray
                        )
                        circle_candidates.append(
                            (score, tap_x, tap_y, f"hough top-right circle r={r} mean={mean_gray:.1f} center=({abs_x},{abs_y})")
                        )
                if circle_candidates:
                    circle_candidates.sort(reverse=True)
                    _score, x, y, label = circle_candidates[0]
                    return "PANAH_KANAN/TOP", label, int(x), int(y)
        except Exception:
            pass

        search_h = int(height * 0.20)
        # Prioritaskan kanan atas, lalu kiri atas.
        areas = [
            (int(width * 0.58), 0, width, search_h, "kanan-atas"),
            (0, 0, int(width * 0.42), search_h, "kiri-atas"),
        ]
        candidates = []
        for ax1, ay1, ax2, ay2, area_name in areas:
            roi = img[ay1:ay2, ax1:ax2]
            if roi.size == 0:
                continue
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            # Tombol next/close MBridge biasanya lingkaran abu gelap.
            dark = cv2.inRange(gray, 35, 135)
            kernel = np.ones((3, 3), np.uint8)
            dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel)
            dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, kernel, iterations=2)
            contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                if area < 450 or area > 6500:
                    continue
                if w < 25 or h < 25 or w > 95 or h > 95:
                    continue
                aspect = w / float(h)
                if aspect < 0.65 or aspect > 1.55:
                    continue
                abs_x = ax1 + x + w // 2
                abs_y = ay1 + y + h // 2
                if abs_y > height * 0.18:
                    continue
                # Jangan klik icon/header palsu playable-ad. Tombol close/next MBridge asli
                # biasanya muncul agak turun dari status/pointer overlay, bukan menempel di y=0.
                if abs_y < max(78, int(height * 0.045)):
                    continue
                # Area aktif close/next biasanya dekat tepi. Hindari logo DANA/header iklan.
                if area_name == "kanan-atas" and abs_x < width * 0.76:
                    continue
                if area_name == "kiri-atas" and abs_x > width * 0.16:
                    continue

                perimeter = cv2.arcLength(contour, True)
                circularity = (4 * np.pi * area / (perimeter * perimeter)) if perimeter else 0
                if circularity < 0.45:
                    continue

                # Klik tepat di pusat kontur tombol hasil deteksi.
                tap_x = abs_x
                tap_y = abs_y
                right_bonus = 4000 if area_name == "kanan-atas" else 0
                edge_bonus = (abs_x / width) * 900 if area_name == "kanan-atas" else ((width - abs_x) / width) * 250
                score = area + right_bonus + edge_bonus - abs_y * 2
                candidates.append((score, tap_x, tap_y, f"top-corner {area_name} area={int(area)} circ={circularity:.2f} bbox=({ax1+x},{ay1+y},{w},{h})"))

        if not candidates:
            return None
        candidates.sort(reverse=True)
        _score, x, y, label = candidates[0]
        return "PANAH_KANAN/TOP", label, int(x), int(y)

    def find_ad_finish_button_by_image(self, png_data: bytes, width: int, height: int) -> Optional[Tuple[str, str, int, int]]:
        """Deteksi konservatif ikon X di pojok atas layar iklan."""
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
            (int(width * 0.68), 0, width, int(height * 0.125)),         # kanan atas
            (0, 0, int(width * 0.32), int(height * 0.125)),             # kiri atas
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
                if w < 14 or h < 14 or w > 95 or h > 95:
                    continue
                aspect = w / float(h)
                if aspect < 0.45 or aspect > 2.2:
                    continue

                patch = edges[max(0, y - 4): min(edges.shape[0], y + h + 4), max(0, x - 4): min(edges.shape[1], x + w + 4)]
                lines = cv2.HoughLinesP(patch, 1, np.pi / 180, threshold=10, minLineLength=10, maxLineGap=4)
                if lines is None:
                    continue

                pos_diag = 0
                neg_diag = 0
                for line in lines.reshape(-1, 4):
                    x1, y1, x2, y2 = [int(v) for v in line]
                    dx = x2 - x1
                    dy = y2 - y1
                    if dx == 0 and dy == 0:
                        continue
                    angle = np.degrees(np.arctan2(dy, dx))
                    if 25 <= angle <= 70:
                        pos_diag += 1
                    elif -70 <= angle <= -25:
                        neg_diag += 1

                abs_x = ax1 + x + w // 2
                abs_y = ay1 + y + h // 2
                if abs_y < max(85, int(height * 0.052)):
                    continue
                # Jangan klik jika berada di area tombol Penarikan kanan atas
                if abs_x >= int(width * 0.48) and int(height * 0.04) <= abs_y <= int(height * 0.20):
                    if self.has_top_right_penarikan():
                        continue
                if abs_y < height * 0.125 and (abs_x < width * 0.30 or abs_x > width * 0.70):
                    if pos_diag >= 1 and neg_diag >= 1:
                        return "X", "ikon X terdeteksi", abs_x, abs_y
        return None

    def find_ad_finish_button(self) -> Optional[Tuple[str, str, int, int, str]]:
        screenshot = self.capture_screenshot()
        if not screenshot:
            return None
        png_data, width, height = screenshot

        # 1. Cek tombol pojok atas via OpenCV gambar (super cepat ~5ms)
        top_corner_found = self.find_ad_top_corner_button_by_image(png_data, width, height)
        if top_corner_found:
            kind, label, x, y = top_corner_found
            return kind, label, x, y, "top-corner"

        # 2. Cek ikon X via OpenCV gambar (~5ms)
        image_found = self.find_ad_finish_button_by_image(png_data, width, height)
        if image_found:
            kind, label, x, y = image_found
            return kind, label, x, y, "image"

        # 3. Cek OCR untuk tombol X/Close/Skip
        ocr_found = self.find_ad_finish_button_by_ocr(png_data, width, height)
        if ocr_found:
            kind, label, x, y = ocr_found
            return kind, label, x, y, "ocr"

        # 4. Fallback UI dump hanya jika OpenCV/OCR belum menemukan
        ui_found = self.find_ad_finish_button_by_ui()
        if ui_found:
            kind, label, x, y = ui_found
            return kind, label, x, y, "ui"

        return None

    def try_finish_ad(self, app: Optional[ForegroundApp]) -> None:
        if self.handle_tiktok_ad_if_needed(app):
            return
        if not app or not self.is_game_ad(app) or self.ad_start_ts is None:
            return
        # Hanya periksa tombol Penarikan jika sedang di UnityPlayerActivity (karena activity SDK iklan murni pasti bukan game)
        if app.package == TARGET_PACKAGE and "unityplayeractivity" in (app.activity or "").lower():
            if self.has_top_right_penarikan():
                self.ad_start_ts = None
                self.ad_activity = None
                return

        now = time.time()
        elapsed = now - self.ad_start_ts

        target_watch = AD_CLOSE_MIN_SECONDS
        if elapsed < target_watch:
            return

        if now - self.last_ad_close_check_ts < AD_CLOSE_CHECK_INTERVAL:
            return
        self.last_ad_close_check_ts = now

        found = self.find_ad_finish_button()
        if not found:
            if elapsed >= AD_TARGET_SECONDS and (now - self.last_ad_close_tap_ts >= 3.0):
                self.last_ad_close_tap_ts = now
                self.log(f"TARGET {int(AD_TARGET_SECONDS)}s TERCAPAI: iklan terbuka {self.format_duration(elapsed)} belum ada tombol tutup, kirim BACK")
                self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
            return

        kind, label, x, y, source = found
        if x < 20 and y < 20:
            self.log(f"ABORT KLIK IKLAN: koordinat tidak valid ({x},{y})")
            return

        # Track klik berulang pada tombol yang sama tanpa efek
        btn_key = f"{x}_{y}_{kind}"
        if self.ad_close_last_btn_key == btn_key:
            self.ad_close_same_btn_count += 1
        else:
            self.ad_close_same_btn_count = 1
            self.ad_close_last_btn_key = btn_key

        # Jika tombol yang sama sudah diklik >= 5x tanpa efek, skip dan fallback BACK
        if self.ad_close_same_btn_count >= 5:
            self.log(
                f"SKIP TOMBOL TIDAK BEREAKSI: {kind} di ({x},{y}) sudah diklik {self.ad_close_same_btn_count}x | "
                f"durasi {self.format_duration(elapsed)}, fallback BACK"
            )
            self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
            if self.ad_close_same_btn_count >= 8:
                self.log(f"TOMBOL STUCK {self.ad_close_same_btn_count}x: restart game")
                self.ad_close_same_btn_count = 0
                self.ad_close_last_btn_key = ""
                self.restart_game_for_stuck_ad(f"tombol {kind} di ({x},{y}) tidak bereaksi {self.ad_close_same_btn_count}x")
            return

        self.log(
            f"MENEMUKAN TOMBOL SELESAI IKLAN: {kind} '{label}' "
            f"di ({x},{y}) via {source} | durasi {self.format_duration(elapsed)}"
        )

        if now - self.last_ad_close_tap_ts < 0.04:
            return
        self.last_ad_close_tap_ts = now
        self.log(f"KLIK TOMBOL SELESAI IKLAN: {kind} di ({x},{y})")
        # Burst tap cepat tombol selesai iklan
        self.monkey_burst([(x, y), (x, y), (x + 2, y + 2)], delay_ms=0, timeout=1)
        self.ad_finished_reported = True
        self.on_ad_finished(self.ad_activity or (app.activity if app else "unknown"), elapsed)
        # Jangan reset ad_start_ts = now agar tidak menghambat penutupan endcard berikutnya
        self.ad_close_same_btn_count = 0
        self.ad_close_last_btn_key = ""
        self.last_ad_log_second = 0

    def ocr_current_screen(self, prefix: str) -> list[Tuple[str, str, int, int]]:
        """OCR layar sekarang. Return: [(text, bbox, x, y), ...]."""
        if not os.path.exists(OCR_HELPER):
            return []

        now = time.time()
        if hasattr(self, "_ocr_cache_ts") and (now - self._ocr_cache_ts < 0.05):
            if hasattr(self, "_ocr_cache_entries") and self._ocr_cache_entries is not None:
                return self._ocr_cache_entries

        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
        screenshot_path = f"/tmp/magic_ocean_{prefix}_{safe_serial}.png"
        screenshot = self.capture_screenshot()
        if not screenshot:
            return []
        png_data, width, height = screenshot

        try:
            with open(screenshot_path, "wb") as f:
                f.write(png_data)
            result = subprocess.run(
                [OCR_HELPER, screenshot_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            return []

        entries = []
        for line in (result.stdout or "").splitlines():
            text, _, bbox = line.partition("|")
            text = text.strip()
            bbox = bbox.strip()
            if not text or not bbox:
                continue
            try:
                bx, by, bw, bh = [float(part) for part in bbox.split(",")]
                x = int((bx + bw / 2) * width)
                y = int((1 - by - bh / 2) * height)
            except ValueError:
                x, y = width // 2, height // 2
            entries.append((text, bbox, x, y))
        self._ocr_cache_entries = entries
        self._ocr_cache_ts = now
        return entries

    def find_reward_offer_buttons(self) -> Tuple[
        Optional[Tuple[str, str, int, int]],
        Optional[Tuple[str, str, int, int]],
        Optional[Tuple[str, str, int, int]],
        Optional[Tuple[float, str, int, int]],
        Optional[Tuple[str, str, int, int]],
    ]:
        """Cari tombol DOBEL, tombol BUKA, tombol NOT NOW/NOW NOT, nominal Rp reward, serta tombol X pop-up Pengaturan."""
        dobel = None
        buka_btn = None
        not_now = None
        settings_btn = None
        reward_candidates: list[Tuple[int, float, str, int, int]] = []
        entries = self.ocr_current_screen("reward_offer")
        screen_w, _screen_h = self.get_screen_size()
        for text, bbox, x, y in entries:
            value = self.parse_rupiah_value(text)
            # Abaikan saldo header atas; yang dicari adalah nominal reward di popup DOBEL.
            if value is not None and y > 300:
                reward_candidates.append((y, value, text, x, y))

            norm = self.normalize_text(text)
            if dobel is None and "dobel" in norm:
                dobel = (text, bbox, x, y)
                continue

            # Tombol BUKA (peti hadiah/bonus yang sering muncul berdampingan/di atas tombol NOT NOW / NOW NOT)
            is_store = any(w in norm for w in ("toko", "store", "play", "google", "web", "browser", "situs", "link"))
            is_buka = (
                not is_store
                and (
                    norm == "buka"
                    or "bukasekarang" in norm
                    or "bukapet" in norm
                    or "bukahadiah" in norm
                    or norm.startswith("buka")
                    or norm in {"open", "klaim", "claim", "ambil"}
                )
                and (350 <= y <= 1350)
            )
            if buka_btn is None and is_buka:
                buka_btn = (text, bbox, x, y)
                continue

            # Pop-up Pengaturan: tombol X berada di sebelah kanan teks Pengaturan (ujung kanan banner header pop-up).
            if settings_btn is None and ("pengaturan" in norm or "setting" in norm or "pengatur" in norm):
                x_close = int(screen_w * 0.88) if screen_w else (x + 270)
                y_close = y + 21 if y else 545
                settings_btn = (text, bbox, x_close, y_close)
                continue

            # OCR kadang membaca "NOT NOW" sebagai "NOW NOT"; tangani dua-duanya.
            is_not_now = (
                "notnow" in norm
                or "nownot" in norm
                or "nothanks" in norm
                or "tidaksekarang" in norm
                or "nantidulu" in norm
                or norm in {"nanti", "skip", "lewati"}
            )
            if not_now is None and is_not_now:
                not_now = (text, bbox, x, y)

        reward_rp = None
        if reward_candidates:
            target_y = dobel[3] if dobel else (buka_btn[3] if buka_btn else 1120)
            # Pilih nominal Rp yang paling dekat di atas tombol DOBEL/BUKA, misalnya "Rp 41,9".
            above = [item for item in reward_candidates if item[0] < target_y and (target_y - item[0]) <= 430]
            pool = above or reward_candidates
            pool.sort(key=lambda item: abs(target_y - item[0]))
            _sort_y, value, raw_text, x, y = pool[0]
            reward_rp = (value, raw_text, x, y)
        return dobel, buka_btn, not_now, reward_rp, settings_btn

    def handle_confirm_close_popup(self, app: Optional[ForegroundApp]) -> bool:
        """Jika muncul popup 'Confirm to close app' (Exit/Continue), klik Continue."""
        if not app or app.package != TARGET_PACKAGE:
            return False
        now = time.time()
        if now - self.last_confirm_close_check_ts < 2.5:
            return False
        self.last_confirm_close_check_ts = now

        entries = self.ocr_current_screen("confirm_close")
        if not entries:
            return False
        has_context = False
        continue_btn = None
        for text, bbox, x, y in entries:
            norm = self.normalize_text(text)
            if (
                "confirmtoclose" in norm
                or "confirmclose" in norm
                or ("confirm" in norm and "close" in norm)
                or "toclosetheapp" in norm
                or "closetheapp" in norm
                or ("wantto" in norm and ("exit" in norm or "quit" in norm or "close" in norm))
                or norm in {"exit", "quit"}
            ):
                has_context = True
            if continue_btn is None and ("continue" in norm or norm == "contin" or "continu" in norm):
                continue_btn = (text, bbox, x, y)
        if not (has_context and continue_btn):
            return False
        if now - self.last_confirm_close_tap_ts < 2.0:
            return False
        self.last_confirm_close_tap_ts = now
        text, bbox, x, y = continue_btn
        self.log(f"POPUP CONFIRM TO CLOSE TERDETEKSI: klik Continue '{text}' di ({x},{y}) | bbox={bbox}")
        self.tap(x, y)
        time.sleep(0.5)
        self.dobel_visible = False
        self.not_now_visible = False
        return True

    def perform_wallet_full_withdrawal(self) -> bool:
        """Di halaman Dompet Saya: klik Penarikan Penuh (keduanya jika ada dialog konfirmasi), lalu kembali ke halaman utama."""
        self.log("HALAMAN DOMPET SAYA: Memulai proses Penarikan Penuh...")
        time.sleep(0.8)

        # 1. Cari & klik tombol Penarikan Penuh pertama
        entries = self.ocr_current_screen("wallet_withdraw")
        btn = None
        for text, _bbox, x, y in entries:
            norm = self.normalize_text(text)
            if "penarikanpenuh" in norm or ("penarikan" in norm and "penuh" in norm):
                btn = (x, y)
                break

        tap_x, tap_y = btn if btn else (360, 1528)
        self.log(f"DOMPET SAYA: Klik 'Penarikan Penuh' di ({tap_x},{tap_y})")
        self.tap(tap_x, tap_y, color="blue")
        time.sleep(1.5)

        # 2. Periksa apakah ada dialog konfirmasi / tombol 'Penarikan Penuh' kedua (keduanya)
        entries2 = self.ocr_current_screen("wallet_confirm")
        for text, _bbox, x, y in entries2:
            norm = self.normalize_text(text)
            if "penarikanpenuh" in norm or ("penarikan" in norm and "penuh" in norm) or "konfirmasi" in norm or "setuju" in norm or "tarik" in norm:
                # Hindari klik judul header atas
                if y > 300:
                    self.log(f"DOMPET SAYA: Konfirmasi Penarikan Penuh kedua terdeteksi ('{text}') di ({x},{y}) -> Klik konfirmasi")
                    self.tap(x, y, color="blue")
                    time.sleep(1.5)
                    break

        # 3. Kembali ke halaman utama dari Detail Penarikan & Dompet Saya (klik panah kiri di (45, 198))
        for back_attempt in range(3):
            entries_back = self.ocr_current_screen(f"wallet_back_{back_attempt}")
            top_text = " ".join(t.lower() for t, _, _, y in entries_back if y <= 280)
            is_wallet_page = any(k in top_text for k in ["detail", "tertunda", "dompet", "sejarah", "riwayat", "catatan"]) or (
                "penarikan" in top_text and "rp" not in top_text
            )
            if is_wallet_page:
                self.log(f"HALAMAN KEMBALI ({top_text[:40]}): Klik panah kiri di (45, 198) untuk kembali ke halaman utama")
                self.tap(45, 198, color="blue")
                time.sleep(1.0)
            else:
                break

        self.last_auto_withdraw_ts = time.time()
        self.log("SELESAI PENARIKAN PENUH: Kembali ke halaman utama game Magic Ocean")
        self.dobel_visible = False
        self.not_now_visible = False
        self.bubble_watch_active = False
        return True

    def check_auto_withdraw_if_needed(self, app: Optional[ForegroundApp]) -> bool:
        """Cek apakah saldo >= Rp 300 di halaman utama. Jika ya, klik tombol Penarikan di kanan Rp, lakukan penarikan penuh, lalu kembali."""
        if not app or app.package != TARGET_PACKAGE or self.is_game_ad(app):
            return False

        # Jangan ganggu jika ada tombol DOBEL / popup hadiah aktif
        if getattr(self, "dobel_visible", False) or getattr(self, "not_now_visible", False):
            return False

        now = time.time()
        # Periksa saldo tiap 8 detik
        if now - getattr(self, "last_saldo_withdraw_check_ts", 0.0) < 8.0:
            return False
        self.last_saldo_withdraw_check_ts = now

        # Cooldown penarikan otomatis 45 detik
        if now - getattr(self, "last_auto_withdraw_ts", 0.0) < 45.0:
            return False

        # Hanya jalankan jika berada di Halaman Utama (ada tombol Penarikan di kanan atas)
        if not self.has_top_right_penarikan():
            return False

        # Deteksi saldo Rp di header atas
        balance_info = self.detect_top_rupiah_balance()
        if not balance_info:
            return False

        current_val, raw_text = balance_info
        if current_val < 300.0:
            return False

        self.log(f"AUTO-WITHDRAW: Saldo melebihi Rp 300 (saldo={raw_text} / Rp {current_val:.2f}) -> Klik tombol Penarikan di kanan Rp")

        # Cari koordinat tombol Penarikan di kanan Rp (y <= 260, x >= 300)
        entries = self.ocr_current_screen("penarikan_btn")
        target_btn = None
        for text, _bbox, x, y in entries:
            norm = self.normalize_text(text)
            if ("penarikan" in norm or "tarik" in norm) and y <= 260 and x >= 300:
                target_btn = (x, y)
                break

        tap_x, tap_y = target_btn if target_btn else (567, 169)
        self.log(f"AUTO-WITHDRAW: Klik tombol Penarikan di ({tap_x},{tap_y})")
        self.tap(tap_x, tap_y, color="blue")
        time.sleep(1.8)

        # Jalankan proses penarikan penuh di Dompet Saya
        self.perform_wallet_full_withdrawal()
        self.capture_and_report_balance(reason="pasca auto-penarikan saldo > 300")
        return True

    def handle_wallet_page_if_needed(self, app: Optional[ForegroundApp]) -> bool:
        if not app or app.package != TARGET_PACKAGE or self.is_game_ad(app):
            return False
        now = time.time()
        if now - self.last_wallet_check_ts < 2.0:
            return False
        self.last_wallet_check_ts = now

        entries = self.ocr_current_screen("wallet_page")
        for text, bbox, x, y in entries:
            norm = self.normalize_text(text)
            is_wallet_title = (
                "dompetsaya" in norm
                or ("dompet" in norm and "saya" in norm)
                or "detailpenarikan" in norm
                or "riwayatpenarikan" in norm
            )
            # Judul halaman biasanya di area header atas; jangan salah tangkap tombol Penarikan di saldo/header game.
            if is_wallet_title and 90 <= y <= 280:
                # Jika saldo >= 300 dan sedang di Dompet Saya, jalankan penarikan penuh
                state = self.load_saldo_state()
                saldo_val = state.get("saldo_value") or 0.0
                if saldo_val >= 300.0 and ("dompetsaya" in norm or ("dompet" in norm and "saya" in norm)):
                    self.perform_wallet_full_withdrawal()
                    return True

                tap_x = 45
                tap_y = y
                self.log(f"HALAMAN DOMPET TERDETEKSI: '{text}' | bbox={bbox} | klik panah kiri di ({tap_x},{tap_y})")
                self.tap(tap_x, tap_y)
                time.sleep(0.6)
                self.dobel_visible = False
                self.not_now_visible = False
                self.bubble_watch_active = False
                return True
        return False

    def handle_gagal_popup(self, app: Optional[ForegroundApp]) -> bool:
        """Jika muncul popup 'gagal' (level kalah/stuck), klik tombol 'Hidup kembali' (prioritas tombol video bawah)."""
        if not app or app.package != TARGET_PACKAGE or self.is_game_ad(app):
            return False

        now = time.time()
        if now - self.last_gagal_check_ts < 0.8:
            return False
        self.last_gagal_check_ts = now

        entries = self.ocr_current_screen("gagal_popup")
        if not entries:
            return False

        has_gagal = False
        candidates: list[Tuple[str, str, int, int]] = []
        for text, bbox, x, y in entries:
            norm = self.normalize_text(text)
            if "gagal" in norm or "kalah" in norm or "failed" in norm:
                has_gagal = True
            if "hidup" in norm or ("kembali" in norm and has_gagal):
                if 700 <= y <= 1200:
                    candidates.append((text, bbox, x, y))

        if not (has_gagal or candidates):
            return False

        if now - self.last_gagal_tap_ts < 1.2:
            return True
        self.last_gagal_tap_ts = now

        # Prioritaskan tombol video bawah (y > 950, target sekitar y=1041)
        video_candidates = [c for c in candidates if c[3] > 950]
        if video_candidates:
            video_candidates.sort(key=lambda c: abs(c[3] - 1041))
            best = video_candidates[0]
            tap_x, tap_y = 360, best[3]
            log_desc = f"tombol video '{best[0]}' di ({tap_x},{tap_y})"
        elif candidates:
            best = candidates[0]
            if has_gagal and best[3] < 920:
                tap_x, tap_y = 360, 1041
                log_desc = f"tombol video di ({tap_x},{tap_y}) (posisi video di bawah '{best[0]}' y={best[3]})"
            else:
                tap_x, tap_y = 360, best[3]
                log_desc = f"tombol '{best[0]}' di ({tap_x},{tap_y})"
        else:
            tap_x, tap_y = 360, 1041
            log_desc = f"tombol video di ({tap_x},{tap_y}) (koordinat default pop-up gagal)"

        self.log(f"POPUP GAGAL TERDETEKSI: klik Hidup Kembali -> {log_desc}")
        self.tap(tap_x, tap_y, color="green")
        time.sleep(0.5)
        self.dobel_visible = False
        self.not_now_visible = False
        self.bubble_watch_active = False
        return True

    def update_dobel_log(self, app: Optional[ForegroundApp]) -> None:
        # Cukup cek saat masih di package game, supaya tidak berat dan tidak salah deteksi app lain.
        if not app or app.package != TARGET_PACKAGE:
            self.dobel_visible = False
            self.not_now_visible = False
            return

        now = time.time()
        if now - self.last_dobel_check_ts < DOBEL_CHECK_INTERVAL:
            return
        self.last_dobel_check_ts = now

        dobel, buka_btn, not_now, reward_rp, settings_btn = self.find_reward_offer_buttons()
        if settings_btn:
            stext, sbbox, sx, sy = settings_btn
            self.log(f"MENEMUKAN POP-UP PENGATURAN: '{stext}' | bbox={sbbox} | klik tombol X di kanan teks di ({sx},{sy})")
            self.show_tap_marker([(sx, sy, "blue", 1.5, 34)])
            self.tap(sx, sy)
            time.sleep(0.5)
            self.dobel_visible = False
            self.not_now_visible = False
            return

        if dobel or buka_btn:
            # Pasca-iklan, rutinitas Google/DAFTAR hanya boleh berjalan bila
            # reward berikutnya benar-benar tersedia. Setelah selesai, scan ulang;
            # jangan klik koordinat lama karena tampilan dapat berubah.
            if self.pending_slot_seeding_after_ad:
                self.pending_slot_seeding_after_ad = False
                self.last_chrome_seed_ts = now
                target = "DOBEL" if dobel else "BUKA"
                self.log(f"VALIDASI LOLOS: tombol {target} ada. Iklan sebelumnya bukan slot -> Jalankan siklus injeksi slot sebelum klik {target}")
                self.run_slot_seeding_and_app_routine()
                self.dobel_visible = False
                self.not_now_visible = False
                self.last_dobel_check_ts = 0.0
                return

        if dobel:
            text, bbox, x, y = dobel
            screen_w, _screen_h = self.get_screen_size()
            # OCR memberi titik tengah tulisan "DOBEL", bukan selalu titik tengah tombol.
            # Tombol DOBEL pada game ini berada di tengah layar; klik tengah tombol lebih stabil
            # daripada klik tepat di huruf yang kadang tidak memicu iklan.
            tap_x = screen_w // 2 if screen_w else x
            tap_y = y
            if not self.dobel_visible:
                self.log(f"MENEMUKAN TOMBOL DOBEL: '{text}' | bbox={bbox} | ocr=({x},{y}) | tap=({tap_x},{tap_y}) | reward={reward_rp}")
                self.notify_dobel_found(text, bbox, x, y, tap_x, tap_y, reward_rp)
            else:
                self.log(f"DOBEL MASIH TERDETEKSI: '{text}' | bbox={bbox} | ocr=({x},{y}) | retry tap=({tap_x},{tap_y})")

            # Kalau tap pertama tidak membuka iklan, jangan anggap selesai; coba ulang berkala.
            if (not self.dobel_visible) or (now - self.last_dobel_tap_ts >= DOBEL_TAP_RETRY_SECONDS):
                self.last_dobel_tap_ts = now
                self.remember_pending_dobel_reward(reward_rp)
                self.log(f"KLIK TOMBOL DOBEL di ({tap_x},{tap_y}) | simpan reward DOBEL={reward_rp}")
                self.monkey_burst([(tap_x, tap_y), (tap_x, tap_y)], delay_ms=0, timeout=1)
            self.dobel_visible = True
            self.not_now_visible = False
            self.bubble_watch_active = False

        elif buka_btn:
            text, bbox, x, y = buka_btn
            screen_w, _screen_h = self.get_screen_size()
            tap_x = screen_w // 2 if screen_w else x
            tap_y = y
            self.log(f"MENEMUKAN TOMBOL BUKA (PRIORITAS BUKA, JANGAN NOW NOT): '{text}' | bbox={bbox} | ocr=({x},{y}) | tap=({tap_x},{tap_y})")
            if (not hasattr(self, "last_buka_tap_ts")) or (now - self.last_buka_tap_ts >= 1.2):
                self.last_buka_tap_ts = now
                self.log(f"KLIK TOMBOL BUKA di ({tap_x},{tap_y})")
                self.tap(tap_x, tap_y, color="green")
            self.dobel_visible = False
            self.not_now_visible = False
            self.bubble_watch_active = False

        elif not_now:
            text, bbox, x, y = not_now
            if not self.not_now_visible:
                self.log(f"TIDAK ADA DOBEL/BUKA, MENEMUKAN TOMBOL NOW NOT/NOT NOW: '{text}' | bbox={bbox} | tap=({x},{y})")
                self.log(f"KLIK TOMBOL NOW NOT/NOT NOW SEKALI di ({x},{y})")
                self.tap(x, y)
                time.sleep(0.3)
                self.capture_and_report_balance("setelah klik NOW NOT sebelum cari gelembung")
                self.bubble_watch_active = True
                self.bubble_watch_start_ts = time.time()
                self.bubble_search_notified = False
                self.last_bubble_check_ts = 0.0
                self.log(f"MODE CARI GELEMBUNG AKTIF: timeout {self.format_duration(BUBBLE_TIMEOUT_SECONDS)}")
                self.notify_bubble_search_once("setelah klik NOW NOT")
            self.not_now_visible = True
            self.dobel_visible = False
        else:
            self.dobel_visible = False
            self.not_now_visible = False

    def find_moving_bubble(self) -> Optional[Tuple[int, int, str]]:
        """Cari objek bulat/gelembung yang bergerak (3x lebih cepat; diff frame langsung atau single-frame fast detect)."""
        try:
            import cv2
            import numpy as np
        except Exception:
            return None

        first_res = self.capture_screenshot()
        if not first_res:
            return None
        first_png, width, height = first_res
        self.last_bubble_screen_size = (width, height)
        now_ts = time.time()
        img_current = cv2.imdecode(np.frombuffer(first_png, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img_current is None:
            return None

        cached_img = getattr(self, "_cached_bubble_frame", None)
        cached_ts = getattr(self, "_cached_bubble_ts", 0.0)

        # Jika ada frame sebelumnya yang masih valid (hingga 6.0 detik), gunakan langsung untuk hitung gerak (0 screenshot tambahan!)
        if cached_img is not None and (now_ts - cached_ts < 6.0) and cached_img.shape == img_current.shape:
            img1 = cached_img
            first_ts = cached_ts
            img2 = img_current
            second_ts = now_ts
            second_png = first_png
        else:
            # Cek cepat single-frame jika ada cash bubble langsung di layar
            fast_icon = self.find_reward_bubble_icon(first_png, width, height)
            if fast_icon:
                ix, iy, iinfo = fast_icon
                self._cached_bubble_frame = img_current
                self._cached_bubble_ts = now_ts
                return ix, iy, f"fast-detect {iinfo}"

            # Frame kedua dengan delay super singkat (30ms)
            img1 = img_current
            first_ts = now_ts
            time.sleep(0.03)
            second_res = self.capture_screenshot()
            if not second_res:
                return None
            second_png, width, height = second_res
            second_ts = time.time()
            img2 = cv2.imdecode(np.frombuffer(second_png, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img2 is None or img1.shape != img2.shape:
                return None

        self._cached_bubble_frame = img2
        self._cached_bubble_ts = second_ts

        diff = cv2.absdiff(img1, img2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 24, 255, cv2.THRESH_BINARY)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.dilate(mask, kernel, iterations=2)

        # Eksklusi zona statis atas saja. Area gelembung sekarang dibuat penuh
        # sampai bawah layar, mulai dari bawah tombol menu garis-3.
        scan_top = int(height * BUBBLE_SCAN_TOP_RATIO)
        scan_bottom = int(height * BUBBLE_SCAN_BOTTOM_RATIO)
        mask[:scan_top, :] = 0  # saldo / bar atas / tombol menu
        mask[scan_bottom:, :] = 0  # sisakan margin bawah kecil

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
            if center_y < scan_top or center_y > scan_bottom:
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
            target1 = cv2.bitwise_or(money1, white1)
            target2 = cv2.bitwise_or(money2, white2)
            money_ratio = float(money2.mean() / 255.0)
            white_ratio = float(white2.mean() / 255.0)
            sat_mean = float(hsv2[:, :, 1].mean())

            if money_ratio < 0.05 and sat_mean < 25:
                continue
            if white_ratio < 0.04 and money_ratio < 0.08:
                continue

            m2 = cv2.moments(target2)
            if m2["m00"] > 0:
                latest_x = int(rx1 + m2["m10"] / m2["m00"])
                latest_y = int(ry1 + m2["m01"] / m2["m00"])
            else:
                latest_x, latest_y = center_x, center_y

            vx, vy = 0.0, -160.0
            m1 = cv2.moments(target1)
            dt_pair = max(0.001, second_ts - first_ts)
            if m1["m00"] > 0 and m2["m00"] > 0:
                old_x = int(rx1 + m1["m10"] / m1["m00"])
                old_y = int(ry1 + m1["m01"] / m1["m00"])
                calc_vx = (latest_x - old_x) / dt_pair
                calc_vy = (latest_y - old_y) / dt_pair
                if abs(calc_vx) < 900 and abs(calc_vy) < 1200:
                    vx, vy = calc_vx, calc_vy

            lead = 0.34
            pred_x = int(latest_x + vx * lead)
            pred_y = int(latest_y + vy * lead)
            if abs(pred_x - latest_x) > 170 or abs(pred_y - latest_y) > 220:
                pred_x, pred_y = latest_x, latest_y
            self.last_bubble_pair_velocity = (vx, vy)

            score = area + money_ratio * 4200 + white_ratio * 2800 + sat_mean * 10
            candidates.append((score, pred_x, pred_y, f"moving-bubble area={int(area)} bbox=({x},{y},{w},{h}) latest=({latest_x},{latest_y}) v=({vx:.0f},{vy:.0f}) money={money_ratio:.2f} white={white_ratio:.2f}"))

        if not candidates:
            reward_icon = self.find_reward_bubble_icon(second_png, width, height)
            if reward_icon:
                ix, iy, iinfo = reward_icon
                diff_roi = diff[max(0, iy - 35):min(height, iy + 35), max(0, ix - 35):min(width, ix + 35)]
                if diff_roi.size > 0 and float(diff_roi.mean()) > 3.5:
                    return ix, iy, f"motion-confirmed {iinfo}"

        if not candidates:
            return None
        candidates.sort(reverse=True)
        _, cx, cy, info = candidates[0]
        return int(cx), int(cy), info

    def find_reward_bubble_icon(self, png_data: bytes, width: int, height: int) -> Optional[Tuple[int, int, str]]:
        """Deteksi cash-bubble reward yang bergerak.

        Target yang benar adalah gelembung transparan berisi uang hijau/kuning.
        Filter ini menghindari ikon bell kanan-bawah dan objek background seperti kura-kura.
        """
        try:
            import cv2
            import numpy as np
        except Exception:
            return None

        img = cv2.imdecode(np.frombuffer(png_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return None

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Warna uang di dalam bubble: hijau + kuning/oranye.
        green = cv2.inRange(hsv, np.array([35, 60, 80]), np.array([90, 255, 255]))
        yellow = cv2.inRange(hsv, np.array([15, 70, 100]), np.array([38, 255, 255]))
        mask = cv2.bitwise_or(green, yellow)

        scan_top = int(height * BUBBLE_SCAN_TOP_RATIO)
        scan_bottom = int(height * BUBBLE_SCAN_BOTTOM_RATIO)
        allowed = np.zeros_like(mask)
        allowed[scan_top:scan_bottom, :] = 255
        # Exclude papan puzzle tengah dan label Level yang juga hijau/kuning.
        cv2.rectangle(allowed, (210, int(height * 0.33)), (520, int(height * 0.58)), 0, -1)
        cv2.rectangle(allowed, (240, 300), (480, 430), 0, -1)
        # Exclude saldo / tombol atas. Area bawah sengaja tetap aktif.
        cv2.rectangle(allowed, (0, 0), (width, scan_top), 0, -1)
        cv2.rectangle(allowed, (0, scan_bottom), (width, height), 0, -1)
        mask = cv2.bitwise_and(mask, allowed)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if area < 1000 or area > 28000:
                continue
            if w < 35 or h < 35 or w > 230 or h > 230:
                continue
            center_x = x + w // 2
            center_y = y + h // 2
            # Hindari kandidat terlalu mepet tepi layar
            if center_x < 35 or center_x > width - 45:
                continue
            if center_y < scan_top or center_y > scan_bottom:
                continue

            # Bubble asli punya lingkaran/shine putih transparan di sekitar uang.
            pad = 70
            x1 = max(0, center_x - pad)
            y1 = max(0, center_y - pad)
            x2 = min(width, center_x + pad)
            y2 = min(height, center_y + pad)
            crop_hsv = hsv[y1:y2, x1:x2]
            if crop_hsv.size == 0:
                continue
            white = cv2.inRange(crop_hsv, np.array([0, 0, 165]), np.array([179, 85, 255]))
            colored = cv2.inRange(crop_hsv, np.array([15, 60, 80]), np.array([95, 255, 255]))
            white_ratio = float(white.mean() / 255.0)
            colored_ratio = float(colored.mean() / 255.0)
            if white_ratio < 0.10 or colored_ratio < 0.12:
                continue

            # Bubble reward biasanya di area sisi/tengah luar puzzle
            side_bonus = 1200 if (center_x < width * 0.34 or center_x > width * 0.66) else 0
            score = area + side_bonus + white_ratio * 6500 + colored_ratio * 1300
            candidates.append((score, center_x, center_y, f"cash-bubble area={int(area)} bbox=({x},{y},{w},{h}) white={white_ratio:.2f} color={colored_ratio:.2f}"))

        if not candidates:
            return None
        candidates.sort(reverse=True)
        _, x, y, info = candidates[0]
        return int(x), int(y), info

    def build_bubble_burst_points(self, x: int, y: int, width: int, height: int) -> list[Tuple[int, int]]:
        """Titik tap brutal: bubble + sweep area aman. Sama brutalnya dengan Magic Ocean."""
        import math
        now = time.time()
        cx, cy = int(x), int(y)
        pair_v = getattr(self, "last_bubble_pair_velocity", None) or (0.0, -180.0)
        vx, vy = pair_v
        if abs(vx) < 20 and abs(vy) < 20:
            vy = -180.0
        self.prev_bubble_detection = (now, cx, cy)

        points: list[Tuple[int, int]] = []
        seen: set[Tuple[int, int]] = set()

        # Zona exclude: Penarikan kanan atas, menu kiri atas, puzzle tengah
        withdraw_rect = (int(width * 0.48), int(height * 0.04), width, int(height * 0.20))
        menu_rect = (0, int(height * 0.145), int(width * 0.18), int(height * 0.235))
        center_tiles_rect = (int(width * 0.30), int(height * 0.33), int(width * 0.72), int(height * 0.58))

        def in_rect(px, py, rect):
            x1, y1, x2, y2 = rect
            return x1 <= px <= x2 and y1 <= py <= y2

        def safe(px, py):
            px, py = int(px), int(py)
            if px < 18 or px > width - 18:
                return False
            if py < int(height * BUBBLE_SCAN_TOP_RATIO) or py > int(height * BUBBLE_SCAN_BOTTOM_RATIO):
                return False
            if in_rect(px, py, withdraw_rect):
                return False
            if in_rect(px, py, menu_rect):
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

        # 2) Ring ekstra di sekitar badan bubble dan jalur geraknya (prioritas batch pertama)
        for px, py in centers[:5]:
            for radius in (18, 32, 48, 68, 92):
                steps = max(8, int(2 * math.pi * radius / 18))
                for i in range(steps):
                    angle = 2 * math.pi * i / steps
                    add_p(int(px + radius * math.cos(angle)), int(py + radius * math.sin(angle)))

        # 3) Sweep area aman jika bubble melenceng jauh
        step = 28
        y_start = int(height * BUBBLE_SCAN_TOP_RATIO)
        y_end = int(height * BUBBLE_SCAN_BOTTOM_RATIO)
        rows = list(range(y_start, y_end, step))
        ordered_rows: list[int] = []
        lo, hi = 0, len(rows) - 1
        while lo <= hi:
            ordered_rows.append(rows[lo])
            if lo != hi:
                ordered_rows.append(rows[hi])
            lo += 1
            hi -= 1
        row = 0
        for gy in ordered_rows:
            offset = 0 if row % 2 == 0 else step // 2
            for gx in range(24 + offset, width - 20, step):
                add_p(gx, gy)
            row += 1

        for dy in range(0, int(height * 0.75), 18):
            add_p(cx, cy - dy)
            add_p(cx, cy + dy)
            add_p(cx - 24, cy - dy)
            add_p(cx + 24, cy - dy)
            add_p(cx - 48, cy - dy)
            add_p(cx + 48, cy - dy)
            add_p(cx - 24, cy + dy)
            add_p(cx + 24, cy + dy)
            add_p(cx - 48, cy + dy)
            add_p(cx + 48, cy + dy)

        # 4) Crosshair rapat
        for offset in range(-150, 151, 18):
            add_p(cx + offset, cy)
            add_p(cx, cy + offset)
            add_p(cx + offset, cy - 36)
            add_p(cx + offset, cy + 36)

        self.log(
            "BUILD BURST GELEMBUNG BRUTAL: "
            f"{len(points)} titik | exclude penarikan={withdraw_rect}, menu={menu_rect}"
        )
        return points[:1400]

    def generate_magic_ocean_tile_points(self) -> list[Tuple[int, int]]:
        """Titik tap di area board kotak-kotak ubin Magic Ocean Tile Crush (720x1640)."""
        points = []
        col_w = (580 - 140) / 4.0
        row_h = (850 - 550) / 4.0

        idx = self.tile_tap_index
        for i in range(3):
            cur_idx = (idx + i) % 16
            c = cur_idx % 4
            r = cur_idx // 4
            x = int(140 + (c + 0.5) * col_w)
            y = int(550 + (r + 0.5) * row_h)
            points.append((x, y))

        self.tile_tap_index = (self.tile_tap_index + 3) % 16
        return points

    def find_gameplay_tiles(self, png_data: bytes, width: int, height: int) -> list[Tuple[int, int]]:
        """Deteksi kotak-kotak ubin langsung di layar gameplay board Magic Ocean."""
        try:
            import cv2
            import numpy as np
            img = cv2.imdecode(np.frombuffer(png_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                return []
            crop = img[500:900, 100:620]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            tiles = []
            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                if 50 <= w <= 110 and 50 <= h <= 110:
                    cx = 100 + x + w // 2
                    cy = 500 + y + h // 2
                    if not any(abs(cx - tx) < 30 and abs(cy - ty) < 30 for tx, ty in tiles):
                        tiles.append((cx, cy))
            return tiles
        except Exception:
            return []

    def do_gameplay_tile_tap(self) -> None:
        """Tap kotak-kotak ubin di halaman utama untuk mencocokkan ubin & memicu pop-up hadiah/iklan."""
        now = time.time()
        if now - self.last_tile_tap_ts < 0.05:
            return
        self.last_tile_tap_ts = now

        screenshot = self.capture_screenshot()
        tiles = []
        if screenshot:
            png_data, width, height = screenshot
            tiles = self.find_gameplay_tiles(png_data, width, height)

        if tiles:
            tap_points = tiles[:3]
            self.log(f"TAP KOTAK UBIN TERDETEKSI: tap {len(tap_points)} ubin {tap_points} untuk memicu iklan/hadiah")
        else:
            tap_points = self.generate_magic_ocean_tile_points()
            self.log(f"TAP KOTAK UBIN GRID: tap {len(tap_points)} ubin {tap_points} untuk memicu iklan/hadiah")

        self.monkey_burst(tap_points, delay_ms=0, timeout=2)

    def update_bubble_search(self, app: Optional[ForegroundApp]) -> None:
        now = time.time()
        if app and self.is_game_ad(app):
            self.bubble_watch_active = False
            self.prev_bubble_detection = None
            return
        if not app or app.package != TARGET_PACKAGE:
            return

        # Jangan tulis log "tidak ada DOBEL" saat OCR sebelumnya jelas masih melihat tombol DOBEL.
        # Saat DOBEL masih terlihat, prioritasnya retry klik DOBEL, bukan scan gelembung.
        if self.dobel_visible:
            return

        if self.bubble_watch_active:
            self.notify_bubble_search_once("mode cari gelembung aktif")

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
                screen_w, screen_h = getattr(self, "last_bubble_screen_size", self.get_screen_size())
                points = self.build_bubble_burst_points(x, y, screen_w, screen_h)
                self.log(f"TAP GELEMBUNG TERFOKUS: {len(points)} titik rapat tepat di badan & jalur ({x},{y})")
                tap_start_ts = time.time()
                opened = self.tap_bubble_until_ad(points)
                tap_ms = int((time.time() - tap_start_ts) * 1000)
                self.log(f"SELESAI TAP GELEMBUNG: durasi_tap={tap_ms}ms opened={opened}")
                after = self.get_foreground_app()
                if opened or (after and self.is_game_ad(after)):
                    activity = after.activity if after else "unknown"
                    self.log(f"BERHASIL BUKA IKLAN SETELAH TAP GELEMBUNG: {activity}")
                    self.notify_ad_opened(activity, source="GELEMBUNG", info=info)
                    self.bubble_watch_active = False
                    self.prev_bubble_detection = None
            return

        if not self.bubble_watch_active:
            self.log("MENUNGGU TARGET: tidak ada DOBEL/NOW NOT, scan cash-bubble normal belum menemukan target")
            self.do_gameplay_tile_tap()
            return

        elapsed = now - self.bubble_watch_start_ts
        self.log(f"BELUM MENEMUKAN GELEMBUNG BERGERAK | durasi cari {self.format_duration(elapsed)}")
        self.do_gameplay_tile_tap()
        if elapsed >= BUBBLE_TIMEOUT_SECONDS:
            self.restart_game_for_bubble_search(
                f"{self.format_duration(elapsed)} tidak menemukan gelembung"
            )

    def step(self) -> Tuple[str, Optional[ForegroundApp]]:
        if getattr(self, "seeding_slot_routine", False):
            return "seeding_slot_routine", None
        app = self.get_foreground_app()
        if not app:
            self.update_ad_log(None)
            self.update_dobel_log(None)
            self.launch_game(reason="foreground tidak terbaca")
            return "launch_unknown_foreground", None

        if app.package != self.last_foreground:
            self.last_foreground = app.package
            self.log(f"Foreground: {app.package}/{app.activity}")

        if self.handle_confirm_close_popup(app):
            self.last_action = "clicked_confirm_close_continue"
            return "clicked_confirm_close_continue", app

        if app.activity == "Application Not Responding":
            self.clear_apps_and_reopen_game(f"ANR/stuck terdeteksi pada {app.package}")
            self.last_action = "cleared_anr"
            return "cleared_anr", app

        if app.package == TARGET_PACKAGE:
            if self.handle_wallet_page_if_needed(app):
                self.last_action = "closed_wallet_page"
                return "closed_wallet_page", app
            if self.handle_gagal_popup(app):
                self.last_action = "clicked_hidup_kembali"
                return "clicked_hidup_kembali", app

            if self.is_game_ad(app):
                if self.handle_tiktok_ad_if_needed(app):
                    self.last_action = "cleared_tiktok_recents_and_reopened"
                    return "cleared_tiktok_recents_and_reopened", app
                self.update_ad_log(app)
                self.try_finish_ad(app)
                self.last_action = "handling_ad"
                return "handling_ad", app

            # Berada di Halaman Utama Game (ada tombol Penarikan di kanan atas)
            if self.ad_start_ts is not None:
                elapsed = time.time() - self.ad_start_ts
                finished_ad = self.ad_activity or "unknown"
                net, ad_type, short_id = self.get_ad_info(finished_ad)
                is_slot = getattr(self, "current_ad_slot_detected", False) or getattr(self, "last_ad_was_slot", False)
                slot_tag = "IKLAN SLOT" if is_slot else "BUKAN SLOT"
                self.log(f"IKLAN SELESAI [DETEKSI: {slot_tag} | NETWORK: {net} | ID: {short_id}]: {finished_ad} | total durasi {self.format_duration(elapsed)}")
                self.ad_start_ts = None
                self.ad_activity = None
                self.last_ad_log_second = -1
                self.last_ad_close_check_ts = 0.0
                if not getattr(self, "ad_finished_reported", False):
                    self.ad_finished_reported = True
                    self.on_ad_finished(finished_ad, elapsed)
                self.current_ad_slot_detected = False

            if self.check_auto_withdraw_if_needed(app):
                self.last_action = "auto_withdraw_performed"
                return "auto_withdraw_performed", app

            self.update_dobel_log(app)
            self.update_bubble_search(app)

            self.last_action = "game_main_screen"
            return "game_main_screen", app

        if self.handle_tiktok_ad_if_needed(app):
            self.last_action = "cleared_tiktok_recents_and_reopened"
            return "cleared_tiktok_recents_and_reopened", app

        self.update_ad_log(app)
        self.try_finish_ad(app)

        if getattr(self, "seeding_slot_routine", False):
            return "seeding_slot_routine", app

        if app.package in BLOCKED_PACKAGES:
            self.close_blocked_app_and_return(app.package)
            self.last_action = "closed_blocked_and_returned"
            return "closed_blocked_and_returned", app

        if getattr(self, "seeding_slot_routine", False):
            return "seeding_slot_routine", app

        # Kalau bukan game dan bukan app sistem penting, buka game.
        self.launch_game(reason=f"foreground sekarang {app.package}")
        self.last_action = "launched_game"
        return "launched_game", app

    def run(self, once: bool = False) -> int:
        self.log(f"Bot aktif untuk {TARGET_NAME} ({TARGET_PACKAGE})")
        self.log(f"Log: {LOG_FILE}")
        if not self.has_device():
            return 2
        if not self.is_target_installed():
            self.log(f"Game belum terinstall: {TARGET_PACKAGE}")
            return 3

        try:
            while True:
                self.step()
                if once:
                    return 0
                time.sleep(0.002 if self.bubble_watch_active else self.interval)
        except KeyboardInterrupt:
            self.log("Bot dihentikan oleh user")
            return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Guardian bot untuk menjaga Magic Ocean Tile Crush tetap terbuka")
    parser.add_argument("--serial", "-s", default="", help="Serial device ADB, opsional jika cuma 1 device")
    parser.add_argument("--interval", "-i", type=float, default=DEFAULT_INTERVAL, help="Interval cek foreground dalam detik")
    parser.add_argument("--once", action="store_true", help="Cek sekali lalu keluar")
    parser.add_argument("--dry-run", action="store_true", help="Log aksi tanpa mengeksekusi force-stop/launch")
    args = parser.parse_args()

    bot = MagicOceanGuardian(serial=args.serial, interval=max(0.005, args.interval), dry_run=args.dry_run)
    return bot.run(once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
