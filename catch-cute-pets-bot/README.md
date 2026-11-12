# Catch Cute Pets Bot

Target package: `com.NAMMUNIS.CatchCutePets`.

Fitur:
- membuka ulang game jika tidak berada di foreground;
- menyalakan kontrol jempol biru `OFF` di kanan-bawah menjadi `ON`;
- mengetuk tombol hijau `KLAIM`/`CLAIM`.

## Jalankan dengan tmux

```bash
tmux new-session -d -s catch-cute-pets-bot 'cd /Users/macbookair/android-game-bots/catch-cute-pets-bot && exec ./run_catch_cute_pets_bot.sh --serial 062322513B000705'
```

Lihat bot: `tmux attach -t catch-cute-pets-bot`.
Keluar dari tampilan tmux tanpa menghentikan bot: `Ctrl+B`, lalu `D`.
Stop bot: `tmux kill-session -t catch-cute-pets-bot`.
