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

TARGET_PACKAGE = "com.dudufun.juicyslashbladefruit"
TARGET_NAME = "Juicy Slash Blade Fruit"

# App yang sering terbuka karena iklan / redirect.
BLOCKED_PACKAGES = {
    "com.android.chrome": "Chrome",
    "com.chrome.beta": "Chrome Beta",
    "com.chrome.dev": "Chrome Dev",
    "com.google.android.apps.chrome": "Chrome",
    "com.android.vending": "Play Store",
    "com.starlightgame.woodlandtilematcher": "Woodland Tile Matcher redirect",
    "com.bubble.crush.stick.magicgames": "Bubble Crush redirect",
    "com.starlightgame.magicoceantilecrush": "Magic Ocean redirect",
    "com.corona.cardjam": "Card Jam redirect",
}

LOG_FILE = os.path.expanduser("~/juicy_slash_guardian_bot.log")
SALDO_STATE_FILE = os.path.expanduser("~/juicy_slash_saldo_state.json")
TELEGRAM_SENDER = "/Users/macbookair/telegram_sender.py"
DEFAULT_INTERVAL = 1.0
OCR_HELPER = "/Users/macbookair/ocr_helper"
TAP_MARKER = "/Users/macbookair/scrcpy_tap_marker"
DOBEL_CHECK_INTERVAL = 2.0
DOBEL_TAP_RETRY_SECONDS = 4.0
AD_CLOSE_CHECK_INTERVAL = 1.0
AD_CLOSE_MIN_SECONDS = 5.0
AD_STUCK_RESTART_SECONDS = 120.0
BUBBLE_CHECK_INTERVAL = 0.0
BUBBLE_TIMEOUT_SECONDS = 16.0
BUBBLE_TAP_COOLDOWN = 0.0
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
BAD_AD_ACTIVITIES = {
    "com.applovin.adview.applovinfullscreenactivity",
}


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
        self.last_ad_close_check_ts = 0.0
        self.last_ad_close_tap_ts = 0.0
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
        self.last_weapon_check_ts = 0.0
        self.prev_bubble_detection: Optional[Tuple[float, int, int]] = None
        self.last_progress_pct: float = -1.0        # % progress bar terakhir (-1 = tidak terdeteksi)
        self.last_progress_log_ts: float = 0.0      # kapan terakhir log progress
        self.last_countdown_sec: int = -1            # detik countdown terakhir terdeteksi (-1 = tidak ada)
        self.last_countdown_log_ts: float = 0.0      # kapan terakhir log countdown

    def log(self, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        print(line, flush=True)
        if os.environ.get("JUICY_SLASH_NO_FILE_LOG") == "1":
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

    def tap(self, x: int, y: int) -> None:
        self.show_tap_marker([(int(x), int(y), "blue", 1.3, 58)])
        if self.dry_run:
            self.log(f"DRY RUN: tap {x},{y}")
            return
        self.adb_out(["shell", "input", "tap", str(x), str(y)], timeout=5)

    def show_tap_marker(self, specs: list[Tuple[int, int, str, float, int]]) -> None:
        if not os.path.exists(TAP_MARKER) or os.environ.get("FRUIT_BLADE_DISABLE_MARKER") == "1":
            self.log(f"MARKER TIDAK AKTIF: file tidak ada atau disable | specs={len(specs)}")
            return
        args: list[str] = []
        # Batasi supaya marker tetap ringan.
        for x, y, color, duration, diameter in specs[:220]:
            args += [str(int(x)), str(int(y)), color, str(float(duration)), str(int(diameter))]
        try:
            subprocess.Popen([TAP_MARKER, *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            preview = ", ".join(f"({x},{y},{color})" for x, y, color, _, _ in specs[:8])
            self.log(f"MARKER DIBUAT: {len(specs)} titik | {preview}")
        except Exception:
            self.log("MARKER GAGAL DIBUAT")

    def monkey_burst(self, points: list[Tuple[int, int]], delay_ms: int = 1, timeout: int = 8) -> None:
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

        self.monkey_burst(unique_points, delay_ms=3, timeout=timeout)

    def tap_bubble_until_ad(self, points: list[Tuple[int, int]]) -> bool:
        """Tap gelembung brutal: kirim semua titik sekaligus, cek iklan setelah burst selesai."""
        if not points:
            return False
        self.log(f"TAP BURST GELEMBUNG: {len(points)} titik presisi – delay 1ms per tap")
        self.tap_many(points, timeout=6, color="red")
        self.last_dobel_check_ts = 0.0
        time.sleep(0.15)
        app = self.get_foreground_app()
        if app and (self.is_game_ad(app) or app.package != TARGET_PACKAGE):
            self.log(f"STOP TAP GELEMBUNG: foreground berubah ke iklan ({app.package}/{app.activity})")
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
        if not devices or (self.serial and self.serial not in devices):
            # Coba auto-reconnect ADB server jika koneksi sempat drop
            try:
                subprocess.run(["adb", "kill-server"], timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["adb", "start-server"], timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1.0)
                output = self.adb_out(["devices"], timeout=8)
                devices = []
                for line in output.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "device":
                        devices.append(parts[0])
            except Exception:
                pass
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
        self.last_progress_pct = -1.0
        self.last_progress_log_ts = 0.0
        self.last_countdown_sec = -1
        self.last_countdown_log_ts = 0.0
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
        if same_ad and same_reward and now - self.last_duplicate_dobel_restart_ts >= 20:
            self.last_duplicate_dobel_restart_ts = now
            self.clear_apps_and_reopen_game(
                f"iklan DOBEL sama dan reward tidak berubah ({activity}); "
                f"reward sekarang={current_reward_raw}, sebelumnya={previous_reward_raw}"
            )
            self.pending_dobel_reward_value = None
            self.pending_dobel_reward_raw = ""
            return True

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
        if app.package != TARGET_PACKAGE:
            return False
        activity = app.activity.lower()
        # Juicy Slash memakai AppActivity sebagai halaman game / halaman awal.
        # Setelah iklan selesai foreground kembali ke AppActivity; jangan dianggap iklan.
        if activity.endswith(".appactivity") or activity == "com.dudufun.juicyslashbladefruit.appactivity":
            return False
        if any(keyword in activity for keyword in AD_ACTIVITY_KEYWORDS):
            return True
        # Fail-safe: game utama biasanya UnityPlayerActivity/AppActivity. Kalau package game membuka
        # activity lain, biasanya itu fullscreen/interstitial ad. Jangan diam scan bubble.
        if activity and activity not in {"application not responding"} and "unityplayeractivity" not in activity and "appactivity" not in activity:
            return True
        return False

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

            if self.ad_start_ts is None or self.ad_activity != app.activity:
                self.ad_start_ts = now
                self.ad_activity = app.activity
                self.last_ad_log_second = 0
                self.log(f"IKLAN TERBUKA: {app.activity} | durasi {self.format_duration(0)}")
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
            # Log durasi setiap interval cek, tapi tidak dobel dalam detik yang sama.
            if elapsed_second != self.last_ad_log_second:
                self.last_ad_log_second = elapsed_second
                self.log(f"[IKLAN] Sedang menunggu iklan selesai... ({app.activity} berjalan {self.format_duration(elapsed)})")
            return

        if self.ad_start_ts is not None:
            elapsed = time.time() - self.ad_start_ts
            self.log(f"IKLAN SELESAI: {self.ad_activity} | total durasi {self.format_duration(elapsed)}")
            self.ad_start_ts = None
            self.ad_activity = ""
            self.last_ad_log_second = -1
            self.last_ad_close_check_ts = 0.0

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
        if not os.path.exists(TELEGRAM_SENDER):
            self.log(f"TELEGRAM GAGAL: sender tidak ada {TELEGRAM_SENDER}")
            return
        try:
            result = subprocess.run(
                ["python3", TELEGRAM_SENDER, message],
                capture_output=True,
                text=True,
                timeout=15,
            )
            ok = result.returncode == 0
            self.log(f"TELEGRAM {'TERKIRIM' if ok else 'GAGAL'}: saldo report | rc={result.returncode}")
            if result.stdout.strip():
                self.log(f"TELEGRAM STDOUT: {result.stdout.strip()[:180]}")
            if result.stderr.strip():
                self.log(f"TELEGRAM STDERR: {result.stderr.strip()[:180]}")
        except Exception as exc:
            self.log(f"TELEGRAM ERROR: {exc}")

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
            "💰 <b>UPDATE SALDO JUICY SLASH BLADE FRUIT</b>\n"
            f"🕐 <b>Waktu:</b> {html.escape(now_str)}\n"
            f"📌 <b>Pemicu:</b> {html.escape(reason)}\n"
            f"📊 <b>Saldo sebelumnya:</b> {html.escape(prev_display)}\n"
            f"✅ <b>Saldo sekarang:</b> {html.escape(self.format_rupiah(current_value))}\n"
            f"↕️ <b>Selisih saldo:</b> {html.escape(diff_display)}\n"
            f"⏱️ <b>Jarak dari data sebelumnya:</b> {html.escape(elapsed_text)}\n"
            f"🔎 <b>OCR:</b> <code>{html.escape(raw_text[:80])}</code>"
        )
        self.log(
            f"SALDO TERDETEKSI: sekarang={self.format_rupiah(current_value)} "
            f"sebelumnya={prev_display} selisih={diff_display} elapsed={elapsed_text}"
        )
        self.send_telegram_message(message)

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
            "<b>JUICY SLASH BLADE FRUIT: TOMBOL DOBEL TERDETEKSI</b>\n"
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
        self.send_telegram_message(message)

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
            "<b>JUICY SLASH BLADE FRUIT: IKLAN TERBUKA</b>\n"
            f"<b>Waktu:</b> {html.escape(now_str)}\n"
            f"<b>Sumber:</b> {html.escape(source)}\n"
            f"<b>Activity iklan:</b> <code>{html.escape(activity)}</code>\n"
            f"<b>Lama cari gelembung:</b> {html.escape(search_elapsed)}\n"
            f"<b>Info:</b> {html.escape(info[:160])}"
        )
        self.log(f"TELEGRAM NOTIF: iklan terbuka | source={source} | {activity}")
        self.send_telegram_message(message)

    def notify_bubble_search_once(self, reason: str) -> None:
        if self.bubble_search_notified:
            return
        self.bubble_search_notified = True
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
        message = (
            "🔎 <b>JUICY SLASH BLADE FRUIT: MULAI CARI GELEMBUNG</b>\n"
            f"🕐 <b>Waktu:</b> {html.escape(now_str)}\n"
            f"📌 <b>Pemicu:</b> {html.escape(reason)}\n"
            f"⏳ <b>Timeout:</b> {html.escape(self.format_duration(BUBBLE_TIMEOUT_SECONDS))}\n"
            "🎯 <i>Bot mulai scan cash-bubble dan akan brutal tap jika ketemu.</i>"
        )
        self.log(f"TELEGRAM NOTIF: mulai cari gelembung | {reason}")
        self.send_telegram_message(message)

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
        try:
            from PIL import Image
            from io import BytesIO

            image = Image.open(BytesIO(png_data))
            width, height = image.size
            return png_data, width, height
        except Exception:
            width, height = self.get_screen_size()
            return png_data, width, height

    def dump_ui_tree(self) -> Optional[ET.Element]:
        # Pada sebagian iklan uiautomator bisa gagal "could not get idle state"; itu normal.
        self.adb_out(["shell", "uiautomator", "dump", "/sdcard/juicy_slash_ui.xml"], timeout=5)
        xml_text = self.adb_out(["shell", "cat", "/sdcard/juicy_slash_ui.xml"], timeout=5)
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
            "×",
            "close",
            "tutup",
            "skip",
            "lewati",
            "next",
            "see next",
            "seenext",
            "continue",
            "lanjutkan",
            "lanjut",
            ">",
            "›",
            "»",
        }
        screen_w, screen_h = self.get_screen_size()
        for node in root.iter("node"):
            text = (node.get("text") or "").strip()
            desc = (node.get("content-desc") or "").strip()
            res_id = (node.get("resource-id") or "").strip().lower()
            label = text or desc
            if not label and any(token in res_id for token in ("close", "skip", "dismiss", "tutup", "btn_close")):
                label = res_id
            if not label:
                continue
            norm = self.normalize_text(label)
            raw = label.strip().lower()
            if raw not in finish_words and norm not in finish_words and not any(token in norm for token in ("close", "tutup", "skip", "lewati", "seenext", "continue", "lanjutkan")):
                continue
            center = self.parse_bounds(node.get("bounds", ""))
            if not center:
                continue
            x, y = center
            # Hindari tombol navigasi Android bawah; tombol close/next iklan biasanya tepi atas/kanan.
            if y > screen_h * 0.88:
                continue
            if raw == "see next" or norm == "seenext" or "seenext" in norm:
                return "PANAH_KANAN/NEXT", label, x, y
            if raw == "continue" or norm == "continue" or raw == "lanjutkan" or norm == "lanjutkan":
                return "PANAH_KANAN/NEXT", label, x, y
            is_corner = y < screen_h * 0.30 and (x < screen_w * 0.35 or x > screen_w * 0.65)
            is_store = raw in {"play", "google play", "buka toko", "open store", "store", "install", "instal"}
            if x > screen_w * 0.65 or y < screen_h * 0.30 or raw in {"close", "tutup", "skip", "lewati", "next", "see next", "continue", "lanjutkan", "lanjut"}:
                if is_store and not is_corner:
                    continue
                kind = "X" if raw in {"x", "×", "close", "tutup"} else ("PLAY/STORE" if is_store else "PANAH_KANAN/NEXT")
                return kind, label, x, y

        # Kwai/Alliance sering menaruh tombol X sebagai ImageView tanpa text/content-desc.
        # Contoh stuck: bounds [586,479][618,511] di sisi kanan kartu promo.
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
            # Tombol close promo biasanya kecil di sisi kanan, bukan tombol CTA tengah/bawah.
            if x < screen_w * 0.72 or y < screen_h * 0.18 or y > screen_h * 0.70:
                continue
            score = x + (screen_h * 0.70 - y) * 0.2
            image_candidates.append((score, x, y, bounds))
        if image_candidates:
            image_candidates.sort(reverse=True)
            _score, x, y, bounds = image_candidates[0]
            return "X", f"kwai image close {bounds}", x, y

        # Fallback: cari tombol Buka Toko / Install / Open Store di endcard iklan
        store_labels = {"buka toko", "open store", "install", "instal", "unduh", "download", "dapatkan", "get"}
        for node in root.iter("node"):
            text = (node.get("text") or "").strip()
            desc = (node.get("content-desc") or "").strip()
            label = text or desc
            if not label:
                continue
            norm_s = self.normalize_text(label)
            raw_s = label.strip().lower()
            is_store_btn = (
                raw_s in store_labels
                or any(t in norm_s for t in ("bukatoko", "openstore", "install", "unduh", "download", "dapatkan"))
            )
            if not is_store_btn:
                continue
            center = self.parse_bounds(node.get("bounds", ""))
            if not center:
                continue
            xs, ys = center
            # Hanya klik tombol Buka Toko di pojok kanan atas atau kiri atas.
            # Tombol di tengah layar / bawah adalah CTA iklan – JANGAN diklik.
            is_top_corner = (
                ys < screen_h * 0.30
                and (xs < screen_w * 0.35 or xs > screen_w * 0.65)
            )
            if not is_top_corner:
                self.log(f"[UI BUKA TOKO] Abaikan tombol '{label}' di ({xs},{ys}) – bukan pojok atas (hanya pojok kanan/kiri atas yang diklik)")
                continue
            self.log(f"[UI BUKA TOKO] Ditemukan tombol '{label}' di ({xs},{ys}) – posisi pojok atas VALID")
            return "BUKA_TOKO", label, xs, ys
        return None

    def find_ad_finish_button_by_ocr(self, png_data: bytes, width: int, height: int) -> Optional[Tuple[str, str, int, int]]:
        if not os.path.exists(OCR_HELPER):
            return None

        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
        screenshot_path = f"/tmp/juicy_slash_ad_close_{safe_serial}.png"
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
            "seenext": "PANAH_KANAN/NEXT",
            "continue": "PANAH_KANAN/NEXT",
            "lanjutkan": "PANAH_KANAN/NEXT",
            "lanjut": "PANAH_KANAN/NEXT",
        }
        arrow_chars = {">", "›", "»", "→"}
        for line in (result.stdout or "").splitlines():
            text, _, bbox = line.partition("|")
            label = text.strip()
            if not label or not bbox:
                continue
            norm = self.normalize_text(label)
            raw = label.strip().lower()
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
            if raw == "see next" or norm == "seenext" or "seenext" in norm:
                return "PANAH_KANAN/NEXT", label, x, y
            if raw == "continue" or norm == "continue" or raw == "lanjutkan" or norm == "lanjutkan":
                return "PANAH_KANAN/NEXT", label, x, y
            is_corner = y < height * 0.32 and (x < width * 0.38 or x > width * 0.62)
            if kind == "PLAY/STORE" and not is_corner:
                continue
            # Tulisan Close/Tutup kadang berupa tombol teks di tengah/bawah iklan.
            # Klik selama masih bukan area navigation bar bawah.
            if kind == "X" and any(token in norm for token in ("close", "tutup")) and y < height * 0.86:
                return kind, label, x, y
            if x > width * 0.60 or y < height * 0.30:
                return kind, label, x, y

        # Fallback: cari teks Buka Toko / Install / Open Store (endcard iklan)
        store_labels_ocr = {"buka toko", "open store", "install", "instal", "unduh", "download", "dapatkan", "get"}
        for line2 in (result.stdout or "").splitlines():
            txt2, _, bbox2 = line2.partition("|")
            lbl2 = txt2.strip()
            if not lbl2 or not bbox2:
                continue
            norm2 = self.normalize_text(lbl2)
            raw2 = lbl2.strip().lower()
            is_store_ocr = (
                raw2 in store_labels_ocr
                or any(t in norm2 for t in ("bukatoko", "openstore", "install", "unduh", "download", "dapatkan"))
            )
            if not is_store_ocr:
                continue
            try:
                bx2, by2, bw2, bh2 = [float(p) for p in bbox2.split(",")]
            except ValueError:
                continue
            xo = int((bx2 + bw2 / 2) * width)
            yo = int((1 - by2 - bh2 / 2) * height)
            # Hanya klik tombol Buka Toko di pojok kanan atas atau kiri atas.
            is_top_corner_ocr = (
                yo < height * 0.30
                and (xo < width * 0.35 or xo > width * 0.65)
            )
            if not is_top_corner_ocr:
                self.log(f"[OCR BUKA TOKO] Abaikan '{lbl2}' di ({xo},{yo}) – bukan pojok atas")
                continue
            self.log(f"[OCR BUKA TOKO] Ditemukan tombol '{lbl2}' di ({xo},{yo}) – posisi pojok atas VALID")
            return "BUKA_TOKO", lbl2, xo, yo
        return None

    def find_ad_continue_button_by_ocr(self, png_data: bytes, width: int, height: int) -> Optional[Tuple[str, str, int, int]]:
        """Prioritas khusus popup konfirmasi close: jika ada Continue/Lanjutkan, klik itu.

        Dipanggil sebelum deteksi ikon pojok agar popup "confirm to close" tidak kalah
        oleh tombol close/next yang masih terlihat di belakang popup.
        """
        if not os.path.exists(OCR_HELPER):
            return None
        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
        screenshot_path = f"/tmp/juicy_slash_ad_continue_{safe_serial}.png"
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

        candidates = []
        for line in (result.stdout or "").splitlines():
            text, _, bbox = line.partition("|")
            label = text.strip()
            if not label or not bbox:
                continue
            norm = self.normalize_text(label)
            raw = label.strip().lower()
            if raw not in {"continue", "lanjutkan"} and norm not in {"continue", "lanjutkan"}:
                continue
            try:
                bx, by, bw, bh = [float(part) for part in bbox.split(",")]
            except ValueError:
                continue
            x = int((bx + bw / 2) * width)
            y = int((1 - by - bh / 2) * height)
            if y > height * 0.88:
                continue
            # Tombol popup biasanya tengah/bawah layar; prioritaskan yang lebih dekat tengah.
            score = 1000 - abs(x - width // 2) - abs(y - int(height * 0.62)) * 0.3
            candidates.append((score, label, x, y))

        if not candidates:
            return None
        candidates.sort(reverse=True)
        _score, label, x, y = candidates[0]
        return "PANAH_KANAN/NEXT", label, int(x), int(y)

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

        # Juicy/MBridge playable: panah putih kecil sering muncul di kanan atas,
        # tepat di bawah overlay pointer-location. Tombol aktif sekitar x 660 y 110.
        try:
            rx1, rx2 = int(width * 0.82), width
            ry1, ry2 = max(70, int(height * 0.04)), int(height * 0.105)
            roi = img[ry1:ry2, rx1:rx2]
            if roi.size:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                white = cv2.inRange(gray, 185, 255)
                white = cv2.morphologyEx(white, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8), iterations=1)
                contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                arrow_candidates = []
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w < 10 or h < 12 or w > 55 or h > 55:
                        continue
                    abs_x = rx1 + x + w // 2
                    abs_y = ry1 + y + h // 2
                    patch = white[
                        max(0, y - 4):min(white.shape[0], y + h + 4),
                        max(0, x - 4):min(white.shape[1], x + w + 4),
                    ]
                    lines = cv2.HoughLinesP(patch, 1, np.pi / 180, threshold=6, minLineLength=9, maxLineGap=5)
                    if lines is None:
                        continue
                    diag = 0
                    for line in lines.reshape(-1, 4):
                        x1, y1, x2, y2 = [int(v) for v in line]
                        dx, dy = x2 - x1, y2 - y1
                        if dx == 0 and dy == 0:
                            continue
                        angle = abs(np.degrees(np.arctan2(dy, dx)))
                        if 20 <= angle <= 75:
                            diag += 1
                    if diag >= 1:
                        area = cv2.contourArea(contour)
                        score = area + abs_x - abs(abs_y - int(height * 0.07)) * 3
                        arrow_candidates.append((score, abs_x, abs_y, f"top-right white arrow bbox=({rx1+x},{ry1+y},{w},{h})"))
                if arrow_candidates:
                    arrow_candidates.sort(reverse=True)
                    _score, x, y, label = arrow_candidates[0]
                    # Tap pusat area aktif tombol, bukan tepat di garis ikon.
                    return "PANAH_KANAN/TOP", label, min(width - 12, max(int(x), int(width * 0.92))), max(70, int(y))
        except Exception:
            pass

        # Juicy/MBridge playable kadang menampilkan X putih di kanan atas
        # pada tombol hijau. Ini harus dideteksi sebelum tombol Continue tengah.
        try:
            rx1 = int(width * 0.78)
            ry1 = max(30, int(height * 0.018))
            ry2 = int(height * 0.115)
            roi = img[ry1:ry2, rx1:width]
            if roi.size:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                white = cv2.inRange(gray, 185, 255)
                white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
                contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                white_x_candidates = []
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w < 16 or h < 16 or w > 70 or h > 70:
                        continue
                    abs_x = rx1 + x + w // 2
                    abs_y = ry1 + y + h // 2
                    if abs_x < width * 0.84 or abs_y > height * 0.12:
                        continue
                    patch = white[
                        max(0, y - 5):min(white.shape[0], y + h + 5),
                        max(0, x - 5):min(white.shape[1], x + w + 5),
                    ]
                    lines = cv2.HoughLinesP(patch, 1, np.pi / 180, threshold=8, minLineLength=12, maxLineGap=5)
                    if lines is None:
                        continue
                    pos_diag = 0
                    neg_diag = 0
                    for line in lines.reshape(-1, 4):
                        x1, y1, x2, y2 = [int(v) for v in line]
                        dx, dy = x2 - x1, y2 - y1
                        if dx == 0 and dy == 0:
                            continue
                        angle = np.degrees(np.arctan2(dy, dx))
                        if 25 <= angle <= 75:
                            pos_diag += 1
                        elif -75 <= angle <= -25:
                            neg_diag += 1
                    if pos_diag >= 1 and neg_diag >= 1:
                        area = cv2.contourArea(contour)
                        score = area + abs_x * 0.5 - abs(abs_y - int(height * 0.04)) * 3
                        white_x_candidates.append((score, abs_x, abs_y, f"top-right white X bbox=({rx1+x},{ry1+y},{w},{h})"))
                if white_x_candidates:
                    white_x_candidates.sort(reverse=True)
                    _score, x, y, label = white_x_candidates[0]
                    return "X", label, int(x), int(y)
        except Exception:
            pass

        # Jalur khusus Pangle/Bytedance IAB landing page:
        # tombol close asli sering berupa ikon "X" hitam di kiri atas pada bar putih,
        # sementara deteksi generik bisa salah memilih ikon/logo di kanan atas.
        try:
            lx1, lx2 = 0, int(width * 0.24)
            ly1, ly2 = max(70, int(height * 0.045)), int(height * 0.18)
            roi = img[ly1:ly2, lx1:lx2]
            if roi.size:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                # X hitam kuat di atas latar putih/terang.
                dark = cv2.inRange(gray, 0, 80)
                dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
                contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                left_x_candidates = []
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w < 18 or h < 18 or w > 70 or h > 70:
                        continue
                    area = cv2.contourArea(contour)
                    # Tolak ikon speaker/play berupa lingkaran gelap besar.
                    if area > 1200:
                        continue
                    perimeter = cv2.arcLength(contour, True)
                    circularity = (4 * np.pi * area / (perimeter * perimeter)) if perimeter else 0
                    if circularity > 0.55:
                        continue
                    abs_x = lx1 + x + w // 2
                    abs_y = ly1 + y + h // 2
                    if abs_x > width * 0.18 or abs_y > height * 0.18:
                        continue
                    bg_patch = gray[max(0, y - 10):min(gray.shape[0], y + h + 10), max(0, x - 10):min(gray.shape[1], x + w + 10)]
                    if bg_patch.size == 0 or float(bg_patch.mean()) < 135:
                        continue
                    patch = dark[max(0, y - 5):min(dark.shape[0], y + h + 5), max(0, x - 5):min(dark.shape[1], x + w + 5)]
                    lines = cv2.HoughLinesP(patch, 1, np.pi / 180, threshold=8, minLineLength=12, maxLineGap=5)
                    if lines is None:
                        continue
                    pos_diag = 0
                    neg_diag = 0
                    for line in lines.reshape(-1, 4):
                        x1, y1, x2, y2 = [int(v) for v in line]
                        dx, dy = x2 - x1, y2 - y1
                        if dx == 0 and dy == 0:
                            continue
                        angle = np.degrees(np.arctan2(dy, dx))
                        if 25 <= angle <= 75:
                            pos_diag += 1
                        elif -75 <= angle <= -25:
                            neg_diag += 1
                    if pos_diag >= 1 and neg_diag >= 1:
                        score = area + (width - abs_x) * 2 - abs(abs_y - int(height * 0.08))
                        left_x_candidates.append((score, abs_x, abs_y, f"left-top black X bbox=({lx1+x},{ly1+y},{w},{h})"))
                if left_x_candidates:
                    left_x_candidates.sort(reverse=True)
                    _score, x, y, label = left_x_candidates[0]
                    return "X", label, int(x), int(y)
        except Exception:
            pass

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
                        if abs_x < width * 0.82:
                            continue
                        if abs_y < max(78, int(height * 0.045)) or abs_y > height * 0.16:
                            continue
                        patch = gray[
                            max(0, cy - r): min(gray.shape[0], cy + r),
                            max(0, cx - r): min(gray.shape[1], cx + r),
                        ]
                        if patch.size == 0:
                            continue
                        mean_gray = float(patch.mean())
                        # Lingkaran close/next gelap; hindari lingkaran terang UI/game.
                        if not (45 <= mean_gray <= 135):
                            continue
                        # Titik aktif tombol X/panah kanan atas di Juicy sering sedikit
                        # lebih naik dan agak ke kanan dari center/hasil Hough.
                        tap_x = min(width - 12, abs_x + 10)
                        tap_y = max(55, abs_y - 12)
                        score = (abs_x / width) * 3000 + r * 40 - abs(abs_y - 115) * 8 - mean_gray
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

                # Klik sedikit lebih naik dari center; beberapa tombol X/panah Juicy miss jika terlalu bawah.
                tap_x = abs_x
                tap_y = max(70, abs_y - 6)
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
        """Deteksi konservatif ikon X / panah kanan di area tepi iklan."""
        try:
            import cv2
            import numpy as np
        except Exception:
            return None

        arr = np.frombuffer(png_data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        # Area yang biasanya berisi tombol close/next iklan.
        search_areas = [
            (int(width * 0.70), 0, width, int(height * 0.28)),          # kanan atas
            (0, 0, int(width * 0.30), int(height * 0.28)),              # kiri atas
            (int(width * 0.78), int(height * 0.18), width, int(height * 0.62)),  # sisi kanan
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
                horizontal = 0
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
                    elif abs(angle) <= 15:
                        horizontal += 1

                abs_x = ax1 + x + w // 2
                abs_y = ay1 + y + h // 2
                # Abaikan pointer-location overlay/status bar dan ikon palsu yang terlalu atas.
                if abs_y < max(85, int(height * 0.052)):
                    continue
                # Untuk deteksi generik, jangan ambil panah tengah playable-ad.
                # Tombol selesai iklan harus sangat atas atau sangat kanan.
                is_upper_corner = abs_y < height * 0.16 and (abs_x < width * 0.20 or abs_x > width * 0.70)
                is_right_edge = abs_x > width * 0.88
                if not (is_upper_corner or is_right_edge):
                    continue
                if pos_diag >= 1 and neg_diag >= 1:
                    kind = "X" if aspect < 1.35 else "PANAH_KANAN/NEXT"
                    return kind, "ikon terdeteksi", abs_x, abs_y
                if neg_diag >= 1 and horizontal >= 1 and abs_x > width * 0.75:
                    return "PANAH_KANAN/NEXT", "ikon terdeteksi", abs_x, abs_y
        return None

    def detect_countdown_timer(self, png_data: bytes, width: int, height: int) -> int:
        """Deteksi countdown timer di pojok kanan/kiri atas dengan OCR hanya pada crop kecil.
        Jauh lebih cepat dari OCR full-screen karena crop hanya ~15% area.
        Return: detik (>0), 0 jika habis, -1 jika tidak ada.
        """
        if not os.path.exists(OCR_HELPER):
            return -1
        try:
            import cv2
            import numpy as np
            from PIL import Image
            from io import BytesIO
        except Exception:
            return -1

        img_arr = cv2.imdecode(np.frombuffer(png_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img_arr is None:
            return -1

        # Crop hanya pojok kanan atas dan kiri atas (masing-masing 30%x20% layar)
        h, w = img_arr.shape[:2]
        margin_top    = max(55, int(h * 0.034))
        crop_h        = int(h * 0.20)
        crop_w_right  = int(w * 0.35)
        crop_w_left   = int(w * 0.35)

        crops = [
            img_arr[margin_top:margin_top + crop_h, w - crop_w_right:w],   # kanan atas
            img_arr[margin_top:margin_top + crop_h, 0:crop_w_left],         # kiri atas
        ]

        cd_pattern = re.compile(
            r"^(?:(\d{1,2}):(\d{2})|(\d{1,3})\s*s(?:ec)?\.?|(\d{1,3}))$",
            re.IGNORECASE,
        )
        best_sec = -1
        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")

        for idx, crop in enumerate(crops):
            if crop.size == 0:
                continue
            # Tulis crop ke file sementara
            crop_path = f"/tmp/juicy_slash_cd_{safe_serial}_{idx}.png"
            ok, buf = cv2.imencode(".png", crop)
            if not ok:
                continue
            try:
                with open(crop_path, "wb") as f:
                    f.write(buf.tobytes())
                result = subprocess.run(
                    [OCR_HELPER, crop_path],
                    capture_output=True, text=True, timeout=5,
                )
            except Exception:
                continue

            for line in (result.stdout or "").splitlines():
                text, _, bbox = line.partition("|")
                text = text.strip()
                if not text:
                    continue
                mm = cd_pattern.match(text)
                if not mm:
                    continue
                if mm.group(1) is not None:
                    secs = int(mm.group(1)) * 60 + int(mm.group(2))
                elif mm.group(3) is not None:
                    secs = int(mm.group(3))
                else:
                    secs = int(mm.group(4))
                    if secs > 120:
                        continue
                if secs > best_sec:
                    best_sec = secs

        return best_sec

    def detect_progress_bar(self, png_data: bytes, width: int, height: int) -> float:
        """Deteksi progress bar horizontal iklan:
          - Strip TIPIS (min 2 baris konsisten)
          - Kedua sisi cukup homogen (std < 25)
          - Kontras kiri-kanan > 25
          - Zona atas <15% dan zona bawah diperlebar sampai mepet bawah
          - Jalur tambahan: progress bar biru di bawah layar
        Return: 0.0-1.0 atau -1.0 jika tidak ditemukan.
        """
        try:
            import cv2
            import numpy as np
        except Exception:
            return -1.0

        img = cv2.imdecode(np.frombuffer(png_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return -1.0

        scan_zones = [
            (max(60, int(height * 0.038)), int(height * 0.15), "atas"),
            (int(height * 0.80), height, "bawah"),
        ]

        best_ratio = -1.0

        for y1, y2, zone_name in scan_zones:
            if y1 >= y2 or y2 > height:
                continue
            roi = img[y1:y2, :, :]
            if roi.size == 0:
                continue

            # Progress bar iklan sering berupa garis biru tipis dominan di area bawah,
            # kadang tanpa kontras grayscale yang kuat. Deteksi khusus warna biru.
            if zone_name == "bawah":
                try:
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    h, s, v = cv2.split(hsv)
                    b, g, r = cv2.split(roi)
                    blue_hsv = (h >= 90) & (h <= 140) & (s >= 60) & (v >= 70)
                    blue_bgr = (b >= 100) & (b >= g + 18) & (b >= r + 35) & (r <= 130)
                    blue_mask = (blue_hsv | blue_bgr).astype(np.uint8) * 255
                    kernel = np.ones((1, 5), np.uint8)
                    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)

                    blue_ratios = []
                    # 1) Deteksi per baris: cocok untuk progress bar tipis yang mepet bawah.
                    min_blue_px = max(18, int(width * 0.025))
                    min_span_px = max(28, int(width * 0.04))
                    for row_off in range(blue_mask.shape[0]):
                        row_mask = blue_mask[row_off, :] > 0
                        xs = np.flatnonzero(row_mask)
                        if xs.size < min_blue_px:
                            continue
                        left_x = int(xs[0])
                        right_x = int(xs[-1])
                        span = right_x - left_x + 1
                        if span < min_span_px:
                            continue
                        density = xs.size / max(1, span)
                        # Progress bar filled biasanya garis rapat dan mulai dari kiri/tepi track.
                        if density < 0.45 or left_x > int(width * 0.22):
                            continue
                        ratio = (right_x + 1) / max(1, width)
                        # Jika garis biru sudah hampir menyentuh kanan, anggap sudah selesai.
                        if right_x >= int(width * 0.92):
                            ratio = max(ratio, 0.96)
                        if 0.03 <= ratio <= 1.0:
                            blue_ratios.append(ratio)

                    # 2) Deteksi komponen horizontal: lebih kuat untuk bar biru tebal/terputus.
                    comp_mask = cv2.dilate(blue_mask, np.ones((2, 17), np.uint8), iterations=1)
                    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(comp_mask, 8)
                    for label_i in range(1, num_labels):
                        x, y, w, hgt, area = stats[label_i]
                        if w < max(50, int(width * 0.12)):
                            continue
                        if hgt > max(36, int(height * 0.035)):
                            continue
                        if area < max(40, int(w * hgt * 0.18)):
                            continue
                        if x > int(width * 0.25):
                            continue
                        right_x = int(x + w - 1)
                        ratio = (right_x + 1) / max(1, width)
                        if right_x >= int(width * 0.92):
                            ratio = max(ratio, 0.96)
                        if 0.05 <= ratio <= 1.0:
                            blue_ratios.append(ratio)

                    if len(blue_ratios) >= 2:
                        blue_ratios.sort()
                        median_b = blue_ratios[len(blue_ratios) // 2]
                        consistent_b = [r for r in blue_ratios if abs(r - median_b) < 0.10]
                        if len(consistent_b) >= 2:
                            avg_b = sum(consistent_b) / len(consistent_b)
                            if avg_b > best_ratio:
                                best_ratio = avg_b
                except Exception:
                    pass

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(float)
            strip_ratios = []
            for row_off in range(gray.shape[0]):
                row = gray[row_off, :]
                n = len(row)
                if n < 60:
                    continue
                left  = row[:n // 2]
                right = row[n // 2:]
                lm, ls = float(left.mean()),  float(left.std())
                rm, rs = float(right.mean()), float(right.std())
                diff = abs(lm - rm)
                # Kriteria dilonggarkan agar progress bar bawah/halus tetap terdeteksi.
                if diff < 25 or ls > 25 or rs > 25:
                    continue
                # Cari panjang blok filled dari kiri yang berkesinambungan
                threshold = (lm + rm) / 2.0
                filled_mask = (row < threshold) if lm < rm else (row >= threshold)
                run = 0
                for col in range(n):
                    if filled_mask[col]:
                        run = col + 1
                    else:
                        noise = int(np.sum(filled_mask[col:min(col + 6, n)]))
                        if noise <= 1:
                            break
                ratio = run / n
                if 0.03 <= ratio <= 1.0:
                    strip_ratios.append(ratio)
            if len(strip_ratios) < 2:
                continue
            strip_ratios.sort()
            median_r = strip_ratios[len(strip_ratios) // 2]
            consistent = [r for r in strip_ratios if abs(r - median_r) < 0.08]
            if len(consistent) < 2:
                continue
            avg_ratio = sum(consistent) / len(consistent)
            if avg_ratio > best_ratio:
                best_ratio = avg_ratio

        return min(1.0, best_ratio) if best_ratio >= 0.0 else -1.0

    def find_ad_finish_button(self) -> Optional[Tuple[str, str, int, int, str]]:
        screenshot = self.capture_screenshot()
        if not screenshot:
            ui_found = self.find_ad_finish_button_by_ui()
            if ui_found:
                kind, label, x, y = ui_found
                return kind, label, x, y, "ui"
            return None
        png_data, width, height = screenshot

        # PRIORITAS UTAMA: jika X/panah pojok atas terlihat, klik itu dulu.
        # Jangan kalah oleh tombol Continue tengah.
        top_corner_found = self.find_ad_top_corner_button_by_image(png_data, width, height)
        if top_corner_found:
            kind, label, x, y = top_corner_found
            return kind, label, x, y, "top-corner"

        image_top_found = self.find_ad_finish_button_by_image(png_data, width, height)
        if image_top_found:
            kind, label, x, y = image_top_found
            is_top_edge = y < height * 0.22 and (x < width * 0.38 or x > width * 0.55)
            if is_top_edge and kind in {"X", "PANAH_KANAN/NEXT", "PANAH_KANAN/TOP"}:
                return kind, label, x, y, "image-top"

        ui_found = self.find_ad_finish_button_by_ui()
        if ui_found:
            kind, label, x, y = ui_found
            ui_is_continue = self.normalize_text(label) in {"continue", "lanjutkan"} or label.strip().lower() == "continue"
            ui_is_top = y < height * 0.32 and (x < width * 0.38 or x > width * 0.55)
            if ui_is_top or not ui_is_continue:
                return kind, label, x, y, "ui"

        # Popup "confirm to close" / Continue hanya fallback jika tidak ada X/panah pojok atas.
        continue_found = self.find_ad_continue_button_by_ocr(png_data, width, height)
        if continue_found:
            kind, label, x, y = continue_found
            return kind, label, x, y, "ocr-continue"
        if ui_found:
            kind, label, x, y = ui_found
            return kind, label, x, y, "ui"

        ocr_found = self.find_ad_finish_button_by_ocr(png_data, width, height)
        if ocr_found:
            kind, label, x, y = ocr_found
            return kind, label, x, y, "ocr"

        image_found = self.find_ad_finish_button_by_image(png_data, width, height)
        if image_found:
            kind, label, x, y = image_found
            return kind, label, x, y, "image"

        return None

    def try_finish_ad(self, app: Optional[ForegroundApp]) -> None:
        if not app or not self.is_game_ad(app) or self.ad_start_ts is None:
            return

        now = time.time()
        elapsed = now - self.ad_start_ts
        if elapsed < AD_CLOSE_MIN_SECONDS:
            self.log(f"[IKLAN] Menunggu durasi awal video: {elapsed:.0f}s / {AD_CLOSE_MIN_SECONDS:.0f}s...")
            return
        if now - self.last_ad_close_check_ts < AD_CLOSE_CHECK_INTERVAL:
            return
        self.last_ad_close_check_ts = now

        # ── AMBIL SCREENSHOT SEKALI – dipakai ulang untuk countdown & progress bar ──
        _ss = self.capture_screenshot()
        _ss_png: bytes = b""
        _ss_w = _ss_h = 0
        if _ss:
            _ss_png, _ss_w, _ss_h = _ss

        now_log = time.time()

        # ── CEK COUNTDOWN TIMER (pojok kanan/kiri atas) ──────────────────────
        cd_sec = -1
        if _ss_png:
            cd_sec = self.detect_countdown_timer(_ss_png, _ss_w, _ss_h)

        if cd_sec > 0:
            self.last_countdown_sec = cd_sec
            if now_log - self.last_countdown_log_ts >= 1.5:
                self.last_countdown_log_ts = now_log
                self.log(
                    f"[COUNTDOWN] ⏳ {cd_sec}s tersisa – iklan belum selesai, tunggu countdown hilang "
                    f"| durasi {self.format_duration(elapsed)}"
                )
            return   # jangan klik apapun selama countdown masih ada
        elif cd_sec == 0:
            # Countdown mencapai 0 – biarkan lanjut ke pencarian tombol
            if now_log - self.last_countdown_log_ts >= 1.0:
                self.last_countdown_log_ts = now_log
                self.log(f"[COUNTDOWN] ✅ Countdown habis (0s) – lanjut cari tombol tutup")
            self.last_countdown_sec = 0
        elif self.last_countdown_sec > 0:
            # Countdown sebelumnya ada, sekarang tidak terdeteksi → kemungkinan hilang = selesai
            if now_log - self.last_countdown_log_ts >= 1.0:
                self.last_countdown_log_ts = now_log
                self.log(
                    f"[COUNTDOWN] ✅ Countdown hilang (sebelumnya {self.last_countdown_sec}s) "
                    f"– lanjut cari tombol tutup"
                )
            self.last_countdown_sec = -1

        # ── CEK PROGRESS BAR ─────────────────────────────────────────────────
        pb_ratio = -1.0
        if _ss_png:
            pb_ratio = self.detect_progress_bar(_ss_png, _ss_w, _ss_h)

        if pb_ratio >= 0.0:
            pct = pb_ratio * 100.0
            self.last_progress_pct = pct
            if now_log - self.last_progress_log_ts >= 1.5:
                self.last_progress_log_ts = now_log
                bar_len = 20
                filled_len = int(bar_len * pb_ratio)
                bar_vis = "█" * filled_len + "░" * (bar_len - filled_len)
                self.log(
                    f"[PROGRESS BAR] [{bar_vis}] {pct:.0f}% "
                    f"| durasi iklan {self.format_duration(elapsed)}"
                )
            if pb_ratio < 0.95:
                # Khusus iklan playable/endcard: kadang progress bar masih terdeteksi 40-90%,
                # tetapi tombol X / panah di pojok atas sudah aktif. Jika tombol pojok atas
                # terlihat, tetap klik sesuai instruksi user.
                top_found = None
                ui_top = self.find_ad_finish_button_by_ui()
                if ui_top:
                    k, lbl, tx, ty = ui_top
                    is_top_edge = ty < _ss_h * 0.32 and (tx < _ss_w * 0.38 or tx > _ss_w * 0.62)
                    if is_top_edge and k in {"X", "PANAH_KANAN/NEXT", "PANAH_KANAN/TOP"}:
                        top_found = (k, lbl, tx, ty, "ui-progress-top")
                if not top_found and _ss_png:
                    top_corner = self.find_ad_top_corner_button_by_image(_ss_png, _ss_w, _ss_h)
                    if top_corner:
                        k, lbl, tx, ty = top_corner
                        is_top_edge = ty < _ss_h * 0.32 and (tx < _ss_w * 0.38 or tx > _ss_w * 0.62)
                        if is_top_edge and k in {"X", "PANAH_KANAN/NEXT", "PANAH_KANAN/TOP"}:
                            top_found = (k, lbl, tx, ty, "image-progress-top")
                if top_found:
                    k, lbl, tx, ty, src = top_found
                    if src.endswith("progress-top"):
                        if int(tx) > _ss_w * 0.55:
                            tx = min(_ss_w - 12, int(tx) + 12)
                            ty = max(55, int(ty) - 18)
                        else:
                            ty = max(55, int(ty) - 10)
                    self.log(
                        f"[IKLAN] Progress {pct:.0f}% tapi tombol pojok atas terlihat: "
                        f"{k} '{lbl}' di ({tx},{ty}) via {src} – klik tetap"
                    )
                    if now - self.last_ad_close_tap_ts >= 3:
                        self.last_ad_close_tap_ts = now
                        self.show_tap_marker([(tx, ty, "blue", 2.5, 54)])
                        self.tap(tx, ty)
                    return
                self.log(
                    f"[IKLAN] Progress bar {pct:.0f}% – belum selesai, tunggu ~100% sebelum klik tombol"
                )
                return
        else:
            if now_log - self.last_progress_log_ts >= 3.0:
                self.last_progress_log_ts = now_log
                self.log("[PROGRESS BAR] Tidak terdeteksi – lanjut cari tombol tutup iklan")

        self.log(f"[IKLAN] Memindai tombol panah kanan / X / Buka Toko / lewati iklan... (durasi {self.format_duration(elapsed)}) – cek UI, OCR, gambar pojok atas")
        found = self.find_ad_finish_button()
        if not found:
            self.log(f"[IKLAN] Belum ada tombol tutup/panah/Buka Toko (video tayang {self.format_duration(elapsed)}) – tunggu & scan ulang...")
            if elapsed > 28 and (now - self.last_ad_close_tap_ts >= 4):
                self.last_ad_close_tap_ts = now
                self.log(f"[IKLAN] FALLBACK: iklan berjalan {self.format_duration(elapsed)} belum ada tombol tutup, mengirim tombol BACK...")
                self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
            return

        kind, label, x, y, source = found
        if x < 20 and y < 20:
            self.log(f"[IKLAN] ABORT: koordinat tidak valid ({x},{y})")
            return
        if source in {"top-corner", "image-progress-top", "ui-progress-top"} and y < _ss_h * 0.32:
            if x > _ss_w * 0.55:
                x = min(_ss_w - 12, int(x) + 12)
                y = max(55, int(y) - 18)
            else:
                y = max(55, int(y) - 10)
        self.log(
            f"MENEMUKAN TOMBOL SELESAI IKLAN: {kind} '{label}' di ({x},{y}) via {source} | durasi {self.format_duration(elapsed)}"
        )

        if now - self.last_ad_close_tap_ts < 3:
            return
        self.last_ad_close_tap_ts = now
        self.log(f"KLIK TOMBOL SELESAI IKLAN: {kind} di ({x},{y})")
        label_norm = self.normalize_text(label)

        # Handler khusus BUKA_TOKO: klik tombol lalu tangani Play Store yang mungkin terbuka
        if kind == "BUKA_TOKO":
            self.log(f"[IKLAN] TOMBOL BUKA TOKO: '{label}' di ({x},{y}) via {source} – klik lalu pantau redirect...")
            self.show_tap_marker([(x, y, "orange", 2.5, 54)])
            self.tap(x, y)
            time.sleep(2.5)
            fg = self.get_foreground_app()
            if fg and fg.package == "com.android.vending":
                self.log("[IKLAN] Play Store terbuka setelah klik Buka Toko – menutup Play Store dan kembali ke game...")
                self.close_blocked_app_and_return("com.android.vending")
            elif fg and fg.package != TARGET_PACKAGE and fg.package in BLOCKED_PACKAGES:
                self.log(f"[IKLAN] App asing terbuka setelah Buka Toko: {fg.package} – menutup dan kembali...")
                self.close_blocked_app_and_return(fg.package)
            elif fg and fg.package != TARGET_PACKAGE:
                self.log(f"[IKLAN] Foreground asing setelah Buka Toko: {fg.package} – kirim BACK dan kembali ke game...")
                self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
                time.sleep(1.2)
                fg2 = self.get_foreground_app()
                if fg2 and fg2.package != TARGET_PACKAGE:
                    self.log(f"[IKLAN] Masih di {fg2.package} – force-stop dan buka game")
                    self.close_blocked_app_and_return(fg2.package)
            else:
                self.log(f"[IKLAN] Setelah klik Buka Toko: masih di game ({fg.package if fg else '?'}), lanjut pantau iklan")
            return

        if kind == "X" and any(token in label_norm for token in ("close", "tutup")):
            # Tombol teks Close kadang area aktifnya bukan tepat di tengah OCR/UI text.
            # Tap beberapa titik sekitar label supaya tidak stuck di iklan jenis ini.
            screen_w, screen_h = self.get_screen_size()
            close_points = []
            for dx, dy in ((0, 0), (42, 0), (84, 0), (-42, 0), (0, 28), (42, 28), (84, 28)):
                px = max(15, min(screen_w - 15, x + dx))
                py = max(85, min(screen_h - 120, y + dy))
                point = (px, py)
                if point not in close_points:
                    close_points.append(point)
            self.tap_many(close_points, timeout=4, color="blue")
            if elapsed > 20:
                self.log(f"FALLBACK CLOSE: tombol Close belum menutup setelah {self.format_duration(elapsed)}, kirim BACK")
                self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
            if elapsed > 45:
                self.restart_game_for_stuck_ad(f"tombol Close tidak bereaksi selama {self.format_duration(elapsed)}")
            return
        self.tap(x, y)

    def ocr_current_screen(self, prefix: str) -> list[Tuple[str, str, int, int]]:
        """OCR layar sekarang. Return: [(text, bbox, x, y), ...]."""
        if not os.path.exists(OCR_HELPER):
            return []

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
        return entries

    def find_reward_offer_buttons(self) -> Tuple[
        Optional[Tuple[str, str, int, int]],
        Optional[Tuple[str, str, int, int]],
        Optional[Tuple[float, str, int, int]],
        Optional[Tuple[str, str, int, int]],
    ]:
        """Cari tombol DOBEL, tombol NOT NOW/NOW NOT, nominal Rp reward, serta tombol X pop-up Pengaturan."""
        dobel = None
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
            # Tombol DOBEL / DOUBLE / BUKA PETI
            is_dobel = (
                "dobel" in norm
                or "double" in norm
                or ("buka" in norm and y > 850)
            )
            if dobel is None and is_dobel and y > 600:
                dobel = (text, bbox, x, y)
                continue

            # Pop-up Pengaturan: tombol X berada di sebelah kanan teks Pengaturan (ujung kanan banner header pop-up).
            if settings_btn is None and ("pengaturan" in norm or "setting" in norm or "pengatur" in norm):
                x_close = int(screen_w * 0.88) if screen_w else (x + 270)
                y_close = y + 21 if y else 545
                settings_btn = (text, bbox, x_close, y_close)
                continue

            # Tombol AMBIL / KLAIM / NOT NOW / NOW NOT
            is_ambil_or_not_now = (
                "ambil" in norm
                or "klaim" in norm
                or "claim" in norm
                or "notnow" in norm
                or "nownot" in norm
                or "nothanks" in norm
                or "tidaksekarang" in norm
                or "nantidulu" in norm
                or norm in {"ambil", "klaim", "claim", "nanti", "skip", "lewati"}
            )
            if not_now is None and is_ambil_or_not_now and y > 600:
                not_now = (text, bbox, x, y)

        reward_rp = None
        if reward_candidates:
            target_y = dobel[3] if dobel else 1120
            # Pilih nominal Rp yang paling dekat di atas tombol DOBEL, misalnya "Rp 41,9".
            above = [item for item in reward_candidates if item[0] < target_y and (target_y - item[0]) <= 430]
            pool = above or reward_candidates
            pool.sort(key=lambda item: abs(target_y - item[0]))
            _sort_y, value, raw_text, x, y = pool[0]
            reward_rp = (value, raw_text, x, y)
        return dobel, not_now, reward_rp, settings_btn

    def handle_wallet_page_if_needed(self, app: Optional[ForegroundApp]) -> bool:
        """Tutup halaman Dompet/Penarikan dengan kembali ke halaman utama."""
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
                or "pilihmetodepenarikan" in norm
                or ("pilih" in norm and "metode" in norm and "penarikan" in norm)
                or norm in {"penarikan", "tarik", "withdraw", "withdrawal"}
            )
            # Judul halaman biasanya di area header atas. Untuk teks "Pilih metode penarikan"
            # kadang muncul sedikit lebih bawah sebagai judul panel.
            is_withdraw_panel = (
                "pilihmetodepenarikan" in norm
                or ("pilih" in norm and "metode" in norm and "penarikan" in norm)
            )
            is_withdraw_button = norm in {"penarikan", "tarik", "withdraw", "withdrawal"}
            if is_wallet_title and ((90 <= y <= 360) or is_withdraw_panel or (is_withdraw_button and y < 520)):
                tap_x = 45
                tap_y = max(95, min(240, y))
                self.log(f"HALAMAN PENARIKAN/DOMPET TERDETEKSI: '{text}' | bbox={bbox} | kembali ke halaman utama via ({tap_x},{tap_y}) + BACK")
                self.tap(tap_x, tap_y)
                time.sleep(0.6)
                # Jika panah kiri tidak bereaksi / posisinya beda, BACK biasanya kembali ke halaman utama.
                fg = self.get_foreground_app()
                if fg and fg.package == TARGET_PACKAGE and not self.is_game_ad(fg):
                    self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
                    time.sleep(0.6)
                self.dobel_visible = False
                self.not_now_visible = False
                self.bubble_watch_active = False
                return True
        return False

    def handle_weapon_page_if_needed(self, app) -> bool:
        """Tutup halaman Weapon (popup weapon terklik) dengan klik panah kiri di atas kiri teks weapon."""
        if not app or app.package != TARGET_PACKAGE or self.is_game_ad(app):
            return False
        now = time.time()
        if now - self.last_weapon_check_ts < 2.0:
            return False
        self.last_weapon_check_ts = now

        entries = self.ocr_current_screen("weapon_page")
        for text, bbox, x, y in entries:
            norm = self.normalize_text(text)
            # Deteksi teks judul halaman weapon di area header atas layar
            is_weapon_title = (
                "weapon" in norm
                or "senjata" in norm
            )
            # Judul halaman biasanya di area header atas; cek y agar tidak salah tangkap
            if is_weapon_title and 60 <= y <= 320:
                # Panah kiri biasanya di pojok kiri atas, sejajar dengan teks judul
                tap_x = 45
                tap_y = y
                self.log(f"HALAMAN WEAPON TERDETEKSI: '{text}' | bbox={bbox} | klik panah kiri di ({tap_x},{tap_y})")
                self.tap(tap_x, tap_y)
                time.sleep(0.6)
                self.dobel_visible = False
                self.not_now_visible = False
                self.bubble_watch_active = False
                return True
        return False

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

        dobel, not_now, reward_rp, settings_btn = self.find_reward_offer_buttons()
        if settings_btn:
            stext, sbbox, sx, sy = settings_btn
            self.log(f"MENEMUKAN POP-UP PENGATURAN: '{stext}' | bbox={sbbox} | klik tombol X di kanan teks di ({sx},{sy})")
            self.show_tap_marker([(sx, sy, "blue", 1.5, 34)])
            self.tap(sx, sy)
            time.sleep(0.5)
            self.dobel_visible = False
            self.not_now_visible = False
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
                self.tap(tap_x, tap_y)
            self.dobel_visible = True
            self.not_now_visible = False
            self.bubble_watch_active = False
        elif not_now:
            # Sesuai instruksi: Jika hanya ada AMBIL tanpa DOBEL maka klik AMBIL, cek Rp dan laporkan ke telegram, lalu lanjut klik bubble
            text, bbox, x, y = not_now
            screen_w, _screen_h = self.get_screen_size()
            tap_x = screen_w // 2 if screen_w else x
            tap_y = y
            if not self.not_now_visible:
                self.log(f"HANYA ADA TOMBOL AMBIL/NOW NOT: '{text}' | bbox={bbox} | tap=({tap_x},{tap_y}) | reward={reward_rp}")
                if reward_rp:
                    r_val, r_text, _, _ = reward_rp
                    rp_formatted = self.format_rupiah(r_val)
                    msg = (
                        "💰 <b>FRUIT BLADE: AMBIL REWARD</b>\n"
                        f"<b>Nominal:</b> <code>{html.escape(rp_formatted)}</code> (OCR: {html.escape(r_text)})\n"
                        f"<b>Aksi:</b> Klik tombol {html.escape(text)}\n"
                        f"<b>Waktu:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}"
                    )
                    self.send_telegram_message(msg)
                self.log(f"KLIK TOMBOL AMBIL di ({tap_x},{tap_y}) SEKALI")
                self.tap(tap_x, tap_y)
                time.sleep(0.6)
                self.capture_and_report_balance("setelah klik AMBIL sebelum cari gelembung")
                self.bubble_watch_active = True
                self.bubble_watch_start_ts = time.time()
                self.bubble_search_notified = False
                self.last_bubble_check_ts = 0.0
                self.log(f"LANJUT CARI GELEMBUNG AKTIF: timeout {self.format_duration(BUBBLE_TIMEOUT_SECONDS)}")
                self.notify_bubble_search_once("setelah klik AMBIL")
            self.not_now_visible = True
            self.dobel_visible = False
        else:
            self.dobel_visible = False
            self.not_now_visible = False

    def find_moving_bubble(self) -> Optional[Tuple[int, int, str]]:
        """Cari objek bulat/gelembung yang bergerak dari dua screenshot berurutan."""
        try:
            import cv2
            import numpy as np
        except Exception:
            return None

        first_ts = time.time()
        first = self.capture_screenshot()
        if not first:
            return None
        first_png, width, height = first
        self.last_bubble_screen_size = (width, height)

        # Jangan langsung klik visual-cash tunggal: banyak yang hanya dekorasi/non-clickable.
        # Cash-bubble harus dikonfirmasi bergerak oleh diff dua frame di bawah.

        # Jeda pendek cukup untuk membaca arah gerak, jangan terlalu lama karena gelembung cepat lewat.
        time.sleep(0.14)
        second_ts = time.time()
        second = self.capture_screenshot()
        if not second:
            return None
        second_png, _, _ = second
        self.last_bubble_screen_size = (width, height)

        img1 = cv2.imdecode(np.frombuffer(first_png, dtype=np.uint8), cv2.IMREAD_COLOR)
        img2 = cv2.imdecode(np.frombuffer(second_png, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img1 is None or img2 is None or img1.shape != img2.shape:
            return None

        diff = cv2.absdiff(img1, img2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 24, 255, cv2.THRESH_BINARY)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.dilate(mask, kernel, iterations=2)

        # Eksklusi zona statis
        mask[:int(height * 0.16), :] = 0  # saldo / bar atas
        mask[int(height * 0.95):, :] = 0  # navigasi / tombol bawah
        mask[int(height * 0.78):, int(width * 0.50):] = 0  # terumbu karang bawah kanan

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
            if center_y < int(height * 0.16) or center_y > int(height * 0.95):
                continue
            # Area tray/bawah sering berisi bubble visual dekoratif yang tidak membuka iklan.
            if center_y > int(height * 0.84):
                continue
            if center_x < 30 or center_x > width - 30:
                continue
            if center_x > int(width * 0.50) and center_y > int(height * 0.78):
                continue
            # Abaikan papan puzzle/tile; animasi tile sering terlihat seperti bubble bergerak tapi tidak clickable.
            if int(width * 0.28) <= center_x <= int(width * 0.73) and int(height * 0.34) <= center_y <= int(height * 0.58):
                continue

            # Periksa ROI di img2 (posisi terkini bubble), bukan pusat jejak diff.
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

            # Warna uang di dalam bubble: hijau dan kuning.
            green1 = cv2.inRange(hsv1, np.array([35, 55, 75]), np.array([90, 255, 255]))
            yellow1 = cv2.inRange(hsv1, np.array([15, 60, 90]), np.array([38, 255, 255]))
            green2 = cv2.inRange(hsv2, np.array([35, 55, 75]), np.array([90, 255, 255]))
            yellow2 = cv2.inRange(hsv2, np.array([15, 60, 90]), np.array([38, 255, 255]))
            money1 = cv2.bitwise_or(green1, yellow1)
            money2 = cv2.bitwise_or(green2, yellow2)

            # Kilau gelembung transparan (putih / highlight).
            white1 = cv2.inRange(hsv1, np.array([0, 0, 160]), np.array([179, 85, 255]))
            white2 = cv2.inRange(hsv2, np.array([0, 0, 160]), np.array([179, 85, 255]))
            target1 = cv2.bitwise_or(money1, white1)
            target2 = cv2.bitwise_or(money2, white2)
            money_ratio = float(money2.mean() / 255.0)
            white_ratio = float(white2.mean() / 255.0)
            sat_mean = float(hsv2[:, :, 1].mean())

            # Bubble reward harus benar-benar berisi uang hijau/kuning; jika dominan putih saja biasanya tile/dekorasi.
            if money_ratio < 0.12:
                continue
            if white_ratio < 0.05 and money_ratio < 0.16:
                continue

            # Ambil titik aktual dari komponen target pada frame kedua.
            # Kontur diff sering berada di tengah jejak lama+baru, sehingga tap telat/meleset.
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

            # Lead kecil langsung dari pair frame terakhir; build_bubble_burst_points akan menambah cone.
            lead = 0.34
            pred_x = int(latest_x + vx * lead)
            pred_y = int(latest_y + vy * lead)
            if abs(pred_x - latest_x) > 170 or abs(pred_y - latest_y) > 220:
                pred_x, pred_y = latest_x, latest_y
            self.last_bubble_pair_velocity = (vx, vy)

            score = area + money_ratio * 4200 + white_ratio * 2800 + sat_mean * 10
            candidates.append((score, pred_x, pred_y, f"moving-bubble area={int(area)} bbox=({x},{y},{w},{h}) latest=({latest_x},{latest_y}) v=({vx:.0f},{vy:.0f}) money={money_ratio:.2f} white={white_ratio:.2f}"))

        if not candidates:
            # Fallback visual hanya valid kalau area ikon ikut berubah nyata; kalau statis, abaikan.
            reward_icon = self.find_reward_bubble_icon(second_png, width, height)
            if reward_icon:
                ix, iy, iinfo = reward_icon
                diff_roi = diff[max(0, iy - 45):min(height, iy + 45), max(0, ix - 45):min(width, ix + 45)]
                if diff_roi.size > 0 and float(diff_roi.mean()) > 6.0:
                    self.last_bubble_pair_velocity = (0.0, -180.0)
                    return ix, iy, f"motion-confirmed-visual {iinfo}"

        if not candidates:
            return None
        candidates.sort(reverse=True)
        _, cx, cy, info = candidates[0]
        return int(cx), int(cy), info

    def find_reward_bubble_icon(self, png_data: bytes, width: int, height: int) -> Optional[Tuple[int, int, str]]:
        """Deteksi cash-bubble reward.

        Target yang benar adalah gelembung transparan bulat berisi uang hijau/kuning.
        Filter ini mengecualikan area terumbu karang statis kanan-bawah dan papan puzzle.
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

        allowed = np.zeros_like(mask)
        allowed[int(height * 0.16):int(height * 0.95), :] = 255
        # Exclude terumbu karang / background statis kanan-bawah
        cv2.rectangle(allowed, (int(width * 0.50), int(height * 0.78)), (width, height), 0, -1)
        # Exclude papan puzzle tengah dan label Level yang juga hijau/kuning.
        cv2.rectangle(allowed, (210, int(height * 0.33)), (520, int(height * 0.58)), 0, -1)
        cv2.rectangle(allowed, (240, 300), (480, 430), 0, -1)
        # Exclude saldo / tombol atas.
        cv2.rectangle(allowed, (0, 0), (width, int(height * 0.16)), 0, -1)
        mask = cv2.bitwise_and(mask, allowed)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if area < 1000 or area > 18000:
                continue
            if w < 42 or h < 42 or w > 150 or h > 150:
                continue
            aspect = w / float(h)
            if aspect < 0.68 or aspect > 1.45:
                continue
            center_x = x + w // 2
            center_y = y + h // 2
            if center_x < 35 or center_x > width - 35:
                continue
            if center_y < int(height * 0.18) or center_y > int(height * 0.84):
                continue
            if center_x > int(width * 0.50) and center_y > int(height * 0.78):
                continue

            # Bubble asli punya lingkaran/shine putih transparan di sekitar uang.
            pad = 65
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

            score = area + white_ratio * 6000 + colored_ratio * 2000
            candidates.append((score, center_x, center_y, f"cash-bubble area={int(area)} bbox=({x},{y},{w},{h}) white={white_ratio:.2f} color={colored_ratio:.2f}"))

        if not candidates:
            return None
        candidates.sort(reverse=True)
        _, x, y, info = candidates[0]
        return int(x), int(y), info

    def build_bubble_burst_points(self, x: int, y: int, width: int, height: int) -> list[Tuple[int, int]]:
        """Titik tap brutal luas: pusat bubble + jalur prediksi + grid seluruh area aman layar.
        Zona BEBAS klik = seluruh layar KECUALI:
          - y < 14% atas  (status bar / header)
          - y > 86% bawah (weapon / pisau)
          - x > 75% DAN y > 78% bawah-kanan (tombol pengaturan & penarikan)
        """
        now = time.time()
        cx, cy = int(x), int(y)
        pair_v = getattr(self, "last_bubble_pair_velocity", None) or (0.0, -180.0)
        vx, vy = pair_v
        if abs(vx) < 20 and abs(vy) < 20:
            vy = -180.0
        self.prev_bubble_detection = (now, cx, cy)

        # Batas zona aman
        y_min = int(height * 0.14)
        y_max = int(height * 0.86)
        x_min = 18
        x_max = width - 18
        bottom_right_bubble = cx > width * 0.68 and cy > height * 0.78

        points: list[Tuple[int, int]] = []
        seen: set[Tuple[int, int]] = set()

        def safe(px: int, py: int) -> bool:
            """True jika koordinat di zona aman (bukan weapon/pengaturan/header)."""
            px, py = int(px), int(py)
            if px < x_min or px > x_max:
                return False
            # Khusus Juicy Slash: reward bubble sering muncul di pojok kanan bawah.
            # Izinkan area ini hanya untuk burst fokus di sekitar bubble yang terdeteksi,
            # bukan untuk grid umum.
            if bottom_right_bubble and px > width * 0.64 and py > height * 0.76 and py < height - 18:
                return True
            if py < y_min or py > y_max:
                return False
            # Pojok kanan bawah = tombol pengaturan & penarikan – LARANG
            if px > width * 0.75 and py > height * 0.78:
                return False
            return True

        def add_p(px: int, py: int) -> None:
            px, py = int(px), int(py)
            if not safe(px, py):
                return
            pt = (px, py)
            if pt not in seen:
                seen.add(pt)
                points.append(pt)

        # ── 1. Pusat bubble + prediksi jalur (prioritas tinggi, masuk duluan) ──
        add_p(cx, cy)
        for lead in (0.08, 0.16, 0.25, 0.36, 0.50, 0.65, 0.80):
            add_p(cx + vx * lead, cy + vy * lead)

        # ── 2. Ring rapat di sekitar bubble (radius 20, 40, 60, 80 px) ──
        import math
        for radius in (20, 40, 60, 80):
            steps = max(8, int(2 * math.pi * radius / 18))
            for i in range(steps):
                angle = 2 * math.pi * i / steps
                add_p(cx + radius * math.cos(angle), cy + radius * math.sin(angle))

        # ── 3. Grid kasar seluruh area aman layar (step 55px) ──
        # Untuk bubble pojok kanan bawah, jangan tambah grid luas agar tidak klik tombol lain.
        if not bottom_right_bubble:
            step = 55
            for gy in range(y_min + step // 2, y_max, step):
                for gx in range(x_min + step // 2, x_max, step):
                    add_p(gx, gy)

        # ── 4. Tambah jalur bubble naik ke atas dari posisi sekarang ──
        for dy in range(0, int(height * 0.55), 28):
            add_p(cx, cy - dy)
            add_p(cx - 30, cy - dy)
            add_p(cx + 30, cy - dy)

        self.log(f"BUILD BURST: {len(points)} titik (bubble={cx},{cy} v={vx:.0f},{vy:.0f})")
        return points

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
                self.log(f"TAP GELEMBUNG BRUTAL: {len(points)} titik luas area aman ({x},{y})")
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
            self.log("[SCAN GELEMBUNG] Sedang memindai layar mencari gelembung reward bergerak... (zona pisau aman tidak diklik)")
            return

        elapsed = now - self.bubble_watch_start_ts
        self.log(f"[SCAN GELEMBUNG] Sedang mencari gelembung bergerak... Durasi: {self.format_duration(elapsed)} / {self.format_duration(BUBBLE_TIMEOUT_SECONDS)}")
        if elapsed >= BUBBLE_TIMEOUT_SECONDS:
            self.restart_game_for_bubble_search(
                f"{self.format_duration(elapsed)} tidak menemukan gelembung"
            )

    def step(self) -> Tuple[str, Optional[ForegroundApp]]:
        app = self.get_foreground_app()
        if not app:
            self.update_ad_log(None)
            self.update_dobel_log(None)
            self.launch_game(reason="foreground tidak terbaca")
            return "launch_unknown_foreground", None

        if app.package != self.last_foreground:
            self.last_foreground = app.package
            self.log(f"Foreground: {app.package}/{app.activity}")

        if app.activity == "Application Not Responding":
            self.clear_apps_and_reopen_game(f"ANR/stuck terdeteksi pada {app.package}")
            self.last_action = "cleared_anr"
            return "cleared_anr", app

        if app.package == TARGET_PACKAGE:
            self.update_ad_log(app)
            self.try_finish_ad(app)
            if self.handle_wallet_page_if_needed(app):
                self.last_action = "closed_wallet_page"
                return "closed_wallet_page", app
            if self.handle_weapon_page_if_needed(app):
                self.last_action = "closed_weapon_page"
                return "closed_weapon_page", app
            self.update_dobel_log(app)
            self.update_bubble_search(app)
            self.last_action = "game_ok"
            return "game_ok", app

        self.update_ad_log(app)
        self.try_finish_ad(app)
        self.update_dobel_log(app)
        self.update_bubble_search(app)

        if app.package in BLOCKED_PACKAGES:
            self.log(f"[REDIRECT TERDETEKSI] Aplikasi dialihkan ke {BLOCKED_PACKAGES.get(app.package, app.package)}. Segera menutup dan kembali ke Fruit Blade...")
            self.close_blocked_app_and_return(app.package)
            self.last_action = "closed_blocked_and_returned"
            return "closed_blocked_and_returned", app

        # Kalau bukan game dan bukan app sistem penting, buka game.
        self.launch_game(reason=f"foreground sekarang {app.package}")
        self.last_action = "launched_game"
        return "launched_game", app

    def run(self, once: bool = False) -> int:
        self.log(f"Bot aktif untuk {TARGET_NAME} ({TARGET_PACKAGE})")
        self.log(f"Log: {LOG_FILE}")
        for attempt in range(4):
            if self.has_device():
                break
            time.sleep(1.5)
        if not self.has_device():
            return 2

        if not self.is_target_installed():
            self.log(f"Game belum terinstall: {TARGET_PACKAGE}")
            return 3

        try:
            while True:
                try:
                    self.step()
                except Exception as step_exc:
                    self.log(f"Transient error pada step: {step_exc}")
                    time.sleep(1.0)
                if once:
                    return 0
                time.sleep(0.25 if self.bubble_watch_active else self.interval)
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

    bot = MagicOceanGuardian(serial=args.serial, interval=max(0.5, args.interval), dry_run=args.dry_run)
    return bot.run(once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
