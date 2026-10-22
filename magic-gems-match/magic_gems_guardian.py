#!/usr/bin/env python3
"""Jaga Magic Gems Match tetap di foreground; tidak berinteraksi dengan iklan/hadiah."""
import argparse
import subprocess
import time

TARGET = "com.glow.magical.match3"
BLOCKED = {"com.android.chrome", "com.google.android.apps.chrome", "com.android.vending"}


def adb(serial, *args, timeout=10):
    return subprocess.run(["adb", *( ["-s", serial] if serial else []), *args], text=True,
                          capture_output=True, timeout=timeout).stdout


def foreground(serial):
    text = adb(serial, "shell", "dumpsys", "window", "windows")
    for line in text.splitlines():
        if "mCurrentFocus=" in line:
            # Window{... u0 package/activity ...}
            part = line.split(" u0 ", 1)
            if len(part) == 2:
                return part[1].split("/", 1)[0].strip()
    return ""


def launch(serial):
    adb(serial, "shell", "monkey", "-p", TARGET, "-c", "android.intent.category.LAUNCHER", "1", timeout=15)


def main():
    ap = argparse.ArgumentParser(description="Guardian Magic Gems Match")
    ap.add_argument("-s", "--serial", default="")
    ap.add_argument("-i", "--interval", type=float, default=1.0)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if "package:" not in adb(args.serial, "shell", "pm", "path", TARGET):
        raise SystemExit(f"Game tidak terpasang: {TARGET}")
    last_launch = 0.0
    while True:
        current = foreground(args.serial)
        if current != TARGET and time.monotonic() - last_launch >= 3:
            if current in BLOCKED:
                adb(args.serial, "shell", "am", "force-stop", current)
            launch(args.serial)
            last_launch = time.monotonic()
            print(f"Kembali ke game dari {current or 'app tidak terdeteksi'}", flush=True)
        if args.once:
            return
        time.sleep(max(.3, args.interval))


if __name__ == "__main__":
    main()
