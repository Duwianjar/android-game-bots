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

# Mode cepat: logging UI lengkap dan screenshot setiap klik membuat loop lambat.
VERBOSE_UI = os.environ.get("AUTO_CLICK_VERBOSE_UI", "0") == "1"
SAVE_SCREENSHOT = os.environ.get("AUTO_CLICK_SCREENSHOT", "0") == "1"
LOOP_SLEEP = float(os.environ.get("AUTO_CLICK_LOOP_SLEEP", "0.08"))
AFTER_CLICK_SLEEP = float(os.environ.get("AUTO_CLICK_AFTER_CLICK_SLEEP", "0.18"))
AFTER_BACK_SLEEP = float(os.environ.get("AUTO_CLICK_AFTER_BACK_SLEEP", "0.35"))
HEARTBEAT_INTERVAL = float(os.environ.get("AUTO_CLICK_HEARTBEAT_INTERVAL", "2.0"))

# Mode turbo 3x: jangan tunggu dump UI untuk tombol close iklan yang posisinya umum.
# Bisa dimatikan: AUTO_CLICK_TURBO=0
TURBO_MODE = os.environ.get("AUTO_CLICK_TURBO", "1") != "0"
TURBO_PROBE_INTERVAL = float(os.environ.get("AUTO_CLICK_TURBO_PROBE_INTERVAL", "0.35"))
TURBO_MIN_AD_AGE = float(os.environ.get("AUTO_CLICK_TURBO_MIN_AD_AGE", "0.7"))
TURBO_DUMP_EVERY_PROBES = int(os.environ.get("AUTO_CLICK_TURBO_DUMP_EVERY_PROBES", "3"))

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


def parse_component(line):
    # Format dumpsys bisa berubah, contoh:
    #   com.game/.AppActivity
    #   com.game/com.vendor.ads.FullscreenActivity
    #   ActivityRecord{... u0 com.game/.AppActivity t123}
    m = re.search(r'([a-z0-9_]+(?:\.[a-z0-9_]+)+)/(?:[a-zA-Z0-9_.$]+(?:\.[a-zA-Z0-9_.$]+)*|\.[a-zA-Z0-9_.$]+)', line)
    return m.group(1) if m else ""


def parse_component_full(line):
    m = re.search(r'(([a-z0-9_]+(?:\.[a-z0-9_]+)+)/(?:[a-zA-Z0-9_.$]+(?:\.[a-zA-Z0-9_.$]+)*|\.[a-zA-Z0-9_.$]+))', line)
    if not m:
        return "", ""
    return m.group(2), m.group(1)


def get_foreground_detail():
    checks = (
        (["shell", "dumpsys", "window"], ("mCurrentFocus", "mFocusedApp")),
        (["shell", "dumpsys", "activity", "activities"], ("mResumedActivity", "topResumedActivity", "ResumedActivity")),
        (["shell", "dumpsys", "activity", "top"], ("ACTIVITY",)),
    )
    for cmd, markers in checks:
        out = adb(cmd, timeout=6)
        for line in out.splitlines():
            if any(marker in line for marker in markers):
                pkg, comp = parse_component_full(line)
                if pkg:
                    return pkg, comp
    return "", ""


def get_foreground():
    checks = (
        (["shell", "dumpsys", "window"], ("mCurrentFocus", "mFocusedApp")),
        (["shell", "dumpsys", "activity", "activities"], ("mResumedActivity", "topResumedActivity", "ResumedActivity")),
        (["shell", "dumpsys", "activity", "top"], ("ACTIVITY",)),
    )
    for cmd, markers in checks:
        out = adb(cmd, timeout=6)
        for line in out.splitlines():
            if any(marker in line for marker in markers):
                pkg = parse_component(line)
                if pkg:
                    return pkg
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

        # X popup/dialog iklan (contoh MBridge feedback).
        # Tombol ini sering berada di kanan atas dialog, bukan kanan atas layar,
        # sehingga rule is_top_right() lama melewatkannya.
        if n["click"] == "true" and label in ('x', 'close', 'tutup'):
            if c[0] > sw * 0.65 and c[1] < sh * 0.45:
                results.append(("X", n["label"] or n["rid"], c, b))
                continue

        if 'mbridge_video_common_alertview_confirm_button' in rid and c[0] > sw * 0.65:
            results.append(("X", n["label"] or n["rid"], c, b))
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


