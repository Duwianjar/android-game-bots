#!/usr/bin/env python3
"""Periodic Telegram reporter untuk Soda Pack Puzzle Android bot.

Fitur:
- Notifikasi Telegram HANYA dikirim jika saldo berubah (bertambah atau berkurang).
- Jika saldo tidak bertambah selama 7 menit, dikirim notifikasi peringatan Bottleneck / bot macet.
- Konfigurasi token & chat ID mengambil dari /Users/macbookair/telegram_sender.py.
"""
import html
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import requests

HOME = Path('/Users/macbookair')
SODA_BOT_PATH = HOME / 'soda_pack_puzzle_bot.py'
TELEGRAM_SENDER_PATH = HOME / 'telegram_sender.py'
PACKAGE_NAME = 'com.soda.pack.puzzle'
INTERVAL_SECONDS = int(os.environ.get('SODA_TG_INTERVAL', '45'))
STALE_SECONDS = int(os.environ.get('SODA_TG_STALE_SECONDS', '420'))  # 7 menit = 420 detik
STATE_PATH = HOME / 'soda_telegram_reporter_state.json'


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def run(cmd, timeout=6, text=True):
    try:
        return subprocess.run(cmd, capture_output=True, text=text, timeout=timeout, check=False)
    except Exception as e:
        class R:
            stdout = '' if text else b''
            stderr = str(e)
            returncode = 999
        return R()


def get_device():
    res = run(['adb', 'devices'], timeout=4)
    for line in res.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == 'device':
            return parts[0]
    return None


def get_focus(serial):
    res = run(['adb', '-s', serial, 'shell', "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"], timeout=4)
    return res.stdout.strip()


def get_screenshot(serial):
    res = run(['adb', '-s', serial, 'exec-out', 'screencap', '-p'], timeout=6, text=False)
    data = res.stdout if isinstance(res.stdout, (bytes, bytearray)) else b''
    if not data:
        return None
    arr = np.frombuffer(data, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def get_bot_pids():
    res = run(['bash', '-lc', "pgrep -fl '/Users/macbookair/soda_pack_puzzle_bot.py' || true"], timeout=4)
    pids = []
    for line in res.stdout.splitlines():
        if 'pgrep' in line:
            continue
        if line.strip():
            pids.append(line.strip())
    return pids


def parse_rp_text(text):
    if not text:
        return None
    t = text.replace('=', '').replace('~', '').replace('≈', '').replace('FRp', 'Rp').replace('ERp', 'Rp')
    t = t.replace('Rpo', 'Rp0').replace('RpO', 'Rp0').replace('RpI', 'Rp1').replace('Rpl', 'Rp1')
    m = re.search(r'Rp\s*([0-9][0-9.,]*)', t, re.I)
    if not m:
        return None
    raw = m.group(1).strip('.,')
    return raw


def saldo_value(raw):
    if raw is None:
        return None
    txt = str(raw).strip()
    if not txt:
        return None
    txt = re.sub(r'[^0-9,.]', '', txt)
    if not txt:
        return None
    if ',' in txt and '.' in txt:
        txt = txt.replace('.', '').replace(',', '.')
    elif ',' in txt:
        txt = txt.replace(',', '.')
    try:
        return float(txt)
    except ValueError:
        return None


def format_saldo_display(raw):
    if raw is None:
        return '-'
    val = saldo_value(raw)
    if val is None:
        return str(raw)
    if val.is_integer():
        return f"Rp {int(val):,}".replace(',', '.')
    return f"Rp {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def load_state():
    try:
        if STATE_PATH.exists():
            return json.loads(STATE_PATH.read_text())
    except Exception:
        pass
    return {}


def save_state(state):
    try:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    except Exception:
        pass


def collect_status():
    status = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB'),
        'device': None,
        'focus': '-',
        'in_game': False,
        'bot_running': False,
        'bot_pids': [],
        'saldo_rp': None,
        'saldo_ticket': None,
        'level': None,
        'queue_left': None,
        'target_colors': [],
        'front_cans': [],
        'ocr_summary': [],
        'error': None,
    }

    serial = get_device()
    status['device'] = serial
    status['bot_pids'] = get_bot_pids()
    status['bot_running'] = bool(status['bot_pids'])
    if not serial:
        status['error'] = 'Tidak ada device ADB aktif'
        return status

    focus = get_focus(serial)
    status['focus'] = focus[-260:] if focus else '-'
    status['in_game'] = PACKAGE_NAME in focus

    img = get_screenshot(serial)
    if img is None:
        status['error'] = 'Gagal mengambil screenshot'
        return status

    try:
        soda = load_module(SODA_BOT_PATH, 'soda_bot_for_report')
        runner = soda.CanSortRunner(serial)
        runner.height, runner.width = img.shape[:2]
        runner.scale_x = runner.width / 720.0
        runner.scale_y = runner.height / 1640.0
        ocr = runner.run_full_ocr(img)
        status['ocr_summary'] = [it.get('text', '') for it in ocr[:12] if it.get('text')]

        # Header: tiket/koin kiri dan =Rp pada baris atas.
        for it in ocr:
            text = it.get('text', '')
            cx, cy = it.get('cx', 0), it.get('cy', 0)
            if 40 * runner.scale_y <= cy <= 170 * runner.scale_y:
                rp = parse_rp_text(text)
                if rp is not None:
                    status['saldo_rp'] = rp
                elif cx <= 230 * runner.scale_x:
                    m = re.search(r'[0-9][0-9.,]*', text)
                    if m:
                        status['saldo_ticket'] = m.group(0)
            if status['level'] is None:
                m = re.search(r'level\s*[: ]?\s*(\d+)', text, re.I)
                if m:
                    status['level'] = m.group(1)
            if status['queue_left'] is None and 760 * runner.scale_y <= cy <= 920 * runner.scale_y:
                if re.fullmatch(r'\d{1,4}', text.strip()):
                    status['queue_left'] = text.strip()

        try:
            status['target_colors'] = sorted(runner.detect_target_box_colors(img))
        except Exception:
            status['target_colors'] = []
        try:
            cans = runner.detect_shelf_cans(img)
            status['front_cans'] = [f"{c.get('color','?')}@{c.get('col','?')}" for c in cans[:8]]
        except Exception:
            status['front_cans'] = []
    except Exception as e:
        status['error'] = f'Parse status error: {e}'

    return status


