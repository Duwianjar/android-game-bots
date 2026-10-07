#!/usr/bin/env python3
"""
auto_click_bot.py
Bot Android via ADB - deteksi & klik tombol X, Next >, >| Google Play
Pakai:  python3 auto_click_bot.py [serial]
"""

import subprocess, re, time, sys, os
import xml.etree.ElementTree as ET
from datetime import datetime

SERIAL = sys.argv[1] if len(sys.argv) > 1 else ""
LOG_DIR = "/Users/macbookair/bot_logs"
SHOT_DIR = "/Users/macbookair/bot_screenshots"
LOG_FILE = os.path.join(LOG_DIR, "bot.log")
HISTORY_FILE = os.path.join(LOG_DIR, "click_history.txt")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(SHOT_DIR, exist_ok=True)

APP_NAMES = {
    "com.android.chrome": "Chrome",
    "com.apnabankshop.juice": "Juice",
    "com.android.vending": "PlayStore",
    "com.google.android.gms": "GMS",
}


def log(msg):
    now = datetime.now().strftime("%H:%M:%S")
    line = f"[{now}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def history(msg):
    now = datetime.now().strftime("%H-%M-%S")
    with open(HISTORY_FILE, "a") as f:
        f.write(f"[{now}] {msg}\n")


def adb(args, timeout=10):
    cmd = ["adb"]
    if SERIAL:
        cmd += ["-s", SERIAL]
    cmd += args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except:
        return ""


def get_foreground():
    out = adb(["shell", "dumpsys", "activity", "activities"])
    for line in out.splitlines():
        if "mResumedActivity" in line or "topResumedActivity" in line:
            m = re.search(r'([a-z0-9._]+)/[a-zA-Z0-9._]+', line)
            if m:
                return m.group(1)
    out = adb(["shell", "dumpsys", "window"])
    for line in out.splitlines():
        if "mCurrentFocus" in line or "mFocusedApp" in line:
            m = re.search(r'([a-z0-9._]+)/[a-zA-Z0-9._]+', line)
            if m:
                return m.group(1)
    return ""


def get_screen():
    out = adb(["shell", "wm", "size"])
    m = re.search(r'(\d+)x(\d+)', out)
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)


def screenshot(prefix):
    ts = datetime.now().strftime("%H%M%S")
    path = os.path.join(SHOT_DIR, f"{prefix}_{ts}.png")
    adb(["shell", "screencap", "-p", "/sdcard/bs.png"], timeout=5)
    adb(["pull", "/sdcard/bs.png", path], timeout=5)
    return path


