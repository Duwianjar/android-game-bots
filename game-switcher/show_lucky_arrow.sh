#!/bin/bash
set -euo pipefail
/Users/macbookair/android-game-bots/game-switcher/stop_all_switcher_bots.sh || true
adb shell monkey -p com.starlightgame.luckyarrowescaper -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true

EXTRA_ARGS="$*"
if [ -n "$EXTRA_ARGS" ]; then
  tmux new-session -d -s lucky_arrow_guardian "cd /Users/macbookair/android-game-bots/lucky-arrow-escaper && ./run_lucky_arrow_escaper_guardian_bot.sh $EXTRA_ARGS"
else
  tmux new-session -d -s lucky_arrow_guardian 'cd /Users/macbookair/android-game-bots/lucky-arrow-escaper && ./run_lucky_arrow_escaper_guardian_bot.sh'
fi
echo "Lucky Arrow Escaper ditampilkan dan bot guardian Lucky Arrow full dijalankan."
