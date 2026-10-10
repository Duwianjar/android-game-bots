#!/bin/bash
# Stop Bot Coin Dash Shot

echo "[+] Menghentikan Bot Coin Dash Shot..."

# Kill tmux session
tmux kill-session -t coin_dash_bot 2>/dev/null

# Kill process
pkill -f "coin_dash_shot_bot.py" 2>/dev/null

echo "[✔] Bot Coin Dash Shot dihentikan"
