#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, re, subprocess, time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

TARGET_PACKAGE = "com.starlightgame.woodlandtilematcher"
TARGET_NAME = "Woodland Tile Matcher"
LOG_FILE = os.path.expanduser("~/woodland_guardian_bot.log")
DEFAULT_INTERVAL = 2.0
BLOCKED_PACKAGES = {
    "com.android.chrome": "Chrome",
    "com.google.android.apps.chrome": "Chrome",
    "com.android.vending": "Play Store",
    "com.starlightgame.magicoceantilecrush": "Magic Ocean",
}

@dataclass
class ForegroundApp:
    package: str
    activity: str = ""
    source: str = ""

class WoodlandGuardian:
    def __init__(self, serial: str = "", interval: float = DEFAULT_INTERVAL):
        self.serial = serial.strip()
        self.interval = interval
        self.last_foreground = ""
        self.last_launch_ts = 0.0
        self.last_block_close_ts = 0.0

    def log(self, msg: str) -> None:
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line, flush=True)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def adb(self, args: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str]:
        cmd = ["adb"] + (["-s", self.serial] if self.serial else []) + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def adb_out(self, args: list[str], timeout: int = 10) -> str:
        try:
            return self.adb(args, timeout=timeout).stdout
        except Exception as exc:
            self.log(f"ADB error: {exc}")
            return ""

    @staticmethod
    def parse_app(text: str) -> Optional[ForegroundApp]:
        anr = re.search(r"Application Not Responding:\s*([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)", text)
        if anr:
            return ForegroundApp(anr.group(1), "Application Not Responding", text.strip())
        for pat in (r"u\d+\s+([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)/([^\s}\]]+)", r"\s([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)/([a-zA-Z0-9_.$]+)"):
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
                    if not line.startswith(" ") and not line.startswith("	"):
                        in_last_anr = False
                    else:
                        continue
                if any(k in line for k in keys):
                    app = self.parse_app(line)
                    if app:
                        return app
        return None

    def force_stop(self, pkg: str) -> None:
        self.log(f"Menutup {BLOCKED_PACKAGES.get(pkg, pkg)} ({pkg})")
        self.adb_out(["shell", "am", "force-stop", pkg], timeout=8)

    def launch(self, reason: str = "") -> None:
        now = time.time()
        if now - self.last_launch_ts < 3:
            return
        self.last_launch_ts = now
        suffix = f" karena {reason}" if reason else ""
        self.log(f"Membuka {TARGET_NAME}{suffix}")
        self.adb_out(["shell", "monkey", "-p", TARGET_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"], timeout=12)

    def step(self) -> None:
        app = self.foreground()
        if not app:
            self.launch("foreground tidak terbaca")
            return
        if app.package != self.last_foreground:
            self.last_foreground = app.package
            self.log(f"Foreground: {app.package}/{app.activity}")
        if app.package == TARGET_PACKAGE:
            return
        if app.package in BLOCKED_PACKAGES:
            now = time.time()
            if now - self.last_block_close_ts >= 2:
                self.last_block_close_ts = now
                self.force_stop(app.package)
                time.sleep(0.4)
                self.launch(f"keluar dari {BLOCKED_PACKAGES.get(app.package, app.package)}")
            return
        self.launch(f"foreground sekarang {app.package}")

    def run(self) -> int:
        self.log(f"Bot aktif untuk {TARGET_NAME} ({TARGET_PACKAGE})")
        while True:
            self.step()
            time.sleep(self.interval)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", "-s", default="")
    ap.add_argument("--interval", "-i", type=float, default=DEFAULT_INTERVAL)
    args = ap.parse_args()
    raise SystemExit(WoodlandGuardian(args.serial, max(0.5, args.interval)).run())
