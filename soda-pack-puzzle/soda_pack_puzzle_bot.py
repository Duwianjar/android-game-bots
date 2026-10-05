#!/usr/bin/env python3
"""
Soda Pack Puzzle Automation Bot (com.soda.pack.puzzle)
Multi-Device Parallel Engine - Calibrated Coordinates, Fast Burst Tap, Smart Reward OCR,
Robust Ad Dismissal (No Ad Loop), Auto-Install, Main Ulang & DANA Withdrawal
"""
import subprocess
import multiprocessing
import time
import sys
import os
import re
import signal
import cv2
import numpy as np
import html
import json
import threading
import requests
from pathlib import Path
from soda_event_logger import log_event

PACKAGE_NAME = "com.soda.pack.puzzle"
LAUNCH_ACTIVITY = "com.soda.pack.puzzle/.act.MainActivity"
GAME_ACTIVITY = "com.soda.pack.puzzle/.act.MainActivity"
OCR_HELPER_PATH = "/Users/macbookair/ocr_helper"
TAP_MARKER_PATH = "/Users/macbookair/scrcpy_tap_marker"

def send_telegram_async(text):
    """Kirim notifikasi ke grup Telegram secara non-blocking di background thread."""
    def _send():
        try:
            url = "https://api.telegram.org/bot8849203378:AAEmh0zmO6GoC1x2eb-s5yUVAUDSqremF44/sendMessage"
            requests.post(url, data={
                "chat_id": "-5421593398",
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }, timeout=6)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()
CLICK_REWARD_DURING_AD_WAIT = False  # Nonaktif: jangan klik Koleksi/Klaim/Unduh saat menunggu iklan
AD_WAIT_SECONDS = 15          # Menonton iklan sampai selesai dulu sebelum ditutup
MIN_WITHDRAWAL_RP = 500        # Klik/penarikan =Rp jika saldo lebih dari 500

# Koordinat 8 Kolom Rak Kaleng & Baris Slot Botol (Terkalibrasi 720x1640)
SHELF_COLUMNS_X = [55, 140, 225, 310, 400, 490, 580, 665]
SHELF_SLOTS_Y = [765, 685, 605, 525, 445]

def get_connected_devices():
    """Mengambil daftar semua HP Android yang terhubung via ADB."""
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3.0, check=False)
        lines = res.stdout.strip().splitlines()[1:]
        devices = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices
    except Exception:
        return []

def is_scrcpy_running_for(serial):
    try:
        res = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=2.0, check=False)
        return any("scrcpy" in line and serial in line for line in res.stdout.splitlines())
    except Exception:
        return False

