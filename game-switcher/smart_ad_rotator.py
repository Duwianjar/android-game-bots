#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

ADB_SERIAL = os.environ.get("ADB_SERIAL", "").strip()

AD_ACTIVITY_KEYWORDS = (
    "ads",
    "adplayer",
    "advert",
    "rewardvideo",
    "rewarded",
    "mbridge",
    "mintegral",
    "applovin",
    "vungle",
    "ironsource",
    "chartboost",
    "adcolony",
    "gms.ads",
    "fullscreenwebviewdisplay",
    "webviewdisplay",
)


@dataclass
class ForegroundApp:
    package: str
    activity: str = ""


@dataclass
class Game:
    key: str
    name: str
    package: str
    session: str
    bot_dir: Path
    run_script: str
    log_file: Path
    pending_ad: bool = False


MAGIC = Game(
    key="magic",
    name="Magic Ocean",
    package="com.starlightgame.magicoceantilecrush",
    session="magic_ocean_guardian",
    bot_dir=Path("/Users/macbookair/android-game-bots/magic-ocean-tile-crush"),
    run_script="./run_magic_ocean_guardian_bot.sh",
    log_file=Path("/Users/macbookair/magic_ocean_guardian_bot.log"),
)
WOODLAND = Game(
    key="woodland",
    name="Woodland",
    package="com.starlightgame.woodlandtilematcher",
    session="woodland_guardian",
    bot_dir=Path("/Users/macbookair/android-game-bots/woodland-tile-matcher"),
    run_script="./run_woodland_guardian_bot.sh",
    log_file=Path("/Users/macbookair/woodland_guardian_bot.log"),
)
GAMES = [MAGIC, WOODLAND]


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{ts()}] {msg}", flush=True)


def run(cmd: list[str], timeout: int = 12) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def adb_cmd(args: list[str], timeout: int = 12) -> subprocess.CompletedProcess[str]:
    cmd = ["adb"]
    if ADB_SERIAL:
        cmd += ["-s", ADB_SERIAL]
    cmd += args
    return run(cmd, timeout=timeout)


def shell(cmd: str, timeout: int = 12) -> subprocess.CompletedProcess[str]:
    return run(["/bin/bash", "-lc", cmd], timeout=timeout)


def parse_app(text: str) -> Optional[ForegroundApp]:
    anr = re.search(r"Application Not Responding:\s*([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)", text)
    if anr:
        return ForegroundApp(anr.group(1), "Application Not Responding")
    patterns = (
        r"u\d+\s+([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)/([^\s}\]]+)",
        r"\s([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)/([a-zA-Z0-9_.$]+)",
    )
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return ForegroundApp(m.group(1), m.group(2))
    return None


def foreground() -> Optional[ForegroundApp]:
    checks = [
        (["shell", "dumpsys", "window", "displays"], ("mCurrentFocus",)),
        (["shell", "dumpsys", "activity", "activities"], ("topResumedActivity", "mResumedActivity", "ResumedActivity")),
        (["shell", "dumpsys", "window", "displays"], ("mFocusedApp",)),
    ]
    for args, keys in checks:
        try:
            out = adb_cmd(args, timeout=8).stdout
        except Exception:
            continue
        in_last_anr = False
        for line in out.splitlines():
            if "Last ANR" in line:
                in_last_anr = True
                continue
            if in_last_anr:
                if not line.startswith(" ") and not line.startswith("	"):
                    in_last_anr = False
                else:
                    continue
            if any(k in line for k in keys):
                app = parse_app(line)
                if app:
                    return app
    return None


def is_ad_for(game: Game, app: Optional[ForegroundApp]) -> bool:
    if not app or app.package != game.package:
        return False
    activity = (app.activity or "").lower()
    return any(k in activity for k in AD_ACTIVITY_KEYWORDS)


def is_game_screen_for(game: Game, app: Optional[ForegroundApp]) -> bool:
    return bool(app and app.package == game.package and app.activity != "Application Not Responding" and not is_ad_for(game, app))


def stop_bot(game: Game) -> None:
    shell(f"tmux kill-session -t {game.session} 2>/dev/null || true", timeout=8)
    py_name = "magic_ocean_guardian_bot.py" if game.key == "magic" else "woodland_guardian_bot.py"
    lock = "/tmp/magic_ocean_guardian_bot.lock" if game.key == "magic" else "/tmp/woodland_guardian_bot.lock"
    
    pattern = '[m]agic_ocean_guardian_bot.py' if game.key == 'magic' else '[w]oodland_guardian_bot.py'
    shell(f"pkill -f '{pattern}' 2>/dev/null || true; rm -rf {lock}", timeout=8)


def stop_all_bots() -> None:
    for game in GAMES:
        stop_bot(game)


def launch_game(game: Game) -> None:
    log(f"BUKA APP: {game.name} ({game.package}) tanpa force-stop agar iklan lama tetap tersimpan")
    try:
        adb_cmd(["shell", "monkey", "-p", game.package, "-c", "android.intent.category.LAUNCHER", "1"], timeout=15)
    except Exception as exc:
        log(f"ADB launch error {game.name}: {exc}")
    time.sleep(1.2)