def is_ad_activity(component):
    c = (component or "").lower()
    ad_keywords = (
        "mbridge", "mintegral", "reward", "interstitial", "adactivity",
        "google.android.gms.ads", "applovin", "unity", "vungle",
        "bytedance", "ironsource", "chartboost", "facebook.ads",
    )
    return any(k in c for k in ad_keywords)


def turbo_close_point(sw, sh):
    # Koordinat close paling umum di iklan portrait 720x1612: sekitar (676,136).
    return (int(sw * 0.94), int(sh * 0.085))


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
    prev_component = ""
    ad_started_at = 0.0
    last_turbo_probe = 0.0
    turbo_probe_count = 0

    while True:
        # === Heartbeat log berkala ===
        now_ts = time.time()
        if now_ts - last_hb >= HEARTBEAT_INTERVAL:
            last_hb = now_ts
            hb_app = APP_NAMES.get(prev_app, prev_app) if prev_app else "(menunggu)"
            log(f"HEARTBEAT | app={hb_app} | last_click={last_click_xy}")

        fg, component = get_foreground_detail()
        name = APP_NAMES.get(fg, fg)

        if not fg:
            # Jangan reset prev_app saat dumpsys gagal sebentar (sering terjadi ketika iklan/Play Store transisi).
            time.sleep(LOOP_SLEEP)
            continue

        if fg != prev_app or component != prev_component:
            log(f"APP -> {name} ({fg}) {component}")
            prev_app = fg
            prev_component = component
            last_click_xy = None  # reset dedup saat ganti app/activity
            if is_ad_activity(component):
                ad_started_at = time.time()
                turbo_probe_count = 0

        # Chrome/Juice: back sekali saat buka
        if fg in ("com.android.chrome", "com.apnabankshop.juice"):
            if fg not in back_done:
                log(f"  {name} dibuka -> BACK sekali")
                back()
                back_done.add(fg)
                history(f"BACK | {name}")
                if SAVE_SCREENSHOT:
                    screenshot("back")
                time.sleep(AFTER_BACK_SLEEP)
                continue
        else:
            back_done.discard("com.android.chrome")
            back_done.discard("com.apnabankshop.juice")

        if TURBO_MODE and is_ad_activity(component):
            now_turbo = time.time()
            if (now_turbo - ad_started_at) >= TURBO_MIN_AD_AGE and (now_turbo - last_turbo_probe) >= TURBO_PROBE_INTERVAL:
                txy = turbo_close_point(sw, sh)
                log(f"  >>> TURBO TAP close-probe di {txy}")
                tap(txy)
                history(f"TURBO_X | close-probe | {txy} | {name}")
                last_turbo_probe = now_turbo
                turbo_probe_count += 1
                # Tetap dump UI tiap beberapa probe untuk menangani popup feedback/X non-standar.
                if TURBO_DUMP_EVERY_PROBES <= 0 or (turbo_probe_count % TURBO_DUMP_EVERY_PROBES) != 0:
                    time.sleep(AFTER_CLICK_SLEEP)
                    continue

        root = dump_ui()
        if not root:
            time.sleep(LOOP_SLEEP)
            continue

        nodes = find_nodes(root)
        labeled = [n for n in nodes if n["label"]]
        if VERBOSE_UI and labeled:
            log(f"  UI nodes ({len(labeled)}):")
            for n in labeled:
                log(f"    '{n['label']}' rid={n['rid']} b={n['bounds']} click={n['click']}")

        targets = detect(nodes, sw, sh)

        if not targets:
            no_click_count += 1
            if no_click_count <= 2:
                log("  -> Tidak ada tombol. GAK KLIK APA-APA.")
            time.sleep(LOOP_SLEEP)
            continue

        no_click_count = 0
        t = targets[0]
        ttype, tinfo, txy, tbounds = t

        # Dedup: jangan klik koordinat yang sama 2x berturut-turut
        if txy == last_click_xy:
            log(f"  -> {ttype} sudah diklik di {txy}. SKIP (dedup).")
            time.sleep(LOOP_SLEEP)
            continue

        log(f"  >>> KLIK {ttype} '{tinfo}' di {txy}")
        tap(txy)
        last_click_xy = txy
        history(f"{ttype} | {tinfo} | {txy} | {name}")
        if SAVE_SCREENSHOT:
            screenshot(ttype)
        time.sleep(AFTER_CLICK_SLEEP)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Bot berhenti.")