def dump_ui():
    adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"], timeout=5)
    cmd = ["adb"]
    if SERIAL:
        cmd += ["-s", SERIAL]
    cmd += ["shell", "cat", "/sdcard/ui.xml"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        s = r.stdout.strip()
    except:
        return None
    if not s or "<hierarchy" not in s:
        return None
    try:
        return ET.fromstring(s)
    except:
        return None


def find_nodes(root):
    nodes = []
    for n in root.iter("node"):
        text = (n.get("text") or "").strip()
        desc = (n.get("content-desc") or "").strip()
        bounds = n.get("bounds", "")
        rid = (n.get("resource-id") or "").strip()
        click = n.get("clickable", "false")
        label = text or desc
        nodes.append({"label": label, "text": text, "desc": desc,
                       "bounds": bounds, "rid": rid, "click": click})
    return nodes


def parse_bounds(b):
    m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', b)
    if not m:
        return None
    return ((int(m.group(1))+int(m.group(3)))//2, (int(m.group(2))+int(m.group(4)))//2)


def is_top_right(b, sw, sh):
    c = parse_bounds(b)
    if not c:
        return False
    return c[0] > sw * 0.75 and c[1] < sh * 0.25


def detect(nodes, sw, sh):
    results = []
    for n in nodes:
        label = n["label"].lower()
        desc = n["desc"].lower()
        rid = n["rid"].lower()
        b = n["bounds"]
        c = parse_bounds(b)
        if not c:
            continue

        # X / Close pojok kanan atas
        if is_top_right(b, sw, sh):
            if label in ('x', 'close', 'tutup', 'kembali') or 'close' in label:
                results.append(("X", n["label"], c, b))
                continue

        # >| Google Play
        if 'google play' in label or 'google play' in desc:
            results.append(("GOOGLE_PLAY", n["label"], c, b))
            continue

        # Next / >
        if label in ('>', 'next', 'lanjut', '▶', '»', '>|'):
            results.append(("NEXT", n["label"], c, b))
            continue

        # rid next/play (hanya next & install, bukan "playable" yang terlalu luas)
        if 'next' in rid or 'install' in rid:
            results.append(("NEXT_RID", n["rid"], c, b))
            continue

    # Prioritas: X > GOOGLE_PLAY > NEXT
    priority = {"X": 0, "GOOGLE_PLAY": 1, "NEXT": 2, "NEXT_RID": 3}
    results.sort(key=lambda r: priority.get(r[0], 9))
    return results


def tap(xy):
    adb(["shell", "input", "tap", str(xy[0]), str(xy[1])])


def back():
    adb(["shell", "input", "keyevent", "4"])


def main():
    sw, sh = get_screen()
    log(f"Screen: {sw}x{sh} | Serial: {SERIAL or 'default'}")
    log("Bot aktif. Ctrl+C untuk berhenti.")
    log(f"Log: {LOG_FILE}")
    log(f"History: {HISTORY_FILE}")
    log("=" * 60)

    prev_app = ""
    back_done = set()
    last_click_xy = None
    no_click_count = 0
    last_hb = 0.0

    while True:
        # === Heartbeat log setiap detik ===
        now_ts = time.time()
        if now_ts - last_hb >= 1.0:
            last_hb = now_ts
            hb_app = APP_NAMES.get(prev_app, prev_app) if prev_app else "(menunggu)"
            log(f"HEARTBEAT | app={hb_app} | last_click={last_click_xy}")

        fg = get_foreground()
        name = APP_NAMES.get(fg, fg)

        if fg != prev_app:
            log(f"APP -> {name} ({fg})")
            prev_app = fg
            last_click_xy = None  # reset dedup saat ganti app

        # Chrome/Juice: back sekali saat buka
        if fg in ("com.android.chrome", "com.apnabankshop.juice"):
            if fg not in back_done:
                log(f"  {name} dibuka -> BACK sekali")
                back()
                back_done.add(fg)
                history(f"BACK | {name}")
                screenshot("back")
                time.sleep(1)
                continue
        else:
            back_done.discard("com.android.chrome")
            back_done.discard("com.apnabankshop.juice")

        root = dump_ui()
        if not root:
            time.sleep(0.3)
            continue

        nodes = find_nodes(root)
        labeled = [n for n in nodes if n["label"]]
        if labeled:
            log(f"  UI nodes ({len(labeled)}):")
            for n in labeled:
                log(f"    '{n['label']}' rid={n['rid']} b={n['bounds']} click={n['click']}")

        targets = detect(nodes, sw, sh)

        if not targets:
            no_click_count += 1
            if no_click_count <= 2:
                log("  -> Tidak ada tombol. GAK KLIK APA-APA.")
            time.sleep(0.3)
            continue

        no_click_count = 0
        t = targets[0]
        ttype, tinfo, txy, tbounds = t

        # Dedup: jangan klik koordinat yang sama 2x berturut-turut
        if txy == last_click_xy:
            log(f"  -> {ttype} sudah diklik di {txy}. SKIP (dedup).")
            time.sleep(0.3)
            continue

        log(f"  >>> KLIK {ttype} '{tinfo}' di {txy}")
        tap(txy)
        last_click_xy = txy
        history(f"{ttype} | {tinfo} | {txy} | {name}")
        screenshot(ttype)
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Bot berhenti.")
