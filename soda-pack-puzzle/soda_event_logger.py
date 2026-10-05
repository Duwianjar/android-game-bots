#!/usr/bin/env python3
"""Modul pencatat aktivitas dan pembuat ringkasan laporan 15 menit untuk Bot Soda Pack."""
import json
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = Path('/Users/macbookair/soda_activity_log.json')


def load_log():
    try:
        if LOG_FILE.exists():
            return json.loads(LOG_FILE.read_text())
    except Exception:
        pass
    now_ts = int(time.time())
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')
    return {
        'period_start_ts': now_ts,
        'period_start_time': now_str,
        'events': []
    }


def save_log(data):
    try:
        LOG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        pass


def log_event(event_type, text, data=None):
    """Menambahkan catatan aktivitas ke riwayat log."""
    try:
        log_data = load_log()
        now = datetime.now()
        entry = {
            'time': now.strftime('%H:%M:%S'),
            'ts': int(time.time()),
            'type': event_type,
            'text': text,
            'data': data or {}
        }
        log_data.setdefault('events', []).append(entry)
        if len(log_data['events']) > 150:
            log_data['events'] = log_data['events'][-150:]
        save_log(log_data)
    except Exception:
        pass


def get_and_reset_report_data():
    """Mengambil riwayat log dan mereset periode untuk 15 menit berikutnya."""
    try:
        log_data = load_log()
        now_ts = int(time.time())
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')
        new_data = {
            'period_start_ts': now_ts,
            'period_start_time': now_str,
            'events': []
        }
        save_log(new_data)
        return log_data
    except Exception:
        return {'events': [], 'period_start_ts': int(time.time()), 'period_start_time': '-'}
