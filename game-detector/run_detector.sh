#!/bin/bash

# Game Detector Runner Script
# Usage: ./run_detector.sh [monitor|check]

cd "$(dirname "$0")"

chmod +x detect_current_game.py

case "$1" in
    monitor)
        echo "🔍 Memulai monitoring mode..."
        ./detect_current_game.py --monitor
        ;;
    check)
        echo "🔍 Single check mode..."
        ./detect_current_game.py
        ;;
    json)
        ./detect_current_game.py --json
        ;;
    *)
        echo "Game Detector - Deteksi game Android yang sedang aktif"
        echo ""
        echo "Usage:"
        echo "  ./run_detector.sh check      - Cek sekali saja"
        echo "  ./run_detector.sh monitor    - Monitor terus-menerus"
        echo "  ./run_detector.sh json       - Output JSON"
        echo ""
        echo "Contoh:"
        echo "  ./run_detector.sh check"
        ;;
esac
