#!/usr/bin/env python3
"""
Tile Juicy Match-3 Bot

Bot untuk main game Tile Juicy dengan deteksi tile dan logika match-3.

Cara kerja:
1. Screenshot layar
2. Deteksi setiap tile di grid berdasarkan warna
3. Cari 3 tile yang sama (atau lebih)
4. Tap ketiga tile tersebut
5. Ulangi sampai level selesai atau slot penuh

Game: com.spiritbreaker.games.tilejuicy
Device: 062322513B000705 (Infinix X692, 720x1640)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple
from PIL import Image
from collections import Counter

TARGET_PACKAGE = "com.spiritbreaker.games.tilejuicy"
TARGET_NAME = "Tile Juicy"

LOG_FILE = os.path.expanduser("~/tile_juicy_match3_bot.log")
DEFAULT_INTERVAL = 1.5

# Grid configuration (berdasarkan analisis screenshot)
GRID_TOP = 850
GRID_BOTTOM = 1150
GRID_LEFT = 100
GRID_RIGHT = 620
GRID_COLS = 6
GRID_ROWS = 5

# Slot area (tempat tile terkumpul di bawah)
SLOT_Y = 1450
SLOT_COUNT = 7

# Tile type detection berdasarkan warna RGB
# Format: (name, (r_min, r_max), (g_min, g_max), (b_min, b_max))
TILE_TYPES = [
    ("kuning", (240, 255), (210, 230), (30, 70)),
    ("pink", (230, 245), (220, 235), (230, 240)),
    ("orange", (250, 255), (140, 160), (10, 25)),
    ("hijau_terang", (50, 70), (210, 225), (75, 90)),
    ("hijau_gelap", (0, 10), (140, 150), (5, 15)),
    ("biru", (50, 80), (150, 180), (200, 230)),
    ("ungu", (180, 210), (100, 140), (180, 220)),
    ("merah", (230, 255), (50, 90), (50, 90)),
]

EMPTY_COLOR_THRESHOLD = 70  # Tile dengan RGB semua < 70 dianggap kosong/background


@dataclass
class Tile:
    row: int
    col: int
    x: int
    y: int
    tile_type: str
    color: Tuple[int, int, int]


class TileJuicyMatch3Bot:
    def __init__(self, serial: str = "", interval: float = DEFAULT_INTERVAL, dry_run: bool = False):
        self.serial = serial.strip()
        self.interval = interval
        self.dry_run = dry_run
        self.total_taps = 0
        self.total_matches = 0
        self.cycles = 0
        
        self.tile_w = (GRID_RIGHT - GRID_LEFT) / GRID_COLS
        self.tile_h = (GRID_BOTTOM - GRID_TOP) / GRID_ROWS

    def log(self, msg: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line, flush=True)
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
        except Exception as exc:
            self.log(f"ADB error: {exc}")
            return ""

    def tap(self, x: int, y: int) -> None:
        if self.dry_run:
            self.log(f"DRY RUN: tap {x},{y}")
            return
        self.adb_out(["shell", "input", "tap", str(x), str(y)], timeout=5)
        self.total_taps += 1
        time.sleep(0.15)

    def screenshot(self) -> Optional[Image.Image]:
        """Ambil screenshot dari device"""
        try:
            cmd = ["adb"]
            if self.serial:
                cmd += ["-s", self.serial]
            cmd += ["exec-out", "screencap", "-p"]
            result = subprocess.run(cmd, capture_output=True, timeout=8)
            if result.returncode == 0 and result.stdout:
                from io import BytesIO
                return Image.open(BytesIO(result.stdout))
        except Exception as exc:
            self.log(f"Screenshot error: {exc}")
        return None

    def detect_tile_type(self, r: int, g: int, b: int) -> str:
        """Deteksi jenis tile berdasarkan warna RGB"""
        # Cek apakah tile kosong/background
        if r < EMPTY_COLOR_THRESHOLD and g < EMPTY_COLOR_THRESHOLD and b < EMPTY_COLOR_THRESHOLD:
            return "empty"
        
        # Cek setiap tile type
        for name, (r_min, r_max), (g_min, g_max), (b_min, b_max) in TILE_TYPES:
            if r_min <= r <= r_max and g_min <= g <= g_max and b_min <= b <= b_max:
                return name
        
        # Unknown tile
        return f"unknown_{r}_{g}_{b}"

    def scan_grid(self, img: Image.Image) -> List[Tile]:
        """Scan semua tile di grid"""
        tiles = []
        pixels = img.load()
        
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                # Hitung posisi center tile
                cx = int(GRID_LEFT + (col + 0.5) * self.tile_w)
                cy = int(GRID_TOP + (row + 0.5) * self.tile_h)
                
                # Sample warna di center
                pixel = pixels[cx, cy]
                if isinstance(pixel, (tuple, list)) and len(pixel) >= 3:
                    r, g, b = pixel[0], pixel[1], pixel[2]
                else:
                    r = g = b = 0
                tile_type = self.detect_tile_type(r, g, b)
                
                if tile_type != "empty":
                    tiles.append(Tile(row, col, cx, cy, tile_type, (r, g, b)))
        
        return tiles

    def find_matches(self, tiles: List[Tile]) -> List[List[Tile]]:
        """Cari grup tile yang bisa di-match (3 atau lebih dengan tipe sama)"""
        # Group tiles by type
        by_type = {}
        for tile in tiles:
            if tile.tile_type not in by_type:
                by_type[tile.tile_type] = []
            by_type[tile.tile_type].append(tile)
        
        # Cari yang punya >= 3 tile
        matches = []
        for tile_type, group in by_type.items():
            if len(group) >= 3:
                # Ambil 3 tile pertama
                matches.append(group[:3])
        
        # Prioritas: ambil yang paling banyak dulu
        matches.sort(key=lambda g: len(by_type[g[0].tile_type]), reverse=True)
        return matches

    def play_match(self, match: List[Tile]) -> None:
        """Tap 3 tile yang match"""
        self.log(f"Match found: {match[0].tile_type} x{len(match)}")
        for tile in match[:3]:
            self.log(f"  Tap [{tile.row},{tile.col}] at ({tile.x},{tile.y})")
            self.tap(tile.x, tile.y)
            time.sleep(0.2)
        self.total_matches += 1

    def check_game_state(self) -> str:
        """Cek state game (playing, level_complete, game_over)"""
        # TODO: implementasi deteksi state game
        # Untuk sekarang assume always playing
        return "playing"

    def step(self) -> bool:
        """Satu langkah gameplay. Return True jika berhasil, False jika perlu restart."""
        self.cycles += 1
        
        # Screenshot
        img = self.screenshot()
        if img is None:
            self.log("Failed to capture screenshot")
            return False
        
        # Scan grid
        tiles = self.scan_grid(img)
        self.log(f"Cycle {self.cycles}: {len(tiles)} tiles detected")
        
        # Debug: tampilkan distribusi tile
        type_count = Counter(t.tile_type for t in tiles)
        self.log(f"  Tiles: {dict(type_count)}")
        
        # Cari match
        matches = self.find_matches(tiles)
        
        if not matches:
            self.log("  No matches found, waiting...")
            time.sleep(1)
            return True
        
        # Main match pertama
        self.play_match(matches[0])
        
        return True

    def run(self) -> int:
        self.log("=" * 60)
        self.log(f"Tile Juicy Match-3 Bot v2.0")
        self.log(f"Target: {TARGET_NAME} ({TARGET_PACKAGE})")
        self.log(f"Serial: {self.serial or 'auto'}")
        self.log(f"Interval: {self.interval}s | DryRun: {self.dry_run}")
        self.log("=" * 60)

        # Check device
        output = self.adb_out(["devices"], timeout=8)
        devices = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        
        if self.serial:
            if self.serial not in devices:
                self.log(f"GAGAL: device {self.serial} tidak terhubung")
                return 1
        else:
            if not devices:
                self.log("GAGAL: tidak ada device terhubung")
                return 1
            if len(devices) > 1:
                self.log(f"GAGAL: ada {len(devices)} devices, gunakan --serial")
                return 1
            self.serial = devices[0]
            self.log(f"Device: {self.serial}")

        self.log("Bot mulai berjalan. Ctrl+C untuk berhenti.")
        
        try:
            while True:
                success = self.step()
                if not success:
                    self.log("Step failed, retrying...")
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.log(f"Bot dihentikan.")
            self.log(f"Stats: {self.total_taps} taps, {self.total_matches} matches, {self.cycles} cycles")
            return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Tile Juicy Match-3 Bot")
    ap.add_argument("--serial", "-s", default="", help="Device serial (ADB)")
    ap.add_argument("--interval", "-i", type=float, default=DEFAULT_INTERVAL, help="Loop interval (detik)")
    ap.add_argument("--dry-run", action="store_true", help="Dry run (tidak kirim input)")
    args = ap.parse_args()
    
    raise SystemExit(TileJuicyMatch3Bot(args.serial, max(0.5, args.interval), args.dry_run).run())
