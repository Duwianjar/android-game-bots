# Dragon Arrow Escape Bot

Bot otomatis untuk game Dragon Arrow Escape. Script ini membuka game di browser web dan mengontrolnya secara otomatis dengan menggunakan keyboard dan mouse.

## Fitur

- 🌐 Mengakses game lokal melalui browser web (folder: `dragon-arrow-escape/`) 
- 🎮 Kontrol otomatis:
  - Menggunakan keyboard (WASD/Arrow keys) untuk mengontrol pemain
  - Menggunakan klik mouse acak untuk mengendalikan panah magis
- ⏱️ Game terus berjalan hingga pengguna menekan Ctrl+C
- 📊 Menampilkan skor di layar

## Prasyarat

- Python 3.8+
- Chrome/Edge/Chromium browser (untuk Selenium)
- ChromeDriver yang terinstal dan kompatibel

## Instalasi

### 1. Clone repository (jika diperlukan)
```bash
git clone <URL-repository>
cd dragon-arrow-escape-bot
```

### 2. Install Python packages
```bash
pip install -r requirements.txt
```

### 3. Install ChromeDriver
- Ubuntu/Debian:
  ```bash
  sudo apt-get update
  sudo apt-get install -y wget
  wget https://chromedriver.storage.googleapis.com/$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE)_chromedriver_linux64.zip
  sudo unzip -o chromedriver_linux64.zip -d /usr/local/bin/
  sudo chmod +x /usr/local/bin/chromedriver
  sudo ln -s /usr/local/bin/chromedriver /usr/bin/chromedriver
  ```

- macOS:
  ```bash
  brew install --cask chromedriver
  ```

- Windows: Unduh dari [ChromeDriver Releases](https://chromedriver.storage.googleapis.com/index.html)

## Penggunaan

### Jalankan bot
```bash
python dragon-arrow-escape-bot.py
```

### Kontrol manual tambahan
- Game memberikan Anda kontrol manual:
  - **WASD / Panah**: kontrol pemain
  - **Space**: gunakan panah magis (jika sudah siap)
  - **ESC**: keluar (di bot ini)

## Cara kerja

1. Bot membuka browser web dan memuat halaman HTML game (`index.html`)
2. Game dimulai secara otomatis
3. Bot mengklik acak di layar untuk melakukan aksi (simulasi penggunaan panah magis)
4. Script terus berjalan hingga Anda menekan Ctrl+C

## Struktur proyek

- `dragon-arrow-escape-bot.py`: Bot utama
- `dragon-arrow-escape/`: Folder HTML game lengkap (konten game)
- `README.md`: File ini

## Kontrol manual dalam game

Selama game berjalan, Anda dapat mengontrol:
- **Posisi karakter** menggunakan WASD atau panah
- **Panah magis** menggunakan Space (setelah cooldown 1 detik)
- **Mulai ulang** setelah Game Over dengan mengklik layar

## Troubleshooting

### Masalah umum

1. **Kesalahan: "chromedriver not found"**
   - Pastikan ChromeDriver ada di PATH:
     ```bash
     chromedriver --version
     ```

2. **Kesalahan: "ModuleNotFoundError: No module named selenium"**
   - Install selenium: `pip install selenium`

3. **Game tidak terbuka**
   - Pastikan tidak ada program lain yang menggunakan port yang sama
   - Coba jalankan bot dengan layar "headless" jika diperlukan

### Mode headless (opsional)

Untuk menjalankan bot tanpa membuka browser window:
```python
# Ubah di open_browser():
options.add_argument('--headless')
```

## Catatan pengembang

Script ini menggunakan:
- **Selenium** untuk otomatisasi browser
- **ActionChains** untuk simulasi mouse
- **Python threading** untuk operasi latar belakang (opsional)

Permasalahan:
- Kontrol acak menggunakan klik mouse mungkin tidak optimal untuk semua pemain
- Game menggunakan posisi absolut pixel; resolusi layar mungkin berpengaruh

## Lisensi

Dibuat untuk tujuan hiburan dan belajar
