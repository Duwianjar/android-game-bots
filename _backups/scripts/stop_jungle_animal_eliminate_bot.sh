#!/bin/bash
echo "[+] Menghentikan Bot Jungle Animal Eliminate..."
tmux kill-session -t jungle_bot 2>/dev/null
pkill -f "jungle_animal_eliminate_bot.py" 2>/dev/null
echo "[✔] Bot dihentikan"
