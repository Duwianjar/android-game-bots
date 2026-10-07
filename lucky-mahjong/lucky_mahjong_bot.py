#!/usr/bin/env python3
"""Lucky Mahjong 2 automation bot (com.lucky.mahjong2).

Bot sederhana berbasis screenshot:
- mengikuti/tutorial otomatis dengan klik pasangan ubin yang terbuka
- mendeteksi ubin putih/aktif saja (bukan ubin gelap/tertutup)
- mencocokkan pasangan berdasarkan kemiripan gambar simbol
- menangani popup dasar: peti hadiah, halaman tukar, iklan/Play Store
"""
import os
import re
import time
import signal
import subprocess
import multiprocessing
from typing import List, Dict, Optional, Tuple

import cv2
import numpy as np

PACKAGE_NAME = "com.lucky.mahjong2"
LAUNCH_ACTIVITY = "com.lucky.mahjong2/.GameActivity"
OCR_HELPER_PATH = "/Users/macbookair/ocr_helper"
DANA_ACCOUNT = "082220649676"
DANA_NAME = "Duwi Anjar Ari Wibowo"


def get_connected_devices():
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3, check=False)
        devices = []
        for line in res.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices
    except Exception:
        return []


def is_scrcpy_running_for(serial):
    try:
        out = subprocess.check_output(["pgrep", "-fl", "scrcpy"], text=True, stderr=subprocess.DEVNULL)
        return serial in out and "Lucky Mahjong" in out
    except Exception:
        return False


