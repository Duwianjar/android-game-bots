#!/bin/bash
set -euo pipefail
/Users/macbookair/android-game-bots/game-switcher/stop_all_switcher_bots.sh || true
adb shell am force-stop com.starlightgame.magicoceantilecrush 2>/dev/null || true
adb shell monkey -p com.starlightgame.woodlandtilematcher -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
tmux new-session -d -s woodland_guardian 'cd /Users/macbookair/android-game-bots/woodland-tile-matcher && ./run_woodland_guardian_bot.sh'
echo "Woodland ditampilkan dan bot guardian Woodland full dijalankan."
