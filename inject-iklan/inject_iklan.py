#!/usr/bin/env python3
"""
inject-iklan

Bot mandiri untuk siklus injeksi persona/iklan (Google Search -> Web -> Daftar -> App Slot -> Magic Ocean).
Langkah yang dijalankan:
  1. Membuka Chrome.
  2. Melakukan pencarian Google terkait situs slot/judi acak.
  3. Membuka hasil pencarian dan mencoba menekan DAFTAR.
  4. Mengisi formulir pendaftaran dengan data tersimpan di bot (tanpa submit).
  5. Membuka salah satu aplikasi slot secara acak, lalu menutupnya dan kembali ke Magic Ocean.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

DEFAULT_TARGET_PACKAGE = "com.starlightgame.magicoceantilecrush"
DEFAULT_TARGET_ACTIVITY = "com.unity3d.player.UnityPlayerActivity"
OCR_HELPER = "/Users/macbookair/ocr_helper"
TAP_MARKER = "/Users/macbookair/scrcpy_tap_marker"
LOG_FILE = os.path.expanduser("~/inject_iklan.log")

DEFAULT_FIELD_VALUES = {
    "username": "Wahyu91123",
    "password": "Wahyu123*",
    "confirm_password": "Wahyu123*",
    "email": "wahyu91123@gmail.com",
    "phone": "085157993801",
    "bank": "OVO",
    "rek": "085157993801",
    "nama_rek": "Wahyu",
}

SLOT_CANDIDATE_APPS = [
    {"name": "RR33", "pkg": "RR33.COM"},
    {"name": "K68", "pkg": "com.k68.id.xulsfy"},
    {"name": "FJ99", "pkg": "org.chromium.webapk.a1ffa4016fb2cda0c_v2"},
    {"name": "Slot Machines Free", "pkg": "casino.games.slot.machines.free"},
]


@dataclass
class ForegroundApp:
    package: str
    activity: str = ""
    source: str = ""


class InjectIklanBot:
    def __init__(
        self,
        serial: str = "",
        target_package: str = DEFAULT_TARGET_PACKAGE,
        target_activity: str = DEFAULT_TARGET_ACTIVITY,
        dry_run: bool = False,
        no_marker: bool = False,
        custom_keywords: Optional[list[str]] = None,
        sites_per_query: int = 2,
        field_values: Optional[dict[str, str]] = None,
    ):
        self.serial = serial.strip() or self.detect_device_serial()
        self.target_package = target_package
        self.target_activity = target_activity
        self.dry_run = dry_run
        self.no_marker = no_marker
        self.custom_keywords = custom_keywords or []
        self.sites_per_query = sites_per_query
        self.field_values = dict(DEFAULT_FIELD_VALUES)
        if field_values:
            self.field_values.update(field_values)

        self._screen_width = 720
        self._screen_height = 1640
        self._update_screen_size()

    def log(self, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        print(line, flush=True)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def detect_device_serial(self) -> str:
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
            lines = [l.strip() for l in (res.stdout or "").splitlines() if l.strip()]
            devices = []
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])
            if len(devices) == 1:
                return devices[0]
            if len(devices) > 1:
                return devices[0]
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
            self.log(f"ADB timeout: {' '.join(args)}")
            return ""
        except FileNotFoundError:
            self.log("ADB tidak ditemukan di PATH.")
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
            res = subprocess.run(cmd, capture_output=True, timeout=timeout)
            return res.stdout or b""
        except Exception:
            return b""

    def show_tap_marker(self, x: int, y: int, color: str = "blue", duration: float = 1.2, diameter: int = 58) -> None:
        if self.no_marker or not os.path.exists(TAP_MARKER):
            return
        try:
            subprocess.Popen(
                [TAP_MARKER, str(int(x)), str(int(y)), color, str(float(duration)), str(int(diameter))],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def tap(self, x: int, y: int, color: str = "blue", duration: float = 1.2) -> None:
        self.show_tap_marker(x, y, color=color, duration=duration)
        if self.dry_run:
            self.log(f"[DRY-RUN] Tap ({x}, {y})")
            return
        self.adb_out(["shell", "input", "tap", str(int(x)), str(int(y))], timeout=5)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        if self.dry_run:
            self.log(f"[DRY-RUN] Swipe ({x1}, {y1}) -> ({x2}, {y2}) [{duration_ms}ms]")
            return
        self.adb_out([
            "shell", "input", "swipe",
            str(int(x1)), str(int(y1)),
            str(int(x2)), str(int(y2)),
            str(int(duration_ms))
        ], timeout=5)

    def adb_type_text(self, text: str) -> None:
        if not text or self.dry_run:
            if self.dry_run:
                self.log(f"[DRY-RUN] Type: '{text}'")
            return
        special = " *?&$()[]{}|;<>`\"'\\"
        if "*" in text:
            parts = text.split("*")
            for i, part in enumerate(parts):
                if part:
                    safe = "".join(("\\" + ch) if ch in special else ch for ch in part)
                    self.adb_out(["shell", "input", "text", safe], timeout=4)
                if i < len(parts) - 1:
                    self.adb_out(["shell", "input", "keyevent", "17"], timeout=3)
        else:
            safe = "".join(("\\" + ch) if ch in special else ch for ch in text)
            self.adb_out(["shell", "input", "text", safe], timeout=4)

    def hide_keyboard_if_shown(self) -> None:
        try:
            res = self.adb_out(["shell", "dumpsys", "input_method"], timeout=3)
            if "mInputShown=true" in res:
                self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=2)
                time.sleep(0.25)
        except Exception:
            pass

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

    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    def ocr_screen(self, prefix: str = "ocr") -> list[Tuple[str, str, int, int]]:
        """Jalankan OCR pada tampilan layar saat ini. Return [(text, bbox, cx, cy), ...]."""
        if not os.path.exists(OCR_HELPER):
            return []
        screenshot = self.capture_screenshot()
        if not screenshot:
            return []
        png_data, width, height = screenshot
        safe_serial = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.serial or "default")
        screenshot_path = f"/tmp/inject_iklan_{prefix}_{safe_serial}.png"
        try:
            with open(screenshot_path, "wb") as f:
                f.write(png_data)
            res = subprocess.run([OCR_HELPER, screenshot_path], capture_output=True, text=True, timeout=10)
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

    def match_registration_field(self, text: str) -> Optional[str]:
        """Mencocokkan teks label atau hint dengan tipe field form pendaftaran."""
        norm = self.normalize_text(text)
        if not norm or len(norm) < 2:
            return None

        # 1. Konfirmasi Kata Sandi (harus sebelum password)
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

        # 3. Nomor Rekening (harus sebelum nomor telepon)
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

        # 5. Bank / Pembayaran / E-Wallet
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
        """Pilih opsi OVO jika dropdown pilihan bank terbuka."""
        entries = self.ocr_screen("bank_ovo")
        for text, _bbox, cx, cy in entries:
            norm = self.normalize_text(text)
            if "ovo" in norm and 180 <= cy <= (self._screen_height - 60):
                self.log(f"  [BANK]: Opsi OVO terdeteksi di ({cx}, {cy}) -> Tap OVO")
                self.tap(cx, cy, color="green")
                time.sleep(0.8)
                return True
        return False

    def get_registration_input_fields_via_ui(self) -> list[Tuple[str, int, int]]:
        """Baca input form dari accessibility tree Chrome melalui uiautomator dump."""
        remote = "/sdcard/inject_iklan_form.xml"
        try:
            self.adb_out(["shell", "uiautomator", "dump", remote], timeout=5)
            xml = self.adb_out(["exec-out", "cat", remote], timeout=5)
            root = ET.fromstring(xml)
        except Exception:
            return []

        fields: list[Tuple[str, int, int]] = []
        text_nodes: list[Tuple[str, list[int]]] = []
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
                node.attrib.get("text", ""),
                node.attrib.get("content-desc", ""),
                node.attrib.get("hint", ""),
                node.attrib.get("resource-id", ""),
            )))
            bounds = node.attrib.get("bounds", "")
            nums = [int(n) for n in re.findall(r"\d+", bounds)]
            if len(nums) != 4:
                continue
            x1, y1, x2, y2 = nums
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

    def find_web_daftar_button(self) -> Optional[Tuple[str, str, int, int]]:
        """Mendeteksi tombol atau tautan DAFTAR/REGISTER pada halaman web yang sedang dibuka."""
        entries = self.ocr_screen("daftar_btn")
        register_keywords = [
            "daftar", "register", "registrasi", "signup", "sign up",
            "gabung", "buka akun", "buat akun", "klaim bonus", "claim bonus", "join now"
        ]
        exclude_words = ["cara", "mengklik", "syarat", "ketentuan", "panduan", "adalah", "tentang", "about", "hasil"]

        candidates: list[Tuple[int, str, str, int, int]] = []
        for text, bbox, cx, cy in entries:
            if cy < 180 or cy > (self._screen_height - 60):
                continue
            words = text.split()
            if len(words) > 4 or len(text) > 25:
                continue
            lower_text = text.lower()
            if any(ex in lower_text for ex in exclude_words):
                continue
            norm = self.normalize_text(text)
            for kw in register_keywords:
                kw_norm = self.normalize_text(kw)
                if kw_norm in norm:
                    priority = 0 if ("daftar" in norm or "register" in norm) else 1
                    candidates.append((priority, text, bbox, cx, cy))
                    break

        if not candidates:
            return None

        candidates.sort(key=lambda c: (c[0], c[4]))
        _, best_text, best_bbox, best_x, best_y = candidates[0]
        return best_text, best_bbox, best_x, best_y

    def fill_registration_form(self, search_label: str = "WEB SLOT") -> None:
        """Langkah 4: Mengisi formulir pendaftaran akun tanpa submit."""
        self.log(f"[{search_label}]: Memulai pengisian formulir pendaftaran akun...")
        self.hide_keyboard_if_shown()

        all_required = ["username", "password", "confirm_password", "email", "phone", "bank", "rek", "nama_rek"]
        filled_fields: set[str] = set()

        def fill(field_type: str, label: str, tap_x: int, tap_y: int) -> None:
            if field_type in filled_fields:
                return
            val = self.field_values.get(field_type)
            if not val:
                return
            if field_type == "bank":
                self.log(f"  [{search_label}]: Field 'bank' terdeteksi '{label}' di ({tap_x},{tap_y}) -> pilih OVO")
                self.tap(tap_x, tap_y, color="yellow")
                time.sleep(0.5)
                if not self.select_ovo_option_if_present():
                    self.adb_type_text(val)
            else:
                self.log(f"  [{search_label}]: Field '{field_type}' terdeteksi '{label}' di ({tap_x},{tap_y}) -> isi '{val}'")
                self.tap(tap_x, tap_y, color="yellow")
                time.sleep(0.3)
                self.adb_type_text(val)
            filled_fields.add(field_type)
            time.sleep(0.25)
            self.hide_keyboard_if_shown()

        def scan_current_viewport() -> None:
            # 1. UIAutomator accessibility tree
            for field_type, x, y in self.get_registration_input_fields_via_ui():
                fill(field_type, "accessibility", x, y)

            # 2. OCR Fallback
            entries = self.ocr_screen("form_viewport")
            entries.sort(key=lambda item: item[3])
            for text, _bbox, cx, cy in entries:
                if cy < 160 or cy > (self._screen_height - 60):
                    continue
                field_type = self.match_registration_field(text)
                if field_type and field_type not in filled_fields:
                    tap_x = (self._screen_width // 2) if cx < 250 else cx
                    tap_y = min(cy + 48, self._screen_height - 90)
                    fill(field_type, text, tap_x, tap_y)

        self.log(f"[{search_label}]: Scan posisi form saat ini, lalu scroll turun perlahan...")
        last_filled_count = -1
        unchanged_scans = 0
        mid_x = self._screen_width // 2
        swipe_y1 = int(self._screen_height * 0.72)
        swipe_y2 = int(self._screen_height * 0.55)

        for pass_num in range(12):
            scan_current_viewport()
            if len(filled_fields) == len(all_required):
                break
            if len(filled_fields) == last_filled_count:
                unchanged_scans += 1
            else:
                unchanged_scans = 0
            last_filled_count = len(filled_fields)

            self.swipe(mid_x, swipe_y1, mid_x, swipe_y2, duration_ms=400)
            time.sleep(0.55)
            self.hide_keyboard_if_shown()

            if unchanged_scans >= 3 and pass_num >= 7:
                break

        for field_type in all_required:
            if field_type not in filled_fields:
                self.log(f"[{search_label}]: Field '{field_type}' tidak terdeteksi di viewport form; lewati.")
        self.log(f"[{search_label}]: Formulir selesai. Field terisi: {sorted(filled_fields)}")

    def generate_random_slot_keyword(self) -> str:
        """Buat kombinasi kata kunci acak untuk pencarian Google."""
        if self.custom_keywords:
            return random.choice(self.custom_keywords)
        keyword_groups = [
            ["toto", "slot", "judi", "casino"],
            ["gacor", "maxwin", "rtp live", "bonus", "rollingan"],
            ["zeus", "pragmatic", "spaceman", "gates of olympus", "mahjong"],
            ["deposit dana", "resmi indonesia", "bonus member", "terpercaya", "hari ini"],
        ]
        words = [random.choice(group) for group in keyword_groups]
        return " ".join(words)

    def browse_google_and_click_sites(self, query: str, search_label: str = "WEB SLOT 1/1") -> None:
        """Langkah 1, 2, 3: Buka Chrome, cari Google query, klik hasil pencarian, & klik DAFTAR."""
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        self.log(f"[{search_label}]: Step 1 & 2 -> Membuka Chrome & Google Search query '{query}'")
        self.adb_out([
            "shell", "am", "start",
            "-a", "android.intent.action.VIEW",
            "-d", url,
            "com.android.chrome"
        ], timeout=6)
        time.sleep(2.0)

        mid_x = self._screen_width // 2
        for site_idx in range(1, self.sites_per_query + 1):
            self.log(f"[{search_label} - SITUS {site_idx}]: Step 3 -> Menjelajah hasil Google & mencari link situs...")
            if site_idx == 1:
                # Scroll sedikit pada hasil Google teratas
                self.swipe(mid_x, int(self._screen_height * 0.58), mid_x, int(self._screen_height * 0.35), 250)
                time.sleep(0.4)
                tap_x, tap_y = mid_x, int(self._screen_height * 0.42)
            else:
                # Scroll lebih ke bawah untuk situs kedua
                self.swipe(mid_x, int(self._screen_height * 0.67), mid_x, int(self._screen_height * 0.28), 300)
                time.sleep(0.4)
                tap_x, tap_y = mid_x, int(self._screen_height * 0.48)

            self.log(f"[{search_label} - SITUS {site_idx}]: Klik link hasil pencarian Google di ({tap_x},{tap_y})")
            self.tap(tap_x, tap_y, color="green")
            time.sleep(2.5)

            # Scroll ke bawah di situs agar tracker dan asset terpicu
            self.swipe(mid_x, int(self._screen_height * 0.60), mid_x, int(self._screen_height * 0.35), 300)
            time.sleep(0.6)

            # Deteksi tombol DAFTAR / REGISTER
            daftar_btn = self.find_web_daftar_button()
            if not daftar_btn:
                # Scroll tambahan jika tombol ada di bawah
                self.swipe(mid_x, int(self._screen_height * 0.55), mid_x, int(self._screen_height * 0.30), 300)
                time.sleep(0.6)
                daftar_btn = self.find_web_daftar_button()

            if daftar_btn:
                dtext, _dbbox, dx, dy = daftar_btn
                self.log(f"[{search_label} - SITUS {site_idx}]: Tombol DAFTAR terdeteksi '{dtext}' di ({dx},{dy}) -> KLIK DAFTAR!")
                self.tap(dx, dy, color="green")
                time.sleep(1.8)

                # Langkah 4: Pengisian formulir
                self.fill_registration_form(search_label=f"{search_label} - SITUS {site_idx}")
                time.sleep(0.5)
            else:
                self.log(f"[{search_label} - SITUS {site_idx}]: Tombol DAFTAR tidak terdeteksi di situs ini.")

            # Kembali ke pencarian Google jika masih ada situs berikutnya
            if site_idx < self.sites_per_query:
                self.log(f"[{search_label}]: Kembali ke hasil pencarian Google...")
                self.adb_out(["shell", "input", "keyevent", "BACK"], timeout=3)
                time.sleep(0.8)
                # Pastikan Chrome tetap di foreground
                self.adb_out([
                    "shell", "am", "start",
                    "-a", "android.intent.action.VIEW",
                    "-d", url,
                    "com.android.chrome"
                ], timeout=6)
                time.sleep(1.2)

    def get_installed_packages(self) -> set[str]:
        out = self.adb_out(["shell", "pm", "list", "packages"], timeout=8)
        pkgs = set()
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                pkgs.add(line[8:].strip())
        return pkgs

    def select_and_open_slot_app(self) -> None:
        """Langkah 5: Buka salah satu aplikasi slot secara acak, interaksi sesaat, lalu force-stop."""
        installed = self.get_installed_packages()
        eligible_apps = [app for app in SLOT_CANDIDATE_APPS if app["pkg"] in installed]

        # Jika ada package acak lain di HP yang berbau slot/casino, sertakan juga
        for pkg in installed:
            lower_pkg = pkg.lower()
            if any(k in lower_pkg for k in ["slot", "casino", "judi", "poker"]) and pkg not in [a["pkg"] for a in SLOT_CANDIDATE_APPS]:
                if pkg != self.target_package:
                    eligible_apps.append({"name": pkg.split(".")[-1].title(), "pkg": pkg})

        if not eligible_apps:
            # Fallback ke daftar standar
            eligible_apps = SLOT_CANDIDATE_APPS

        chosen_app = random.choice(eligible_apps)
        app_name = chosen_app["name"]
        app_pkg = chosen_app["pkg"]
        self.log(f"[APLIKASI SLOT ACAK]: Step 5 -> Membuka aplikasi slot acak: {app_name} ({app_pkg})...")

        # Jalankan via monkey intent launcher
        self.adb_out([
            "shell", "monkey", "-p", app_pkg,
            "-c", "android.intent.category.LAUNCHER", "1"
        ], timeout=6)

        # Sesi aktif di OS & SDK iklan (2.5 detik)
        time.sleep(2.5)
        mid_x = self._screen_width // 2
        self.swipe(mid_x, int(self._screen_height * 0.55), mid_x, int(self._screen_height * 0.40), 250)
        time.sleep(0.5)

        self.log(f"[APLIKASI SLOT ACAK]: {app_name} selesai dibuka, menutup aplikasi (force-stop)")
        self.adb_out(["shell", "am", "force-stop", app_pkg], timeout=4)
        time.sleep(0.4)

    def return_to_magic_ocean(self) -> None:
        """Kembali ke game target."""
        self.log(f"[KEMBALI KE GAME]: Membuka kembali {self.target_package}...")
        res = self.adb_out([
            "shell", "am", "start",
            "-n", f"{self.target_package}/{self.target_activity}"
        ], timeout=6)
        if "SecurityException" in res or "not exported" in res or "Error" in res:
            self.adb_out(["shell", "monkey", "-p", self.target_package, "-c", "android.intent.category.LAUNCHER", "1"], timeout=6)
        time.sleep(0.8)

    def run_cycle(self) -> None:
        """Menjalankan satu siklus lengkap langkah 1 s/d 5."""
        self.log("=" * 60)
        self.log("=== MEMULAI SIKLUS INJECT-IKLAN (LANGKAH 1 s/d 5) ===")
        self.log("=" * 60)

        # Generate 2 query berbeda untuk 2 pencarian berurutan
        q1 = self.generate_random_slot_keyword()
        q2 = self.generate_random_slot_keyword()
        while q2 == q1:
            q2 = self.generate_random_slot_keyword()

        try:
            # 1, 2, 3, 4: Pencarian Google Pertama
            self.browse_google_and_click_sites(q1, search_label="WEB SLOT 1/2")

            # 1, 2, 3, 4: Pencarian Google Kedua
            self.browse_google_and_click_sites(q2, search_label="WEB SLOT 2/2")

            # Tutup Chrome setelah kedua web selesai dijelajahi
            self.log("[CHROME]: Menutup Chrome (force-stop)...")
            self.adb_out(["shell", "am", "force-stop", "com.android.chrome"], timeout=4)
            time.sleep(0.5)

            # 5: Buka 1 aplikasi slot acak lalu tutup
            self.select_and_open_slot_app()

        except Exception as e:
            self.log(f"ERROR DALAM SIKLUS INJECT-IKLAN: {e}")
        finally:
            # Kembalikan ke game Magic Ocean
            self.return_to_magic_ocean()
            self.log("=== SIKLUS INJECT-IKLAN SELESAI ===")
            self.log("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="inject-iklan: Bot mandiri injeksi profil iklan Google slot/judi & app slot acak ke Magic Ocean."
    )
    parser.add_argument("--serial", "-s", default="", help="Serial ADB device (default: auto-detect)")
    parser.add_argument("--target-pkg", default=DEFAULT_TARGET_PACKAGE, help="Package game target (default: Magic Ocean)")
    parser.add_argument("--target-act", default=DEFAULT_TARGET_ACTIVITY, help="Activity game target")
    parser.add_argument("--count", "-n", type=int, default=1, help="Berapa siklus dijalankan (default: 1)")
    parser.add_argument("--loop", action="store_true", help="Jalankan terus menerus secara berkala")
    parser.add_argument("--interval", type=float, default=300.0, help="Jeda antar siklus saat --loop (detik, default: 300)")
    parser.add_argument("--sites", type=int, default=2, help="Jumlah situs yang diklik per query Google (default: 2)")
    parser.add_argument("--dry-run", action="store_true", help="Mode simulasi tanpa tap fisik")
    parser.add_argument("--no-marker", action="store_true", help="Nonaktifkan tap marker visual di scrcpy")
    parser.add_argument("--query", "-q", action="append", help="Kata kunci pencarian kustom (bisa berulang)")

    args = parser.parse_args()

    bot = InjectIklanBot(
        serial=args.serial,
        target_package=args.target_pkg,
        target_activity=args.target_act,
        dry_run=args.dry_run,
        no_marker=args.no_marker,
        custom_keywords=args.query,
        sites_per_query=args.sites,
    )

    if not bot.serial:
        print("ERROR: Tidak ada perangkat Android yang terhubung via ADB.")
        sys.exit(1)

    print(f"Perangkat terdeteksi: {bot.serial}")
    print(f"Target game       : {bot.target_package}")
    print(f"Resolusi layar    : {bot._screen_width}x{bot._screen_height}")
    print(f"Mode              : {'LOOP BERKALA' if args.loop else f'{args.count} siklus'}")
    print(f"Log disimpan di   : {LOG_FILE}\n")

    if args.loop:
        cycle = 1
        while True:
            bot.log(f"--- Siklus Loop #{cycle} dimulai ---")
            bot.run_cycle()
            cycle += 1
            bot.log(f"Menunggu jeda interval {args.interval} detik sebelum siklus berikutnya...")
            time.sleep(args.interval)
    else:
        for i in range(args.count):
            if args.count > 1:
                bot.log(f"--- Siklus #{i + 1} dari {args.count} ---")
            bot.run_cycle()
            if i < args.count - 1:
                time.sleep(2.0)


if __name__ == "__main__":
    main()