def start_bot(game: Game) -> None:
    stop_bot(game)
    cmd = f"cd '{game.bot_dir}' && {game.run_script}"
    rc = shell(f"tmux new-session -d -s {game.session} {cmd!r}", timeout=8).returncode
    if rc != 0:
        # Kalau quoting shell tmux bermasalah, fallback bentuk langsung.
        shell(f"tmux kill-session -t {game.session} 2>/dev/null || true", timeout=5)
        shell(f"tmux new-session -d -s {game.session} 'cd {game.bot_dir} && {game.run_script}'", timeout=8)
    log(f"BOT AKTIF: {game.name} ({game.session})")


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def read_new_lines(path: Path, offset: int) -> tuple[int, list[str]]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            data = f.read()
            return f.tell(), data.splitlines()
    except OSError:
        return offset, []


def run_turn(game: Game, max_turn_seconds: int) -> tuple[bool, bool]:
    """Return (new_ad_opened, pending_ad_after_turn)."""
    old_pending = game.pending_ad
    ready_for_next_ad = not old_pending
    ignored_old_ad_logged = False
    last_fg_poll = 0.0
    start_ts = time.time()
    no_target_since = 0.0
    offset = file_size(game.log_file)

    log("=" * 54)
    if old_pending:
        log(f"GILIRAN {game.name}: selesaikan iklan lama, lalu buka iklan baru")
    else:
        log(f"GILIRAN {game.name}: buka iklan dulu")

    launch_game(game)
    start_bot(game)

    while True:
        now = time.time()
        if now - start_ts > max_turn_seconds:
            log(f"TIMEOUT {game.name}: belum dapat iklan baru dalam {max_turn_seconds} detik")
            stop_bot(game)
            return False, old_pending and not ready_for_next_ad

        offset, lines = read_new_lines(game.log_file, offset)
        for line in lines:
            if "MENUNGGU TARGET" in line and ready_for_next_ad:
                if no_target_since <= 0:
                    no_target_since = time.time()
                elif time.time() - no_target_since >= 70:
                    log(f"{game.name}: 70 detik tidak ada DOBEL/NOW NOT/gelembung, coba game sebelah dulu")
                    stop_bot(game)
                    return False, False

            if "IKLAN SELESAI" in line:
                if old_pending and not ready_for_next_ad:
                    log(f"{game.name}: iklan lama selesai, lanjut cari/buka iklan baru")
                ready_for_next_ad = True

            if "BERHASIL BUKA IKLAN SETELAH TAP GELEMBUNG" in line or "IKLAN TERBUKA" in line:
                if not ready_for_next_ad:
                    if not ignored_old_ad_logged:
                        log(f"{game.name}: iklan lama masih terbuka, tidak dihitung; tunggu selesai dulu")
                        ignored_old_ad_logged = True
                    continue
                log(f"{game.name}: IKLAN BARU TERBUKA, langsung pindah ke game sebelah")
                stop_bot(game)
                return True, True

        if now - last_fg_poll >= 1.0:
            last_fg_poll = now
            app = foreground()
            if old_pending and is_game_screen_for(game, app):
                if not ready_for_next_ad:
                    log(f"{game.name}: sudah kembali ke layar game, lanjut cari/buka iklan baru")
                ready_for_next_ad = True
            if is_ad_for(game, app) and ready_for_next_ad:
                log(f"{game.name}: IKLAN BARU TERBUKA via foreground ({app.activity}), pindah game")
                stop_bot(game)
                return True, True

        time.sleep(0.2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rotator pintar Magic Ocean + Woodland berdasarkan status iklan")
    parser.add_argument("--max-turn-seconds", type=int, default=180, help="Batas maksimal 1 giliran kalau tidak berhasil buka iklan")
    parser.add_argument("--serial", default="", help="Serial ADB opsional")
    args = parser.parse_args()

    global ADB_SERIAL
    if args.serial.strip():
        ADB_SERIAL = args.serial.strip()

    max_turn = max(60, args.max_turn_seconds)

    log("==================================================")
    log("  SMART AD ROTATOR MAGIC OCEAN + WOODLAND AKTIF")
    log("==================================================")
    log("Pola: 1 buka iklan -> 2 buka iklan -> 1 selesaikan+buka iklan -> 2 selesaikan+buka iklan -> ulang")
    log(f"Max 1 giliran: {max_turn} detik")
    if ADB_SERIAL:
        log(f"Device: {ADB_SERIAL}")

    stop_all_bots()

    idx = 0
    try:
        while True:
            game = GAMES[idx]
            opened, pending = run_turn(game, max_turn)
            game.pending_ad = pending
            if not opened:
                log(f"{game.name}: giliran gagal/timeout, tetap lanjut supaya rotasi tidak macet")
            idx = 1 - idx
            time.sleep(0.6)
    except KeyboardInterrupt:
        log("Rotator dihentikan oleh user")
    finally:
        stop_all_bots()
        log("Semua bot anak distop. App/game tidak di-force-stop.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