def ensure_scrcpy_running(serial):
    if not is_scrcpy_running_for(serial):
        print(f"[{serial}] [+] Membuka jendela tampilan layar scrcpy (Soda Pack Puzzle)...", flush=True)
        try:
            subprocess.Popen(
                ["scrcpy", "-s", serial, "--window-title", f"Soda Pack Puzzle - {serial}", "--max-fps=25", "--no-audio"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(0.6)
            print(f"[{serial}] [✔] Jendela scrcpy berhasil dibuka!", flush=True)
        except Exception as e:
            print(f"[{serial}] [!] Catatan scrcpy: {e}", flush=True)

def is_empty_shelf(patch):
    """Mendeteksi apakah slot rak adalah area kosong / latar belakang rak tanpa botol."""
    if patch is None or patch.size == 0:
        return True
    std = float(patch.std())
    if std < 40:
        return True
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    mean_hsv = np.mean(hsv, axis=(0, 1))
    if (100 <= mean_hsv[0] <= 135) and (mean_hsv[2] < 160) and (std < 50):
        return True
    return False

def classify_game_color_hsv(h, s, v):
    """Klasifikasi warna botol/kotak Soda Pack Puzzle dari HSV OpenCV."""
    if v < 65 or s < 45:
        return None
    if h <= 8 or h >= 170:
        return "Red"
    if 9 <= h <= 16:
        return "Orange"
    if 17 <= h <= 38:
        return "Yellow"
    if 39 <= h <= 84:
        return "Green"
    if 85 <= h <= 104:
        return "Cyan"
    if 105 <= h <= 132:
        return "Blue"
    if 133 <= h <= 169:
        return "Pink"
    return None

def dominant_game_color(patch):
    """Ambil warna dominan pada patch, mengabaikan tutup botol abu/putih."""
    if patch is None or patch.size == 0:
        return None
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    mask = (hsv[:, :, 1] > 55) & (hsv[:, :, 2] > 80)
    if int(mask.sum()) < 18:
        return None
    vals = hsv[mask]
    h = int(np.median(vals[:, 0]))
    s = int(np.median(vals[:, 1]))
    v = int(np.median(vals[:, 2]))
    return classify_game_color_hsv(h, s, v)

def colors_match(color, target_colors):
    if not color or not target_colors:
        return False
    if color in target_colors:
        return True
    # Soda Pack punya warna peach/salmon/pink yang sering jatuh ke hue Red,
    # sementara tray terlihat Pink. Anggap Red dan Pink satu keluarga.
    if color in ("Red", "Pink") and ("Red" in target_colors or "Pink" in target_colors):
        return True
    # Orange terang sering terbaca Yellow karena highlight tutup/label.
    if color in ("Orange", "Yellow") and ("Orange" in target_colors or "Yellow" in target_colors):
        return True
    # Cyan/Blue sering kebaca silang karena highlight botol.
    if color in ("Cyan", "Blue") and ("Cyan" in target_colors or "Blue" in target_colors):
        return True
    return False

def detect_popup_reward_button_ocr(ocr_items, scale_y=1.0):
    """Mendeteksi tombol popup reward nyata berbasis teks OCR."""
    all_text = " ".join([it["text"].lower() for it in ocr_items])

    # Iklan Mahjong/AppLovin sering punya teks mirip reward: "Tarik Dana",
    # "Dapatkan Rp...", "Jumlah yang diterima...", dan tombol hijau "Pasang".
    # Jangan pernah dianggap tombol reward game karena itu membuka Play Store.
    ad_like_text = [
        "mahjong", "pasang", "tarik dana", "saldo rp", "saldo rp",
        "hasil akhir tidak dijamin", "jumlah yang dapat anda peroleh",
        "mengikuti aturan", "dipublikasikan di dalam aplikasi",
        "rp100.000", "rp300.000", "rp 100.000", "rp 300.000",
    ]
    if any(k in all_text for k in ad_like_text):
        return None

    modal_indicators = ["selamat", "hadiah", "congratulations", "reward", "koin", "bonus", "menang", "gandakan", "klaim", "koleksi"]
    has_reward_modal = any(k in all_text for k in modal_indicators)

    # 1. Deteksi langsung teks tombol klaim/reward. Batasi area y tombol asli.
    # Jangan pilih "Tidak Perlu"; sesuai instruksi, popup reward harus klik KLAIM.
    reward_keywords = ["bebas klik", "koleksi", "klaim", "claim", "collect", "gandakan", "dapatkan", "ambil", "terima"]
    for it in ocr_items:
        t = it["text"].lower()
        if any(kw in t for kw in reward_keywords) and int(760 * scale_y) <= it["cy"] <= int(1225 * scale_y):
            return it["cx"], it["cy"], f"Tombol Reward '{it['text']}'"

    # 2. Jika modal hadiah terbuka dan ada tombol 'Menarik' di bagian bawah (y > 900)
    if has_reward_modal and ("menarik" in all_text):
        for it in ocr_items:
            t = it["text"].lower()
            if "menarik" in t and it["cy"] > int(900 * scale_y):
                return it["cx"], it["cy"], "Tombol Menarik Modal Reward"

    return None

def normalize_reward_button_coord(cx, cy, scale_x=1.0, scale_y=1.0):
    """Koreksi koordinat tombol reward agar tidak jatuh ke HUD/bawah layar yang bukan tombol popup."""
    # Pada game ini tombol Klaim/Koleksi/Tonton biasanya di area 910..1215.
    # Deteksi visual kadang salah mengambil bar/teks bawah di y 1300+, jadi arahkan naik.
    min_y = int(910 * scale_y)
    max_y = int(1225 * scale_y)
    if cy > max_y:
        corrected_y = int(1085 * scale_y)
        corrected_x = int(360 * scale_x) if cx > int(420 * scale_x) or cx < int(260 * scale_x) else int(cx)
        return corrected_x, corrected_y, True
    if cy < min_y:
        return int(cx), min_y, True
    return int(cx), int(cy), False

def detect_popup_reward_button_fast(ocr_items, img, scale_x=1.0, scale_y=1.0):
    """Deteksi cepat tombol Klaim/Koleksi: OCR dulu, lalu visual tombol besar pada popup reward."""
    ocr_hit = detect_popup_reward_button_ocr(ocr_items, scale_y)
    if ocr_hit:
        return ocr_hit

    if img is None:
        return None

    all_text = " ".join([it["text"].lower() for it in ocr_items])
    ad_like_text = [
        "mahjong", "pasang", "tarik dana", "hasil akhir tidak dijamin",
        "jumlah yang dapat anda peroleh", "mengikuti aturan",
        "dipublikasikan di dalam aplikasi", "rp100.000", "rp300.000",
    ]
    if any(k in all_text for k in ad_like_text):
        return None

    modal_indicators = [
        "selamat", "hadiah", "congratulations", "reward", "koin", "bonus", "menang",
        "gandakan", "klaim", "koleksi", "claim", "collect", "dapatkan", "ambil", "terima"
    ]
    has_modal_hint = any(k in all_text for k in modal_indicators)

    h, w = img.shape[:2]
    x1, x2 = int(80 * scale_x), min(w, int(650 * scale_x))
    y1, y2 = int(720 * scale_y), min(h, int(1360 * scale_y))
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    # Tombol reward biasanya hijau/kuning/oranye/biru/ungu, terang, dan memanjang horizontal.
    bright_sat = ((hsv[:, :, 1] > 55) & (hsv[:, :, 2] > 120)).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 7))
    mask = cv2.morphologyEx(bright_sat, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for c in cnts:
        x, y, bw, bh = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        aspect = bw / float(bh) if bh else 0
        cx, cy = x1 + x + bw // 2, y1 + y + bh // 2
        # Mode visual tanpa OCR dibuat ketat: harus tombol besar, horizontal, dan cukup di tengah.
        min_w = int((130 if has_modal_hint else 190) * scale_x)
        min_area = (3500 if has_modal_hint else 7000) * scale_x * scale_y
        min_aspect = 2.0 if has_modal_hint else 2.35
        centered = int(130 * scale_x) <= cx <= int(590 * scale_x)
        if bw >= min_w and int(38 * scale_y) <= bh <= int(125 * scale_y) and area >= min_area and aspect >= min_aspect and centered:
            # Hindari tombol/header kecil atas dan HUD bawah. Klaim biasanya y 910..1225.
            if int(760 * scale_y) <= cy <= int(1285 * scale_y):
                click_cx, click_cy, corrected = normalize_reward_button_coord(cx, cy, scale_x, scale_y)
                # Kandidat terlalu bawah hanya diterima bila ada hint modal; kalau tidak, ini biasanya HUD/game bawah.
                if cy <= int(1225 * scale_y) or has_modal_hint:
                    candidates.append((click_cx, click_cy, bw, bh, area, cy, corrected))

    if candidates:
        # Prioritaskan posisi y tombol popup yang wajar, bukan objek paling bawah di HUD.
        candidates.sort(key=lambda v: (abs(v[1] - int(1060 * scale_y)), -v[4]))
        cx, cy, bw, bh, area, raw_cy, corrected = candidates[0]
        corr_txt = f", raw_y={raw_cy}->klik_y={cy}" if corrected else ""
        return cx, cy, f"Tombol Klaim/Koleksi Visual (area={int(area)}, ukuran={bw}x{bh}{corr_txt})"

    # 3. Deteksi darurat: kadang OCR gagal dan tombol Klaim hanya terbaca sebagai potongan warna di sisi kiri/kanan.
    #    Jika ada 2+ objek terang pada y yang hampir sama di area popup bawah, klik tengah baris itu.
    if has_modal_hint:
        edge_pieces = []
        for c in cnts:
            x, y, bw, bh = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            cx, cy = x1 + x + bw // 2, y1 + y + bh // 2
            if int(910 * scale_y) <= cy <= int(1225 * scale_y) and area >= 900 * scale_x * scale_y and bw >= int(24 * scale_x) and bh >= int(22 * scale_y):
                edge_pieces.append((cx, cy, area))
        if len(edge_pieces) >= 2:
            # Ambil cluster y terbawah yang paling sering; klik tengah layar pada y tersebut.
            edge_pieces.sort(key=lambda v: v[1], reverse=True)
            base_y = edge_pieces[0][1]
            same_row = [p for p in edge_pieces if abs(p[1] - base_y) <= int(45 * scale_y)]
            if len(same_row) >= 2:
                _, click_y, corrected = normalize_reward_button_coord(int(360 * scale_x), int(base_y), scale_x, scale_y)
                corr_txt = f", raw_y={base_y}->klik_y={click_y}" if corrected else f", y={base_y}"
                return int(360 * scale_x), int(click_y), f"Tombol Klaim/Koleksi Visual Darurat ({corr_txt})"

    # Fallback aman: hanya jika teks popup reward ada tetapi tombol tidak kebaca.
    if has_modal_hint:
        return int(360 * scale_x), int(1050 * scale_y), "Tombol Klaim/Koleksi Perkiraan Popup Reward"
    return None

def detect_dialog_close_x_button(img, scale_x=1.0, scale_y=1.0):
    """Mendeteksi tombol X di sudut dialog modal saat popup menutup papan game."""
    y1, y2 = int(200 * scale_y), int(650 * scale_y)
    x1, x2 = int(520 * scale_x), int(695 * scale_x)
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 130)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    min_dim, max_dim = int(16 * min(scale_x, scale_y)), int(80 * max(scale_x, scale_y))
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if min_dim <= w <= max_dim and min_dim <= h <= max_dim:
            patch = crop[y:y+h, x:x+w]
            if patch.std() > 18:
                candidates.append((x1 + x + w // 2, y1 + y + h // 2, patch.std()))
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        best = candidates[0]
        return best[0], best[1], "Tombol X Tutup Modal"
    return None

class CanSortRunner:
    def __init__(self, serial):
        self.serial = serial
        self.tag = f"[{self.serial}]"
        self.step_counter = 0
        self.width = 720
        self.height = 1640
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.ad_wait_done = False
        self.withdrawn_pending_ad = False
        self.ads_opened_count_since_growth = 0
        self.last_recorded_rp = 0
        try:
            state_p = Path('/Users/macbookair/soda_telegram_reporter_state.json')
            if state_p.exists():
                st_data = json.loads(state_p.read_text())
                if st_data.get('saldo_rp'):
                    self.last_recorded_rp = float(str(st_data['saldo_rp']).replace(',', '.'))
        except Exception:
            pass
        self.aggressive_ad_dismiss_count = 0
        # Counter saat semua botol depan tidak cocok dengan kotak tujuan.
        # Jika dibiarkan, bot standby selamanya; gunakan refresh/shuffle bawah tengah.
        self.no_match_streak = 0
        # Riwayat titik reward yang sudah disentuh agar tidak diklik berulang.
        self.recently_tapped_points = []

    def is_coord_recent(self, cx, cy, threshold_dist=35):
        """True bila titik ini baru saja disentuh dalam radius cooldown."""
        for old_x, old_y in self.recently_tapped_points:
            if abs(cx - old_x) <= threshold_dist * self.scale_x and abs(cy - old_y) <= threshold_dist * self.scale_y:
                return True
        return False

    def record_tapped_coord(self, cx, cy):
        """Mencatat titik sentuh dan menyimpan hanya riwayat terbaru."""
        self.recently_tapped_points.append((int(cx), int(cy)))
        if len(self.recently_tapped_points) > 12:
            self.recently_tapped_points.pop(0)

    def show_tap_marker(self, cx, cy, color="blue", duration=3.0, diameter=None):
        """Menampilkan marker di atas jendela scrcpy. Default: tap biru 3 detik."""
        if os.path.exists(TAP_MARKER_PATH):
            try:
                args = [TAP_MARKER_PATH, str(int(cx)), str(int(cy)), str(color), str(float(duration))]
                if diameter is not None:
                    args.append(str(int(diameter)))
                subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def show_detect_marker(self, cx, cy):
        """Marker hijau 5 detik untuk titik yang baru terdeteksi sebelum tap biru."""
        self.show_tap_marker(cx, cy, color="green", duration=5.0, diameter=66)

    def is_floating_reward_still_visible(self, bx, by, before_img=None, wait=0.08):
        """Validasi reward melayang: objek harus berubah/bergerak di sekitar titik agar bukan objek statis yang sudah lewat."""
        if before_img is None:
            before_img = self.get_screenshot()
        if before_img is None:
            return True
        time.sleep(wait)
        after_img = self.get_screenshot()
        if after_img is None:
            return True
        x1, x2 = max(0, int(bx - 65)), min(self.width, int(bx + 65))
        y1, y2 = max(0, int(by - 65)), min(self.height, int(by + 65))
        if x2 <= x1 or y2 <= y1:
            return False
        roi_before = before_img[y1:y2, x1:x2]
        roi_after = after_img[y1:y2, x1:x2]
        if roi_before.size == 0 or roi_after.size == 0:
            return False
        diff = cv2.absdiff(roi_before, roi_after)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        changed = int(np.sum(gray > 25))
        return changed >= 180

    def run_adb(self, cmd, timeout=5.0):
        try:
            res = subprocess.run(["adb", "-s", self.serial] + cmd, capture_output=True, text=True, timeout=timeout, check=False)
            return res.stdout.strip()
        except Exception:
            return ""

    def tap(self, x, y):
        self.show_tap_marker(x, y)
        subprocess.run(["adb", "-s", self.serial, "shell", f"input tap {int(x)} {int(y)}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def tap_burst(self, coords, delay=0.03):
        """Mengeklik banyak titik koordinat secara cepat/paralel via adb background input."""
        if not coords:
            return
        try:
            clean_coords = [(int(x), int(y)) for x, y in coords]
            # Tampilkan marker biru di scrcpy untuk semua titik yang diklik bot.
            for x, y in clean_coords:
                self.show_tap_marker(x, y)
            # Jangan pakai background "& wait" di shell Android: pada beberapa iklan
            # proses input bisa menggantung dan worker berhenti memproses iklan.
            # Pakai chain serial cepat; lebih stabil dan tetap cukup cepat.
            chained_cmd = (f"; sleep {float(delay):.3f}; ").join(
                [f"input tap {x} {y}" for x, y in clean_coords]
            )
            subprocess.run(["adb", "-s", self.serial, "shell", chained_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3.0)
        except Exception:
            for x, y in coords:
                self.tap(x, y)
                if delay > 0:
                    time.sleep(delay)

    def tap_reward_button_reliably(self, cx, cy):
        """Klik tombol Klaim/Koleksi secara reliabel.

        Burst paralel kadang tidak dianggap game sebagai tap valid, terutama saat popup
        masih animasi. Jadi untuk tombol reward dipakai tap berurutan cepat di tengah
        dan sekitar tombol. Semua titik tetap muncul marker biru.
        """
        sx, sy = self.scale_x, self.scale_y
        x = int(cx)
        y = int(cy)
        # Di Soda Pack tombol Klaim hijau kadang OCR mengambil teks di tengah,
        # tapi tap di teksnya tidak selalu diterima. Klik area tombol bagian atas
        # dan ikon video kiri juga, sedikit lebih NAIK dari hasil OCR.
        if int(930 * sy) <= y <= int(1105 * sy):
            button_cx = int(360 * sx)
            points = [
                (button_cx, y - int(34 * sy)),
                (button_cx, y - int(18 * sy)),
                (button_cx, y),
                (x, y - int(28 * sy)),
                (x, y),
                (int(260 * sx), y - int(24 * sy)),  # ikon video di kiri tombol
                (int(300 * sx), y - int(18 * sy)),
                (int(430 * sx), y - int(18 * sy)),
                (button_cx, y + int(18 * sy)),
            ]
        else:
            points = [
                (x, y),
                (x, y + int(10 * sy)),
                (x - int(45 * sx), y + int(8 * sy)),
                (x + int(45 * sx), y + int(8 * sy)),
                (x, y + int(24 * sy)),
                (x, y - int(18 * sy)),
                (x - int(85 * sx), y + int(12 * sy)),
                (x + int(85 * sx), y + int(12 * sy)),
            ]
        min_x, max_x = int(20 * sx), self.width - int(20 * sx)
        min_y, max_y = int(250 * sy), self.height - int(80 * sy)
        for tx, ty in points:
            tx = max(min_x, min(max_x, int(tx)))
            ty = max(min_y, min(max_y, int(ty)))
            self.tap(tx, ty)
            time.sleep(0.085)
        # Tambahan long-tap pendek di bagian atas tombol Klaim agar tidak miss.
        try:
            lx = max(min_x, min(max_x, int(360 * sx)))
            ly = max(min_y, min(max_y, int(y - 28 * sy)))
            subprocess.run(
                ["adb", "-s", self.serial, "shell", f"input swipe {lx} {ly} {lx} {ly} 140"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2.0
            )
        except Exception:
            pass

    def tap_moving_bubble_to_right(self, bx, by):
        """Klik gelembung/kado melayang dengan tracking agresif dan spam cepat.

        Bot langsung spam klik di posisi awal (pre-tap), lalu tracking 10 frame
        dengan cluster tap besar dan prediksi arah. Delay antar frame diminimalkan
        agar bubble tidak terlewat.
        """
        min_x = int(20 * self.scale_x)
        max_x = max(min_x, self.width - int(20 * self.scale_x))
        min_y = int(210 * self.scale_y)
        max_y = max(min_y, self.height - int(90 * self.scale_y))

        def clamp_pt(x, y):
            return (
                max(min_x, min(max_x, int(x))),
                max(min_y, min(max_y, int(y))),
            )

        tapped = []
        last_x, last_y = int(bx), int(by)

        # Pre-tap: langsung spam klik posisi awal secepat mungkin
        pre_offsets = [
            (0, 0), (-20, 0), (20, 0), (0, -20), (0, 20),
            (40, 0), (60, 0), (80, 0), (-40, 0),
        ]
        pre_points = []
        for dx, dy in pre_offsets:
            pre_points.append(clamp_pt(last_x + dx * self.scale_x, last_y + dy * self.scale_y))
        self.tap_burst(pre_points, delay=0.003)
        tapped.extend(pre_points)

        for frame_idx in range(10):
            img_now = self.get_screenshot()
            fresh = self.detect_floating_reward_bubble([], img_now) if img_now is not None else None
            if fresh:
                last_x, last_y, fresh_desc = fresh
                print(f"{self.tag} [🎯] Tracking gelembung frame {frame_idx+1}: {fresh_desc} -> tap sekitar ({last_x}, {last_y})", flush=True)

            # Cluster tap besar di sekitar posisi saat ini + prediksi kanan, kiri, atas, bawah
            offsets = [
                (0, 0), (-20, 0), (20, 0), (0, -20), (0, 20),
                (40, 0), (70, 0), (100, 0), (130, 0), (-40, 0), (-70, 0),
                (40, -20), (40, 20), (70, -20), (70, 20),
                (100, -20), (100, 20), (130, -20), (130, 20),
            ]
            points = []
            seen = set()
            for dx, dy in offsets:
                pt = clamp_pt(last_x + dx * self.scale_x, last_y + dy * self.scale_y)
                key = (pt[0] // 3, pt[1] // 3)
                if key not in seen:
                    seen.add(key)
                    points.append(pt)
            self.tap_burst(points, delay=0.003)
            tapped.extend(points)

            # Cek popup reward/iklan muncul (tanpa delay tambahan)
            check_img = self.get_screenshot()
            if check_img is not None:
                check_ocr = self.run_full_ocr(check_img)
                check_text = " ".join([it["text"].lower() for it in check_ocr])
                if any(k in check_text for k in ["klaim", "koleksi", "hadiah tunai", "tonton video", "dapatkan"]):
                    print(f"{self.tag} [✔] Gelembung tampaknya kena; popup reward/iklan muncul.", flush=True)
                    break

            # Prediksi pergerakan ke kanan yang lebih agresif
            last_x = min(max_x, last_x + int(80 * self.scale_x))

        return tapped

    def clean_restart_all_apps_and_game(self):
        """Menutup semua aplikasi latar belakang/iklan, membersihkan layar, dan membuka ulang game."""
        print(f"{self.tag} [!] Menjalankan antisipasi bottleneck: Menutup semua aplikasi & restart game...", flush=True)
        log_event("bottleneck", "Bottleneck Auto-Recovery (Restart Game & Tutup Apps)")
        pkgs_to_close = [
            "com.android.vending",
            "com.android.chrome",
            "com.android.browser",
            "com.transsion.phoenix",
            "com.heytap.browser",
            "com.opera.browser",
            "com.opera.mini.native",
            "com.google.android.youtube",
            "com.lemon.lvoverseas",
            "com.ss.android.ugc.trill",
            "com.zhiliaoapp.musically",
            "com.kwai.video",
            "com.facebook.katana",
            "com.facebook.orca",
            "com.instagram.android",
            "com.shopee.id",
            "com.lazada.android",
            "com.tokopedia.tkpd",
            PACKAGE_NAME,
        ]
        for pkg in pkgs_to_close:
            self.run_adb(["shell", "am", "force-stop", pkg])

        self.run_adb(["shell", "input", "keyevent", "3"])
        time.sleep(0.5)

        self.run_adb(["shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])
        time.sleep(0.5)
        self.ad_wait_done = False
        self.aggressive_ad_dismiss_count = 0
        self.ads_opened_count_since_growth = 0

    def bring_game_to_foreground(self):
        """Membawa aplikasi game kembali ke layar depan secara aman tanpa SecurityException."""
        self.run_adb(["shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])

    def press_back(self):
        # Marker biru di area tombol BACK agar aksi BACK juga terlihat di scrcpy.
        self.show_tap_marker(int(75 * self.scale_x), int(self.height - 75 * self.scale_y))
        subprocess.run(["adb", "-s", self.serial, "shell", "input keyevent 4"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def get_screenshot(self):
        try:
            res = subprocess.run(["adb", "-s", self.serial, "exec-out", "screencap -p"], capture_output=True, timeout=3.5)
            if len(res.stdout) > 0:
                img_arr = np.frombuffer(res.stdout, np.uint8)
                img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                if img is not None:
                    h, w = img.shape[:2]
                    self.height, self.width = h, w
                    self.scale_x = self.width / 720.0
                    self.scale_y = self.height / 1640.0
                    return img
        except Exception:
            pass
        return None

    def check_and_wake_device(self):
        power = self.run_adb(["shell", "dumpsys", "power"])
        if any(s in power for s in ["mWakefulness=Asleep", "mWakefulness=Dozing"]):
            print(f"{self.tag} [+] Membangunkan layar HP...", flush=True)
            self.run_adb(["shell", "input keyevent 224 && input keyevent 82"])
            time.sleep(0.5)
        return True

    def check_and_install_game_if_missing(self):
        """Mengecek apakah Soda Pack Puzzle terpasang di HP. Jika belum, otomatis download via Play Store."""
        installed = self.run_adb(["shell", "pm", "list", "packages"])
        if PACKAGE_NAME in installed:
            return True

        print(f"\n{self.tag} [!] Aplikasi Soda Pack Puzzle BELUM TERPASANG di HP ini!", flush=True)
        print(f"{self.tag} [+] Membuka Google Play Store untuk mencari & menginstal Soda Pack Puzzle...", flush=True)
        self.run_adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "market://search?q=Soda+Pack+Puzzle"])
        time.sleep(0.8)

        for _ in range(8):
            img = self.get_screenshot()
            if img is None:
                time.sleep(0.5)
                continue
            ocr_items = self.run_full_ocr(img)
            install_btn = None
            for it in ocr_items:
                t = it["text"].lower()
                if t in ["install", "instal", "pasang", "dapatkan", "unduh"] and (it["cy"] < int(550 * self.scale_y)):
                    install_btn = it
                    break
            if install_btn:
                print(f"{self.tag} [+] Menemukan tombol '{install_btn['text']}' di Play Store ({install_btn['cx']}, {install_btn['cy']})!", flush=True)
                print(f"{self.tag}     -> Mengeklik tombol Install sekarang...", flush=True)
                self.tap(install_btn["cx"], install_btn["cy"])
                break
            time.sleep(0.8)

        print(f"{self.tag} [⏳] Menunggu proses download & instalasi selesai...", flush=True)
        for wait_count in range(45):
            time.sleep(4.0)
            installed_now = self.run_adb(["shell", "pm", "list", "packages"])
            if PACKAGE_NAME in installed_now:
                print(f"{self.tag} [✔] Game Soda Pack Puzzle BERHASIL DIINSTAL di HP!", flush=True)
                time.sleep(0.5)
                self.bring_game_to_foreground()
                time.sleep(0.8)
                return True

            img = self.get_screenshot()
            if img is not None:
                ocr_items = self.run_full_ocr(img)
                for it in ocr_items:
                    if it["text"].lower() in ["buka", "open", "play", "mainkan"] and it["cy"] < int(550 * self.scale_y):
                        print(f"{self.tag} [✔] Menemukan tombol '{it['text']}' di Play Store. Membuka game sekarang...", flush=True)
                        self.tap(it["cx"], it["cy"])
                        time.sleep(0.8)
                        return True
        return False

    def get_foreground_focus(self):
        try:
            res = subprocess.run(["adb", "-s", self.serial, "shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"], capture_output=True, text=True, timeout=2.0, check=False)
            return res.stdout.strip()
        except Exception:
            return ""

    def detect_ad_countdown_seconds(self, img=None):
        """Mendeteksi countdown timer iklan di pojok kiri atas (misal: '53s left to be rewarded' / '16s left')."""
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return None
        ocr_items = self.run_full_ocr(img)
        for it in ocr_items:
            if it["cy"] < int(350 * self.scale_y):
                t = it["text"].lower()
                m = re.search(r'(\d{1,2})\s*s\s*(?:left|to be rewarded|remaining|sisa|detik)?', t, re.IGNORECASE)
                if m:
                    sec = int(m.group(1))
                    if 2 <= sec <= 90:
                        return sec
        return None

    def detect_and_click_ad_x_button(self, img=None):
        """Mendeteksi dan mengeklik tombol X / Tutup di pojok kanan atas pada layar iklan."""
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return False

        sx, sy = self.scale_x, self.scale_y
        ocr_items = self.run_full_ocr(img)

        # 1. Cek via OCR untuk karakter X / Tutup / Close / Skip di area atas (cy < 350 * sy)
        for it in ocr_items:
            if it["cy"] < int(350 * sy):
                t = it["text"].strip().lower()
                if t in ["x", "✕", "✖", "×", ">>", "skip", "close", "tutup"] or (len(t) == 1 and t in "xX+"):
                    print(f"{self.tag} [★] Menemukan tombol Tutup Iklan '{it['text']}' via OCR di ({it['cx']}, {it['cy']})! Mengeklik...", flush=True)
                    self.tap(it["cx"], it["cy"])
                    time.sleep(0.12)
                    return True

        # 2. Cek via deteksi kontur tombol X di pojok kanan atas (x: 580..710, y: 30..300)
        y1, y2 = int(30 * sy), int(300 * sy)
        x1, x2 = int(580 * sx), int(710 * sx)
        crop = img[y1:y2, x1:x2]
        if crop.size > 0:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 40, 140)
            cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            min_dim, max_dim = int(14 * min(sx, sy)), int(85 * max(sx, sy))
            candidates = []
            for cnt in cnts:
                x, y, w, h = cv2.boundingRect(cnt)
                if min_dim <= w <= max_dim and min_dim <= h <= max_dim:
                    patch = crop[y:y+h, x:x+w]
                    if patch.std() > 20:
                        candidates.append((x1 + x + w // 2, y1 + y + h // 2))
            if candidates:
                candidates.sort(key=lambda item: item[0], reverse=True)
                best_x, best_y = candidates[0]
                print(f"{self.tag} [★] Menemukan tombol X di pojok kanan atas di ({best_x}, {best_y})! Mengeklik...", flush=True)
                self.tap(best_x, best_y)
                time.sleep(0.12)
                return True

        # 3. Fallback tap burst semua titik X umum di kanan atas & letterbox
        top_right_x_pts = [
            (int(665 * sx), int(70 * sy)),
            (int(665 * sx), int(115 * sy)),
            (int(665 * sx), int(160 * sy)),
            (int(665 * sx), int(250 * sy)),
            (int(640 * sx), int(80 * sy)),
            (int(675 * sx), int(85 * sy)),
            (int(650 * sx), int(240 * sy)),
            (int(55 * sx), int(70 * sy)),
            (int(55 * sx), int(115 * sy)),
            (int(55 * sx), int(250 * sy))
        ]
        self.tap_burst(top_right_x_pts, delay=0.03)
        return True

    def click_ad_x_if_ready(self, img=None):
        """Klik tombol X/Close/Skip iklan hanya bila benar-benar terlihat.
        Berbeda dari detect_and_click_ad_x_button(), fungsi ini TIDAK melakukan
        fallback tap-burst agar aman dipanggil saat iklan masih countdown.
        """
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return False

        sx, sy = self.scale_x, self.scale_y
        ocr_items = self.run_full_ocr(img)

        # OCR tombol close/skip di area atas. Jangan ambil X search bar bawah.
        for it in ocr_items:
            t = it["text"].strip().lower()
            if it["cy"] < int(350 * sy) and it["cx"] > int(470 * sx):
                if t in ["x", "✕", "✖", "×", "skip", "close", "tutup", ">>"] or (len(t) == 1 and t in "xX+"):
                    print(f"{self.tag} [✔] Tombol X/Skip iklan sudah muncul di ({it['cx']}, {it['cy']}). Klik sekarang, tidak menunggu countdown lagi.", flush=True)
                    self.tap(it["cx"], it["cy"])
                    time.sleep(0.35)
                    return True

        # Deteksi visual tombol X pojok kanan atas (contoh AdMob/AppLovin).
        y1, y2 = int(25 * sy), int(320 * sy)
        x1, x2 = int(575 * sx), int(715 * sx)
        crop = img[max(0, y1):min(self.height, y2), max(0, x1):min(self.width, x2)]
        if crop.size > 0:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 45, 150)
            cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            min_dim, max_dim = int(16 * min(sx, sy)), int(90 * max(sx, sy))
            candidates = []
            for cnt in cnts:
                x, y, w, h = cv2.boundingRect(cnt)
                area = cv2.contourArea(cnt)
                if min_dim <= w <= max_dim and min_dim <= h <= max_dim and area >= 40 * sx * sy:
                    patch = crop[y:y+h, x:x+w]
                    if patch.size and patch.std() > 18:
                        candidates.append((x1 + x + w // 2, y1 + y + h // 2, w, h, area))
            if candidates:
                candidates.sort(key=lambda item: (item[0], -abs(item[2] - item[3])), reverse=True)
                best_x, best_y = candidates[0][0], candidates[0][1]
                print(f"{self.tag} [✔] Tombol X iklan terdeteksi di pojok ({best_x}, {best_y}). Klik sekarang, tidak menunggu countdown lagi.", flush=True)
                self.tap(best_x, best_y)
                time.sleep(0.35)
                return True

        return False

    def close_ad_screen_thoroughly(self):
        """Menutup iklan secara menyeluruh: BACK -> Jika muncul peringatan (Continue vs Close It) klik CONTINUE -> Endcard X -> Kembali Game."""
        sx, sy = self.scale_x, self.scale_y
        self.press_back()
        time.sleep(0.18)

        img = self.get_screenshot()
        if img is not None:
            ocr_items = self.run_full_ocr(img)
            # 1. Jika muncul dialog peringatan (misal: 'Confirm to close?', 'You will not be rewarded', dsb)
            # dan ada tombol Continue / Continui / Lanjutkan, klik CONTINUE!
            for it in ocr_items:
                t = it["text"].lower()
                if any(k in t for k in ["continue", "continui", "continu", "lanjutkan", "resume"]) and it["cy"] > int(200 * sy):
                    print(f"{self.tag} [+] Terdeteksi dialog peringatan iklan. Mengeklik 'Continue' di ({it['cx']}, {it['cy']})...", flush=True)
                    self.tap_burst([(it["cx"], it["cy"]), (it["cx"], it["cy"])], delay=0.01)
                    time.sleep(0.45)
                    break

        # 2. Tap titik tombol X pojok kanan atas & kiri atas (posisi umum endcard / banner close)
        close_points = [
            (int(665 * sx), int(70 * sy)),
            (int(665 * sx), int(115 * sy)),
            (int(635 * sx), int(75 * sy)),
            (int(55 * sx), int(70 * sy)),
            (int(55 * sx), int(115 * sy))
        ]
        self.detect_and_click_ad_x_button(img)
        # Close dipercepat: semua kandidat X diklik burst dan semua titik diberi marker biru.
        self.tap_burst(close_points, delay=0.01)
        time.sleep(0.18)

        # Setelah tombol X, tetap kirim BACK agar endcard/halaman iklan benar-benar tertutup
        # sebelum kembali ke halaman botol.
        print(f"{self.tag} [+] Tombol X/endcard sudah diproses. Mengirim BACK final untuk kembali ke halaman botol...", flush=True)
        self.press_back()
        time.sleep(0.15)

        # Jika activity iklan masih tampil setelah BACK pertama, kirim BACK sekali lagi.
        focus_after_back = self.get_foreground_focus().lower()
        ad_activity_keywords = [
            "rewardvideo", "adactivity", "applovin", "mbridge", "mintegral", "audiencenetwork",
            "unity3d", "adcolony", "vungle", "ironsource", "pangle", "bytedance"
        ]
        if "com.android.vending" in focus_after_back:
            print(f"{self.tag} [!] Play Store masih terbuka setelah iklan. Force-stop Play Store...", flush=True)
            self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
            time.sleep(0.25)

        if any(pkg in focus_after_back for pkg in ["com.android.chrome", "com.android.browser", "com.transsion.phoenix", "com.heytap.browser", "com.opera.browser", "com.lemon.lvoverseas", "com.ss.android.ugc.trill", "com.zhiliaoapp.musically"]):
            print(f"{self.tag} [!] Browser masih terbuka setelah iklan. Force-stop semua browser...", flush=True)
            for pkg in ["com.android.chrome", "com.android.browser", "com.transsion.phoenix", "com.heytap.browser", "com.opera.browser", "com.lemon.lvoverseas", "com.ss.android.ugc.trill", "com.zhiliaoapp.musically"]:
                self.run_adb(["shell", "am", "force-stop", pkg])
            time.sleep(0.25)

        if any(keyword in focus_after_back for keyword in ad_activity_keywords):
            print(f"{self.tag} [+] Layar iklan masih aktif setelah BACK pertama. Mengirim BACK kedua...", flush=True)
            self.press_back()
            time.sleep(0.8)

        focus_after_second = self.get_foreground_focus().lower()
        if any(keyword in focus_after_second for keyword in ad_activity_keywords):
            print(f"{self.tag} [!] Iklan masih macet setelah ditunggu + X + BACK. Force-stop semua aplikasi iklan/game lalu buka ulang game...", flush=True)
            for pkg in [
                "com.android.vending", "com.android.chrome", "com.android.browser",
                "com.transsion.phoenix", "com.heytap.browser", "com.opera.browser",
                PACKAGE_NAME,
            ]:
                self.run_adb(["shell", "am", "force-stop", pkg])
            time.sleep(0.8)
            self.bring_game_to_foreground()
            time.sleep(0.8)
            self.ad_wait_done = False
            self.aggressive_ad_dismiss_count = 0
            return

        # Khusus endcard Mahjong/AppLovin: sering tidak punya X yang valid dan
        # tombol hijau "Pasang" membuka Play Store. Kalau masih terlihat setelah
        # upaya normal, reset game saja agar kembali bersih.
        img_after = self.get_screenshot()
        stubborn_text = ""
        if img_after is not None:
            stubborn_text = " ".join([it["text"].lower() for it in self.run_full_ocr(img_after)])
        mahjong_stubborn = any(k in stubborn_text for k in [
            "mahjong", "pasang", "tarik dana", "hasil akhir tidak dijamin",
            "jumlah yang dapat anda peroleh", "mengikuti aturan", "rp100.000", "rp300.000",
            "bpjs777", "bandar pemain", "judi slot", "game populer", "anti boncos", "wede", "brimo"
        ])
        if mahjong_stubborn or "com.android.vending" in focus_after_second:
            print(f"{self.tag} [!] Iklan Mahjong/AppLovin bandel terdeteksi. Force-stop Play Store + game, lalu buka ulang game...", flush=True)
            self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
            self.run_adb(["shell", "am", "force-stop", PACKAGE_NAME])
            time.sleep(0.8)
            self.bring_game_to_foreground()
            time.sleep(0.6)
            self.ad_wait_done = False
            self.aggressive_ad_dismiss_count = 0
            return

        self.bring_game_to_foreground()
        time.sleep(0.25)

    def read_current_header_rp(self, img=None):
        """Membaca nilai saldo Rp di header atas saat ini via OCR."""
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return None
        ocr = self.run_full_ocr(img)
        sy = self.scale_y
        for item in ocr:
            cy = item.get("cy", 0)
            if int(40 * sy) <= cy <= int(160 * sy):
                t = item.get("text", "").replace("o", "0").replace("O", "0").replace("I", "1").replace("l", "1")
                m = re.search(r"Rp\s*([0-9]+)", t, re.IGNORECASE)
                if m:
                    try:
                        return float(m.group(1))
                    except ValueError:
                        pass
        return None

    def verify_saldo_growth_after_ad(self, saldo_before, reason, elapsed_ad):
        """Skip verifikasi saldo - iklan bukan sumber utama reward. Langsung lanjut main."""
        # Iklan tidak reliabel memberikan reward, jadi skip verifikasi dan langsung lanjut main
        print(f"{self.tag} [→] Skip verifikasi saldo pasca-iklan. Lanjut fokus ke gameplay (bubble & klaim)...", flush=True)
        return

    def send_ad_finished_notification(self, reason, elapsed_sec):
        """Kirim notifikasi Telegram saat iklan selesai ditonton beserta durasinya."""
        now_time = time.strftime("%Y-%m-%d %H:%M:%S WIB")
        dur_str = f"{elapsed_sec} detik" if elapsed_sec < 60 else f"{elapsed_sec // 60} menit {elapsed_sec % 60} detik"
        saldo_info = ""
        try:
            state_p = Path('/Users/macbookair/soda_telegram_reporter_state.json')
            if state_p.exists():
                st_data = json.loads(state_p.read_text())
                if st_data.get('saldo_rp'):
                    saldo_info = f"\n💰 <b>Saldo saat ini:</b> Rp {st_data['saldo_rp']}"
                if st_data.get('level'):
                    saldo_info += f"\n🎮 <b>Level:</b> {st_data['level']}"
        except Exception:
            pass

        fin_msg = (
            f"✅ <b>IKLAN SELESAI DITONTON</b>\n"
            f"🕐 <code>{now_time}</code>\n\n"
            f"⏱️ <b>Durasi nonton iklan:</b> <b>{dur_str}</b>\n"
            f"📺 <b>Jenis iklan:</b> {html.escape(reason)}"
            f"{saldo_info}\n"
            f"📱 <b>Device:</b> <code>{self.serial}</code>\n"
            f"🎮 <i>Bot kembali memainkan game / mengeklaim hadiah.</i>"
        )
        send_telegram_async(fin_msg)
        log_event("selesai_iklan", f"Selesai Iklan ({dur_str})", {"duration": elapsed_sec, "reason": reason})

    def wait_ad_and_close_ad(self, reason="Iklan Video Reward"):
        """Menunggu iklan/reward. Jika timer iklan di pojok kiri atas terdeteksi, waktu tunggu disamakan."""
        if "re-wait" not in reason.lower():
            # Cek apakah sudah pernah buka iklan sebelumnya tanpa penambahan saldo (Bottleneck Ad-Loop)
            if getattr(self, 'ads_opened_count_since_growth', 0) >= 1:
                now_time = time.strftime("%Y-%m-%d %H:%M:%S WIB")
                last_saldo = self.last_recorded_rp or "-"
                try:
                    state_p = Path('/Users/macbookair/soda_telegram_reporter_state.json')
                    if state_p.exists():
                        st_data = json.loads(state_p.read_text())
                        if st_data.get('saldo_rp'):
                            last_saldo = st_data['saldo_rp']
                except Exception:
                    pass

                print(f"\n{self.tag} [!] BOTTLENECK TERDETEKSI: Iklan terbuka berulang tanpa penambahan saldo (Saldo tetap Rp {last_saldo}). Menjalankan antisipasi bottleneck...", flush=True)
                bottleneck_msg = (
                    f"⚠️ <b>BOTTLENECK: IKLAN BERULANG TANPA SALDO BERTAMBAH</b>\n"
                    f"🕐 <code>{now_time}</code>\n\n"
                    f"⏱️ <b>Status:</b> Iklan terbuka kembali padahal saldo belum bertambah (tetap <b>Rp {last_saldo}</b>)!\n"
                    f"📺 <b>Pemicu Iklan:</b> {html.escape(reason)}\n"
                    f"📱 <b>Device:</b> <code>{self.serial}</code>\n\n"
                    f"🔄 <i>Antisipasi Bottleneck: Menutup seluruh aplikasi & membuka ulang game Soda Pack...</i>"
                )
                send_telegram_async(bottleneck_msg)
                self.clean_restart_all_apps_and_game()
                return

            self.ads_opened_count_since_growth = 1

            now_time = time.strftime("%Y-%m-%d %H:%M:%S WIB")
            saldo_info = ""
            try:
                state_p = Path('/Users/macbookair/soda_telegram_reporter_state.json')
                if state_p.exists():
                    st_data = json.loads(state_p.read_text())
                    if st_data.get('saldo_rp'):
                        saldo_info = f"\n💰 <b>Saldo saat ini:</b> Rp {st_data['saldo_rp']}"
                    if st_data.get('level'):
                        saldo_info += f"\n🎮 <b>Level:</b> {st_data['level']}"
            except Exception:
                pass
            ad_msg = (
                f"🎬 <b>MEMBUKA IKLAN</b>\n"
                f"🕐 <code>{now_time}</code>\n\n"
                f"📺 <b>Alasan:</b> {html.escape(reason)}"
                f"{saldo_info}\n"
                f"📱 <b>Device:</b> <code>{self.serial}</code>\n"
                f"⏳ <i>Bot sedang menonton iklan dan memantau tombol tutup / X...</i>"
            )
            send_telegram_async(ad_msg)
            log_event("nonton_iklan", f"Nonton Iklan ({reason})", {"reason": reason})

        saldo_before = self.last_recorded_rp or 0
        if not saldo_before:
            current_read = self.read_current_header_rp()
            if current_read:
                saldo_before = current_read
                self.last_recorded_rp = current_read

        start_ad_time = time.time()
        try:
            self._wait_ad_loop(reason)
        finally:
            if "re-wait" not in reason.lower():
                elapsed_ad = max(1, int(time.time() - start_ad_time))
                self.send_ad_finished_notification(reason, elapsed_ad)
                self.verify_saldo_growth_after_ad(saldo_before, reason, elapsed_ad)

    def _wait_ad_loop(self, reason):
        print(f"\n{self.tag} [⏳] {reason} terdeteksi! Anti bot-detect 5 detik lalu auto BACK ke game...", flush=True)
        ad_start_time = time.time()
        last_anti_detect_tap = 0

        # Anti Bot-Detect: Tap random selama 10 detik
        while time.time() - ad_start_time < 5.0:
            elapsed_ad = time.time() - ad_start_time
            current_time = time.time()
            
            if current_time - last_anti_detect_tap >= 2.0:
                import random
                sx, sy = self.scale_x, self.scale_y
                safe_x = random.randint(int(200 * sx), int(520 * sx))
                safe_y = random.randint(int(400 * sy), int(1000 * sy))
                print(f"{self.tag} [🎭] Anti bot-detect: tap random di ({safe_x}, {safe_y})...", flush=True)
                self.tap(safe_x, safe_y)
                last_anti_detect_tap = current_time
            
            time.sleep(0.5)

        print(f"{self.tag} [✔] Anti bot-detect selesai (5 detik). Auto BACK ke game...", flush=True)
        
        # Tekan BACK untuk keluar dari iklan
        self.press_back()
        time.sleep(0.5)
        
        # Cek apakah sudah kembali ke halaman botol
        focus = self.get_foreground_focus().lower()
        img = self.get_screenshot()
        
        ad_activity_keywords = [
            "rewardvideo", "adactivity", "applovin", "mbridge", "mintegral", "audiencenetwork",
            "unity3d", "adcolony", "vungle", "ironsource", "pangle", "bytedance"
        ]
        
        # Jika masih di iklan atau belum kembali ke game, anggap bottleneck
        if any(k in focus for k in ad_activity_keywords) or PACKAGE_NAME not in focus:
            print(f"{self.tag} [!] BACK pertama gagal kembali ke game. Coba BACK kedua...", flush=True)
            self.press_back()
            time.sleep(0.5)
            focus = self.get_foreground_focus().lower()
            img = self.get_screenshot()
        
        # Cek lagi setelah BACK kedua
        if img is not None and self.detect_shelf_cans(img) and PACKAGE_NAME in focus:
            print(f"{self.tag} [✔] Berhasil kembali ke halaman botol setelah iklan!", flush=True)
            return
        
        # Jika masih belum bisa kembali, anggap bottleneck
        now_time = time.strftime("%Y-%m-%d %H:%M:%S WIB")
        print(f"\n{self.tag} [!] BOTTLENECK: Tidak bisa kembali ke halaman botol setelah iklan! Restart game...", flush=True)
        bottleneck_msg = (
            f"⚠️ <b>BOTTLENECK: TIDAK BISA KEMBALI KE GAME SETELAH IKLAN</b>\n"
            f"🕐 <code>{now_time}</code>\n\n"
            f"⏱️ <b>Status:</b> Setelah 10 detik anti bot-detect + BACK, tidak bisa kembali ke halaman botol!\n"
            f"📺 <b>Jenis iklan:</b> {html.escape(reason)}\n"
            f"📱 <b>Device:</b> <code>{self.serial}</code>\n\n"
            f"🔄 <i>Menjalankan antisipasi bottleneck: Restart game...</i>"
        )
        send_telegram_async(bottleneck_msg)
        self.clean_restart_all_apps_and_game()

    def handle_app_focus_and_ads(self):
        focus = self.get_foreground_focus()

        # 1. Google Play Store terbuka oleh iklan -> Tutup paksa Play Store & kembali ke game
        if "com.android.vending" in focus:
            print(f"{self.tag} [!] Google Play Store terbuka oleh iklan! Menutup paksa Play Store & kembali ke game...", flush=True)
            self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
            self.press_back()
            time.sleep(0.3)
            self.bring_game_to_foreground()
            time.sleep(0.8)
            self.ad_wait_done = False
            return False

        # 1b. Browser/Chrome terbuka oleh iklan -> tutup paksa semua browser umum.
        browser_pkgs = [
            "com.android.chrome", "com.android.browser", "com.transsion.phoenix",
            "com.heytap.browser", "com.opera.browser", "org.mozilla.firefox",
            # Aplikasi yang sering dibuka oleh iklan redirect/endcard.
            "com.lemon.lvoverseas", "com.ss.android.ugc.trill", "com.zhiliaoapp.musically",
            "com.snackvideo", "com.kwai.video",
        ]
        if any(pkg in focus for pkg in browser_pkgs):
            print(f"{self.tag} [!] Browser/Chrome terbuka oleh iklan! Force-stop browser & kembali ke game...", flush=True)
            for pkg in browser_pkgs:
                self.run_adb(["shell", "am", "force-stop", pkg])
            self.press_back()
            time.sleep(0.3)
            self.bring_game_to_foreground()
            time.sleep(0.5)
            self.ad_wait_done = False
            return False

        # 2. Periksa Dialog Konfirmasi Penarikan Sebelum Memeriksa Iklan (Anti-Salah Deteksi Iklan)
        img = self.get_screenshot()
        if img is not None:
            ocr_quick = self.run_full_ocr(img)
            quick_text = " ".join([it["text"].lower() for it in ocr_quick])

            # Cek jika layar Chrome terbuka
            if any(k in quick_text for k in ["selamat datang di chrome", "persyaratan layanan", "google chrome"]):
                print(f"{self.tag} [!] Layar browser Chrome terdeteksi! Menutup paksa Chrome & kembali ke game...", flush=True)
                self.run_adb(["shell", "am", "force-stop", "com.android.chrome"])
                self.press_back()
                time.sleep(0.3)
                self.bring_game_to_foreground()
                time.sleep(0.8)
                return False
            has_konfirmasi = any(any(k in it["text"].lower() for k in ["konfirmasi", "confirm", "setuju"]) and it["cy"] > int(450 * self.scale_y) for it in ocr_quick)
            has_withdr_text = any(k in quick_text for k in ["informasi sudah benar", "pastikan informasi", "periksa akun", "nomor rekening", "nomor akun", "pilih metode"])
            if has_konfirmasi or has_withdr_text:
                print(f"{self.tag} [★] Terdeteksi dialog Konfirmasi Penarikan di layar (Bukan Iklan)! Melanjutkan alur penarikan...", flush=True)
                self.handle_withdrawal_modal_flow()
                return False

        # 3. Iklan Video / Interstitial Ad (Khusus SDK Iklan Nyata)
        ad_keywords = ["mbrewardvideoactivity", "applovinfullscreenactivity", "adactivity", "companionadactivity", "bigo", "bytedance", "pangle", "unity3d", "applovin", "adcolony", "kwad", "mbridge", "vungle", "ironsource", "mintegral", "rewardvideo", "audiencenetwork"]
        is_ad_activity = any(k in focus.lower() for k in ad_keywords)

        if is_ad_activity:
            if not self.ad_wait_done:
                self.wait_ad_and_close_ad("Iklan Video / Interstitial")
                self.ad_wait_done = True
                self.aggressive_ad_dismiss_count = 0
            else:
                self.aggressive_ad_dismiss_count += 1
                if self.aggressive_ad_dismiss_count >= 3:
                    print(f"\n{self.tag} [!] Layar iklan masih aktif berulang ({self.aggressive_ad_dismiss_count}x). Kembali menunggu iklan 10 detik sampai selesai...", flush=True)
                    self.wait_ad_and_close_ad("Iklan Masih Berjalan (Re-wait 10s)")
                    self.aggressive_ad_dismiss_count = 0
                    return False

                print(f"{self.tag} [!] Layar iklan masih aktif ({self.aggressive_ad_dismiss_count}x). Memeriksa timer & tombol X kanan atas...", flush=True)

                img = self.get_screenshot()
                # Cek apakah ada countdown timer di pojok atas
                remaining_sec = self.detect_ad_countdown_seconds(img)
                if remaining_sec and remaining_sec > 1:
                    print(f"{self.tag} [⏳] Terdeteksi timer iklan: '{remaining_sec}s' di pojok atas! Menunggu {remaining_sec} detik sampai selesai...", flush=True)
                    for rem in range(remaining_sec, 0, -2):
                        print(f"{self.tag}    -> Menunggu sisa timer iklan: {rem} detik...", flush=True)
                        time.sleep(2)
                    time.sleep(0.5)
                    self.aggressive_ad_dismiss_count = 0

                # Periksa dan klik tombol X di kanan atas
                self.detect_and_click_ad_x_button(img)
                self.close_ad_screen_thoroughly()
            return False

        # Reset status tunggu iklan saat game normal kembali aktif
        self.ad_wait_done = False
        self.aggressive_ad_dismiss_count = 0
        self.withdrawn_pending_ad = False

        # 3. Jika aplikasi Soda Pack Puzzle sama sekali tidak di layar
        if PACKAGE_NAME not in focus:
            print(f"{self.tag} [!] Soda Pack Puzzle tidak di layar. Membuka aplikasi...", flush=True)
            self.bring_game_to_foreground()
            time.sleep(0.8)
            return False

        return True

    def run_full_ocr(self, img, crop=None):
        if not os.path.exists(OCR_HELPER_PATH) or img is None:
            return []
        if crop is not None:
            x1, y1, x2, y2 = crop
            crop_img = img[y1:y2, x1:x2]
            off_x, off_y = x1, y1
            h_crop, w_crop = crop_img.shape[:2]
        else:
            crop_img = img
            off_x, off_y = 0, 0
            h_crop, w_crop = self.height, self.width

        tmp_path = f"/tmp/can_sort_ocr_{self.serial}.png"
        cv2.imwrite(tmp_path, crop_img)
        try:
            out = subprocess.check_output([OCR_HELPER_PATH, tmp_path], stderr=subprocess.DEVNULL, timeout=2.5).decode("utf-8")
            items = []
            for line in out.strip().splitlines():
                parts = line.split("|")
                if len(parts) == 2:
                    text = parts[0].strip()
                    coords = [float(x) for x in parts[1].split(",")]
                    cx = int((coords[0] + coords[2] / 2.0) * w_crop) + off_x
                    cy = int((1.0 - (coords[1] + coords[3] / 2.0)) * h_crop) + off_y
                    items.append({"text": text, "cx": cx, "cy": cy})
            return items
        except Exception:
            return []

    def is_dana_selected(self, img, ocr_items):
        for it in ocr_items:
            t = it["text"].lower()
            if ("→ dana" in t or "•dana" in t or "• dana" in t) and (int(400*self.scale_y) < it["cy"] < int(800*self.scale_y)):
                return True
        if img is not None:
            y1, y2 = int(600 * self.scale_y), int(730 * self.scale_y)
            x1, x2 = int(380 * self.scale_x), int(660 * self.scale_x)
            dana_roi = img[y1:y2, x1:x2]
            if dana_roi.size > 0:
                hsv = cv2.cvtColor(dana_roi, cv2.COLOR_BGR2HSV)
                red_pixels = np.sum(((hsv[:, :, 0] < 12) | (hsv[:, :, 0] > 168)) & (hsv[:, :, 1] > 80) & (hsv[:, :, 2] > 80))
                if red_pixels > 40:
                    return True
        return False

    def find_modal_confirm_button(self, img, ocr_items):
        """Mencari tombol Konfirmasi/Confirm/Kirim/OK pada modal penarikan via fuzzy OCR & Green Button CV."""
        sx, sy = self.scale_x, self.scale_y

        # 1. Deteksi berbasis teks OCR (Fuzzy match)
        kw = ["konfirm", "kontirm", "firmasi", "irmasi", "confirm", "setuju", "kirim", "mengetahui", "mengerti", "paham"]
        candidates = []
        for it in ocr_items:
            t = it["text"].lower().strip()
            cy, cx = it["cy"], it["cx"]
            if any(ig in t for ig in ["semakin", "aturan", "perkiraan", "diterima", "tingkat", "level"]):
                continue
            if int(950 * sy) <= cy <= int(1350 * sy):
                if any(k in t for k in kw) or t in ["ok", "ya", "lanjut", "tarik"]:
                    candidates.append((cx, cy, f"Tombol '{it['text']}'"))

        if candidates:
            candidates.sort(key=lambda c: c[1], reverse=True)
            return candidates[0]

        # 2. Deteksi berbasis Computer Vision Kontur Tombol Hijau
        if img is not None:
            y1, y2 = int(950 * sy), int(1350 * sy)
            x1, x2 = int(80 * sx), int(640 * sx)
            crop = img[y1:y2, x1:x2]
            if crop.size > 0:
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                green_mask = (hsv[:,:,0] >= 35) & (hsv[:,:,0] <= 85) & (hsv[:,:,1] >= 60) & (hsv[:,:,2] >= 70)
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5))
                clean_mask = cv2.morphologyEx(green_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
                cnts, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                btn_cnts = []
                for c in cnts:
                    x, y, w, h = cv2.boundingRect(c)
                    area = cv2.contourArea(c)
                    if (140 * sx <= w <= 560 * sx) and (30 * sy <= h <= 150 * sy) and (area >= 3500 * sx * sy):
                        btn_cnts.append((x1 + x + w // 2, y1 + y + h // 2, f"Tombol Hijau CV ({w}x{h})"))
                if btn_cnts:
                    btn_cnts.sort(key=lambda b: b[1], reverse=True)
                    return btn_cnts[0]

        return None

    def handle_withdrawal_modal_flow(self):
        """Alur penarikan saldo ke DANA saat =Rp > MIN_WITHDRAWAL_RP."""
        print(f"\n{self.tag} =======================================================", flush=True)
        print(f"{self.tag}       [★] MEMULAI ALUR PENARIKAN DANA OTOMATIS        ", flush=True)
        print(f"{self.tag} =======================================================", flush=True)
        sx, sy = self.scale_x, self.scale_y

        for cycle in range(25):
            time.sleep(0.9)
            img = self.get_screenshot()
            if img is None:
                break
            ocr_items = self.run_full_ocr(img)
            all_text_lower = " ".join([it["text"].lower() for it in ocr_items])

            # 0. Jika saldo sudah Rp0 / penarikan selesai/gagal minimum, segera tutup halaman penarikan.
            # Pada layar gagal, OCR sering membaca Rp0 sebagai "RpO/ERpO" dan muncul teks
            # "Jumlah penarikan minimum adalah Rp50". Jangan terus menekan Konfirmasi.
            norm_text = all_text_lower.replace("o", "0").replace("Ｏ", "0")
            min_withdraw_error = any(k in all_text_lower for k in [
                "jumlah penarikan minimum",
                "menghasilkan lebih banyak",
                "minimum adalah rp",
                "anda perlu",
            ])
            is_saldo_zero = (
                min_withdraw_error
                or any(k in norm_text for k in ["diterima: rp0", "diterima: rp 0", "kurang rp", "~rp0", "~rp 0", "dana rp0", "erp0", "rp0"])
                or ("dana" in norm_text and any(r in norm_text for r in ["rp0", "rp 0"]) and any(p in norm_text for p in ["pastikan", "informasi", "periksa", "akun penarikan"]))
            )
            if is_saldo_zero and any(k in all_text_lower for k in ["pilih metode", "saldo saya", "penukaran", "menarik", "tarik", "pastikan", "akun penarikan"]):
                confirm_once = self.find_modal_confirm_button(img, ocr_items)
                if confirm_once:
                    c_x, c_y, c_desc = confirm_once
                    print(f"{self.tag} [✔] Saldo penarikan Rp0 / minimum belum terpenuhi. Klik {c_desc} sekali di ({c_x}, {c_y}), lalu keluar halaman Tarik...", flush=True)
                    self.tap(c_x, c_y)
                    time.sleep(0.8)
                else:
                    print(f"{self.tag} [✔] Saldo penarikan Rp0 / minimum belum terpenuhi. Menutup halaman Tarik...", flush=True)
                self.press_back()
                time.sleep(0.6)
                self.withdrawn_pending_ad = True
                return

            # 1. Jika soft keyboard terbuka menutupi layar, tekan BACK untuk sembunyikan keyboard
            if any(k in all_text_lower for k in ["?123", "indonesia", "q w", "z x"]) or (any(it["text"] in ["1","2","3","4","5"] and it["cy"] > int(1000 * sy) for it in ocr_items)):
                print(f"{self.tag} [+] Keyboard virtual terdeteksi terbuka. Menutup keyboard...", flush=True)
                self.press_back()
                time.sleep(0.6)
                img = self.get_screenshot()
                ocr_items = self.run_full_ocr(img)
                all_text_lower = " ".join([it["text"].lower() for it in ocr_items])

            # 1b. Jika muncul form kosong (misal OVO belum diisi: 'masukkan hp', 'silakan masukkan nama'), tekan BACK untuk kembali ke DANA
            if any(k in all_text_lower for k in ["masukkan hp", "silakan masukkan", "mulai 08"]):
                print(f"{self.tag} [!] Terdeteksi form akun kosong (bukan DANA terisi). Menekan BACK untuk kembali...", flush=True)
                self.press_back()
                time.sleep(0.6)
                continue

            # 2. PRIORITAS UTAMA: Cari dan klik tombol Konfirmasi (via OCR atau Green Button CV)
            confirm_btn = self.find_modal_confirm_button(img, ocr_items)
            if confirm_btn:
                k_cx, k_cy, k_desc = confirm_btn
                print(f"{self.tag} [+] [Konfirmasi Penarikan ({cycle+1})] Menemukan {k_desc} di ({k_cx}, {k_cy}). Mengeklik Konfirmasi...", flush=True)
                self.tap(k_cx, k_cy)
                time.sleep(0.5)
                continue

            # 3. Pilihan metode DANA
            if "pilih metode" in all_text_lower or ("ovo" in all_text_lower and "dana" in all_text_lower):
                print(f"\n{self.tag} [+] Terdeteksi halaman Pilih Metode Penarikan (Opsi OVO & DANA):", flush=True)
                dana_btn = None
                for it in ocr_items:
                    if "dana" in it["text"].lower() and int(500 * sy) < it["cy"] < int(800 * sy):
                        dana_btn = it
                        break
                d_x = dana_btn["cx"] if dana_btn else int(456 * sx)
                d_y = dana_btn["cy"] if dana_btn else int(661 * sy)
                print(f"{self.tag}     -> Memilih opsi DANA di ({d_x}, {d_y})...", flush=True)
                self.tap(d_x, d_y)
                time.sleep(0.6)
                img = self.get_screenshot()
                ocr_items = self.run_full_ocr(img)

                tarik_btn = None
                for it in ocr_items:
                    t_btn = it["text"].lower().strip()
                    # Tombol hijau di halaman ini terbaca OCR sebagai "Tarik",
                    # bukan "Menarik". Abaikan judul Tarik di atas (y kecil).
                    if ("tarik" in t_btn or "menarik" in t_btn) and int(720 * sy) < it["cy"] < int(850 * sy):
                        tarik_btn = it
                        break
                # Fallback lama (554,852) terlalu bawah/kanan dan sering meleset.
                # Klik tengah tombol hijau yang lebar: sekitar (360,787) pada 720x1640.
                m_cx = tarik_btn["cx"] if tarik_btn else int(360 * sx)
                m_cy = tarik_btn["cy"] if tarik_btn else int(787 * sy)
                print(f"{self.tag}     -> Mengeklik tombol hijau Tarik di ({m_cx}, {m_cy})...", flush=True)
                # Kirim beberapa tap dekat tengah tombol agar animasi/overlay tidak membuat miss.
                self.tap_burst([
                    (m_cx, m_cy),
                    (int(360 * sx), int(787 * sy)),
                    (int(360 * sx), int(805 * sy)),
                    (int(300 * sx), int(787 * sy)),
                    (int(420 * sx), int(787 * sy)),
                ], delay=0.06)
                time.sleep(0.6)
                continue

            # 4. Dialog Modal Penarikan (Periksa Akun / Pastikan Informasi / Berhasil) jika tombol belum tertangkap di atas
            modal_keywords = ["periksa akun", "memastikan", "pastikan informasi", "informasi sudah benar", "nama lengkap", "telah berhasil", "berhasil", "sukses"]
            if any(k in all_text_lower for k in modal_keywords) and not any(k in all_text_lower for k in ["tingkat:", "antri"]):
                pts = [
                    (int(362 * sx), int(1118 * sy)),
                    (int(361 * sx), int(1250 * sy)),
                    (int(360 * sx), int(1200 * sy)),
                    (int(360 * sx), int(1080 * sy)),
                    (int(360 * sx), int(1150 * sy))
                ]
                print(f"{self.tag} [+] Terdeteksi dialog modal penarikan. Mengeklik burst tombol Konfirmasi di ({pts[0][0]}, {pts[0][1]})...", flush=True)
                self.tap_burst(pts, delay=0.08)
                time.sleep(0.6)
                continue

            # 5. Layar game utama kembali aktif
            if any(k in all_text_lower for k in ["tingkat:", "antri", "level"]):
                self.withdrawn_pending_ad = True
                print(f"{self.tag} [✔] Seluruh alur penarikan selesai! Layar game utama aktif.", flush=True)
                return

            self.press_back()
            time.sleep(0.8)

        self.withdrawn_pending_ad = True
        print(f"{self.tag} [✔] Penarikan selesai! Menandai jeda penarikan sampai 1x tonton iklan.", flush=True)
        print(f"{self.tag} [!] Kembali ke game utama.", flush=True)
        self.bring_game_to_foreground()
        time.sleep(0.5)


    def record_saldo_state(self, left_rp):
        """Menyimpan saldo terdeteksi ke state JSON untuk sinkronisasi Telegram reporter."""
        try:
            cur_val = float(str(left_rp).replace(',', '.'))
            if self.last_recorded_rp and cur_val > float(self.last_recorded_rp):
                diff = int(cur_val - float(self.last_recorded_rp))
                log_event("saldo_naik", f"Saldo Naik: Rp {int(self.last_recorded_rp)} ➔ Rp {int(cur_val)} (+Rp {diff})", {"diff": diff, "from": self.last_recorded_rp, "to": cur_val})
                self.last_recorded_rp = cur_val
                self.ads_opened_count_since_growth = 0
            elif not self.last_recorded_rp:
                self.last_recorded_rp = cur_val
        except Exception:
            pass
        try:
            state_file = Path('/Users/macbookair/soda_telegram_reporter_state.json')
            st = {}
            if state_file.exists():
                st = json.loads(state_file.read_text())
            prev_rp = st.get('saldo_rp')
            cur_rp_str = str(left_rp)
            if prev_rp != cur_rp_str:
                now_ts = int(time.time())
                now_str = time.strftime('%Y-%m-%d %H:%M:%S WIB')
                st['saldo_rp'] = cur_rp_str
                st['saldo_rp_time'] = now_str
                st['saldo_rp_ts'] = now_ts
                try:
                    p_val = float(str(prev_rp).replace(',', '.'))
                    c_val = float(cur_rp_str)
                    if c_val > p_val:
                        st['last_growth_ts'] = now_ts
                        st['last_growth_time'] = now_str
                        st['last_stale_alert_ts'] = 0
                except Exception:
                    st['last_growth_ts'] = now_ts
                    st['last_growth_time'] = now_str
                state_file.write_text(json.dumps(st, ensure_ascii=False, indent=2))
        except Exception:
            pass

    def check_and_handle_top_rp(self, ocr_items):
        """Mengecek saldo =Rp KIRI di header atas. Jika > MIN_WITHDRAWAL_RP, langsung tarik saldo."""
        if not ocr_items:
            return False

        if self.withdrawn_pending_ad:
            if self.step_counter % 8 == 1:
                print(f"{self.tag} [.] Penarikan saldo baru saja selesai. Menunggu 1x tonton iklan sebelum penarikan berikutnya.", flush=True)
            return False

        sx, sy = self.scale_x, self.scale_y
        left_rp, right_rp = None, None
        click_coords = (int(240 * sx), int(70 * sy))

        for item in ocr_items:
            cy, cx = item["cy"], item["cx"]
            # Hanya periksa baris badge saldo di y: 45..140 (abaikan banner notifikasi atas cy < 45)
            if not (int(45 * sy) <= cy <= int(140 * sy)):
                continue
            t = item["text"].replace("o", "0").replace("O", "0").replace("I", "1").replace("l", "1")
            m = re.search(r"Rp\s*([0-9]+)", t, re.IGNORECASE)
            if m:
                val = int(m.group(1))
                # Saldo KIRI (=Rp): terletak di area kiri tengah (cx <= 330)
                if cx <= int(330 * sx):
                    left_rp = val
                    click_coords = (cx, cy)
                # Saldo KANAN (Poin): terletak di area kanan (cx > 330)
                else:
                    right_rp = val

        if left_rp is not None:
            self.record_saldo_state(left_rp)
            right_str = f" | Rp Kanan: {right_rp}" if right_rp is not None else ""
            if left_rp > MIN_WITHDRAWAL_RP:
                print(f"\n{self.tag} [★] MENEMUKAN Saldo =Rp{left_rp} > {MIN_WITHDRAWAL_RP} (Target Tercapai!{right_str})", flush=True)
                print(f"{self.tag}     -> Mengeklik tombol =Rp KIRI di ({click_coords[0]}, {click_coords[1]})...", flush=True)
                self.tap(click_coords[0], click_coords[1])
                time.sleep(0.6)
                self.handle_withdrawal_modal_flow()
                return True
            elif self.step_counter % 5 == 1:
                print(f"{self.tag} [.] Status Saldo Header: =Rp{left_rp} / {MIN_WITHDRAWAL_RP}{right_str}", flush=True)

        return False

    def get_patch_color_name(self, img, cx, cy, half_w=28, half_h=28):
        x1 = max(0, int(cx - half_w)); x2 = min(self.width, int(cx + half_w))
        y1 = max(0, int(cy - half_h)); y2 = min(self.height, int(cy + half_h))
        return dominant_game_color(img[y1:y2, x1:x2])

    def detect_target_box_colors(self, img):
        """Deteksi warna kotak/tray tujuan di bagian bawah.

        Bot akan klik botol rak atas yang warnanya sama dengan kotak/tray bawah.
        """
        sx, sy = self.scale_x, self.scale_y
        colors = set()

        # Kotak/tray Soda Pack Puzzle berada di bawah dan ukurannya besar.
        # Jangan scan seluruh bawah layar karena background pantai + banner reward
        # sering menyatu menjadi kontur besar dan bot akhirnya salah warna lalu loop.
        tray_boxes = [
            (45, 1020, 230, 1160),    # kiri atas (jika muncul)
            (268, 1000, 455, 1160),   # tengah atas
            (490, 1020, 680, 1160),   # kanan atas
            (45, 1170, 230, 1310),    # kiri bawah (jika muncul)
            (268, 1170, 455, 1310),   # tengah bawah
            (490, 1170, 680, 1310),   # kanan bawah
        ]

        for bx1, by1, bx2, by2 in tray_boxes:
            x1, y1 = int(bx1 * sx), int(by1 * sy)
            x2, y2 = int(bx2 * sx), int(by2 * sy)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(self.width, x2), min(self.height, y2)
            if x2 <= x1 or y2 <= y1:
                continue

            roi = img[y1:y2, x1:x2]
            if roi.size == 0:
                continue

            # Ambil ring pinggir tray + sedikit isi; lubang coklat biasanya kurang
            # saturated/lebih gelap, sedangkan border tray/botol berwarna cerah.
            strip = max(8, int(16 * sy))
            border_parts = [
                roi[:strip, :],
                roi[-strip:, :],
                roi[:, :max(8, int(14 * sx))],
                roi[:, -max(8, int(14 * sx)):],
            ]
            border = np.concatenate([p.reshape(-1, 3) for p in border_parts if p.size > 0], axis=0)
            if border.size == 0:
                continue
            border_img = border.reshape(-1, 1, 3)
            color = dominant_game_color(border_img)
            if color:
                colors.add(color)

        return colors

    def detect_shelf_cans(self, img):
        """Mendeteksi posisi aktual botol terbawah/terdepan di rak atas Soda Pack.

        Versi sebelumnya memakai 8 kolom tetap dari bot lama. Di Soda Pack Puzzle
        kolomnya berbeda, sehingga background/slot kosong terbaca sebagai botol
        dan bot klik titik kosong berulang. Sekarang deteksi kontur botol aktual,
        lalu ambil botol paling bawah pada tiap tumpukan.
        """
        sx, sy = self.scale_x, self.scale_y
        x1, x2 = int(120 * sx), int(560 * sx)
        y1, y2 = int(330 * sy), int(835 * sy)
        crop = img[max(0, y1):min(self.height, y2), max(0, x1):min(self.width, x2)]
        if crop.size == 0:
            return []

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        mask = ((hsv[:, :, 1] > 80) & (hsv[:, :, 2] > 110)).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []
        for cnt in cnts:
            x, y, w, h = cv2.boundingRect(cnt)
            area = cv2.contourArea(cnt)
            if area < 550 * sx * sy:
                continue
            # Botol bisa muncul sebagai 1 botol pendek atau 1 tumpukan tinggi
            # yang kontur warnanya menyatu. Jangan menolak tumpukan tinggi,
            # tetapi tetap buang pipa/latar atas yang tidak mencapai area rak bawah.
            if w < int(28 * sx) or w > int(95 * sx) or h < int(20 * sy) or h > int(330 * sy):
                continue
            global_top = y1 + y
            global_bottom = y1 + y + h
            if h > int(170 * sy) and global_bottom < int(700 * sy):
                continue
            cx = x1 + x + w // 2
            cy = y1 + y + h // 2
            if cy < int(390 * sy) or cy > int(820 * sy):
                continue
            color = self.get_patch_color_name(img, cx, cy, half_w=int(26 * sx), half_h=int(28 * sy))
            if not color:
                continue
            candidates.append({
                "cx": int(cx),
                "cy": int(cy),
                "raw_cy": int(cy),
                "color": color,
                "area": int(area),
            })

        if not candidates:
            return []

        # Kelompokkan per tumpukan berdasarkan posisi X, pilih kandidat paling
        # bawah karena itu botol yang bisa diklik/keluar.
        candidates.sort(key=lambda c: c["cx"])
        groups = []
        for c in candidates:
            placed = False
            for g in groups:
                if abs(c["cx"] - g[0]["cx"]) <= int(42 * sx):
                    g.append(c)
                    placed = True
                    break
            if not placed:
                groups.append([c])

        front_cans = []
        for idx, group in enumerate(groups, start=1):
            best = sorted(group, key=lambda c: (c["cy"], c["area"]), reverse=True)[0]
            # Klik jangan di kontur warna yang terlalu atas. Di Soda Pack, tap
            # yang diterima biasanya di area slot/badan bawah tumpukan. Jika
            # warna target terdeteksi di bagian atas stack (contoh y=477),
            # tap langsung di situ sering tidak memindahkan botol. Simpan raw_y
            # untuk log, tapi arahkan titik tap minimal ke area bawah slot.
            best["raw_cy"] = int(best.get("cy", 0))
            best["cy"] = max(int(best["cy"]), int(745 * sy))
            best["col"] = idx
            front_cans.append(best)

        front_cans.sort(key=lambda c: c["col"])
        return front_cans

    def detect_floating_reward_bubble(self, ocr_items, img=None):
        """Mendeteksi Kado Terbang, Uang/Koin, dan Gelembung Balon Iklan dengan ukuran fleksibel di mana pun melintas."""
        sx, sy = self.scale_x, self.scale_y

        # 1. Deteksi Berbasis Teks / Simbol OCR (Cakupan luas y: 260..1480).
        # Dibuat ketat: kata generik seperti "ad/play" dan persen kecil (1%)
        # sering muncul di iklan/endcard dan membuat bot salah klik.
        reward_kw = [
            "kado", "gift", "hadiah", "parcel", "bonus", "spin", "film", "tonton",
            "buble", "balon", "bubble", "balloon", "uang", "koin", "coin", "cash", "gold",
            "free", "gratis", "klaim", "claim", "reward", "dapatkan", "ambil", "kupon"
        ]
        for it in ocr_items:
            cy, cx = it["cy"], it["cx"]
            if int(260 * sy) <= cy <= int(1480 * sy):
                if int(260 * sy) <= cy <= int(360 * sy) and cx <= int(200 * sx):
                    continue
                if int(260 * sy) <= cy <= int(360 * sy) and int(240 * sx) <= cx <= int(480 * sx):
                    continue
                t = it["text"].lower().strip()
                if any(ig in t for ig in ["tingkat", "antri", "buka kunci", "level", "refresh", "urutkan"]):
                    continue
                import re
                # Abaikan tombol booster tetap di HUD bawah (contoh: +3 kanan,
                # undo/sort bawah). Sebelumnya OCR membaca +3 sebagai reward,
                # sehingga bot loop klik booster dan tidak memainkan botol.
                if (int(480 * sx) <= cx <= int(635 * sx) and int(845 * sy) <= cy <= int(1035 * sy)) or cy >= int(1480 * sy):
                    continue
                if re.search(r'(\+\s*\d+|\d+\s*koin|\d+\s*rp|rp\s*\d+)', t) or any(kw in t for kw in reward_kw):
                    # Abaikan OCR pendek/gibberish yang sering muncul di iklan atau HUD.
                    if re.fullmatch(r'[a-z0-9%]{1,3}', t) and not t.startswith('+'):
                        continue
                    if not self.is_coord_recent(cx, cy):
                        return cx, cy, f"Reward Teks/Icon '{it['text']}'"

        # 2. Deteksi Visual Adaptif Bebas Ukuran (y: 260..1480)
        if img is not None:
            y1, y2 = int(260 * sy), int(1500 * sy)
            x1, x2 = int(10 * sx), int(710 * sx)
            crop = img[y1:y2, x1:x2]
            if crop.size > 0:
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

                # Floor Masking agar lantai parkir tidak menggabungkan kontur gelembung
                floor_mask = (hsv[:,:,0] >= 100) & (hsv[:,:,0] <= 115) & (hsv[:,:,1] <= 90) & (hsv[:,:,2] >= 190)

                sat_mask = (hsv[:,:,1] > 35) & (hsv[:,:,2] > 50)
                bright_mask = (hsv[:,:,2] > 180) & (hsv[:,:,1] > 20)
                combined_mask = (sat_mask | bright_mask) & (~floor_mask)

                # 1. Exclude Level Banner ('Tingkat:X' banner di tengah atas y: 260..350)
                lv_y1, lv_y2 = int((260 - 260) * sy), int((350 - 260) * sy)
                lv_x1, lv_x2 = int((240 - 10) * sx), int((480 - 10) * sx)
                combined_mask[lv_y1:lv_y2, lv_x1:lv_x2] = 0

                # 2. Exclude Badge Antri (kiri atas y: 250..360)
                aq_y1, aq_y2 = 0, int((360 - 260) * sy)
                aq_x1, aq_x2 = 0, int((200 - 10) * sx)
                combined_mask[aq_y1:aq_y2, aq_x1:aq_x2] = 0

                # 3. Exclude Antrean Penumpang (y: 330..470)
                pq_y1, pq_y2 = int((330 - 260) * sy), int((470 - 260) * sy)
                pq_x1, pq_x2 = int((230 - 10) * sx), int((400 - 10) * sx)
                combined_mask[pq_y1:pq_y2, pq_x1:pq_x2] = 0

                # 4. Exclude Slot Halte (y: 480..680)
                hb_y1, hb_y2 = int((480 - 260) * sy), int((680 - 260) * sy)
                hb_x1, hb_x2 = 0, int((710 - 10) * sx)
                combined_mask[hb_y1:hb_y2, hb_x1:hb_x2] = 0

                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                clean_mask = cv2.morphologyEx(combined_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
                cnts, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                candidates = []
                for c in cnts:
                    x, y, cw, ch = cv2.boundingRect(c)
                    area = cv2.contourArea(c)
                    aspect = cw / float(ch) if ch > 0 else 0
                    perimeter = cv2.arcLength(c, True)
                    circ = (4 * np.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0

                    is_valid_size = (20 * sx <= cw <= 220 * sx) and (16 * sy <= ch <= 220 * sy) and (250 * sx * sy <= area <= 30000 * sx * sy)
                    is_valid_shape = (0.50 <= aspect <= 2.80)

                    if is_valid_size and is_valid_shape:
                        cx = x1 + x + cw // 2
                        cy = y1 + y + ch // 2

                        if cx <= int(200 * sx) and cy <= int(365 * sy):
                            continue
                        if int(480 * sy) <= cy <= int(680 * sy):
                            continue
                        if cy >= int(1440 * sy):
                            continue
                        # Exclude dekorasi dinding/sisi statis game yang sering
                        # terbaca sebagai gelembung karena warnanya cerah.
                        if (cx <= int(115 * sx) or cx >= int(605 * sx)) and int(360 * sy) <= cy <= int(860 * sy):
                            continue
                        # Exclude tombol booster +3 tetap di kanan bawah HUD.
                        if int(480 * sx) <= cx <= int(635 * sx) and int(845 * sy) <= cy <= int(1035 * sy):
                            continue

                        # Exclude bodi bus stasioner di area parkir
                        if cy >= int(700 * sy) and area >= 2000 * sx * sy and (cw >= int(70 * sx) or ch >= int(70 * sy)):
                            continue

                        if self.is_coord_recent(cx, cy):
                            continue

                        patch = crop[y:y+ch, x:x+cw]
                        if patch.size > 0 and np.std(patch) > 12:
                            is_money = (1.30 <= aspect <= 2.80)
                            candidates.append((cx, cy, area, aspect, circ, is_money))

                if candidates:
                    candidates.sort(key=lambda item: item[2], reverse=True)
                    best = candidates[0]
                    if best[5]:
                        obj_name = "Uang / Koin Melayang"
                    elif 0.75 <= best[3] <= 1.30 and best[4] < 0.72:
                        obj_name = "Kado Hadiah Melayang"
                    else:
                        obj_name = "Gelembung Balon Iklan"
                    return best[0], best[1], f"{obj_name} (Posisi ({best[0]}, {best[1]}), Area={int(best[2])})"

        return None

    def play_step(self):
        self.step_counter += 1

        # 1. Pastikan fokus game aktif
        if not self.handle_app_focus_and_ads():
            return

        # 2. Ambil screenshot
        img = self.get_screenshot()
        if img is None:
            time.sleep(0.05)
            return

        # 3. Lakukan OCR untuk deteksi saldo & teks dialog popup
        ocr_items = self.run_full_ocr(img)
        all_text_lower = " ".join([it["text"].lower() for it in ocr_items])
        sx, sy = self.scale_x, self.scale_y

        # Jika bot/restart sudah berada di halaman Tarik, lanjutkan alur
        # penarikan langsung. Tanpa ini, halaman Tarik bisa dianggap layar biasa
        # dan tombol hijau tidak diproses.
        if ("pilih metode" in all_text_lower and ("dana" in all_text_lower or "ovo" in all_text_lower)) or ("saldo saya" in all_text_lower and "ditarik" in all_text_lower):
            self.handle_withdrawal_modal_flow()
            return

        # 4. Deteksi tombol 'CONTINUE' / 'CONTINUI' / 'LANJUTKAN'
        continue_keywords = ["continue", "continui", "continu", "lanjutkan", "lanjut", "teruskan"]
        for it in ocr_items:
            t = it["text"].lower()
            if any(kw in t for kw in continue_keywords):
                print(f"{self.tag} [★] Menemukan tombol '{it['text']}' di ({it['cx']}, {it['cy']})! Mengeklik Continue...", flush=True)
                self.tap(it["cx"], it["cy"])
                time.sleep(0.4)
                return

        # 5. Deteksi tombol 'MAIN ULANG' / 'COBA LAGI' saat level gagal
        main_ulang_keywords = ["main ulang", "coba lagi", "ulang", "restart", "play again"]
        for it in ocr_items:
            t = it["text"].lower()
            if any(kw in t for kw in main_ulang_keywords) and it["cy"] > int(500 * sy):
                print(f"{self.tag} [★] Menemukan tombol '{it['text']}' di ({it['cx']}, {it['cy']})! Mengeklik untuk memulai ulang level...", flush=True)
                self.tap(it["cx"], it["cy"])
                time.sleep(0.4)
                return

        if "gagal" in all_text_lower and ("level" in all_text_lower or "kurang" in all_text_lower or "rp" in all_text_lower):
            mu_x, mu_y = int(360 * sx), int(1160 * sy)
            print(f"{self.tag} [★] Terdeteksi status 'Gagal' di layar! Mengeklik tombol Main Ulang di ({mu_x}, {mu_y})...", flush=True)
            self.tap(mu_x, mu_y)
            time.sleep(0.4)
            return

        # 6. Deteksi Teks Modal (Pengaturan, Login Sehari, Tonton Iklan Spin, Check-in) -> KLIK TOMBOL X DI KANAN (AGAK ATAS)
        dismiss_keywords = [
            ("pengaturan", "Pengaturan", True),
            ("menetapkan", "Pengaturan (Menetapkan)", True),
            ("feedback", "Feedback", True),
            ("umpan balik", "Feedback / Umpan Balik", True),
            ("login sehari", "Login Sehari", False),
            ("tonton iklan untuk spin", "Tonton Iklan Spin", False),
            ("tonton iklan", "Tonton Iklan Spin", False),
            ("check-in", "Check-in Harian", False)
        ]
        for kw, label, is_raised in dismiss_keywords:
            if kw in all_text_lower:
                matched_item = None
                for it in ocr_items:
                    if kw in it["text"].lower():
                        matched_item = it
                        break
                base_y = matched_item["cy"] if matched_item else int(604 * sy)
                target_y = base_y - int(55 * sy) if is_raised else base_y
                target_x = int(645 * sx)
                note_str = " di kanan agak naik sedikit" if is_raised else " di kanan"
                print(f"{self.tag} [★] Menemukan dialog '{label}' di y={base_y}! Mengeklik tombol X{note_str} di ({target_x}, {target_y})...", flush=True)
                self.tap(target_x, target_y)
                time.sleep(0.2)
                self.tap(target_x, base_y)
                time.sleep(0.2)
                self.tap(int(655 * sx), int(420 * sy))
                time.sleep(0.2)
                self.tap(int(670 * sx), int(220 * sy))
                time.sleep(0.3)
                return

        # 7. Periksa Saldo =Rp di Header (Target > 500)
        if self.check_and_handle_top_rp(ocr_items):
            return

        # 8. Periksa Tombol Reward Modal Nyata ('Bebas Klik', 'Koleksi', 'Klaim', 'Menarik')
        #    Dibuat lebih agresif agar saat tombol Klaim muncul bot langsung klik, bukan lanjut tap botol.
        popup_btn = detect_popup_reward_button_fast(ocr_items, img, self.scale_x, self.scale_y)
        if popup_btn:
            self.reward_popup_loop_count = getattr(self, 'reward_popup_loop_count', 0) + 1
            bx, by, desc = popup_btn
            if self.reward_popup_loop_count >= 4:
                print(f"{self.tag} [!] Tombol reward berulang ({self.reward_popup_loop_count}x). Menekan 'Tidak Perlu' / 'Skip' / BACK untuk keluar modal...", flush=True)
                dismissed = False
                for it in ocr_items:
                    t_low = it.get('text', '').lower()
                    if any(k in t_low for k in ['tidak perlu', 'skip', 'nanti', 'lewati', 'batal', 'close', 'tutup']):
                        self.tap(it['cx'], it['cy'])
                        dismissed = True
                        break
                if not dismissed:
                    self.tap(int(360 * self.scale_x), int(1156 * self.scale_y))
                    self.press_back()
                self.reward_popup_loop_count = 0
                time.sleep(0.5)
                return

            print(f"{self.tag} [★] MENEMUKAN {desc} di ({bx}, {by})! Marker hijau 5 detik, lalu KLIK CEPAT tombol klaim/reward...", flush=True)
            self.show_detect_marker(bx, by)
            self.tap_reward_button_reliably(bx, by)
            time.sleep(0.6)
            img_after = self.get_screenshot()
            if img_after is not None:
                still_btn = detect_popup_reward_button_fast(self.run_full_ocr(img_after), img_after, self.scale_x, self.scale_y)
                if still_btn:
                    rb_x, rb_y, rb_desc = still_btn
                    print(f"{self.tag} [!] Tombol reward masih terlihat setelah klik pertama ({rb_desc}) di ({rb_x}, {rb_y}). KLIK ULANG lebih kuat...", flush=True)
                    self.show_detect_marker(rb_x, rb_y)
                    self.tap_reward_button_reliably(rb_x, rb_y)
                    time.sleep(0.7)
                    img_after = self.get_screenshot()
                else:
                    self.reward_popup_loop_count = 0

            if img_after is not None:
                cans_after = self.detect_shelf_cans(img_after)
                if not cans_after:
                    self.wait_ad_and_close_ad("Iklan Terbuka Setelah Klik Koleksi / Bebas Klik")
                    self.reward_popup_loop_count = 0
            return
        else:
            self.reward_popup_loop_count = 0

        # 8b. Deteksi Bubble / Balon Hadiah Terbang (+25 / Uang / Bonus / Film)
        bubble = self.detect_floating_reward_bubble(ocr_items, img)
        if bubble:
            bx, by, desc = bubble
            if not self.is_floating_reward_still_visible(bx, by, img):
                # Jika objek statis berada di area bawah popup, seringnya itu potongan tombol Klaim/Koleksi.
                # Jangan skip lama-lama: langsung klik area tengah tombol popup pada y tersebut.
                if by >= int(880 * sy):
                    # Koreksi jika kandidat statis berada terlalu bawah; tombol popup biasanya lebih atas.
                    _, claim_y, corrected_claim_y = normalize_reward_button_coord(int(360 * sx), int(by), sx, sy)
                    claim_points = [
                        (int(360 * sx), claim_y),
                        (int(360 * sx), max(int(910 * sy), claim_y - int(35 * sy))),
                        (int(360 * sx), min(int(1300 * sy), claim_y + int(45 * sy))),
                        (int(360 * sx), int(1050 * sy)),
                        (int(360 * sx), int(1150 * sy)),
                    ]
                    corr_note = " (posisi dinaikkan)" if corrected_claim_y else ""
                    print(f"{self.tag} [★] Kandidat reward statis di area popup ({bx}, {by}){corr_note}. Marker hijau 5 detik, anggap tombol Klaim/Koleksi, KLIK CEPAT tengah popup...", flush=True)
                    self.show_detect_marker(int(360 * sx), claim_y)
                    self.tap_reward_button_reliably(int(360 * sx), claim_y)
                    # Tambahan burst ringan di area yang sama setelah tap berurutan, untuk popup yang sulit merespons.
                    self.tap_burst(claim_points, delay=0.01)
                    self.record_tapped_coord(bx, by)
                    time.sleep(0.18)
                    return
                print(f"{self.tag} [.] Kandidat reward di ({bx}, {by}) sudah lewat/statis. Lewati agar tidak salah klik.", flush=True)
                self.record_tapped_coord(bx, by)
                return
            print(f"{self.tag} [★] MENEMUKAN {desc} di ({bx}, {by})! Marker hijau 5 detik, bubble bergerak kiri->kanan, spam klik jalur kanan sampai ujung...", flush=True)
            self.show_detect_marker(bx, by)
            path_points = self.tap_moving_bubble_to_right(bx, by)
            self.record_tapped_coord(bx, by)
            if path_points:
                self.record_tapped_coord(path_points[-1][0], path_points[-1][1])
            time.sleep(0.1)
            img_after = self.get_screenshot()
            if img_after is not None:
                cans_after = self.detect_shelf_cans(img_after)
                if not cans_after:
                    self.wait_ad_and_close_ad("Iklan Terbuka Setelah Klik Bubble Terbang")
            return

        # 9. Deteksi Kaleng di Rak
        front_cans = self.detect_shelf_cans(img)

        # 10. Jika TIDAK ada kaleng di rak (mungkin tertutup popup modal lain)
        if not front_cans:
            close_x = detect_dialog_close_x_button(img, self.scale_x, self.scale_y)
            if close_x:
                cx, cy, desc = close_x
                print(f"{self.tag} [★] MENEMUKAN {desc} di ({cx}, {cy})! Menutup modal...", flush=True)
                self.tap(cx, cy)
                time.sleep(0.08)
                return
            else:
                self.press_back()
                time.sleep(0.08)
                return

        # 11. Klik botol sesuai warna kotak/tray bawah.
        if front_cans:
            target_colors = self.detect_target_box_colors(img)
            matching_cans = [
                c for c in front_cans
                if c.get("color") and colors_match(c.get("color"), target_colors)
            ]

            if matching_cans:
                self.no_match_streak = 0
                tap_points = [(c["cx"], c["cy"]) for c in matching_cans]
                cols_desc = ", ".join([f"{c.get('color','?')} Col {c['col']} klik@({c['cx']},{c['cy']}) raw_y={c.get('raw_cy','-')}" for c in matching_cans])
                print(f"{self.tag} [⚡⚡] TAP BOTOL SESUAI WARNA KOTAK {sorted(target_colors)} ({len(tap_points)} Botol): {cols_desc}", flush=True)
                self.tap_burst(tap_points, delay=0.008)
            else:
                # Jangan klik fallback asal. Pada Soda Pack, jika warna target
                # tidak cocok/terbaca salah, klik bebas bisa mengenai indikator
                # jumlah sisa botol di kiri atau slot kosong dan jadi looping.
                self.no_match_streak += 1
                cols_desc = ", ".join([f"{x.get('color') or '?'} Col {x['col']} klik@({x['cx']},{x['cy']}) raw_y={x.get('raw_cy','-')}" for x in front_cans])
                print(f"{self.tag} [.] Tidak ada botol cocok dengan kotak {sorted(target_colors)}. Streak={self.no_match_streak}. Terbaca: {cols_desc}", flush=True)
                if self.no_match_streak >= 4:
                    refresh_x, refresh_y = int(360 * sx), int(1565 * sy)
                    print(f"{self.tag} [↻] Stuck warna {self.no_match_streak}x. Mengeklik tombol Refresh/Shuffle bawah tengah di ({refresh_x}, {refresh_y})...", flush=True)
                    self.show_tap_marker(refresh_x, refresh_y, color="green", duration=2.0)
                    self.tap(refresh_x, refresh_y)
                    self.no_match_streak = 0
                    time.sleep(0.5)
                else:
                    time.sleep(0.1)
        else:
            self.no_match_streak += 1
            print(f"{self.tag} [.] Tidak ada botol valid terdeteksi. Standby, tidak tap 8 kolom fallback. Streak={self.no_match_streak}", flush=True)
            if self.no_match_streak >= 6:
                refresh_x, refresh_y = int(360 * self.scale_x), int(1565 * self.scale_y)
                print(f"{self.tag} [↻] Tidak ada botol valid terlalu lama. Mengeklik Refresh/Shuffle di ({refresh_x}, {refresh_y})...", flush=True)
                self.tap(refresh_x, refresh_y)
                self.no_match_streak = 0
                time.sleep(1.0)
            else:
                time.sleep(0.25)

def run_device_worker(serial, parent_pid):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    print(f"[{serial}] [+] Worker proses aktif dan berjalan untuk {serial}!", flush=True)
    runner = CanSortRunner(serial)
    runner.check_and_wake_device()
    runner.check_and_install_game_if_missing()
    try:
        while True:
            if os.getppid() != parent_pid or os.getppid() == 1:
                break
            runner.play_step()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        print(f"[{serial}] [!] Worker error: {e}", flush=True)

def main():
    print("==================================================================", flush=True)
    print("      BOT SODA PACK PUZZLE - MULTI-DEVICE PARALLEL ENGINE                 ", flush=True)
    print("==================================================================", flush=True)
    active_processes = {}
    main_pid = os.getpid()
    print("[+] Memindai semua perangkat Android yang terhubung via ADB...", flush=True)
    print(f"[+] Target Game: Soda Pack Puzzle (com.soda.pack.puzzle)", flush=True)
    print(f"[+] Aturan Aktif: Auto-Install, Main Ulang, Iklan {AD_WAIT_SECONDS}s, DANA (> {MIN_WITHDRAWAL_RP}).\n", flush=True)
    print("[+] Tekan Ctrl+C untuk berhenti kapan saja.\n", flush=True)

    try:
        while True:
            current_devices = get_connected_devices()
            for serial in list(active_processes.keys()):
                if serial not in current_devices:
                    print(f"[-] Perangkat {serial} terputus. Menghentikan worker...", flush=True)
                    active_processes[serial].terminate()
                    active_processes[serial].join(timeout=1.0)
                    del active_processes[serial]

            for serial in current_devices:
                if serial not in active_processes or not active_processes[serial].is_alive():
                    if serial in active_processes:
                        try:
                            active_processes[serial].terminate()
                        except Exception:
                            pass

                    print(f"\n[+] Perangkat terdeteksi: {serial}", flush=True)
                    ensure_scrcpy_running(serial)
                    p = multiprocessing.Process(target=run_device_worker, args=(serial, main_pid), daemon=True)
                    p.start()
                    active_processes[serial] = p

            if not current_devices:
                print("[!] Tidak ada HP Android terhubung via ADB. Menunggu perangkat...", end="\r", flush=True)

            time.sleep(2.0)
    except KeyboardInterrupt:
        print("\n[+] Menghentikan semua bot worker...", flush=True)
        for p in active_processes.values():
            try:
                p.terminate()
                p.join(timeout=1.0)
            except Exception:
                pass
        print("[+] Semua bot selesai dihentikan.", flush=True)

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    main()