def app_state_from_focus(focus_short):
    if 'com.android.vending' in focus_short:
        return 'Play Store/iklan'
    if 'com.android.chrome' in focus_short or 'browser' in focus_short.lower():
        return 'Browser/iklan'
    if PACKAGE_NAME in focus_short:
        return 'Game aktif'
    return 'Di luar game / tidak diketahui'


def warnings_for(st):
    warn = []
    if not st.get('device'):
        warn.append('ADB device tidak terdeteksi')
    if not st.get('bot_running'):
        warn.append('bot Android tidak berjalan')
    if st.get('device') and not st.get('in_game'):
        warn.append('fokus bukan game')
    if st.get('error'):
        warn.append(st['error'])
    return warn


def format_duration(seconds):
    """Format detik menjadi teks durasi bahasa Indonesia (misal: 2 menit 15 detik)."""
    if seconds is None or seconds < 0:
        return "-"
    if seconds < 60:
        return f"{seconds} detik"
    m = seconds // 60
    s = seconds % 60
    if m < 60:
        return f"{m} menit {s} detik" if s > 0 else f"{m} menit"
    h = m // 60
    m_rem = m % 60
    if m_rem > 0:
        return f"{h} jam {m_rem} menit"
    return f"{h} jam"


def fmt_status(st, kind, old_saldo=None, diff=0, stale_minutes=7, elapsed_seconds=None, state=None):
    if state is None:
        state = load_state()

    focus_short = st.get('focus') or '-'
    app_state = app_state_from_focus(focus_short)
    warn = warnings_for(st)
    target = ', '.join(st.get('target_colors') or []) or '-'
    cans = ', '.join(st.get('front_cans') or []) or '-'

    current_rp_raw = st.get('saldo_rp') or state.get('saldo_rp')
    current_rp_disp = format_saldo_display(current_rp_raw)
    old_rp_disp = format_saldo_display(old_saldo)

    ticket_disp = html.escape(str(st.get('saldo_ticket') or state.get('saldo_ticket') or '-'))
    level_disp = html.escape(str(st.get('level') or state.get('level') or '-'))
    queue_disp = html.escape(str(st.get('queue_left') or state.get('queue_left') or '-'))
    last_growth_time = state.get('last_growth_time') or '-'

    if kind == 'saldo_increased':
        diff_str = f"+Rp {int(diff):,}".replace(',', '.') if isinstance(diff, (int, float)) and float(diff).is_integer() else f"+Rp {diff:.2f}"
        dur_str = format_duration(elapsed_seconds)
        title = f"💰 <b>SALDO BERTAMBAH JADI {html.escape(current_rp_disp)}</b> ({html.escape(diff_str)})"
        saldo_line = (
            f"💰 <b>Perubahan:</b> <b>{html.escape(old_rp_disp)}</b> ➔ <b>{html.escape(current_rp_disp)}</b>\n"
            f"⏱️ <b>Jeda sejak perubahan terakhir:</b> <b>{html.escape(dur_str)}</b>"
        )
    elif kind == 'saldo_decreased':
        diff_str = f"-Rp {int(abs(diff)):,}".replace(',', '.') if isinstance(diff, (int, float)) and float(diff).is_integer() else f"-Rp {abs(diff):.2f}"
        title = "💸 <b>SALDO SODA PACK BERKURANG (PENARIKAN)</b>"
        saldo_line = f"💰 <b>Saldo =Rp:</b> <b>{html.escape(old_rp_disp)}</b> ➔ <b>{html.escape(current_rp_disp)}</b> (<b>{diff_str}</b>)"
    elif kind == 'bottleneck':
        title = "⚠️ <b>BOTTLENECK TERDETEKSI (BOT SODA PACK MACET)</b>"
        saldo_line = (
            f"⏱️ <b>Status:</b> Saldo tidak bertambah selama <b>{stale_minutes} menit</b>!\n"
            f"💰 <b>Saldo terakhir:</b> <b>{html.escape(current_rp_disp)}</b> (terakhir naik: <code>{html.escape(last_growth_time)}</code>)"
        )
    else:
        title = "📊 <b>SODA PACK BOT STATUS</b>"
        saldo_line = f"💰 <b>Saldo =Rp:</b> <b>{html.escape(current_rp_disp)}</b>"

    msg = (
        f"{title}\n"
        f"🕐 {html.escape(st.get('time','-'))}\n\n"
        f"{saldo_line}\n"
        f"🎟️ <b>Tiket/koin:</b> <b>{ticket_disp}</b>\n"
        f"🎮 <b>Level:</b> <b>{level_disp}</b>\n"
        f"📦 <b>Sisa antrian:</b> <b>{queue_disp}</b>\n\n"
        f"🎯 <b>Target warna:</b> <code>{html.escape(target)}</code>\n"
        f"🥤 <b>Botol depan:</b> <code>{html.escape(cans)}</code>\n\n"
        f"🤖 <b>Bot Android:</b> <b>{'RUNNING' if st.get('bot_running') else 'STOPPED'}</b>\n"
        f"📱 <b>Device:</b> <code>{html.escape(str(st.get('device') or '-'))}</code>\n"
        f"🧭 <b>Status app:</b> <b>{html.escape(app_state)}</b>\n"
    )
    if warn:
        msg += "\n⚠️ <b>Catatan:</b> " + html.escape('; '.join(warn)) + "\n"
    if kind == 'bottleneck':
        msg += "\n🔄 <i>Auto-Recovery: Seluruh aplikasi ditutup paksa, riwayat dibersihkan, dan game Soda Pack dibuka ulang.</i>"

    return msg


