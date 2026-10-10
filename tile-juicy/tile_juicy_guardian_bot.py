#!/usr/bin/env python3
"""
Tile Juicy Guardian Bot

Tugas utama:
- Jika game Tile Juicy belum foreground, buka game.
- Jika foreground masuk Chrome, Play Store, atau app lain karena iklan redirect,
  tutup app tersebut lalu kembali ke game.
- Deteksi activity iklan di dalam game dan tunggu selesai (auto-close X jika stuck).
- Gameplay auto-tap area tile secara periodik (blind tap di area gameplay).

Target game:
  App     : Tile Juicy
  Package : com.spiritbreaker.games.tilejuicy

Perangkat: 062322513B000705 (Infinix X692, 720x1640)
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

TARGET_PACKAGE = "com.spiritbreaker.games.tilejuicy"
TARGET_NAME = "Tile Juicy"

# App yang sering terbuka karena iklan / redirect.
BLOCKED_PACKAGES = {
    "com.android.chrome": "Chrome",
    "com.chrome.beta": "Chrome Beta",
    "com.chrome.dev": "Chrome Dev",
    "com.google.android.apps.chrome": "Chrome",
    "com.android.vending": "Play Store",
    "com.starlightgame.woodlandtilematcher": "Woodland Tile Matcher redirect",
    "com.starlightgame.magicoceantilecrush": "Magic Ocean redirect",
    "com.bubble.crush.stick.magicgames": "Bubble Crush redirect",
}

LOG_FILE = os.path.expanduser("~/tile_juicy_guardian_bot.log")
SALDO_STATE_FILE = os.path.expanduser("~/tile_juicy_saldo_state.json")
TELEGRAM_SENDER = "/Users/macbookair/telegram_sender.py"
DEFAULT_INTERVAL = 2.0
TAP_MARKER = "/Users/macbookair/scrcpy_tap_marker"

AD_CLOSE_CHECK_INTERVAL = 2.0
AD_CLOSE_MIN_SECONDS = 5.0
AD_STUCK_RESTART_SECONDS = 120.0

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

BAD_AD_ACTIVITIES = {
    "com.applovin.adview.applovinfullscreenactivity",
}

# Area gameplay tile (piksel pada layar 720x1640).
# Berdasarkan analisis piksel: tile grid ada di y=850-1150, x=100-620.
SCREEN_W = 720
SCREEN_H = 1640
GAMEPLAY_TOP = 850
GAMEPLAY_BOTTOM = 1150
GAMEPLAY_LEFT = 100
GAMEPLAY_RIGHT = 620
GAMEPLAY_COLS = 6
GAMEPLAY_ROWS = 4

# Tombol X umum untuk tutup iklan (pojok-pojok layar).
AD_CLOSE_POSITIONS = [
    (680, 80),   # kanan atas
    (680, 120),  # kanan atas lebih bawah
    (670, 60),   # kanan atas ketat
    (40, 80),    # kiri atas
    (40, 120),   # kiri atas lebih bawah
    (50, 60),    # kiri atas ketat
    (360, 1550), # bawah tengah (skip/close)
]

# Interval gameplay tap (detik).
GAMEPLAY_TAP_INTERVAL = 3.0
GAMEPLAY_TAP_BATCH = 4  # jumlah tile tap per siklus


@dataclass
class ForegroundApp:
    package: str
    activity: str = ""
    source: str = ""


class TileJuicyGuardian:
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
        self.last_ad_close_check_ts = 0.0
        self.last_ad_close_tap_ts = 0.0
        self.last_ad_stuck_restart_ts = 0.0
        self.last_gameplay_tap_ts = 0.0
        self.gameplay_tap_index = 0
        self.total_taps = 0
        self.cycles = 0

    # ─── Logging ───
    def log(self, msg: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line, flush=True)
        if os.environ.get("TILE_JUICY_NO_FILE_LOG") == "1":
            return
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    # ─── ADB helpers ───
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

    def tap(self, x: int, y: int) -> None:
        self.show_tap_marker([(int(x), int(y), "blue", 1.3, 58)])
        if self.dry_run:
            self.log(f"DRY RUN: tap {x},{y}")
            return
        self.adb_out(["shell", "input", "tap", str(x), str(y)], timeout=5)
        self.total_taps += 1

    def press_back(self) -> None:
        if self.dry_run:
            self.log("DRY RUN: BACK")
            return
        self.adb_out(["shell", "input", "keyevent", "KEYCODE_BACK"], timeout=5)

    def show_tap_marker(self, specs: list[Tuple[int, int, str, float, int]]) -> None:
        if not os.path.exists(TAP_MARKER) or os.environ.get("TILE_JUICY_DISABLE_MARKER") == "1":
            return
        args: list[str] = []
        for x, y, color, duration, diameter in specs[:220]:
            args += [str(int(x)), str(int(y)), color, str(float(duration)), str(int(diameter))]
        try:
            subprocess.Popen([TAP_MARKER, *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def monkey_burst(self, points: list[Tuple[int, int]], delay_ms: int = 3, timeout: int = 6) -> None:
        """Kirim banyak tap berkecepatan tinggi menggunakan monkey script."""
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
        script_content = "\n".join(script_lines) + "\n"

        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += ["shell", "cat > /data/local/tmp/burst_tap.txt && monkey -f /data/local/tmp/burst_tap.txt 1"]
        try:
            subprocess.run(cmd, input=script_content, text=True, capture_output=True, timeout=timeout)
            self.total_taps += len(points)
        except subprocess.TimeoutExpired:
            self.log("ADB timeout saat monkey burst tap")
        except Exception as exc:
            self.log(f"Monkey burst error: {exc}")

    # ─── Foreground detection ───
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

    def foreground(self) -> Optional[ForegroundApp]:
        checks = [
            (["shell", "dumpsys", "window", "displays"], ("mCurrentFocus",)),
            (["shell", "dumpsys", "activity", "activities"], ("topResumedActivity", "mResumedActivity", "ResumedActivity")),
            (["shell", "dumpsys", "window", "displays"], ("mFocusedApp",)),
        ]
        for args, keys in checks:
            out = self.adb_out(args, timeout=8)
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
                if any(k in line for k in keys):
                    app = self.parse_app(line)
                    if app:
                        return app
        return None

    def is_game_ad(self, app: ForegroundApp) -> bool:
        if app.package != TARGET_PACKAGE:
            return False
        activity = app.activity.lower()
        if any(keyword in activity for keyword in AD_ACTIVITY_KEYWORDS):
            return True
        # Game utama biasanya MainActivity. Kalau activity lain di package game, kemungkinan iklan.
        if activity and activity not in {"application not responding"} and "mainactivity" not in activity:
            return True
        return False

    def is_bad_ad_activity(self, activity: str) -> bool:
        return activity.lower() in BAD_AD_ACTIVITIES

    # ─── Telegram notification ───
    def send_telegram(self, message: str) -> None:
        if not os.path.exists(TELEGRAM_SENDER):
            return
        try:
            subprocess.Popen(
                [sys.executable, TELEGRAM_SENDER, "--message", message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    # ─── Game lifecycle ───
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
            self.log("Tidak ada device ADB aktif. Cek USB debugging.")
            return False
        if len(devices) > 1:
            self.log(f"Ada lebih dari 1 device: {devices}. Jalankan dengan --serial SERIAL.")
            return False
        self.serial = devices[0]
        self.log(f"Device dipakai: {self.serial}")
        return True

    def force_stop(self, pkg: str) -> None:
        name = BLOCKED_PACKAGES.get(pkg, pkg)
        if self.dry_run:
            self.log(f"DRY RUN: force-stop {name} ({pkg})")
            return
        self.log(f"Menutup {name} ({pkg})")
        self.adb_out(["shell", "am", "force-stop", pkg], timeout=8)

    def launch_game(self, reason: str = "") -> None:
        now = time.time()
        if now - self.last_launch_ts < 3:
            return
        self.last_launch_ts = now
        suffix = f" karena {reason}" if reason else ""
        if self.dry_run:
            self.log(f"DRY RUN: buka {TARGET_NAME}{suffix}")
            return
        self.log(f"Membuka {TARGET_NAME}{suffix}")
        self.adb_out([
            "shell", "monkey", "-p", TARGET_PACKAGE,
            "-c", "android.intent.category.LAUNCHER", "1",
        ], timeout=12)

    def close_blocked_app_and_return(self, pkg: str) -> None:
        now = time.time()
        if now - self.last_block_close_ts < 2:
            return
        self.last_block_close_ts = now
        self.force_stop(pkg)
        time.sleep(0.4)
        self.launch_game(reason=f"keluar dari {BLOCKED_PACKAGES.get(pkg, pkg)}")

    def clear_apps_and_reopen(self, reason: str) -> None:
        self.log(f"BERSIHKAN APP DAN BUKA ULANG GAME: {reason}")
        self.press_back()
        packages = [TARGET_PACKAGE, *BLOCKED_PACKAGES.keys()]
        seen = set()
        for pkg in packages:
            if pkg in seen:
                continue
            seen.add(pkg)
            if self.dry_run:
                self.log(f"DRY RUN: force-stop {pkg}")
            else:
                self.adb_out(["shell", "am", "force-stop", pkg], timeout=8)
        self.ad_start_ts = None
        self.ad_activity = ""
        self.last_ad_log_second = -1
        self.last_ad_close_check_ts = 0.0
        self.last_ad_close_tap_ts = 0.0
        time.sleep(0.8)
        self.launch_game(reason=reason)

    def restart_for_stuck_ad(self, reason: str) -> None:
        now = time.time()
        if now - self.last_ad_stuck_restart_ts < 30:
            return
        self.last_ad_stuck_restart_ts = now
        self.log(f"IKLAN STUCK: {reason}")
        self.clear_apps_and_reopen(reason)

    # ─── Ad handling ───
    @staticmethod
    def format_duration(seconds: float) -> str:
        total = max(0, int(seconds))
        m, s = divmod(total, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h} jam {m} menit {s} detik"
        if m:
            return f"{m} menit {s} detik"
        return f"{s} detik"

    def try_close_ad(self) -> None:
        """Coba tap tombol X untuk tutup iklan setelah cukup lama."""
        now = time.time()
        if now - self.last_ad_close_check_ts < AD_CLOSE_CHECK_INTERVAL:
            return
        self.last_ad_close_check_ts = now

        if self.ad_start_ts is None:
            return
        elapsed = now - self.ad_start_ts
        if elapsed < AD_CLOSE_MIN_SECONDS:
            return

        self.log(f"Coba tutup iklan (sudah {self.format_duration(elapsed)})")
        # Tap semua posisi X yang umum.
        for x, y in AD_CLOSE_POSITIONS:
            self.tap(x, y)
            time.sleep(0.15)

    def update_ad_state(self, app: Optional[ForegroundApp]) -> None:
        if app and self.is_game_ad(app):
            now = time.time()

            if self.is_bad_ad_activity(app.activity):
                self.clear_apps_and_reopen(f"iklan blacklist: {app.activity}")
                return

            if self.ad_start_ts is None or self.ad_activity != app.activity:
                self.ad_start_ts = now
                self.ad_activity = app.activity
                self.last_ad_log_second = 0
                self.log(f"IKLAN TERBUKA: {app.activity}")
                return

            elapsed = now - self.ad_start_ts
            if elapsed >= AD_STUCK_RESTART_SECONDS:
                self.restart_for_stuck_ad(
                    f"{app.activity} terbuka {self.format_duration(elapsed)} tanpa selesai"
                )
                return

            elapsed_s = int(elapsed)
            if elapsed_s != self.last_ad_log_second:
                self.last_ad_log_second = elapsed_s
                if elapsed_s % 5 == 0:  # log tiap 5 detik supaya tidak spam
                    self.log(f"IKLAN MASIH TERBUKA: {app.activity} | {self.format_duration(elapsed)}")

            self.try_close_ad()
            return

        if self.ad_start_ts is not None:
            elapsed = time.time() - self.ad_start_ts
            self.log(f"IKLAN SELESAI: {self.ad_activity} | total {self.format_duration(elapsed)}")
            self.ad_start_ts = None
            self.ad_activity = ""
            self.last_ad_log_second = -1
            self.last_ad_close_check_ts = 0.0

    # ─── Gameplay auto-tap ───
    def generate_tile_points(self) -> list[Tuple[int, int]]:
        """Generate titik tap di area gameplay, berputar supaya menyentuh semua tile."""
        points = []
        col_w = (GAMEPLAY_RIGHT - GAMEPLAY_LEFT) / GAMEPLAY_COLS
        row_h = (GAMEPLAY_BOTTOM - GAMEPLAY_TOP) / GAMEPLAY_ROWS

        # Ambil beberapa tile berdasarkan index yang berputar.
        for i in range(GAMEPLAY_TAP_BATCH):
            idx = (self.gameplay_tap_index + i) % (GAMEPLAY_COLS * GAMEPLAY_ROWS)
            col = idx % GAMEPLAY_COLS
            row = idx // GAMEPLAY_COLS
            x = int(GAMEPLAY_LEFT + col * col_w + col_w / 2)
            y = int(GAMEPLAY_TOP + row * row_h + row_h / 2)
            points.append((x, y))

        self.gameplay_tap_index = (self.gameplay_tap_index + GAMEPLAY_TAP_BATCH) % (GAMEPLAY_COLS * GAMEPLAY_ROWS)
        return points

    def do_gameplay_tap(self) -> None:
        """Tap area tile secara periodik."""
        now = time.time()
        if now - self.last_gameplay_tap_ts < GAMEPLAY_TAP_INTERVAL:
            return
        self.last_gameplay_tap_ts = now

        points = self.generate_tile_points()
        self.cycles += 1
        self.log(f"GAMEPLAY TAP cycle={self.cycles} tiles={len(points)} total_taps={self.total_taps}")

        # Gunakan monkey burst untuk kecepatan.
        self.monkey_burst(points, delay_ms=80, timeout=6)

        # Marker visual.
        self.show_tap_marker([(x, y, "green", 1.5, 40) for x, y in points])

    # ─── Main loop ───
    def step(self) -> None:
        app = self.foreground()
        if not app:
            self.launch_game("foreground tidak terbaca")
            return

        if app.package != self.last_foreground:
            self.last_foreground = app.package
            self.log(f"Foreground: {app.package}/{app.activity}")

        self.update_ad_state(app)

        # Jika app iklan di dalam game, tunggu selesai.
        if app.package == TARGET_PACKAGE and self.is_game_ad(app):
            return

        # Jika app game di MainActivity, jalankan gameplay.
        if app.package == TARGET_PACKAGE:
            self.do_gameplay_tap()
            return

        # Jika app terblokir (Chrome, Play Store, redirect), tutup dan kembali.
        if app.package in BLOCKED_PACKAGES:
            self.close_blocked_app_and_return(app.package)
            return

        # App lain yang tidak dikenal, coba kembali ke game.
        self.launch_game(f"foreground bukan game ({app.package})")

    def run(self) -> int:
        self.log("=" * 60)
        self.log(f"Tile Juicy Guardian Bot v1.0")
        self.log(f"Target: {TARGET_NAME} ({TARGET_PACKAGE})")
        self.log(f"Serial: {self.serial or 'auto'}")
        self.log(f"Interval: {self.interval}s | DryRun: {self.dry_run}")
        self.log("=" * 60)

        if not self.has_device():
            self.log("GAGAL: device tidak terhubung")
            return 1

        # Pastikan game terpasang.
        pm_out = self.adb_out(["shell", "pm", "path", TARGET_PACKAGE], timeout=8)
        if "package:" not in pm_out:
            self.log(f"GAGAL: {TARGET_PACKAGE} tidak terpasang di device")
            return 1

        self.log("Bot mulai berjalan. Ctrl+C untuk berhenti.")
        self.send_telegram(
            f"🎮 <b>Tile Juicy Guardian Bot AKTIF</b>\n"
            f"📱 Device: {self.serial}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}"
        )

        try:
            while True:
                self.step()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.log(f"Bot dihentikan. Total taps: {self.total_taps}, cycles: {self.cycles}")
            self.send_telegram(
                f"🛑 <b>Tile Juicy Guardian Bot BERHENTI</b>\n"
                f"Total taps: {self.total_taps} | Cycles: {self.cycles}\n"
                f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}"
            )
            return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Tile Juicy Guardian Bot")
    ap.add_argument("--serial", "-s", default="", help="Device serial (ADB)")
    ap.add_argument("--interval", "-i", type=float, default=DEFAULT_INTERVAL, help="Loop interval (detik)")
    ap.add_argument("--dry-run", action="store_true", help="Dry run (tidak kirim input)")
    args = ap.parse_args()
    raise SystemExit(TileJuicyGuardian(args.serial, max(0.5, args.interval), args.dry_run).run())