def ensure_scrcpy_running(serial):
    if is_scrcpy_running_for(serial):
        return
    try:
        subprocess.Popen(
            ["scrcpy", "-s", serial, "--window-title", f"Lucky Mahjong - {serial}", "--max-fps=25", "--no-audio"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.55)
    except Exception as e:
        print(f"[{serial}] [!] scrcpy tidak dibuka: {e}", flush=True)


class LuckyMahjongRunner:
    def __init__(self, serial: str):
        self.serial = serial
        self.tag = f"[{serial}]"
        self.width = 720
        self.height = 1640
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.step_counter = 0
        self.no_match_streak = 0
        self.last_popup_check = 0
        self.fast_mode = True
        self.last_withdraw_attempt = 0

    def run_adb(self, cmd, timeout=5.0):
        try:
            res = subprocess.run(["adb", "-s", self.serial] + cmd, capture_output=True, text=True, timeout=timeout, check=False)
            return res.stdout.strip()
        except Exception:
            return ""

    def tap(self, x, y):
        subprocess.run(["adb", "-s", self.serial, "shell", f"input tap {int(x)} {int(y)}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def tap_pair_fast(self, x1, y1, x2, y2):
        # Dua tap dalam satu adb shell jauh lebih cepat daripada dua subprocess terpisah.
        cmd = f"input tap {int(x1)} {int(y1)}; sleep 0.05; input tap {int(x2)} {int(y2)}"
        subprocess.run(["adb", "-s", self.serial, "shell", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def press_back(self):
        subprocess.run(["adb", "-s", self.serial, "shell", "input keyevent 4"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def input_text(self, text):
        safe = text.replace(" ", "%s")
        subprocess.run(["adb", "-s", self.serial, "shell", f"input text {safe}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def auto_fill_tukar_dana(self):
        """Isi halaman Tukar dengan DANA sesuai data user, lalu tekan tombol Tukar."""
        now = time.time()
        if now - self.last_withdraw_attempt < 12:
            return True
        self.last_withdraw_attempt = now
        sx, sy = self.scale_x, self.scale_y
        print(f"{self.tag} [💸] Halaman Tukar: pilih DANA, isi nomor/nama, lalu klik TUKAR", flush=True)
        # pilih metode DANA dan nominal Rp10
        self.tap(int(112 * sx), int(560 * sy))
        time.sleep(0.18)
        self.tap(int(140 * sx), int(720 * sy))
        time.sleep(0.18)
        # isi akun DANA
        self.tap(int(210 * sx), int(842 * sy))
        time.sleep(0.15)
        self.input_text(DANA_ACCOUNT)
        time.sleep(0.25)
        # isi nama penerima
        self.tap(int(240 * sx), int(958 * sy))
        time.sleep(0.15)
        self.input_text(DANA_NAME)
        time.sleep(0.25)
        # tutup keyboard jika muncul, centang Ingat Saya, lalu klik Tukar
        self.press_back()
        time.sleep(0.25)
        self.tap(int(58 * sx), int(1038 * sy))
        time.sleep(0.15)
        self.tap(int(360 * sx), int(1500 * sy))
        time.sleep(1.2)
        return True

    def bring_game_to_foreground(self):
        self.run_adb(["shell", "am", "start", "-n", LAUNCH_ACTIVITY], timeout=5)
        self.run_adb(["shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"], timeout=5)

    def get_focus(self):
        return self.run_adb(["shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"], timeout=4)

    def get_screenshot(self):
        try:
            res = subprocess.run(["adb", "-s", self.serial, "exec-out", "screencap", "-p"], capture_output=True, timeout=5, check=False)
            if not res.stdout:
                return None
            arr = np.frombuffer(res.stdout, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                self.height, self.width = img.shape[:2]
                self.scale_x = self.width / 720.0
                self.scale_y = self.height / 1640.0
            return img
        except Exception:
            return None

    def run_full_ocr(self, img):
        if not os.path.exists(OCR_HELPER_PATH) or img is None:
            return []
        tmp = f"/tmp/lucky_mahjong_ocr_{self.serial}.png"
        try:
            cv2.imwrite(tmp, img)
            out = subprocess.check_output([OCR_HELPER_PATH, tmp], stderr=subprocess.DEVNULL, timeout=2.5).decode("utf-8")
            items = []
            for line in out.strip().splitlines():
                parts = line.split("|")
                if len(parts) != 2:
                    continue
                text = parts[0].strip()
                coords = [float(x) for x in parts[1].split(",")]
                cx = int((coords[0] + coords[2] / 2.0) * self.width)
                cy = int((1.0 - (coords[1] + coords[3] / 2.0)) * self.height)
                items.append({"text": text, "cx": cx, "cy": cy})
            return items
        except Exception:
            return []

    def handle_focus_and_popups(self, img, ocr_items):
        focus = self.get_focus()
        if PACKAGE_NAME not in focus:
            # Iklan/Play Store/Browser: balik ke game.
            if "com.android.vending" in focus or "chrome" in focus.lower() or "browser" in focus.lower():
                print(f"{self.tag} [.] Fokus iklan/PlayStore, tekan BACK lalu bawa game ke depan", flush=True)
                self.press_back()
                time.sleep(0.7)
            self.bring_game_to_foreground()
            time.sleep(0.7)
            return True

        text_all = " ".join(it["text"].lower() for it in ocr_items)
        sx, sy = self.scale_x, self.scale_y

        # Status penukaran sedang ditinjau / hadiah diterima / tombol cek
        if any(k in text_all for k in ["ditinjau", "hadiah akan diterima", "tinjau"]):
            print(f"{self.tag} [💸] Status penukaran DITINJAU terdeteksi, klik CEK/kembali", flush=True)
            self.tap(int(360 * sx), int(1030 * sy))
            time.sleep(0.6)
            return True

        # Iklan overlay/endcard kadang masih di dalam package game. Jangan klik tombol Buka iklan; tutup/back saja.
        if any(k in text_all for k in ["ad 1 of", "ad 2 of", "ad 3 of", "google play", "bersponsor", "install", "instal"]):
            print(f"{self.tag} [.] Iklan overlay terdeteksi, tekan BACK", flush=True)
            self.press_back()
            time.sleep(0.55)
            return True

        # Halaman penukaran: user meminta pakai DANA dengan nomor/nama yang diberikan.
        if any(k in text_all for k in ["metode penukaran", "akun dana", "akun gopay", "akun ovo", "nama penerima", "riwayat penukaran"]):
            return self.auto_fill_tukar_dana()

        # Banner saldo sudah 100% / Tukarkan Sekarang: masuk ke halaman Tukar.
        if ("tukarkan sekarang" in text_all or "100%" in text_all) and "tukar" in text_all and "level" in text_all:
            print(f"{self.tag} [💸] Saldo 100% terdeteksi, klik tombol Tukar", flush=True)
            self.tap(int(585 * sx), int(160 * sy))
            time.sleep(0.8)
            return True

        # Popup selesai level: utamakan LEVEL BERIKUTNYA agar tidak wajib nonton iklan peti.
        if "level berikutnya" in text_all:
            print(f"{self.tag} [★] Popup selesai level, klik LEVEL BERIKUTNYA", flush=True)
            self.tap(int(360 * sx), int(1410 * sy))
            time.sleep(0.5)
            return True

        # Peti hadiah/tutorial reward.
        if any(k in text_all for k in ["buka peti", "peti keberuntungan", "buka"]):
            # Jika tombol level berikutnya belum muncul, klik BUKA sesuai tutorial.
            print(f"{self.tag} [★] Popup peti/hadiah, klik BUKA/lanjut", flush=True)
            self.tap(int(360 * sx), int(1275 * sy))
            time.sleep(0.55)
            return True

        # Prompt Tukar saat tutorial selesai: klik jika tangan memaksa, lalu balik di handler berikutnya.
        if "ketuk di sini" in text_all and "menukarkan" in text_all:
            print(f"{self.tag} [★] Tutorial Tukar, klik Tukar lalu nanti kembali", flush=True)
            self.tap(int(585 * sx), int(160 * sy))
            time.sleep(0.55)
            return True

        # Tombol umum jika ada.
        for it in ocr_items:
            t = it["text"].lower()
            if any(k in t for k in ["lanjut", "continue", "ok", "baik", "klaim", "koleksi", "terima"]):
                if it["cy"] > int(450 * sy):
                    print(f"{self.tag} [★] Klik tombol '{it['text']}'", flush=True)
                    self.tap(it["cx"], it["cy"])
                    time.sleep(0.5)
                    return True
        return False

    def detect_hint_highlight_pair(self, img):
        """Deteksi ubin yang disorot warna cyan oleh fitur Hint, lalu klik pasangan itu."""
        if img is None:
            return None
        # Highlight hint berwarna cyan/tosca: channel B dan G tinggi, R relatif rendah.
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        b, g, r = cv2.split(img)
        mask = (b > 115) & (g > 120) & (r < 185) & (hsv[:, :, 1] > 35)
        mask[:int(430 * self.scale_y), :] = False
        mask[int(1370 * self.scale_y):, :] = False
        m = mask.astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)))
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            if area >= 6000 * self.scale_x * self.scale_y and 70 * self.scale_x <= w <= 180 * self.scale_x and 70 * self.scale_y <= h <= 190 * self.scale_y:
                candidates.append({"cx": x + w // 2, "cy": y + h // 2, "area": area})
        if len(candidates) >= 2:
            candidates.sort(key=lambda it: it["area"], reverse=True)
            return candidates[0], candidates[1]
        return None

    def detect_open_tiles(self, img) -> List[Dict]:
        """Deteksi ubin aktif/putih yang bisa diklik. Ubin gelap/tertutup diabaikan."""
        if img is None:
            return []
        sx, sy = self.scale_x, self.scale_y
        # Area main board (abaikan header dan tombol bawah)
        y1, y2 = int(430 * sy), int(1370 * sy)
        x1, x2 = int(35 * sx), int(685 * sx)
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            return []

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        # White/off-white tile body: saturasi rendah-menengah, value tinggi. Ubin gelap tidak lolos.
        mask = ((hsv[:, :, 1] < 125) & (hsv[:, :, 2] > 115)).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            if area < 4500 * sx * sy:
                continue
            # Tile size on 720x1640 is ~120-140w x 150-170h. Adjacent tiles can merge.
            # Izinkan kontur gabungan hingga beberapa baris/kolom; nanti akan di-split.
            if not (70 * sy <= h <= 560 * sy and 55 * sx <= w <= 650 * sx):
                continue
            gx, gy = x1 + x, y1 + y
            # Split merged horizontal/vertical runs into individual tile cells.
            # Ukuran ubin game ini relatif stabil di 720x1640: ~132x164 px.
            # Kontur sering menyatu antar ubin, jadi pecah pakai pitch tetap lalu filter occupancy.
            # Pada baris bawah ubin sering overlap, pitch efektif sekitar 110px.
            tile_w = (110 * sx) if w >= 450 * sx else (132 * sx)
            tile_h = 150 * sy if h < 320 * sy else 164 * sy
            n_cols = max(1, min(6, int(round(w / tile_w))))
            n_rows = max(1, min(5, int(round(h / tile_h))))
            part_w = w / n_cols
            part_h = h / n_rows
            for rr in range(n_rows):
                for cc in range(n_cols):
                    bx = int(gx + cc * part_w)
                    by = int(gy + rr * part_h)
                    bw = int(part_w)
                    bh = int(part_h)
                    # Pastikan cell benar-benar berisi badan ubin putih, bukan ruang kosong di dalam kontur gabungan.
                    mx1, my1 = max(0, bx - x1), max(0, by - y1)
                    mx2, my2 = min(mask.shape[1], mx1 + bw), min(mask.shape[0], my1 + bh)
                    occ = float(np.mean(mask[my1:my2, mx1:mx2] > 0)) if mx2 > mx1 and my2 > my1 else 0.0
                    if occ >= 0.35:
                        boxes.append((bx, by, bw, bh))

        # De-dupe near-identical boxes.
        boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
        final = []
        for b in boxes:
            cx, cy = b[0] + b[2] // 2, b[1] + b[3] // 2
            if any(abs(cx - (e[0] + e[2] // 2)) < 25 * sx and abs(cy - (e[1] + e[3] // 2)) < 25 * sy for e in final):
                continue
            final.append(b)

        tiles = []
        for idx, (x, y, w, h) in enumerate(final):
            # Inner crop for symbol matching.
            ix1 = max(0, int(x + 16 * sx)); ix2 = min(self.width, int(x + w - 16 * sx))
            iy1 = max(0, int(y + 18 * sy)); iy2 = min(self.height, int(y + h - 14 * sy))
            if ix2 <= ix1 or iy2 <= iy1:
                continue
            crop_tile = img[iy1:iy2, ix1:ix2]
            gray = cv2.cvtColor(crop_tile, cv2.COLOR_BGR2GRAY)
            feat = cv2.resize(gray, (64, 64)).astype(np.float32)
            tiles.append({"id": idx, "box": (x, y, w, h), "cx": x + w // 2, "cy": y + h // 2, "feat": feat})
        return tiles

    def tile_similarity(self, a, b):
        fa, fb = a["feat"], b["feat"]
        # Correlation: identical symbols high; different symbols low.
        va = fa.flatten(); vb = fb.flatten()
        if np.std(va) < 1 or np.std(vb) < 1:
            return -1.0, 999999.0
        corr = float(np.corrcoef(va, vb)[0, 1])
        mse = float(np.mean((fa - fb) ** 2))
        return corr, mse

    def find_best_pair(self, tiles):
        best = None
        for i in range(len(tiles)):
            for j in range(i + 1, len(tiles)):
                corr, mse = self.tile_similarity(tiles[i], tiles[j])
                # Threshold longgar untuk variasi scale/lighting, tapi cukup ketat agar tidak salah pair.
                if corr >= 0.90 or mse <= 650:
                    score = corr - (mse / 50000.0)
                    if best is None or score > best[0]:
                        best = (score, tiles[i], tiles[j], corr, mse)
        return best

    def play_step(self):
        self.step_counter += 1
        img = self.get_screenshot()
        if img is None:
            time.sleep(0.08)
            return

        # PRIORITY CHECK: setiap beberapa step cek OCR dulu untuk Tukar Sekarang / halaman penarikan.
        if self.step_counter % 5 == 1:
            ocr = self.run_full_ocr(img)
            if self.handle_focus_and_popups(img, ocr):
                return

        # FAST PATH: mainkan board dulu tanpa OCR/dumpsys (OCR sangat lambat).
        hint_pair = self.detect_hint_highlight_pair(img)
        if hint_pair:
            a, b = hint_pair
            print(f"{self.tag} [💡] Klik pasangan hasil Hint ({a['cx']},{a['cy']}) -> ({b['cx']},{b['cy']})", flush=True)
            self.tap_pair_fast(a["cx"], a["cy"], b["cx"], b["cy"])
            self.no_match_streak = 0
            time.sleep(0.12)
            return

        tiles = self.detect_open_tiles(img)
        pair = self.find_best_pair(tiles)
        if pair:
            _, a, b, corr, mse = pair
            print(f"{self.tag} [🀄] Match pair ({a['cx']},{a['cy']}) -> ({b['cx']},{b['cy']}) corr={corr:.3f} mse={mse:.0f} tiles={len(tiles)}", flush=True)
            self.tap_pair_fast(a["cx"], a["cy"], b["cx"], b["cy"])
            self.no_match_streak = 0
            time.sleep(0.12)
            return

        # SLOW PATH: baru OCR untuk popup/iklan/reward ketika tidak ada gerakan board.
        should_check_popup = (self.step_counter - self.last_popup_check >= 2) or len(tiles) <= 1
        if should_check_popup:
            self.last_popup_check = self.step_counter
            ocr = self.run_full_ocr(img)
            if self.handle_focus_and_popups(img, ocr):
                return

        self.no_match_streak += 1
        print(f"{self.tag} [.] Tidak ada pasangan terbuka. tiles={len(tiles)} streak={self.no_match_streak}", flush=True)
        if self.no_match_streak >= 2:
            # Mode cepat: bila tidak yakin, pakai hint lebih cepat daripada menunggu lama.
            print(f"{self.tag} [💡] Stuck cepat, klik hint", flush=True)
            self.tap(int(360 * self.scale_x), int(1560 * self.scale_y))
            self.no_match_streak = 0
            time.sleep(0.35)
        else:
            time.sleep(0.08)


def run_device_worker(serial, parent_pid):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    print(f"[{serial}] [+] Worker aktif untuk Lucky Mahjong ({serial})", flush=True)
    runner = LuckyMahjongRunner(serial)
    runner.bring_game_to_foreground()
    time.sleep(0.55)
    try:
        while True:
        last_click_pos = None
        same_click_count = 0
        max_same_click = 3  # Force BACK setelah 3x klik posisi sama

            if os.getppid() != parent_pid:
                break
            runner.play_step()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        print(f"[{serial}] [!] Worker error: {e}", flush=True)


def main():
    print("==================================================================", flush=True)
    print("      BOT LUCKY MAHJONG 2 - AUTO MATCH ENGINE", flush=True)
    print("==================================================================", flush=True)
    print(f"[+] Target Game: {PACKAGE_NAME}", flush=True)
    print("[+] Tekan Ctrl+C untuk berhenti.\n", flush=True)
    active = {}
    parent = os.getpid()
    try:
        while True:
            devices = get_connected_devices()
            for serial in list(active.keys()):
                if serial not in devices or not active[serial].is_alive():
                    try:
                        active[serial].terminate()
                        active[serial].join(timeout=1)
                    except Exception:
                        pass
                    del active[serial]
            for serial in devices:
                if serial not in active:
                    print(f"[+] Device terdeteksi: {serial}", flush=True)
                    ensure_scrcpy_running(serial)
                    p = multiprocessing.Process(target=run_device_worker, args=(serial, parent), daemon=True)
                    p.start()
                    active[serial] = p
            if not devices:
                print("[!] Tidak ada device ADB aktif...", end="\r", flush=True)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n[+] Menghentikan worker...", flush=True)
        for p in active.values():
            try:
                p.terminate()
                p.join(timeout=1)
            except Exception:
                pass
        print("[+] Selesai.", flush=True)


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    main()
