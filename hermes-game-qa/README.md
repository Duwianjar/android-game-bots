# Hermes Android Game QA Agents

Workflow ini memakai Hermes Kanban untuk koordinasi 3 agent secara aman.

## Batasan wajib
- Tidak untuk memanipulasi saldo, reward, iklan, revenue, atau endpoint produksi.
- Tidak mencari endpoint yang bisa menaikkan saldo.
- Security test hanya untuk aplikasi/backend milik sendiri atau staging yang diizinkan.
- Semua aksi Android harus bisa dihentikan manual dan dicatat lognya.

## Board
```bash
hermes kanban boards switch android-game-qa
hermes kanban list
```

## Agent/peran
1. `android-automator`
   - Deteksi foreground app via ADB.
   - Capture screenshot, UI XML, logcat.
   - Menjalankan test otomasi non-abusive pada perangkat sendiri.

2. `balance-observer`
   - Membaca UI/log untuk verifikasi QA.
   - Membandingkan nilai tampilan sebelum/sesudah flow.
   - Membuat laporan anomali dan rekomendasi perbaikan.

3. `security-qa`
   - Audit endpoint staging/own app untuk integritas reward.
   - Cek validasi server-side, signature, replay protection, rate limit.
   - Tidak mengeksploitasi endpoint produksi.

## Menjalankan worker
Jalankan dispatcher Hermes untuk memproses task siap:
```bash
hermes kanban dispatch --help
hermes kanban dispatch
```

Pantau board:
```bash
hermes kanban watch
hermes kanban list
hermes kanban show t_5926ef0f
```

Stop darurat Hermes:
```bash
hermes pause
# lanjutkan:
hermes resume
```

## Task yang dibuat
- Automator: `t_5926ef0f`
- Observer: `t_9aea2687`
- Security QA: `t_ba5dbd09`
- Verifier: `t_b451bd01`
- Synthesizer: `t_49a28fa8`
