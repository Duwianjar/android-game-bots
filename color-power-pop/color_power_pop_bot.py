#!/usr/bin/env python3
"""
Color Power Pop Automation Bot (auto-detect package)
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

GAME_DISPLAY_NAME = "Color Power Pop"
PACKAGE_NAME = os.environ.get("COLOR_POWER_POP_PACKAGE", "com.giraffeeapp.power")  # Color Power Pop
LAUNCH_ACTIVITY = ""
GAME_ACTIVITY = ""
PACKAGE_KEYWORDS = ["color", "colour", "power", "pop"]
OCR_HELPER_PATH = "/Users/macbookair/ocr_helper"
TAP_MARKER_PATH = "/Users/macbookair/scrcpy_tap_marker"
CLICK_REWARD_DURING_AD_WAIT = False  # Nonaktif: jangan klik Koleksi/Klaim/Unduh saat menunggu iklan
AD_WAIT_SECONDS = 6           # Menonton iklan selama 6 detik
AD_TIMER_STUCK_REPEAT_LIMIT = 4  # Jika OCR timer sama terus, anggap bukan countdown valid
MIN_WITHDRAWAL_RP = 200        # Target saldo =Rp minimal untuk penarikan
ENABLE_FLOATING_REWARD_DETECTION = False  # Color Power Pop tidak pakai reward/bubble melayang
ENABLE_AUTO_CLOSE_UNKNOWN_MODAL = False    # Matikan spam klik X modal palsu
DEBUG_COLOR_MARKERS_ONLY = False           # False = klik kartu atas sesuai warna kotak/wadah bawah
COLOR_MARKER_DURATION = 8.0                # Marker warna lebih lama agar mudah dicek

# Area grid/kotak Color Power Pop (terkalibrasi 720x1640).
# Bot akan deteksi kotak warna aktual di area ini, bukan tap asal layar.
GRID_X1, GRID_X2 = 35, 685
GRID_Y1, GRID_Y2 = 410, 1125
GRID_COLS = 8
GRID_ROWS = 7
TOP_SLOT_MARKER_Y = 764  # posisi y marker 4 slot atas disamakan mengikuti posisi slot 3 yang paling pas

# Tetap disediakan untuk fallback kompatibilitas log lama.
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
        print(f"[{serial}] [+] Membuka jendela tampilan layar scrcpy (Color Power Pop)...", flush=True)
        try:
            subprocess.Popen(
                ["scrcpy", "-s", serial, "--window-title", f"Color Power Pop - {serial}", "--max-fps=25", "--no-audio"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.2)
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

def detect_popup_reward_button_ocr(ocr_items, scale_y=1.0):
    """Mendeteksi tombol popup reward nyata berbasis teks OCR."""
    all_text = " ".join([it["text"].lower() for it in ocr_items])
    modal_indicators = ["selamat", "hadiah", "congratulations", "reward", "koin", "bonus", "menang", "gandakan", "klaim", "koleksi"]
    has_reward_modal = any(k in all_text for k in modal_indicators)

    # 1. Deteksi langsung teks tombol klaim/reward
    reward_keywords = ["bebas klik", "koleksi", "klaim", "claim", "collect", "gandakan", "dapatkan", "ambil", "terima"]
    for it in ocr_items:
        t = it["text"].lower()
        if any(kw in t for kw in reward_keywords) and it["cy"] > int(500 * scale_y):
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


def classify_hsv_color(h, s, v):
    """Klasifikasi warna utama kartu/blok Color Power Pop dari HSV OpenCV."""
    if v < 60 or s < 35:
        return None
    if h <= 8 or h >= 170:
        return "Red"
    if 9 <= h <= 19:
        return "Orange"
    # Di Color Power Pop warna kuning sering punya hue 20-24 dan sebelumnya
    # salah terbaca Orange. Geser batas agar kuning target/kartu terbaca benar.
    if 20 <= h <= 38:
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

def dominant_color_name(patch):
    if patch is None or patch.size == 0:
        return None
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    # Ambil pixel terang & saturated agar border/teks putih tidak ikut.
    mask = (hsv[:, :, 1] > 55) & (hsv[:, :, 2] > 90)
    if int(mask.sum()) < 20:
        return None
    vals = hsv[mask]
    h = int(np.median(vals[:, 0]))
    s = int(np.median(vals[:, 1]))
    v = int(np.median(vals[:, 2]))
    return classify_hsv_color(h, s, v)

def colors_match(card_color, target_colors):
    if card_color in target_colors:
        return True
    # Di Color Power Pop warna cyan/blue kadang terbaca silang karena garis/efek highlight.
    if card_color == "Cyan" and ("Blue" in target_colors or "Cyan" in target_colors):
        return True
    if card_color == "Blue" and ("Cyan" in target_colors or "Blue" in target_colors):
        return True
    return False

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
        self.aggressive_ad_dismiss_count = 0
        self.package_name = PACKAGE_NAME.strip()
        self.package_checked = False
        self.last_bottom_cards_log = ""
        self.last_slot_cards_log = ""
        self.slot_marker_counter = 0
        # Riwayat titik reward yang sudah disentuh agar tidak diklik berulang.
        self.recently_tapped_points = []
        self.last_reward_click_at = 0.0
        self.last_reward_click_coord = None
        self.external_redirect_loop_count = 0
        self.feedback_false_loop_count = 0
        self.last_external_redirect_at = 0.0

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

    def marker_color_for_game_color(self, color):
        mapping = {
            "Red": "red",
            "Orange": "orange",
            "Yellow": "yellow",
            "Green": "green",
            "Cyan": "blue",
            "Blue": "blue",
            "Pink": "purple",
        }
        return mapping.get(color or "", "green")

    def show_slot_color_marker(self, cx, cy, color, empty=False, duration=COLOR_MARKER_DURATION):
        # Jika kosong, beri hijau agar jelas slot kosong/tersedia.
        marker_color = "green" if empty else self.marker_color_for_game_color(color)
        self.show_tap_marker(cx, cy, color=marker_color, duration=duration, diameter=62)

    def show_card_color_marker(self, cx, cy, color, duration=COLOR_MARKER_DURATION):
        marker_color = self.marker_color_for_game_color(color)
        self.show_tap_marker(cx, cy, color=marker_color, duration=duration, diameter=56)

    def show_color_markers_batch(self, markers, duration=COLOR_MARKER_DURATION):
        """Tampilkan banyak marker warna sekaligus dalam satu proses agar muncul barengan."""
        if not markers or not os.path.exists(TAP_MARKER_PATH):
            return
        args = [TAP_MARKER_PATH]
        for m in markers:
            cx, cy = int(m.get('cx')), int(m.get('cy'))
            color = m.get('marker_color') or self.marker_color_for_game_color(m.get('color'))
            diameter = int(m.get('diameter', 56))
            args.extend([str(cx), str(cy), str(color), str(float(duration)), str(diameter)])
        try:
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            # fallback satu-satu jika batch gagal
            for m in markers:
                self.show_tap_marker(m.get('cx'), m.get('cy'), color=m.get('marker_color') or self.marker_color_for_game_color(m.get('color')), duration=duration, diameter=m.get('diameter', 56))

    def show_all_debug_color_markers(self, img, force=False):
        """Marker 4 slot atas + 6 kartu bawah langsung bersamaan."""
        if not (force or DEBUG_COLOR_MARKERS_ONLY or self.step_counter % 3 == 1):
            return
        markers = []
        for c in self.detect_lowest_slot_cards(img):
            markers.append({
                'cx': c.get('cx'), 'cy': c.get('cy'),
                'color': c.get('color'),
                'marker_color': 'green' if c.get('empty', False) else self.marker_color_for_game_color(c.get('color')),
                'diameter': 66,
            })
        for c in self.detect_bottom_cards(img):
            markers.append({
                'cx': c.get('cx'), 'cy': c.get('cy'),
                'color': c.get('color'),
                'diameter': 58,
            })
        self.show_color_markers_batch(markers, duration=COLOR_MARKER_DURATION)

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
            cmd_parts = [f"input tap {x} {y}" for x, y in clean_coords]
            chained_cmd = " & ".join(cmd_parts) + " & wait"
            subprocess.run(["adb", "-s", self.serial, "shell", chained_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4.0)
        except Exception:
            for x, y in coords:
                self.tap(x, y)
                if delay > 0:
                    time.sleep(delay)

    def tap_reward_button_reliably(self, cx, cy):
        """Klik tombol Klaim/Koleksi SATU KALI saja.

        Di Color Power Pop double/burst tap pada tombol Koleksi/Klaim bisa membuat
        tap kedua mengenai endcard iklan dan membuka Play Store. Jadi tombol reward
        tidak boleh di-spam.
        """
        sx, sy = self.scale_x, self.scale_y
        min_x, max_x = int(20 * sx), self.width - int(20 * sx)
        min_y, max_y = int(250 * sy), self.height - int(80 * sy)
        tx = max(min_x, min(max_x, int(cx)))
        ty = max(min_y, min(max_y, int(cy)))

        now = time.time()
        if self.last_reward_click_coord is not None:
            ox, oy = self.last_reward_click_coord
            if (now - self.last_reward_click_at) < 1.2 and abs(tx - ox) <= int(80 * sx) and abs(ty - oy) <= int(80 * sy):
                print(f"{self.tag} [.] Reward baru saja diklik. Skip tap kedua agar tidak dobel/masuk Play Store.", flush=True)
                return False

        self.last_reward_click_at = now
        self.last_reward_click_coord = (tx, ty)
        print(f"{self.tag} [+] Klik reward SATU KALI CEPAT di ({tx}, {ty}).", flush=True)
        self.tap(tx, ty)
        return True

    def tap_moving_bubble_to_right(self, bx, by):
        """Bubble/kado terbang bergerak kiri -> kanan: spam klik dari posisi deteksi ke arah kanan."""
        min_x = int(20 * self.scale_x)
        max_x = max(min_x, self.width - int(20 * self.scale_x))
        min_y = int(210 * self.scale_y)
        max_y = max(min_y, self.height - int(90 * self.scale_y))
        x_offsets = [0, 28, 56, 84, 112, 145, 180, 215, 250, 285]
        y_offsets = [0, -18, 18]
        points = []
        seen = set()
        for dx in x_offsets:
            for dy in y_offsets:
                x = max(min_x, min(max_x, int(bx + dx * self.scale_x)))
                y = max(min_y, min(max_y, int(by + dy * self.scale_y)))
                key = (x // 3, y // 3)
                if key not in seen:
                    seen.add(key)
                    points.append((x, y))
        self.tap_burst(points, delay=0.01)
        return points

    def auto_detect_game_package(self):
        """Cari package Color Power Pop dari daftar aplikasi terpasang."""
        if self.package_name:
            return self.package_name

        installed = self.run_adb(["shell", "pm", "list", "packages"], timeout=6.0)
        packages = []
        for line in installed.splitlines():
            if line.startswith("package:"):
                pkg = line.split("package:", 1)[1].strip()
                if pkg:
                    packages.append(pkg)

        def score(pkg):
            low = pkg.lower()
            # Jangan salah ambil aplikasi bisnis/Yoong/Speedometer yang kebetulan mengandung "power".
            excluded = ["spdspeedometer", "speedometer", "yoong", "powerplus", "dokter", "warehouse"]
            if any(x in low for x in excluded):
                return -100
            if low.startswith(("com.android", "com.google.android", "com.transsion", "android")):
                return -50

            has_color = ("color" in low or "colour" in low)
            has_power = "power" in low
            has_pop = "pop" in low
            # Syarat minimal agar tidak false-positive: harus ada color/colour, atau kombinasi power+pop.
            if not (has_color or (has_power and has_pop)):
                return 0

            sc = 0
            if has_color: sc += 20
            if has_power: sc += 10
            if has_pop: sc += 10
            if "game" in low or "puzzle" in low or "block" in low:
                sc += 5
            return sc

        candidates = sorted([(score(pkg), pkg) for pkg in packages if score(pkg) > 0], reverse=True)
        if candidates:
            self.package_name = candidates[0][1]
            print(f"{self.tag} [✔] Package {GAME_DISPLAY_NAME} terdeteksi otomatis: {self.package_name}", flush=True)
            return self.package_name

        return ""

    def bring_game_to_foreground(self):
        """Membawa aplikasi game kembali ke layar depan secara aman tanpa SecurityException."""
        pkg = self.auto_detect_game_package()
        if not pkg:
            print(f"{self.tag} [!] Package {GAME_DISPLAY_NAME} belum diketahui. Tidak bisa membuka game.", flush=True)
            return
        self.run_adb(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])

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
            time.sleep(1.0)
        return True

    def check_and_install_game_if_missing(self):
        """Cek apakah Color Power Pop terpasang. Jika belum ketemu, buka Play Store pencarian."""
        if self.auto_detect_game_package():
            self.bring_game_to_foreground()
            time.sleep(2.0)
            return True

        print(f"\n{self.tag} [!] Aplikasi {GAME_DISPLAY_NAME} belum terdeteksi di HP ini!", flush=True)
        print(f"{self.tag} [+] Membuka Google Play Store untuk mencari & menginstal {GAME_DISPLAY_NAME}...", flush=True)
        self.run_adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "market://search?q=Color+Power+Pop"])
        time.sleep(3.0)

        for _ in range(10):
            img = self.get_screenshot()
            if img is None:
                time.sleep(1.0)
                continue
            ocr_items = self.run_full_ocr(img)
            for it in ocr_items:
                t = it["text"].lower()
                if t in ["install", "instal", "pasang", "dapatkan", "unduh"] and (it["cy"] < int(650 * self.scale_y)):
                    print(f"{self.tag} [+] Menemukan tombol '{it['text']}' di Play Store ({it['cx']}, {it['cy']}). Mengeklik install...", flush=True)
                    self.tap(it["cx"], it["cy"])
                    break
            time.sleep(1.5)

        print(f"{self.tag} [⏳] Menunggu game terpasang/terdeteksi...", flush=True)
        for _ in range(45):
            time.sleep(4.0)
            if self.auto_detect_game_package():
                print(f"{self.tag} [✔] {GAME_DISPLAY_NAME} terdeteksi setelah install: {self.package_name}", flush=True)
                self.bring_game_to_foreground()
                time.sleep(3.0)
                return True
            img = self.get_screenshot()
            if img is not None:
                for it in self.run_full_ocr(img):
                    if it["text"].lower() in ["buka", "open", "play", "mainkan"] and it["cy"] < int(650 * self.scale_y):
                        print(f"{self.tag} [✔] Menemukan tombol '{it['text']}'. Membuka game...", flush=True)
                        self.tap(it["cx"], it["cy"])
                        time.sleep(3.0)
                        self.auto_detect_game_package()
                        return True
        return False

    def get_foreground_focus(self):
        try:
            res = subprocess.run(["adb", "-s", self.serial, "shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"], capture_output=True, text=True, timeout=2.0, check=False)
            return res.stdout.strip()
        except Exception:
            return ""

    def detect_ad_countdown_seconds(self, img=None):
        """Mendeteksi countdown timer iklan di area atas.

        Timer iklan kadang muncul di kiri atas, kadang kanan atas. Formatnya juga
        tidak selalu sama: "6s", "6 s left", atau angka saja dekat tombol close.
        """
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return None
        ocr_items = self.run_full_ocr(img)
        candidates = []
        for it in ocr_items:
            cx, cy = it["cx"], it["cy"]
            if cy > int(350 * self.scale_y):
                continue

            t = it["text"].lower().strip()
            # Jangan ambil saldo / level / angka reward yang bukan timer.
            if any(skip in t for skip in ["rp", "level", "tingkat", "coin", "koin", "%", "+"]):
                continue

            # Format jelas: 6s, 6 s left, 12 detik, 10 remaining, dst.
            m = re.search(r'\b(\d{1,2})\s*(?:s|sec|second|seconds|left|remaining|sisa|detik)\b', t, re.IGNORECASE)
            if m:
                sec = int(m.group(1))
                if 2 <= sec <= 90:
                    candidates.append((0, sec, cx, cy, it["text"]))
                    continue

            # Format angka saja: biasanya muncul di pojok kiri/kanan atas iklan.
            in_top_corner = (
                cy <= int(260 * self.scale_y)
                and (cx <= int(230 * self.scale_x) or cx >= int(490 * self.scale_x))
            )
            if in_top_corner:
                m2 = re.fullmatch(r'\D*(\d{1,2})\D*', t)
                if m2:
                    sec = int(m2.group(1))
                    if 2 <= sec <= 90:
                        candidates.append((1, sec, cx, cy, it["text"]))

        if candidates:
            # Prioritaskan format yang ada "s/left/detik", lalu angka terbesar.
            candidates.sort(key=lambda x: (x[0], -x[1]))
            _, sec, cx, cy, raw = candidates[0]
            print(f"{self.tag} [⏱] Timer iklan OCR terdeteksi '{raw}' di ({cx}, {cy}) = {sec} detik.", flush=True)
            return sec
        return None

    def handle_external_redirect_during_ad(self):
        """Saat sedang tunggu iklan, jika dilempar ke Play Store/Chrome, segera balik ke game."""
        focus = self.get_foreground_focus().lower()
        if "com.android.vending" not in focus and "com.android.chrome" not in focus:
            return False

        app_name = "Play Store" if "com.android.vending" in focus else "Chrome"
        now = time.time()
        if now - self.last_external_redirect_at > 20:
            self.external_redirect_loop_count = 0
        self.last_external_redirect_at = now
        self.external_redirect_loop_count += 1

        if self.external_redirect_loop_count >= 3:
            print(f"{self.tag} [!] Loop {app_name} terdeteksi {self.external_redirect_loop_count}x. Reset paksa: BACK, force-stop Play Store/Chrome/game, buka game ulang...", flush=True)
            self.aggressive_reset_to_game()
            self.external_redirect_loop_count = 0
            return True

        print(f"{self.tag} [!] Saat tunggu iklan tiba-tiba masuk {app_name}. Tekan BACK/force-stop lalu kembali ke game...", flush=True)
        for _ in range(2):
            self.press_back()
            time.sleep(0.25)
        if "com.android.vending" in focus:
            self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
        if "com.android.chrome" in focus:
            self.run_adb(["shell", "am", "force-stop", "com.android.chrome"])
        self.bring_game_to_foreground()
        time.sleep(0.8)
        return True

    def aggressive_reset_to_game(self):
        """Reset paksa jika stuck looping Play Store/Chrome/iklan."""
        pkg = self.auto_detect_game_package()
        for _ in range(4):
            self.press_back()
            time.sleep(0.18)
        self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
        self.run_adb(["shell", "am", "force-stop", "com.android.chrome"])
        if pkg:
            self.run_adb(["shell", "am", "force-stop", pkg])
            time.sleep(0.5)
        self.bring_game_to_foreground()
        time.sleep(1.5)
        self.ad_wait_done = False
        self.aggressive_ad_dismiss_count = 0
        self.feedback_false_loop_count = 0

    def reset_stuck_ad_timer_to_game(self, stuck_timer, repeat_count):
        """Timer OCR iklan sama terus: jangan tunggu angka palsu, BACK lalu restart game."""
        print(f"{self.tag} [!] Timer iklan OCR macet di {stuck_timer} detik ({repeat_count}x). Anggap bukan countdown valid. Tekan BACK dan mulai ulang game...", flush=True)
        pkg = self.auto_detect_game_package()
        for _ in range(4):
            self.press_back()
            time.sleep(0.22)
        if pkg:
            self.run_adb(["shell", "am", "force-stop", pkg])
            time.sleep(0.5)
        self.bring_game_to_foreground()
        time.sleep(1.5)
        self.ad_wait_done = False
        self.aggressive_ad_dismiss_count = 0
        self.feedback_false_loop_count = 0

    def detect_and_close_feedback_modal(self, img=None, ocr_items=None):
        """Tutup popup Feedback iklan Mintegral/SDK lain.

        Popup ini muncul saat bot menekan X iklan, tetapi activity masih terdeteksi
        sebagai iklan. Karena itu harus dicek di jalur iklan juga, bukan hanya
        play_step normal.
        """
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return False
        if ocr_items is None:
            ocr_items = self.run_full_ocr(img)

        all_text = " ".join([it["text"].lower() for it in ocr_items])
        has_feedback_title = any(k in all_text for k in ["feedback", "feed back", "feedbak", "umpan balik"])
        option_hits = sum(1 for k in ["not playing", "sound problems", "misleading", "fraud", "pornography"] if k in all_text)
        has_submit = "submit" in all_text or "kirim" in all_text
        has_privacy = "privacy policy" in all_text or "mintegral" in all_text

        # Jangan false-detect hanya karena ada "Mintegral Privacy Policy" di endcard iklan.
        # Feedback valid harus ada judul Feedback, atau minimal 2 opsi laporan + tombol Submit/Privacy.
        if not (has_feedback_title or (option_hits >= 2 and (has_submit or has_privacy))):
            return False

        sx, sy = self.scale_x, self.scale_y
        feedback_item = None
        for it in ocr_items:
            t = it["text"].lower()
            if "feedback" in t or "feed back" in t or "feedbak" in t:
                feedback_item = it
                break

        if feedback_item:
            # Dari screenshot real: Feedback cx≈362 cy≈537, X di kanan teks ≈620,532.
            target_x = min(self.width - int(70 * sx), feedback_item["cx"] + int(258 * sx))
            target_y = max(int(45 * sy), feedback_item["cy"] - int(5 * sy))
        else:
            # Fallback kalau OCR hanya baca opsi seperti "Not playing".
            target_x = int(620 * sx)
            target_y = int(532 * sy)

        self.feedback_false_loop_count += 1
        if self.feedback_false_loop_count >= 6 and not has_feedback_title:
            print(f"{self.tag} [!] Deteksi Feedback berulang tanpa judul Feedback. Anggap false-detect, reset paksa ke game.", flush=True)
            self.aggressive_reset_to_game()
            return True

        print(f"{self.tag} [★] Popup Feedback terdeteksi saat mode iklan. Klik X Feedback di ({target_x}, {target_y})...", flush=True)
        # Klik kecil di sekitar X agar tidak meleset.
        self.tap(target_x, target_y)
        time.sleep(0.10)
        self.tap(target_x - int(18 * sx), target_y)
        time.sleep(0.10)
        self.tap(target_x, target_y + int(18 * sy))
        time.sleep(0.35)
        return True

    def detect_and_click_see_next_button(self, img=None):
        """Klik tombol 'See Next' pada iklan jika muncul."""
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return False

        ocr_items = self.run_full_ocr(img)
        for it in ocr_items:
            t = it["text"].lower().strip()
            normalized = re.sub(r"[^a-z0-9]+", " ", t).strip()
            if (
                "see next" in normalized
                or "seenext" in normalized.replace(" ", "")
                or "next" == normalized
                or "berikut" in normalized
                or "selanjutnya" in normalized
            ):
                # Biasanya tombol ada di tengah/bawah iklan; tapi tetap klik posisi OCR teksnya.
                print(f"{self.tag} [+] Saat iklan menemukan tombol/teks 'See Next' di ({it['cx']}, {it['cy']}). Klik sekali...", flush=True)
                self.tap(it["cx"], it["cy"])
                time.sleep(0.35)
                return True
        return False

    def detect_and_click_ad_sequence_button(self, img=None):
        """Klik tombol tahap iklan bertingkat: Iklan 1/3, 2/3, 3/3.

        Urutan yang diinginkan:
        - Jika ada See Next, klik itu dulu.
        - Jika terlihat "Iklan 1 dari 3" atau "Iklan 2 dari 3", klik tombol >> di atasnya.
        - Jika "Iklan 3 dari 3", klik >> atau X di atasnya untuk menutup/lanjut.
        """
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return False

        sx, sy = self.scale_x, self.scale_y
        ocr_items = self.run_full_ocr(img)

        # 1. Prioritas See Next di tengah/bawah.
        for it in ocr_items:
            t = it["text"].lower().strip()
            normalized = re.sub(r"[^a-z0-9]+", " ", t).strip()
            if (
                "see next" in normalized
                or "seenext" in normalized.replace(" ", "")
                or normalized in ["next", "berikut", "selanjutnya"]
            ):
                print(f"{self.tag} [+] Iklan bertahap: menemukan 'See Next' di ({it['cx']}, {it['cy']}). Klik sekali...", flush=True)
                self.tap(it["cx"], it["cy"])
                time.sleep(0.35)
                return True

        # 2. Cari teks indikator tahap iklan di pojok/area atas kiri/kanan.
        seq_hits = []
        top_text = " ".join([it["text"].lower() for it in ocr_items if it["cy"] <= int(390 * sy)])
        for it in ocr_items:
            cx, cy = it["cx"], it["cy"]
            if cy > int(390 * sy):
                continue
            raw = it["text"].lower().strip()
            norm = re.sub(r"[^a-z0-9/]+", " ", raw).strip()

            stage = None
            total = None
            patterns = [
                r'(?:iklan|ilan|ad|ads)?\s*(\d)\s*(?:dari|of|/)\s*(\d)',
                r'(\d)\s*/\s*(\d)',
            ]
            for pat in patterns:
                m = re.search(pat, norm)
                if m:
                    stage, total = int(m.group(1)), int(m.group(2))
                    break
            # Kadang OCR memecah teks, fallback dari gabungan teks atas.
            if stage is None:
                m2 = re.search(r'(?:iklan|ilan|ad|ads)?\s*(1|2|3)\s*(?:dari|of|/)\s*3', top_text)
                if m2:
                    stage, total = int(m2.group(1)), 3
                    # Tentukan label kira-kira di kiri atau kanan dari posisi OCR kata terkait.
                    left_score = 0
                    right_score = 0
                    for top_item in ocr_items:
                        if top_item["cy"] > int(390 * sy):
                            continue
                        tt = top_item["text"].lower()
                        if any(k in tt for k in ["ad", "ads", "iklan", "ilan", "of", "dari", "/3", "3"]):
                            if top_item["cx"] < int(360 * sx):
                                left_score += 1
                            else:
                                right_score += 1
                    cx = int(95 * sx) if left_score > right_score else int(620 * sx)
                    cy = int(145 * sy)

            if stage in [1, 2, 3] and total == 3:
                seq_hits.append((stage, cx, cy, raw))

        if not seq_hits:
            return False

        # Ambil label nyata lebih dulu; kalau ada beberapa, pilih yang paling atas.
        seq_hits.sort(key=lambda v: (0 if v[3] else 1, v[2]))
        stage, seq_x, seq_y, raw = seq_hits[0]

        # 3. Cari tombol >> atau X di atas/dekat teks tahap iklan.
        control_candidates = []
        for it in ocr_items:
            tx, ty = it["cx"], it["cy"]
            if ty > seq_y + int(60 * sy):
                continue
            # Tombol bisa berada di atas label kiri atau kanan. Jangan paksa kanan saja.
            if abs(tx - seq_x) > int(230 * sx):
                continue
            text = it["text"].strip().lower()
            compact = re.sub(r"\s+", "", text)

            is_next = compact in [">", ">>", "›", "››", "»", "》", "next", "skip"] or ">>" in compact
            is_close = compact in ["x", "×", "✕", "✖", "+", "close", "tutup"]
            if stage in [1, 2] and is_next:
                control_candidates.append((tx, ty, text))
            elif stage == 3 and (is_next or is_close):
                control_candidates.append((tx, ty, text))

        if control_candidates:
            control_candidates.sort(key=lambda p: (p[1], -p[0]))
            tx, ty, text = control_candidates[0]
            print(f"{self.tag} [+] Terdeteksi '{raw or f'Iklan {stage} dari 3'}'. Klik tombol '{text}' di atasnya ({tx}, {ty})...", flush=True)
            self.tap(tx, ty)
            time.sleep(0.35)
            return True

        # 4. Fallback jika OCR tombol >>/X tidak terbaca: tap titik umum di atas label kiri/kanan.
        # Untuk tahap 1/2 diarahkan ke >>; tahap 3 diarahkan ke X/>> di area yang sama.
        fallback_x = int(60 * sx) if seq_x < int(360 * sx) else int(660 * sx)
        fallback_y = max(int(55 * sy), int(seq_y - 62 * sy))
        print(f"{self.tag} [+] Terdeteksi '{raw or f'Iklan {stage} dari 3'}' tapi tombol >>/X tidak terbaca OCR. Fallback klik atas label di ({fallback_x}, {fallback_y})...", flush=True)
        self.tap(fallback_x, fallback_y)
        time.sleep(0.35)
        return True

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

        # 2. Cek via deteksi kontur tombol X di pojok kanan ATAU kiri atas.
        y1, y2 = int(30 * sy), int(300 * sy)
        corner_regions = [
            ("kanan", int(580 * sx), int(710 * sx)),
            ("kiri", int(10 * sx), int(145 * sx)),
        ]
        all_candidates = []
        for side, x1, x2 in corner_regions:
            crop = img[y1:y2, x1:x2]
            if crop.size <= 0:
                continue
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 40, 140)
            cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            min_dim, max_dim = int(14 * min(sx, sy)), int(85 * max(sx, sy))
            for cnt in cnts:
                x, y, w, h = cv2.boundingRect(cnt)
                if min_dim <= w <= max_dim and min_dim <= h <= max_dim:
                    patch = crop[y:y+h, x:x+w]
                    if patch.std() > 20:
                        all_candidates.append((side, x1 + x + w // 2, y1 + y + h // 2))
        if all_candidates:
            # Prioritas kanan dulu, tapi kiri tetap bisa dipilih kalau hanya itu yang ada.
            all_candidates.sort(key=lambda item: (0 if item[0] == "kanan" else 1, item[2]))
            side, best_x, best_y = all_candidates[0]
            print(f"{self.tag} [★] Menemukan tombol X iklan di pojok {side} atas di ({best_x}, {best_y})! Mengeklik...", flush=True)
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

    def close_ad_screen_thoroughly(self):
        """Menutup iklan secara menyeluruh: BACK -> Jika muncul peringatan (Continue vs Close It) klik CONTINUE -> Endcard X -> Kembali Game."""
        sx, sy = self.scale_x, self.scale_y
        img0 = self.get_screenshot()
        if img0 is not None and self.detect_and_close_feedback_modal(img0):
            return

        self.press_back()
        time.sleep(0.18)

        img = self.get_screenshot()
        if img is not None:
            if self.detect_and_close_feedback_modal(img):
                return
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
        time.sleep(0.32)

        # Jika activity iklan masih tampil setelah BACK pertama, kirim BACK sekali lagi.
        focus_after_back = self.get_foreground_focus().lower()
        ad_activity_keywords = [
            "rewardvideo", "adactivity", "applovin", "mbridge", "mintegral",
            "unity3d", "adcolony", "vungle", "ironsource", "pangle", "bytedance"
        ]
        if any(keyword in focus_after_back for keyword in ad_activity_keywords):
            print(f"{self.tag} [+] Layar iklan masih aktif setelah BACK pertama. Mengirim BACK kedua...", flush=True)
            self.press_back()
            time.sleep(0.25)

        self.bring_game_to_foreground()
        time.sleep(0.25)

    def wait_ad_and_close_ad(self, reason="Iklan Video Reward", initial_remaining=None):
        """Menunggu iklan/reward. Jika timer iklan di pojok kiri atas terdeteksi, waktu tunggu disamakan."""
        print(f"\n{self.tag} [⏳] {reason} terdeteksi! Menunggu iklan (cek timer pojok kiri/kanan atas, tanpa klik reward saat iklan)...", flush=True)
        clicked_reward_during_wait = False
        remaining = int(initial_remaining) if initial_remaining and initial_remaining > 0 else AD_WAIT_SECONDS
        last_timer_seen = None
        same_timer_seen_count = 0
        same_timer_first_seen_at = 0.0

        if "Koleksi / Bebas Klik" in reason:
            slot1_x = int(188 * self.scale_x)
            slot1_y = int(TOP_SLOT_MARKER_Y * self.scale_y)
            print(f"{self.tag} [+] Setelah klik Koleksi/Bebas Klik: tap Slot 1 SATU KALI di ({slot1_x}, {slot1_y}) karena tombol/aksi ada di belakangnya.", flush=True)
            self.tap(slot1_x, slot1_y)
            time.sleep(0.05)

        while remaining > 0:
            if self.handle_external_redirect_during_ad():
                print(f"{self.tag} [✔] Sudah dikembalikan dari Play Store/Chrome ke game. Mengakhiri tunggu iklan agar tidak loop.", flush=True)
                self.ensure_back_to_card_board()
                return

            img_wait = self.get_screenshot()

            # 1. Sinkronkan waktu tunggu dengan timer iklan di pojok kiri atas jika terlihat.
            if img_wait is not None:
                if self.detect_and_close_feedback_modal(img_wait):
                    print(f"{self.tag} [✔] Feedback ditutup saat menunggu iklan. Lanjut cek kembali ke game...", flush=True)
                    self.ensure_back_to_card_board()
                    return

                detected_timer = self.detect_ad_countdown_seconds(img_wait)
                if detected_timer and 1 <= detected_timer <= 90:
                    # Jika OCR timer sama terus (contoh 80,80,80...), itu biasanya bukan countdown detik.
                    # Jangan loop menunggu angka palsu; BACK lalu restart game.
                    now = time.time()
                    if last_timer_seen == detected_timer:
                        same_timer_seen_count += 1
                    else:
                        same_timer_seen_count = 1
                        same_timer_first_seen_at = now

                    if (
                        same_timer_seen_count >= AD_TIMER_STUCK_REPEAT_LIMIT
                        and now - same_timer_first_seen_at >= 5.0
                    ):
                        self.reset_stuck_ad_timer_to_game(detected_timer, same_timer_seen_count)
                        return

                    # Samakan dengan timer iklan yang tampil, terutama jika lebih lama dari default.
                    if last_timer_seen != detected_timer:
                        print(f"{self.tag} [⏱] Timer iklan terdeteksi di pojok atas: {detected_timer} detik. Menyamakan waktu tunggu...", flush=True)
                    remaining = detected_timer
                    last_timer_seen = detected_timer

                # Kalau iklan menampilkan tahap berikutnya:
                # See Next di tengah/bawah, atau >>/X di atas teks Iklan 1/3, 2/3, 3/3.
                if self.detect_and_click_ad_sequence_button(img_wait):
                    remaining = max(remaining, AD_WAIT_SECONDS)
                    img_wait = self.get_screenshot()
                    if img_wait is not None:
                        new_timer = self.detect_ad_countdown_seconds(img_wait)
                        if new_timer and 1 <= new_timer <= 90:
                            remaining = new_timer
                            last_timer_seen = new_timer
                            same_timer_seen_count = 1
                            same_timer_first_seen_at = time.time()

                # Klik Koleksi/Klaim/Unduh saat tunggu iklan DINONAKTIFKAN.
                # Bot hanya memeriksa timer dan menunggu iklan hingga selesai.

            print(f"{self.tag}    -> Menonton iklan: sisa {remaining} detik...", flush=True)
            sleep_for = 2 if remaining >= 2 else remaining
            time.sleep(sleep_for)
            remaining -= sleep_for

            focus = self.get_foreground_focus().lower()
            if "com.android.vending" in focus or "com.android.chrome" in focus:
                if self.handle_external_redirect_during_ad():
                    print(f"{self.tag} [✔] Redirect iklan eksternal sudah ditutup. Mengakhiri tunggu iklan.", flush=True)
                    self.ensure_back_to_card_board()
                    return

        if clicked_reward_during_wait:
            print(f"{self.tag} [✔] Tombol reward sempat diklik saat menunggu. Melanjutkan penutupan iklan...", flush=True)
        print(f"{self.tag} [✔] Waktu tunggu iklan selesai! Menutup iklan (BACK + Tap X pojok)...", flush=True)
        self.close_ad_screen_thoroughly()
        if self.withdrawn_pending_ad:
            self.withdrawn_pending_ad = False
            print(f"{self.tag} [✔] Selesai 1x menonton iklan! Fitur penarikan saldo =Rp kini aktif kembali.", flush=True)

    def get_board_presence(self, img=None):
        """Mengembalikan status elemen board Color Power Pop: kotak bawah dan kartu slot atas."""
        if img is None:
            img = self.get_screenshot()
        if img is None:
            return False, False
        bottom_cards = self.detect_bottom_cards(img)
        slot_cards = self.detect_lowest_slot_cards(img)
        has_bottom_boxes = bool(bottom_cards)
        has_top_cards = any((c.get("color") and not c.get("empty")) for c in slot_cards)
        return has_bottom_boxes, has_top_cards

    def ensure_back_to_card_board(self, max_attempts=7):
        """Pastikan setelah iklan/halaman luar bot kembali ke layar kartu-kotak game."""
        pkg = self.auto_detect_game_package()
        for attempt in range(1, max_attempts + 1):
            focus = self.get_foreground_focus().lower()

            if "com.android.vending" in focus or "com.android.chrome" in focus:
                app_name = "Play Store" if "com.android.vending" in focus else "Chrome"
                print(f"{self.tag} [!] Masih di {app_name} setelah iklan. BACK/force-stop lalu kembali ke game (percobaan {attempt})...", flush=True)
                self.press_back()
                time.sleep(0.25)
                if "com.android.vending" in focus:
                    self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
                if "com.android.chrome" in focus:
                    self.run_adb(["shell", "am", "force-stop", "com.android.chrome"])
                self.bring_game_to_foreground()
                time.sleep(0.9)
                continue

            if pkg and pkg not in focus:
                print(f"{self.tag} [!] Fokus belum di game ({focus[:90] or 'kosong/home'}). Membuka game lagi (percobaan {attempt})...", flush=True)
                self.press_back()
                time.sleep(0.25)
                self.bring_game_to_foreground()
                time.sleep(0.9)
                continue

            img_check = self.get_screenshot()
            has_bottom, has_top = self.get_board_presence(img_check)
            if has_bottom and has_top:
                print(f"{self.tag} [✔] Sudah kembali ke halaman kartu/kotak game.", flush=True)
                return True

            print(f"{self.tag} [.] Game fokus, tapi board belum lengkap (kotak={has_bottom}, kartu={has_top}). Coba tutup sisa iklan/modal via X/BACK...", flush=True)
            if img_check is not None:
                self.detect_and_click_ad_x_button(img_check)
            self.press_back()
            time.sleep(0.45)

        print(f"{self.tag} [!] Board belum terlihat setelah recovery. Membuka ulang game agar tidak klik layar luar.", flush=True)
        self.bring_game_to_foreground()
        time.sleep(1.2)
        return False

    def recover_when_board_missing(self, img=None):
        """Jika kartu/kotak game hilang total, anggap halaman iklan/luar lalu tutup dan balik ke game."""
        focus = self.get_foreground_focus().lower()
        pkg = self.auto_detect_game_package()

        # Play Store / Chrome akibat iklan: tekan BACK beberapa kali lalu buka game lagi.
        if "com.android.vending" in focus or "com.android.chrome" in focus:
            app_name = "Play Store" if "com.android.vending" in focus else "Chrome"
            print(f"{self.tag} [!] {app_name} terbuka. BACK beberapa kali lalu kembali ke game...", flush=True)
            for _ in range(3):
                self.press_back()
                time.sleep(0.35)
            if "com.android.vending" in focus:
                self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
            if "com.android.chrome" in focus:
                self.run_adb(["shell", "am", "force-stop", "com.android.chrome"])
            self.bring_game_to_foreground()
            time.sleep(1.0)
            self.ensure_back_to_card_board()
            return True

        # Jika bukan game, coba kembali dulu.
        if pkg and pkg not in focus:
            print(f"{self.tag} [!] Fokus bukan game ({focus[:90]}). Mengirim BACK lalu buka game lagi...", flush=True)
            for _ in range(2):
                self.press_back()
                time.sleep(0.35)
            self.bring_game_to_foreground()
            time.sleep(1.0)
            return True

        # Masih package game tapi board hilang: biasanya iklan/endcard/webview di dalam game.
        timer = self.detect_ad_countdown_seconds(img) if img is not None else self.detect_ad_countdown_seconds()
        if timer and timer > 1:
            print(f"{self.tag} [⏳] Board kartu hilang dan timer iklan kiri atas terdeteksi: {timer}s. Menunggu sesuai timer...", flush=True)
        else:
            print(f"{self.tag} [⏳] Board kartu/kotak tidak ada. Anggap iklan/interstitial, tunggu default {AD_WAIT_SECONDS}s lalu tutup...", flush=True)
        self.wait_ad_and_close_ad("Board Kartu Hilang / Kemungkinan Iklan", initial_remaining=timer)

        # Setelah close, pastikan balik game; kalau masih tidak fokus game, buka ulang.
        self.ensure_back_to_card_board()
        return True


    def handle_app_focus_and_ads(self):
        focus = self.get_foreground_focus()
        focus_lower = focus.lower()

        # 1. Google Play Store terbuka oleh iklan -> Tutup paksa Play Store & kembali ke game
        if "com.android.vending" in focus_lower:
            now = time.time()
            if now - self.last_external_redirect_at > 20:
                self.external_redirect_loop_count = 0
            self.last_external_redirect_at = now
            self.external_redirect_loop_count += 1
            if self.external_redirect_loop_count >= 3:
                print(f"{self.tag} [!] Google Play Store looping {self.external_redirect_loop_count}x. Reset paksa dan buka game ulang...", flush=True)
                self.aggressive_reset_to_game()
                return False
            print(f"{self.tag} [!] Google Play Store terbuka oleh iklan! Menutup paksa Play Store & kembali ke game...", flush=True)
            self.run_adb(["shell", "am", "force-stop", "com.android.vending"])
            self.press_back()
            time.sleep(0.3)
            self.bring_game_to_foreground()
            time.sleep(0.8)
            self.ad_wait_done = False
            return False

        if "com.android.chrome" in focus_lower:
            now = time.time()
            if now - self.last_external_redirect_at > 20:
                self.external_redirect_loop_count = 0
            self.last_external_redirect_at = now
            self.external_redirect_loop_count += 1
            if self.external_redirect_loop_count >= 3:
                print(f"{self.tag} [!] Chrome looping {self.external_redirect_loop_count}x. Reset paksa dan buka game ulang...", flush=True)
                self.aggressive_reset_to_game()
                return False
            print(f"{self.tag} [!] Chrome terbuka oleh iklan! BACK/force-stop Chrome & kembali ke game...", flush=True)
            self.press_back()
            time.sleep(0.25)
            self.run_adb(["shell", "am", "force-stop", "com.android.chrome"])
            self.bring_game_to_foreground()
            time.sleep(0.8)
            self.ad_wait_done = False
            return False

        # 2. Periksa Dialog Konfirmasi Penarikan Sebelum Memeriksa Iklan (Anti-Salah Deteksi Iklan)
        img = self.get_screenshot()
        if img is not None:
            ocr_quick = self.run_full_ocr(img)
            quick_text = " ".join([it["text"].lower() for it in ocr_quick])

            if self.detect_and_close_feedback_modal(img, ocr_quick):
                print(f"{self.tag} [✔] Feedback ditutup sebelum proses iklan/WD.", flush=True)
                return False

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
        ad_keywords = ["mbrewardvideoactivity", "applovinfullscreenactivity", "adactivity", "companionadactivity", "bigo", "bytedance", "pangle", "unity3d", "applovin", "adcolony", "kwad", "mbridge", "vungle", "ironsource", "mintegral", "rewardvideo"]
        is_ad_activity = any(k in focus_lower for k in ad_keywords)

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
                if img is not None and self.detect_and_close_feedback_modal(img):
                    print(f"{self.tag} [✔] Feedback ditutup saat layar iklan aktif berulang.", flush=True)
                    self.aggressive_ad_dismiss_count = 0
                    return False
                # Cek apakah ada countdown timer di pojok atas
                remaining_sec = self.detect_ad_countdown_seconds(img)
                if remaining_sec and remaining_sec > 1:
                    print(f"{self.tag} [⏳] Terdeteksi timer iklan: '{remaining_sec}s' di pojok atas! Menunggu {remaining_sec} detik sampai selesai...", flush=True)
                    for rem in range(remaining_sec, 0, -2):
                        print(f"{self.tag}    -> Menunggu sisa timer iklan: {rem} detik...", flush=True)
                        time.sleep(2)
                    time.sleep(1.0)
                    self.aggressive_ad_dismiss_count = 0

                # Periksa dan klik tombol X di kanan atas
                self.detect_and_click_ad_x_button(img)
                self.close_ad_screen_thoroughly()
            return False

        # Reset status tunggu iklan saat game normal kembali aktif
        self.ad_wait_done = False
        self.aggressive_ad_dismiss_count = 0
        self.withdrawn_pending_ad = False

        # 3. Jika aplikasi Color Power Pop sama sekali tidak di layar
        pkg = self.auto_detect_game_package()
        if pkg and pkg not in focus:
            print(f"{self.tag} [!] {GAME_DISPLAY_NAME} tidak di layar. Membuka aplikasi...", flush=True)
            self.bring_game_to_foreground()
            time.sleep(1.5)
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
        """Alur penarikan saldo ke DANA saat =Rp >= MIN_WITHDRAWAL_RP."""
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
            normalized_text = (
                all_text_lower
                .replace("o", "0").replace("O", "0")
                .replace("l", "1").replace("I", "1")
                .replace("d", "p").replace("D", "p")
            )

            # 0. Jika saldo sudah Rp0 / muncul pesan minimum, anggap WD sudah berhasil/selesai.
            withdrawal_page_hint = any(k in normalized_text for k in [
                "pilih metode", "saldo saya", "penukaran", "menarik", "pastikan",
                "periksa akun", "nama lengkap", "nomor akun", "pana", "dana", "ovo"
            ])
            zero_patterns = [
                r"[=~\\-–—]?\s*r\s*p\s*0\b",
                r"diterima\s*:?\s*r\s*p\s*0\b",
                r"saldo.*r\s*p\s*0\b",
                r"dana\s*r\s*p\s*0\b",
                r"pana\s*r\s*p\s*0\b",
            ]
            is_saldo_zero = any(re.search(pat, normalized_text, re.IGNORECASE) for pat in zero_patterns)
            minimum_50_done = (
                ("minimum" in normalized_text or "minim" in normalized_text or "minimal" in normalized_text)
                and ("50" in normalized_text or "5o" in all_text_lower)
                and ("penarikan" in normalized_text or "jumlah" in normalized_text or "menarik" in normalized_text)
            )
            if withdrawal_page_hint and (is_saldo_zero or minimum_50_done):
                reason = "Saldo penarikan sudah =Rp0" if is_saldo_zero else "Muncul pesan jumlah penarikan minimum 50"
                print(f"{self.tag} [✔] {reason}. Anggap WD sudah selesai, menutup halaman penarikan...", flush=True)
                self.press_back()
                time.sleep(0.6)
                self.press_back()
                time.sleep(0.4)
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
                time.sleep(1.0)
                continue

            # 3. Pilihan metode DANA
            if "pilih metode" in all_text_lower or ("ovo" in all_text_lower and "dana" in all_text_lower):
                print(f"\n{self.tag} [+] Terdeteksi halaman Pilih Metode Penarikan (Opsi OVO & DANA):", flush=True)
                dana_btn = None
                for it in ocr_items:
                    if "dana" in it["text"].lower() and int(480 * sy) < it["cy"] < int(850 * sy):
                        dana_btn = it
                        break
                # Di Color Power Pop posisi DANA ada di sebelah kiri, OVO di kanan.
                d_x = dana_btn["cx"] if dana_btn else int(255 * sx)
                d_y = dana_btn["cy"] if dana_btn else int(661 * sy)
                print(f"{self.tag}     -> Memilih opsi DANA SEBELAH KIRI di ({d_x}, {d_y})...", flush=True)
                self.tap(d_x, d_y)
                time.sleep(0.6)
                img = self.get_screenshot()
                ocr_items = self.run_full_ocr(img)

                menarik_btn = None
                for it in ocr_items:
                    if "menarik" in it["text"].lower() and int(750 * sy) < it["cy"] < int(1200 * sy):
                        menarik_btn = it
                        break
                m_cx = menarik_btn["cx"] if menarik_btn else int(554 * sx)
                m_cy = menarik_btn["cy"] if menarik_btn else int(852 * sy)
                print(f"{self.tag}     -> Mengeklik tombol hijau Menarik di ({m_cx}, {m_cy})...", flush=True)
                self.tap(m_cx, m_cy)
                time.sleep(1.2)
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
                time.sleep(1.2)
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


    def check_and_handle_top_rp(self, ocr_items):
        """Mengecek saldo =Rp KIRI di header atas. Jika >= MIN_WITHDRAWAL_RP, langsung tarik saldo."""
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
            raw_t = item["text"]
            # OCR sering salah baca =Rp161 sebagai "~RD161", "RP 161", "R0161", dsb.
            t = (
                raw_t
                .replace("o", "0").replace("O", "0")
                .replace("I", "1").replace("l", "1")
                .replace("D", "p").replace("d", "p")
            )
            m = re.search(r"(?:[=~\\-–—]?\s*)?R\s*[pP]\s*([0-9][0-9.,]*)", t, re.IGNORECASE)
            if m:
                val = int(re.sub(r"[^0-9]", "", m.group(1)) or "0")
                # Saldo KIRI (=Rp): di Color Power Pop kadang OCR berada agak tengah (cx 330..430).
                if cx <= int(430 * sx):
                    left_rp = val
                    click_coords = (cx, cy)
                # Saldo KANAN (Poin): terletak di area kanan (cx > 330)
                else:
                    right_rp = val

        if left_rp is not None:
            right_str = f" | Rp Kanan: {right_rp}" if right_rp is not None else ""
            if left_rp >= MIN_WITHDRAWAL_RP:
                print(f"\n{self.tag} [★] MENEMUKAN Saldo =Rp{left_rp} >= {MIN_WITHDRAWAL_RP} (Target Tercapai!{right_str})", flush=True)
                print(f"{self.tag}     -> Mengeklik tombol =Rp KIRI di ({click_coords[0]}, {click_coords[1]})...", flush=True)
                self.tap(click_coords[0], click_coords[1])
                time.sleep(0.6)
                self.handle_withdrawal_modal_flow()
                return True
            elif self.step_counter % 5 == 1:
                print(f"{self.tag} [.] Status Saldo Header: =Rp{left_rp} / {MIN_WITHDRAWAL_RP}{right_str}", flush=True)

        return False

    def get_patch_color_name(self, img, cx, cy, half_w=32, half_h=24):
        x1 = max(0, int(cx - half_w)); x2 = min(self.width, int(cx + half_w))
        y1 = max(0, int(cy - half_h)); y2 = min(self.height, int(cy + half_h))
        return dominant_color_name(img[y1:y2, x1:x2])

    def colored_card_patch_info(self, img, cx, cy, half_w=36, half_h=22):
        """Return (warna, rasio pixel kartu) di sekitar titik klik.

        Dipakai untuk membedakan kartu nyata vs slot kosong. Slot kosong kadang
        masih punya kontur/warna dari kartu di atasnya, jadi titik yang akan
        diklik harus divalidasi berisi area warna kartu juga.
        """
        x1 = max(0, int(cx - half_w)); x2 = min(self.width, int(cx + half_w))
        y1 = max(0, int(cy - half_h)); y2 = min(self.height, int(cy + half_h))
        patch = img[y1:y2, x1:x2]
        if patch.size == 0:
            return None, 0.0
        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        mask = ((hsv[:, :, 1] > 55) & (hsv[:, :, 2] > 110))
        ratio = float(mask.sum()) / float(mask.size or 1)
        if int(mask.sum()) < 20:
            return None, ratio
        vals = hsv[mask]
        median_v = int(np.median(vals[:, 2]))
        # Background slot kosong berwarna biru tua juga saturated, tapi lebih
        # gelap (contoh V ~170). Kartu nyata jauh lebih terang. Ini mencegah
        # slot kosong terbaca sebagai kartu Blue lalu diklik berulang.
        if median_v < 190:
            return None, ratio
        return dominant_color_name(patch), ratio

    def detect_top_play_colors(self, img):
        """Ambil warna yang sedang muncul/tersedia di area permainan atas."""
        sx, sy = self.scale_x, self.scale_y
        # Fokus ke tumpukan kartu/blok di mesin atas, bukan UI saldo/header.
        x1, x2 = int(95 * sx), int(490 * sx)
        y1, y2 = int(300 * sy), int(890 * sy)
        crop = img[max(0, y1):min(self.height, y2), max(0, x1):min(self.width, x2)]
        colors = set()
        if crop.size == 0:
            return colors
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        mask = ((hsv[:, :, 1] > 70) & (hsv[:, :, 2] > 110)).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in cnts:
            x, y, w, h = cv2.boundingRect(cnt)
            area = cv2.contourArea(cnt)
            if area < 350 * sx * sy:
                continue
            # Potongan kartu biasanya horizontal; tetapi gabungan kolom juga boleh diambil warnanya.
            cx, cy = x1 + x + w // 2, y1 + y + h // 2
            color = self.get_patch_color_name(img, cx, cy, half_w=max(12, min(35, w//3)), half_h=max(10, min(25, h//3)))
            if color:
                colors.add(color)
        return colors

    def detect_bottom_cards(self, img):
        """Deteksi 6 kartu bawah yang bisa diklik beserta warna dan posisi aktualnya.

        Posisi kartu bawah bisa naik/bertumpuk, jadi titik klik tidak boleh pakai
        koordinat tetap. Untuk tiap slot bawah, cari kontur warna kartu aktual dan
        klik center kontur tersebut.
        """
        sx, sy = self.scale_x, self.scale_y
        base_centers = [
            (160, 1235), (360, 1235), (560, 1235),
            (160, 1380), (360, 1380), (560, 1380),
        ]
        cards = []
        for idx, (base_x, base_y) in enumerate(base_centers, start=1):
            base_cx, base_cy = int(base_x * sx), int(base_y * sy)
            # Area cukup tinggi agar kartu yang sedang naik/bertumpuk tetap terdeteksi.
            x1, x2 = max(0, base_cx - int(95 * sx)), min(self.width, base_cx + int(95 * sx))
            y1, y2 = max(0, base_cy - int(170 * sy)), min(self.height, base_cy + int(105 * sy))
            crop = img[y1:y2, x1:x2]
            if crop.size == 0:
                continue
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            mask = ((hsv[:, :, 1] > 55) & (hsv[:, :, 2] > 90)).astype(np.uint8) * 255
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            candidates = []
            for cnt in cnts:
                x, y, w, h = cv2.boundingRect(cnt)
                area = cv2.contourArea(cnt)
                if area < 800 * sx * sy:
                    continue
                aspect = w / float(h) if h else 0
                # Kartu/wadah bawah biasanya blok cukup besar; hindari garis tipis/noise.
                if w < int(55 * sx) or h < int(45 * sy) or not (0.45 <= aspect <= 2.2):
                    continue
                cx, cy = x1 + x + w // 2, y1 + y + h // 2
                top_y = y1 + y
                # Warna tetap boleh diambil dari tengah kontur, tapi titik klik harus di badan kartu atas,
                # bukan di kotak/wadah bawah.
                color = self.get_patch_color_name(img, cx, cy, half_w=int(48 * sx), half_h=int(34 * sy))
                if not color:
                    continue
                click_y = int(top_y + min(int(78 * sy), max(int(38 * sy), h * 0.32)))
                candidates.append({"cx": int(cx), "cy": int(click_y), "raw_cy": int(cy), "color": color, "area": int(area), "top_y": int(top_y), "h": int(h)})

            if candidates:
                # Bias ke kontur terbesar; jika mirip, pilih yang lebih atas (kartu aktif/terangkat).
                candidates.sort(key=lambda c: (c["area"], -c["top_y"]), reverse=True)
                best = candidates[0]
                row = 1 if idx <= 3 else 2
                col = ((idx - 1) % 3) + 1
                cards.append({
                    "col": col,
                    "row": row,
                    "cx": best["cx"],
                    "cy": best["cy"],
                    "raw_cy": best.get("raw_cy"),
                    "top_y": best.get("top_y"),
                    "base_cx": base_cx,
                    "base_cy": base_cy,
                    "color": best["color"],
                    "area": best["area"],
                })
        return cards

    def format_bottom_cards_log(self, img):
        cards = self.detect_bottom_cards(img)
        if not cards:
            return "6 wadah/kartu bawah: BELUM TERBACA"
        by_pos = {(c["row"], c["col"]): c.get("color", "?") for c in cards}
        parts = []
        for row in [1, 2]:
            row_vals = []
            for col in [1, 2, 3]:
                row_vals.append(f"R{row}C{col}={by_pos.get((row, col), '-')}")
            parts.append(" | ".join(row_vals))
        return "6 wadah/kartu bawah: " + " || ".join(parts)

    def log_bottom_cards_once(self, img, force=False):
        msg = self.format_bottom_cards_log(img)
        if force or msg != self.last_bottom_cards_log:
            print(f"{self.tag} [🎨] {msg}", flush=True)
            self.last_bottom_cards_log = msg
        # Marker 6 bawah ditampilkan bareng dengan 4 slot oleh show_all_debug_color_markers().

    def detect_lowest_slot_cards(self, img):
        """Deteksi warna kartu paling bawah pada 4 slot/tumpukan atas.

        Slot kosong tetap dikembalikan agar posisinya bisa diberi marker hijau.
        """
        sx, sy = self.scale_x, self.scale_y
        # Pusat 4 slot/tumpukan atas pada resolusi referensi 720x1640.
        # S4 biasanya kolom kosong di kanan.
        slot_xs = [188, 303, 418, 535]
        y_top, y_bottom = int(300 * sy), int(880 * sy)
        marker_y = int(TOP_SLOT_MARKER_Y * sy)
        cards = []
        for idx, base_x in enumerate(slot_xs, start=1):
            cx = int(base_x * sx)

            # Mode utama Color Power Pop:
            # posisi klik/warna kartu atas sudah dikalibrasi sejajar di marker_y.
            # Deteksi kontur kadang mengambil kartu/efek di bagian atas slot,
            # sehingga S1 Pink bisa salah terbaca Yellow. Jadi baca warna langsung
            # dari area posisi klik yang benar terlebih dahulu.
            direct_half_w = int(36 * sx)
            direct_half_h = int(22 * sy)
            px1, px2 = max(0, cx - direct_half_w), min(self.width, cx + direct_half_w)
            py1, py2 = max(0, marker_y - direct_half_h), min(self.height, marker_y + direct_half_h)
            direct_patch = img[py1:py2, px1:px2]
            direct_color, direct_ratio = self.colored_card_patch_info(
                img, cx, marker_y, half_w=direct_half_w, half_h=direct_half_h
            )

            if direct_color and direct_ratio >= 0.30:
                cards.append({
                    "slot": idx,
                    "cx": cx,
                    "cy": marker_y,
                    "raw_cy": marker_y,
                    "color": direct_color,
                    "empty": False,
                    "method": "fixed_marker",
                })
                continue

            x1, x2 = max(0, cx - int(42 * sx)), min(self.width, cx + int(42 * sx))
            crop = img[y_top:y_bottom, x1:x2]
            if crop.size == 0:
                cards.append({"slot": idx, "cx": cx, "cy": marker_y, "raw_cy": None, "color": None, "empty": True})
                continue
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            # Deteksi warna kartu. Exclude background biru gelap slot kosong dengan syarat brightness tinggi.
            mask = ((hsv[:, :, 1] > 65) & (hsv[:, :, 2] > 135)).astype(np.uint8) * 255
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            candidates = []
            for cnt in cnts:
                x, y, w, h = cv2.boundingRect(cnt)
                area = cv2.contourArea(cnt)
                # Kartu horizontal cukup lebar; background kosong biasanya area besar/vertikal atau gelap.
                if area < 180 * sx * sy:
                    continue
                if w < int(30 * sx) or h < int(8 * sy):
                    continue
                aspect = w / float(h) if h else 0
                # Exclude background slot kosong: biasanya kontur vertikal sangat tinggi/aspect kecil.
                if h > int(230 * sy) or aspect < 0.35:
                    continue
                cy_abs = y_top + y + h // 2
                cx_abs = x1 + x + w // 2
                color = self.get_patch_color_name(img, cx_abs, cy_abs, half_w=int(30 * sx), half_h=int(14 * sy))
                if color:
                    # Pastikan titik aktual kandidat memang berisi kartu, bukan
                    # background/slot kosong. Nanti klik di titik aktual ini,
                    # bukan selalu di marker_y, agar tidak tap ruang kosong saat
                    # kartu paling bawah bergeser/lebih tinggi.
                    point_color, point_ratio = self.colored_card_patch_info(
                        img, cx_abs, cy_abs, half_w=int(28 * sx), half_h=int(14 * sy)
                    )
                    if point_color and point_ratio >= 0.25:
                        candidates.append({
                            "cy": cy_abs,
                            "cx": cx_abs,
                            "color": point_color or color,
                            "area": area,
                            "ratio": point_ratio,
                        })
            if not candidates:
                # Slot kosong: marker di area bawah slot tempat klik/kartu akan muncul.
                cards.append({"slot": idx, "cx": cx, "cy": marker_y, "raw_cy": None, "color": None, "empty": True})
                continue
            # Ambil kartu/warna paling bawah di slot.
            candidates.sort(key=lambda c: (c["cy"], c["area"]), reverse=True)
            best = candidates[0]
            # Klik tepat ke kartu nyata yang terdeteksi. Sebelumnya cy selalu
            # marker_y; saat marker_y kosong tetapi ada kontur kartu di atas,
            # bot jadi tap slot kosong berulang.
            cards.append({
                "slot": idx,
                "cx": int(best["cx"]),
                "cy": int(best["cy"]),
                "raw_cy": int(best["cy"]),
                "color": best["color"],
                "empty": False,
                "method": "contour_actual",
            })
        return cards

    def format_lowest_slot_cards_log(self, img):
        cards = self.detect_lowest_slot_cards(img)
        parts = []
        for c in cards:
            val = c.get("color") or "KOSONG"
            cy = c.get("cy")
            pos = f"@({c.get('cx')},{cy})" if cy is not None else ""
            parts.append(f"S{c['slot']}={val}{pos}")
        return "4 slot atas kartu paling bawah: " + " | ".join(parts)

    def log_lowest_slot_cards_once(self, img, force=False):
        msg = self.format_lowest_slot_cards_log(img)
        if force or msg != self.last_slot_cards_log:
            print(f"{self.tag} [🃏] {msg}", flush=True)
            self.last_slot_cards_log = msg
        # Marker 4 slot + 6 bawah ditampilkan bersamaan dalam satu batch.
        self.show_all_debug_color_markers(img, force=force)

    def detect_shelf_cans(self, img):
        """Klik kartu atas/slot mesin yang warnanya cocok dengan salah satu kotak/wadah bawah.

        Penting: kotak/wadah bawah hanya target warna. Yang diklik adalah posisi kartu di atas.
        """
        bottom_cards = self.detect_bottom_cards(img)
        # Target utama adalah kotak/wadah bawah baris pertama posisi 1-3.
        # Baris kedua hanya dipakai kalau baris pertama belum terbaca.
        first_row_cards = [c for c in bottom_cards if c.get("row") == 1 and 1 <= int(c.get("col", 0)) <= 3]
        target_cards = first_row_cards if first_row_cards else bottom_cards
        bottom_colors = {c.get("color") for c in target_cards if c.get("color")}
        slot_cards = self.detect_lowest_slot_cards(img)

        if not bottom_cards:
            print(f"{self.tag} [🎨] 6 wadah/kartu bawah: BELUM TERBACA", flush=True)
            return []
        if not bottom_colors:
            print(f"{self.tag} [.] Warna kotak/wadah bawah belum terbaca. Standby.", flush=True)
            return []

        clickable_slots = []
        for c in slot_cards:
            # Slot kosong tidak diklik.
            if c.get("empty") or not c.get("color"):
                continue
            if colors_match(c.get("color"), bottom_colors):
                clickable_slots.append({
                    "slot": c.get("slot"),
                    "col": c.get("slot"),
                    "row": 0,
                    "cx": c.get("cx"),
                    "cy": c.get("cy"),
                    "raw_cy": c.get("raw_cy"),
                    "color": c.get("color"),
                    "area": 9999,
                    "is_top_card": True,
                })

        bottom_desc = ", ".join([f"{c['color']} R{c['row']}C{c['col']}" for c in bottom_cards])
        target_desc = ", ".join([f"{c['color']} R{c['row']}C{c['col']}" for c in target_cards])
        slot_desc = ", ".join([f"S{c['slot']}={c.get('color') or 'KOSONG'}" for c in slot_cards])
        if clickable_slots:
            print(f"{self.tag} [.] Target warna kotak bawah 1-3: {sorted(bottom_colors)} ({target_desc}) | Slot atas: {slot_desc} | KARTU ATAS cocok untuk diklik: " + ", ".join([f"S{c['slot']} {c['color']} @({c['cx']},{c['cy']})" for c in clickable_slots]), flush=True)
        else:
            print(f"{self.tag} [.] Target warna kotak bawah 1-3: {sorted(bottom_colors)} ({target_desc}) | Slot atas: {slot_desc} | Tidak ada kartu atas yang cocok. Semua kotak bawah: {bottom_desc}. Standby.", flush=True)

        # Klik kartu atas dari kiri ke kanan; slot 4 boleh diklik jika ada kartu dan warnanya cocok.
        clickable_slots.sort(key=lambda c: c["slot"])
        return clickable_slots[:4]

    def detect_floating_reward_bubble(self, ocr_items, img=None):
        """Mendeteksi Kado Terbang, Uang/Koin, dan Gelembung Balon Iklan dengan ukuran fleksibel di mana pun melintas."""
        sx, sy = self.scale_x, self.scale_y

        # 1. Deteksi Berbasis Teks / Simbol OCR (Cakupan luas y: 260..1480)
        reward_kw = [
            "kado", "gift", "box", "hadiah", "parcel", "bonus", "spin", "film", "tonton",
            "buble", "balon", "bubble", "balloon", "uang", "koin", "coin", "cash", "gold",
            "free", "gratis", "klaim", "claim", "reward", "dapatkan", "ambil", "ad", "video", "play", "kupon"
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
                if re.search(r'(\+\s*\d+|\d+\s*koin|\d+\s*rp|rp\s*\d+|\d+\s*%)', t) or any(kw in t for kw in reward_kw):
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
            time.sleep(0.15)
            return

        # 3. Lakukan OCR untuk deteksi saldo & teks dialog popup
        ocr_items = self.run_full_ocr(img)
        all_text_lower = " ".join([it["text"].lower() for it in ocr_items])
        sx, sy = self.scale_x, self.scale_y
        self.log_bottom_cards_once(img)
        self.log_lowest_slot_cards_once(img)

        # 4. Deteksi tombol 'CONTINUE' / 'CONTINUI' / 'LANJUTKAN'
        continue_keywords = ["continue", "continui", "continu", "lanjutkan", "lanjut", "teruskan"]
        for it in ocr_items:
            t = it["text"].lower()
            if any(kw in t for kw in continue_keywords):
                print(f"{self.tag} [★] Menemukan tombol '{it['text']}' di ({it['cx']}, {it['cy']})! Mengeklik Continue...", flush=True)
                self.tap(it["cx"], it["cy"])
                time.sleep(1.0)
                return

        # 5. Deteksi tombol 'MAIN ULANG' / 'COBA LAGI' saat level gagal
        main_ulang_keywords = ["main ulang", "coba lagi", "ulang", "restart", "play again"]
        for it in ocr_items:
            t = it["text"].lower()
            if any(kw in t for kw in main_ulang_keywords) and it["cy"] > int(500 * sy):
                print(f"{self.tag} [★] Menemukan tombol '{it['text']}' di ({it['cx']}, {it['cy']})! Mengeklik untuk memulai ulang level...", flush=True)
                self.tap(it["cx"], it["cy"])
                time.sleep(1.0)
                return

        if "gagal" in all_text_lower and ("level" in all_text_lower or "kurang" in all_text_lower or "rp" in all_text_lower):
            mu_x, mu_y = int(360 * sx), int(1160 * sy)
            print(f"{self.tag} [★] Terdeteksi status 'Gagal' di layar! Mengeklik tombol Main Ulang di ({mu_x}, {mu_y})...", flush=True)
            self.tap(mu_x, mu_y)
            time.sleep(1.0)
            return

        # 6. Deteksi Teks Modal (Pengaturan, Login Sehari, Tonton Iklan Spin, Check-in) -> KLIK TOMBOL X DI KANAN (AGAK ATAS)
        dismiss_keywords = [
            ("pengaturan", "Pengaturan", True),
            ("menetapkan", "Pengaturan (Menetapkan)", True),
            ("feedback", "Feedback", True),
            ("feed back", "Feedback", True),
            ("feedbak", "Feedback", True),
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
                if "Feedback" in label and matched_item:
                    # Tombol X Feedback kadang bukan pojok kanan layar, tetapi tepat
                    # di sebelah kanan teks Feedback. Ikuti posisi teksnya.
                    target_x = min(self.width - int(70 * sx), matched_item["cx"] + int(258 * sx))
                    target_y = max(int(45 * sy), matched_item["cy"] - int(5 * sy))
                else:
                    target_y = base_y - int(55 * sy) if is_raised else base_y
                    target_x = int(645 * sx)
                note_str = " di kanan agak naik sedikit" if is_raised else " di kanan"
                print(f"{self.tag} [★] Menemukan dialog '{label}' di y={base_y}! Mengeklik tombol X{note_str} di ({target_x}, {target_y})...", flush=True)
                self.tap(target_x, target_y)
                if "Feedback" in label:
                    # Klik cadangan kecil di sekitar X feedback karena OCR teks bisa beda 10-20px.
                    time.sleep(0.12)
                    self.tap(target_x - int(18 * sx), target_y)
                    time.sleep(0.12)
                    self.tap(target_x, target_y + int(18 * sy))
                    time.sleep(0.25)
                    return
                time.sleep(0.2)
                self.tap(target_x, base_y)
                time.sleep(0.2)
                self.tap(int(655 * sx), int(420 * sy))
                time.sleep(0.2)
                self.tap(int(670 * sx), int(220 * sy))
                time.sleep(0.3)
                return

        # 7. Periksa Saldo =Rp di Header (Target >= MIN_WITHDRAWAL_RP / 200)
        if self.check_and_handle_top_rp(ocr_items):
            return

        # 8. Periksa Tombol Reward Modal Nyata ('Bebas Klik', 'Koleksi', 'Klaim', 'Menarik')
        #    Dibuat lebih agresif agar saat tombol Klaim muncul bot langsung klik, bukan lanjut tap botol.
        popup_btn = detect_popup_reward_button_fast(ocr_items, img, self.scale_x, self.scale_y)
        if popup_btn:
            bx, by, desc = popup_btn
            print(f"{self.tag} [★] MENEMUKAN {desc} di ({bx}, {by})! Klik klaim/reward SATU KALI CEPAT...", flush=True)
            clicked_reward = self.tap_reward_button_reliably(bx, by)
            if not clicked_reward:
                time.sleep(0.08)
                return
            # Setelah popup Klaim/Koleksi hilang, tombol/kartu game bisa berada tepat
            # di belakangnya. Tap slot 1 langsung di sini supaya tidak menunggu sampai
            # loop iklan; hanya satu kali.
            slot1_x = int(188 * self.scale_x)
            slot1_y = int(TOP_SLOT_MARKER_Y * self.scale_y)
            time.sleep(0.05)
            print(f"{self.tag} [+] Setelah klik Klaim/Koleksi: tap kartu Slot 1 SATU KALI CEPAT di ({slot1_x}, {slot1_y}).", flush=True)
            self.tap(slot1_x, slot1_y)
            time.sleep(0.08)
            img_after = self.get_screenshot()
            # Jangan klik ulang walaupun OCR masih melihat tombol. Tap kedua sering
            # jatuh ke iklan/endcard dan membuka Play Store.

            if img_after is not None:
                cans_after = self.detect_shelf_cans(img_after)
                if not cans_after:
                    self.wait_ad_and_close_ad("Iklan Terbuka Setelah Klik Koleksi / Bebas Klik")
            return

        # 8b. Deteksi Bubble / Balon Hadiah Terbang dimatikan untuk Color Power Pop
        bubble = self.detect_floating_reward_bubble(ocr_items, img) if ENABLE_FLOATING_REWARD_DETECTION else None
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
                    print(f"{self.tag} [★] Kandidat reward statis di area popup ({bx}, {by}){corr_note}. Klik klaim/reward SATU KALI CEPAT...", flush=True)
                    clicked_reward = self.tap_reward_button_reliably(int(360 * sx), claim_y)
                    if not clicked_reward:
                        time.sleep(0.08)
                        return
                    self.record_tapped_coord(bx, by)
                    time.sleep(0.12)
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
            time.sleep(0.7)
            img_after = self.get_screenshot()
            if img_after is not None:
                cans_after = self.detect_shelf_cans(img_after)
                if not cans_after:
                    self.wait_ad_and_close_ad("Iklan Terbuka Setelah Klik Bubble Terbang")
            return

        # 9. Deteksi kotak/blok warna di grid
        front_cans = self.detect_shelf_cans(img)

        # 10. Jika tidak ada kartu cocok, bedakan antara board masih ada vs board hilang total.
        if not front_cans:
            bottom_cards_now = self.detect_bottom_cards(img)
            slot_cards_now = self.detect_lowest_slot_cards(img)
            board_has_cards = bool(bottom_cards_now) or any((c.get("color") and not c.get("empty")) for c in slot_cards_now)

            if not board_has_cards:
                print(f"{self.tag} [!] Tidak ada kotak/wadah bawah dan tidak ada kartu slot atas. Anggap sudah masuk iklan/halaman luar.", flush=True)
                self.recover_when_board_missing(img)
                return

            if ENABLE_AUTO_CLOSE_UNKNOWN_MODAL:
                close_x = detect_dialog_close_x_button(img, self.scale_x, self.scale_y)
                if close_x:
                    cx, cy, desc = close_x
                    print(f"{self.tag} [★] MENEMUKAN {desc} di ({cx}, {cy})! Menutup modal...", flush=True)
                    self.tap(cx, cy)
                    time.sleep(0.18)
                    return
            self.log_bottom_cards_once(img, force=True)
            self.log_lowest_slot_cards_once(img, force=True)
            free_slots = []
            for c in slot_cards_now:
                if not (c.get("color") and not c.get("empty") and c.get("cx") is not None and c.get("cy") is not None):
                    continue
                # Validasi terakhir sebelum "klik bebas": titik tap harus
                # benar-benar ada warna kartu. Kalau tidak, anggap slot kosong
                # walaupun deteksi kontur memberi warna dari area lain.
                point_color, point_ratio = self.colored_card_patch_info(
                    img, c["cx"], c["cy"], half_w=int(34 * self.scale_x), half_h=int(20 * self.scale_y)
                )
                if not point_color or point_ratio < 0.22:
                    print(f"{self.tag} [skip] S{c.get('slot')} terdeteksi {c.get('color')} tapi titik klik kosong/meragukan ratio={point_ratio:.2f} @({c.get('cx')},{c.get('cy')})", flush=True)
                    continue
                c["color"] = point_color
                free_slots.append(c)
            if free_slots:
                free_slots.sort(key=lambda c: c.get("slot", 99))
                c = free_slots[0]
                desc = ", ".join([f"S{x.get('slot')}={x.get('color')}@({x.get('cx')},{x.get('cy')})/{x.get('method','?')}" for x in free_slots])
                print(f"{self.tag} [⚡] Tidak ada warna cocok. KLIK 1 KARTU BEBAS yang valid, bukan slot kosong: {desc}", flush=True)
                self.tap(c["cx"], c["cy"])
                time.sleep(0.10)
                return

            print(f"{self.tag} [.] Board masih ada tapi tidak ada kartu bebas valid. Standby, tidak klik slot kosong/kotak bawah.", flush=True)
            time.sleep(0.25)
            return

        # 11. MODE BEBAS TURBO: Klik kotak/blok warna yang terdeteksi
        if front_cans:
            tap_points = [(c["cx"], c["cy"]) for c in front_cans]
            cols_desc = ", ".join([f"{c.get('color','?')} S{c.get('slot', c.get('col'))} klik@({c['cx']},{c['cy']}) raw_y={c.get('raw_cy','-')}" for c in front_cans])
            if DEBUG_COLOR_MARKERS_ONLY:
                print(f"{self.tag} [👁] MODE CEK POSISI: KARTU ATAS cocok terdeteksi tapi BELUM DIKLIK: {cols_desc}", flush=True)
                time.sleep(0.45)
                return
            print(f"{self.tag} [⚡⚡] TAP KARTU ATAS COCOK ({len(tap_points)} Kartu): {cols_desc}", flush=True)
            for tx, ty in tap_points:
                self.tap(tx, ty)
                time.sleep(0.08)
        else:
            shelf_cols_x = [int(x * sx) for x in SHELF_COLUMNS_X]
            fallback_points = [(x, int(765 * sy)) for x in shelf_cols_x]
            print(f"{self.tag} [⚡] Tidak ada kotak terdeteksi jelas. Fallback scan grid ringan...", flush=True)
            self.tap_burst(fallback_points, delay=0.01)

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
    print("      BOT COLOR POWER POP - MULTI-DEVICE PARALLEL ENGINE                 ", flush=True)
    print("==================================================================", flush=True)
    active_processes = {}
    main_pid = os.getpid()
    print("[+] Memindai semua perangkat Android yang terhubung via ADB...", flush=True)
    print(f"[+] Target Game: {GAME_DISPLAY_NAME} (package auto-detect; override: COLOR_POWER_POP_PACKAGE)", flush=True)
    print(f"[+] Aturan Aktif: Auto-Install, Main Ulang, Iklan {AD_WAIT_SECONDS}s, DANA (>= {MIN_WITHDRAWAL_RP}).\n", flush=True)
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