def clean_restart_all_apps_and_game(serial):
    """Menutup paksa semua aplikasi latar belakang/iklan/browser, membersihkan layar, dan membuka ulang game."""
    if not serial:
        return
    print(f"[recovery] Menutup semua aplikasi & restart game pada device {serial}...", flush=True)
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
        run(['adb', '-s', serial, 'shell', 'am', 'force-stop', pkg], timeout=4)

    run(['adb', '-s', serial, 'shell', 'input', 'keyevent', '3'], timeout=3)
    time.sleep(1.0)

    run(['adb', '-s', serial, 'shell', 'monkey', '-p', PACKAGE_NAME, '-c', 'android.intent.category.LAUNCHER', '1'], timeout=5)
    time.sleep(3.0)


def notification_for(st):
    state = load_state()
    now_ts = int(time.time())
    now_str = st.get('time') or datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')

    state['last_check_time'] = now_str
    state['last_check_ts'] = now_ts

    # Update metadata jika terdeteksi dari OCR
    for key in ['saldo_ticket', 'level', 'queue_left']:
        if st.get(key):
            state[key] = st.get(key)
            state[key + '_time'] = now_str

    cur_rp_str = st.get('saldo_rp')
    if cur_rp_str is not None:
        state['saldo_rp'] = cur_rp_str
        state['saldo_rp_time'] = now_str
        state['saldo_rp_ts'] = now_ts
    else:
        # Gunakan saldo terakhir dari state jika OCR frame ini tidak menangkap header
        cur_rp_str = state.get('saldo_rp')

    cur_val = saldo_value(cur_rp_str)
    last_reported_str = state.get('last_reported_saldo')
    last_reported_val = saldo_value(last_reported_str)

    # Inisialisasi last_growth_ts jika belum ada
    if not state.get('last_growth_ts'):
        state['last_growth_ts'] = now_ts
        state['last_growth_time'] = now_str

    # Kasus 1: Pertama kali berjalan dan belum ada baseline last_reported_saldo
    if last_reported_val is None and cur_val is not None:
        state['last_reported_saldo'] = str(cur_rp_str)
        state['last_growth_ts'] = now_ts
        state['last_growth_time'] = now_str
        state['last_stale_alert_ts'] = 0
        save_state(state)
        return None

    # Kasus 2: Saldo berubah (bertambah atau berkurang)
    if cur_val is not None and last_reported_val is not None and cur_val != last_reported_val:
        old_str = last_reported_str
        diff = cur_val - last_reported_val
        state['last_reported_saldo'] = str(cur_rp_str)
        prev_growth_ts = int(state.get('last_growth_ts') or now_ts)
        elapsed_seconds = max(0, now_ts - prev_growth_ts)

        if cur_val > last_reported_val:
            state['last_growth_ts'] = now_ts
            state['last_growth_time'] = now_str
            state['last_stale_alert_ts'] = 0
            kind = 'saldo_increased'
        else:
            kind = 'saldo_decreased'
        save_state(state)
        return fmt_status(st, kind=kind, old_saldo=old_str, diff=diff, elapsed_seconds=elapsed_seconds, state=state)

    # Kasus 3: Saldo tidak bertambah. Cek apakah sudah 7 menit (STALE_SECONDS)
    last_growth_ts = int(state.get('last_growth_ts', now_ts))
    stale_duration = now_ts - last_growth_ts
    last_stale_alert_ts = int(state.get('last_stale_alert_ts', 0))

    if stale_duration >= STALE_SECONDS:
        # Kirim peringatan bottleneck jika belum pernah dikirim dalam window 7 menit terakhir
        if (now_ts - last_stale_alert_ts) >= STALE_SECONDS:
            state['last_stale_alert_ts'] = now_ts
            state['last_growth_ts'] = now_ts  # Reset window setelah recovery
            state['last_growth_time'] = now_str
            save_state(state)
            stale_minutes = max(7, stale_duration // 60)
            msg = fmt_status(st, kind='bottleneck', stale_minutes=stale_minutes, state=state)
            # Jalankan pembersihan & restart game
            clean_restart_all_apps_and_game(st.get('device'))
            return msg

    save_state(state)
    return None



def generate_15min_report(st, state):
    """Menghasilkan laporan tabel log aktivitas dan ringkasan rata-rata kenaikan saldo setiap 15 menit."""
    from soda_event_logger import get_and_reset_report_data
    report_data = get_and_reset_report_data()
    events = report_data.get('events', [])
    period_start_str = report_data.get('period_start_time', '-')
    period_start_ts = report_data.get('period_start_ts', int(time.time() - 900))
    now_ts = int(time.time())
    now_str = st.get('time') or datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')

    # Hitung statistik
    total_ads = sum(1 for e in events if e.get('type') == 'selesai_iklan')
    total_growth = sum(e.get('data', {}).get('diff', 0) for e in events if e.get('type') == 'saldo_naik')
    total_bottlenecks = sum(1 for e in events if e.get('type') == 'bottleneck')

    elapsed_min = max(1.0, (now_ts - period_start_ts) / 60.0)
    avg_per_ad = (total_growth / total_ads) if total_ads > 0 else 0.0
    rpm = total_growth / elapsed_min
    rph = rpm * 60.0

    current_rp_raw = st.get('saldo_rp') or state.get('saldo_rp')
    current_rp_disp = format_saldo_display(current_rp_raw)
    ticket_disp = html.escape(str(st.get('saldo_ticket') or state.get('saldo_ticket') or '-'))
    level_disp = html.escape(str(st.get('level') or state.get('level') or '-'))

    if events:
        log_lines = []
        for it in events:
            t = it.get('time', '-')
            txt = it.get('text', '-')
            log_lines.append(f"• <code>{t}</code> - {html.escape(txt)}")
        log_table = "\n".join(log_lines)
    else:
        log_table = "• <i>Tidak ada aktivitas signifikan pada periode 15 menit ini.</i>"

    msg = (
        "📋 <b>LAPORAN AKTIVITAS BOT (15 MENIT)</b>\n"
        f"🕐 <code>{html.escape(period_start_str)} ➔ {html.escape(now_str)}</code>\n\n"
        "<b>📜 Log Riwayat:</b>\n"
        f"{log_table}\n\n"
        "<b>📊 Ringkasan Statistik 15 Menit:</b>\n"
        f"• 📺 <b>Total Iklan Ditonton:</b> <b>{total_ads}x</b>\n"
        f"• 💰 <b>Total Saldo Bertambah:</b> <b>+Rp {total_growth:,}</b>\n"
        f"• 📈 <b>Rata-rata Saldo per Iklan:</b> <b>+Rp {avg_per_ad:.1f} / iklan</b>\n"
        f"• ⚡ <b>Kecepatan Kenaikan Saldo:</b> <b>Rp {rpm:.1f} / menit</b> (~Rp {int(rph):,} / jam)\n"
        f"• ⚠️ <b>Total Bottleneck/Recovery:</b> <b>{total_bottlenecks}x</b>\n\n"
        f"💰 <b>Saldo Saat Ini:</b> <b>{html.escape(current_rp_disp)}</b>\n"
        f"🎟️ <b>Tiket/Koin:</b> <b>{ticket_disp}</b>\n"
        f"🎮 <b>Level:</b> <b>{level_disp}</b>\n"
        f"🤖 <b>Status Bot:</b> <b>{'RUNNING' if st.get('bot_running') else 'STOPPED'}</b>\n"
        f"📱 <b>Device:</b> <code>{html.escape(str(st.get('device') or '-'))}</code>"
    )
    return msg

def send_telegram(text):
    sender = load_module(TELEGRAM_SENDER_PATH, 'telegram_sender_config')
    token = getattr(sender, 'BOT_TOKEN', None)
    chat_id = getattr(sender, 'CHAT_ID', None)
    if not token or not chat_id:
        raise RuntimeError('BOT_TOKEN/CHAT_ID tidak ditemukan di telegram_sender.py')
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    res = requests.post(url, data={
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }, timeout=15)
    body = res.json()
    if not body.get('ok'):
        raise RuntimeError(str(body)[:500])
    return body


def main():
    once = '--once' in sys.argv
    print(f"[reporter] start interval={INTERVAL_SECONDS}s stale_threshold={STALE_SECONDS}s 15m_report=900s once={once}", flush=True)
    last_15m_ts = int(time.time())
    while True:
        try:
            st = collect_status()
            text = notification_for(st)
            if text:
                send_telegram(text)
                print(f"[reporter] sent telegram notif at {st.get('time')} saldo={st.get('saldo_rp')} level={st.get('level')}", flush=True)
            else:
                print(f"[reporter] check ok (no change) at {st.get('time')} saldo={st.get('saldo_rp')} level={st.get('level')}", flush=True)

            # Cek Laporan Periodik 15 Menit
            now_ts = int(time.time())
            state = load_state()
            last_rep_ts = int(state.get('last_15m_report_ts') or last_15m_ts)
            if (now_ts - last_rep_ts) >= 900:
                state['last_15m_report_ts'] = now_ts
                save_state(state)
                last_15m_ts = now_ts
                report_15m = generate_15min_report(st, state)
                send_telegram(report_15m)
                print(f"[reporter] sent 15-minute summary report at {st.get('time')}", flush=True)

        except Exception as e:
            print(f"[reporter] error: {e}", flush=True)
        if once:
            break
        time.sleep(INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
