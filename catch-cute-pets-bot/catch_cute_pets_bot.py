#!/usr/bin/env python3
"""
Bot penjaga Catch Cute Pets.

- Membuka ulang game saat foreground berpindah dari game.
- Di halaman utama, mencari kontrol bertuliskan OFF di kanan-bawah dan
  mengetuknya satu kali agar berubah menjadi ON (jempol merah).
- Mengetuk tombol hijau KLAIM saat muncul di halaman game.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, Tuple

from PIL import Image


TARGET_PACKAGE = "com.NAMMUNIS.CatchCutePets"
TARGET_NAME = "Catch Cute Pets"
LOG_FILE = os.path.expanduser("~/catch_cute_pets_bot.log")
OCR_HELPER = "/Users/macbookair/ocr_helper"
DEFAULT_INTERVAL = 0.5
OFF_CHECK_INTERVAL = 1.0
CLAIM_CHECK_INTERVAL = 1.0
LAUNCH_COOLDOWN = 3.0
TAP_COOLDOWN = 3.0


class CatchCutePetsBot:
    def __init__(self, serial: str = "", interval: float = DEFAULT_INTERVAL, dry_run: bool = False):
        self.serial = serial.strip()
        self.interval = interval
        self.dry_run = dry_run
        self.last_launch_ts = 0.0
        self.last_off_check_ts = 0.0
        self.last_off_tap_ts = 0.0
        self.last_claim_check_ts = 0.0
        self.last_claim_tap_ts = 0.0
        self.last_foreground = ""

    def log(self, message: str) -> None:
        line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
        print(line, flush=True)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as log_file:
                log_file.write(line + "\n")
        except OSError:
            pass

    def adb(self, args: list[str], timeout: int = 12) -> subprocess.CompletedProcess[str]:
        cmd = ["adb"]
        if self.serial:
            cmd.extend(["-s", self.serial])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def adb_bytes(self, args: list[str], timeout: int = 12) -> bytes:
        cmd = ["adb"]
        if self.serial:
            cmd.extend(["-s", self.serial])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, timeout=timeout).stdout

    def has_device(self) -> bool:
        result = self.adb(["devices"], timeout=8)
        serials = []
        for line in result.stdout.splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 2 and fields[1] == "device":
                serials.append(fields[0])
        if self.serial:
            available = self.serial in serials
        else:
            available = len(serials) == 1
            if len(serials) > 1:
                self.log("Lebih dari satu device terhubung; jalankan dengan --serial.")
        if not available:
            self.log("Device Android tidak ditemukan/siap.")
        return available

    def is_target_installed(self) -> bool:
        return bool(self.adb(["shell", "pm", "path", TARGET_PACKAGE]).stdout.strip())

    def get_foreground_package(self) -> Optional[str]:
        foreground = self.get_foreground_app()
        return foreground[0] if foreground else None

    def get_foreground_app(self) -> Optional[Tuple[str, str]]:
        checks = (
            ["shell", "dumpsys", "window", "displays"],
            ["shell", "dumpsys", "activity", "activities"],
        )
        for command in checks:
            output = self.adb(command, timeout=8).stdout
            # Jangan mencari ke seluruh dump: riwayat task lama juga ada di
            # sana. Hanya baris current/resumed yang boleh dipakai.
            for line in output.splitlines():
                if "mCurrentFocus=" not in line and "mResumedActivity:" not in line and "topResumedActivity" not in line:
                    continue
                match = re.search(r"u\d+\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)/([^\s}\]]+)", line)
                if match:
                    return match.group(1), match.group(2)
        return None

    def launch_game(self, reason: str) -> None:
        now = time.monotonic()
        if now - self.last_launch_ts < LAUNCH_COOLDOWN:
            return
        self.last_launch_ts = now
        self.log(f"MEMBUKA {TARGET_NAME}: {reason}")
        if not self.dry_run:
            # monkey memilih activity launcher aplikasi sehingga tidak bergantung
            # pada nama activity yang dapat berubah saat game diperbarui.
            self.adb(["shell", "monkey", "-p", TARGET_PACKAGE, "1"], timeout=15)

    @staticmethod
    def parse_bounds(bounds: str) -> Optional[Tuple[int, int, int, int]]:
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
        if not match:
            return None
        return tuple(map(int, match.groups()))  # type: ignore[return-value]

    @staticmethod
    def is_bottom_right(x: int, y: int, width: int, height: int) -> bool:
        # Tidak menyentuh navigation bar paling bawah, tetapi cukup longgar untuk
        # variasi resolusi dan posisi tombol game.
        return x >= int(width * 0.55) and int(height * 0.50) <= y <= int(height * 0.98)

    def find_off_in_ui_dump(self) -> Optional[Tuple[int, int]]:
        remote_path = "/sdcard/catch_cute_pets_bot.xml"
        result = self.adb(["shell", "uiautomator", "dump", remote_path], timeout=10)
        if result.returncode != 0:
            return None
        xml_data = self.adb(["exec-out", "cat", remote_path], timeout=10).stdout
        if not xml_data:
            return None
        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError:
            return None

        # Ambil ukuran layar dari root node Android.
        root_bounds = self.parse_bounds(root.attrib.get("bounds", ""))
        if not root_bounds:
            return None
        _, _, width, height = root_bounds
        for node in root.iter("node"):
            label = (node.attrib.get("text") or node.attrib.get("content-desc") or "").strip()
            if label.upper() != "OFF":
                continue
            bounds = self.parse_bounds(node.attrib.get("bounds", ""))
            if not bounds:
                continue
            x1, y1, x2, y2 = bounds
            x, y = (x1 + x2) // 2, (y1 + y2) // 2
            if self.is_bottom_right(x, y, width, height):
                return x, y
        return None

    def find_off_with_ocr(self) -> Optional[Tuple[int, int]]:
        if not os.path.isfile(OCR_HELPER):
            return None
        png_data = self.adb_bytes(["exec-out", "screencap", "-p"], timeout=12)
        if not png_data.startswith(b"\x89PNG"):
            return None

        fd, screenshot_path = tempfile.mkstemp(prefix="catch_cute_pets_", suffix=".png")
        try:
            with os.fdopen(fd, "wb") as screenshot:
                screenshot.write(png_data)
            result = subprocess.run([OCR_HELPER, screenshot_path], capture_output=True, text=True, timeout=12)
        except (OSError, subprocess.SubprocessError):
            return None
        finally:
            try:
                os.unlink(screenshot_path)
            except OSError:
                pass

        # ocr_helper memberi bbox sebagai x,y,w,h dalam rasio layar; titik y
        # dihitung dari bawah gambar.
        width, height = 720, 1640
        # PNG: signature (8), panjang IHDR (4), "IHDR" (4), lalu width/height.
        if len(png_data) >= 24:
            width = int.from_bytes(png_data[16:20], "big")
            height = int.from_bytes(png_data[20:24], "big")

        for line in result.stdout.splitlines():
            text, separator, raw_box = line.partition("|")
            if separator != "|" or text.strip().upper() != "OFF":
                continue
            try:
                left, bottom, box_width, box_height = map(float, raw_box.split(","))
            except ValueError:
                continue
            x = int((left + box_width / 2) * width)
            y = int((1 - bottom - box_height / 2) * height)
            if self.is_bottom_right(x, y, width, height) and self.has_blue_thumb_nearby(png_data, x, y):
                return x, y
        return None

    @staticmethod
    def has_blue_thumb_nearby(png_data: bytes, x: int, y: int) -> bool:
        """Pastikan tulisan OFF memang milik tombol jempol biru, bukan teks lain."""
        try:
            image = Image.open(io.BytesIO(png_data)).convert("RGB")
        except OSError:
            return False

        width, height = image.size
        # Ikon jempol biasanya berada di kiri teks OFF; area dibuat longgar agar
        # tetap cocok pada skala layar dan tata letak game yang berbeda.
        left = max(0, x - int(width * 0.32))
        right = min(width, x + int(width * 0.12))
        top = max(0, y - int(height * 0.12))
        bottom = min(height, y + int(height * 0.12))
        blue_pixels = 0
        for py in range(top, bottom, 4):
            for px in range(left, right, 4):
                red, green, blue = image.getpixel((px, py))
                if blue >= 90 and blue >= red * 1.25 and blue >= green * 1.08:
                    blue_pixels += 1
                    if blue_pixels >= 18:
                        return True
        return False

    @staticmethod
    def has_green_button_nearby(png_data: bytes, x: int, y: int) -> bool:
        """Pastikan label KLAIM berada di atas/di dalam tombol berwarna hijau."""
        try:
            image = Image.open(io.BytesIO(png_data)).convert("RGB")
        except OSError:
            return False

        width, height = image.size
        left = max(0, x - int(width * 0.24))
        right = min(width, x + int(width * 0.24))
        top = max(0, y - int(height * 0.08))
        bottom = min(height, y + int(height * 0.08))
        green_pixels = 0
        for py in range(top, bottom, 4):
            for px in range(left, right, 4):
                red, green, blue = image.getpixel((px, py))
                if green >= 85 and green >= red * 1.22 and green >= blue * 1.18:
                    green_pixels += 1
                    if green_pixels >= 24:
                        return True
        return False

    def find_claim_in_ui_dump(self) -> Optional[Tuple[int, int]]:
        remote_path = "/sdcard/catch_cute_pets_bot.xml"
        result = self.adb(["shell", "uiautomator", "dump", remote_path], timeout=10)
        if result.returncode != 0:
            return None
        xml_data = self.adb(["exec-out", "cat", remote_path], timeout=10).stdout
        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError:
            return None

        for node in root.iter("node"):
            label = (node.attrib.get("text") or node.attrib.get("content-desc") or "").strip().upper()
            if label not in {"KLAIM", "CLAIM"}:
                continue
            bounds = self.parse_bounds(node.attrib.get("bounds", ""))
            if bounds:
                x1, y1, x2, y2 = bounds
                return (x1 + x2) // 2, (y1 + y2) // 2
        return None

    def find_green_claim_with_ocr(self) -> Optional[Tuple[int, int]]:
        if not os.path.isfile(OCR_HELPER):
            return None
        png_data = self.adb_bytes(["exec-out", "screencap", "-p"], timeout=12)
        if not png_data.startswith(b"\x89PNG"):
            return None

        fd, screenshot_path = tempfile.mkstemp(prefix="catch_cute_pets_", suffix=".png")
        try:
            with os.fdopen(fd, "wb") as screenshot:
                screenshot.write(png_data)
            result = subprocess.run([OCR_HELPER, screenshot_path], capture_output=True, text=True, timeout=12)
        except (OSError, subprocess.SubprocessError):
            return None
        finally:
            try:
                os.unlink(screenshot_path)
            except OSError:
                pass

        if len(png_data) < 24:
            return None
        width = int.from_bytes(png_data[16:20], "big")
        height = int.from_bytes(png_data[20:24], "big")
        for line in result.stdout.splitlines():
            text, separator, raw_box = line.partition("|")
            if separator != "|" or text.strip().upper() not in {"KLAIM", "CLAIM"}:
                continue
            try:
                left, bottom, box_width, box_height = map(float, raw_box.split(","))
            except ValueError:
                continue
            x = int((left + box_width / 2) * width)
            y = int((1 - bottom - box_height / 2) * height)
            if self.has_green_button_nearby(png_data, x, y):
                return x, y
        return None

    def tap_green_claim_if_present(self) -> bool:
        now = time.monotonic()
        if now - self.last_claim_check_ts < CLAIM_CHECK_INTERVAL:
            return False
        self.last_claim_check_ts = now
        if now - self.last_claim_tap_ts < TAP_COOLDOWN:
            return False

        point = self.find_claim_in_ui_dump()
        if point:
            png_data = self.adb_bytes(["exec-out", "screencap", "-p"], timeout=12)
            if not self.has_green_button_nearby(png_data, *point):
                point = None
        point = point or self.find_green_claim_with_ocr()
        if not point:
            return False

        x, y = point
        self.last_claim_tap_ts = now
        self.log(f"TOMBOL KLAIM HIJAU TERDETEKSI; klik ({x}, {y}).")
        if not self.dry_run:
            self.adb(["shell", "input", "tap", str(x), str(y)], timeout=8)
        return True

    def tap_off_control_if_present(self) -> bool:
        now = time.monotonic()
        if now - self.last_off_check_ts < OFF_CHECK_INTERVAL:
            return False
        self.last_off_check_ts = now
        if now - self.last_off_tap_ts < TAP_COOLDOWN:
            return False

        point = self.find_off_in_ui_dump()
        if point:
            png_data = self.adb_bytes(["exec-out", "screencap", "-p"], timeout=12)
            if not self.has_blue_thumb_nearby(png_data, *point):
                point = None
        point = point or self.find_off_with_ocr()
        if not point:
            return False

        x, y = point
        self.last_off_tap_ts = now
        self.log(f"OFF TERDETEKSI di kanan-bawah; klik ({x}, {y}) agar menjadi ON/merah.")
        if not self.dry_run:
            self.adb(["shell", "input", "tap", str(x), str(y)], timeout=8)
        return True

    def step(self) -> None:
        foreground = self.get_foreground_app()
        package = foreground[0] if foreground else None
        if package != self.last_foreground:
            self.last_foreground = package or ""
            self.log(f"Foreground: {package or 'tidak terbaca'}")

        if package != TARGET_PACKAGE:
            self.launch_game("game berada di luar foreground")
            return

        # Dahulukan hadiah; setelah klaim layar biasanya berubah.
        if not self.tap_green_claim_if_present():
            self.tap_off_control_if_present()

    def run(self, once: bool = False) -> int:
        self.log(f"Bot aktif untuk {TARGET_NAME} ({TARGET_PACKAGE})")
        if not self.has_device():
            return 2
        if not self.is_target_installed():
            self.log(f"Game belum terpasang: {TARGET_PACKAGE}")
            return 3
        try:
            while True:
                self.step()
                if once:
                    return 0
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.log("Bot dihentikan.")
            return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bot penjaga Catch Cute Pets")
    parser.add_argument("--serial", "-s", default="", help="Serial ADB jika device lebih dari satu")
    parser.add_argument("--interval", "-i", type=float, default=DEFAULT_INTERVAL, help="Interval cek dalam detik")
    parser.add_argument("--once", action="store_true", help="Cek satu kali lalu keluar")
    parser.add_argument("--dry-run", action="store_true", help="Deteksi dan log tanpa membuka/mengetuk")
    args = parser.parse_args()
    return CatchCutePetsBot(args.serial, max(args.interval, 0.1), args.dry_run).run(args.once)


if __name__ == "__main__":
    raise SystemExit(main())
