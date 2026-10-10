#!/bin/bash
set -euo pipefail
/Users/macbookair/android-game-bots/game-switcher/stop_all_switcher_bots.sh || true
adb shell am force-stop com.starlightgame.woodlandtilematcher 2>/dev/null || true
adb shell monkey -p com.starlightgame.magicoceantilecrush -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
tmux new-session -d -s magic_ocean_guardian 'cd /Users/macbookair/android-game-bots/magic-ocean-tile-crush && ./run_magic_ocean_guardian_bot.sh'
echo "Magic Ocean ditampilkan dan bot Magic dijalankan."
