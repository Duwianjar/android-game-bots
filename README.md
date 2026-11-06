# Android Game Bots Collection

Koleksi bot otomatis untuk berbagai game Android yang menghasilkan saldo real money.

## Tabel Check

Game-game yang memiliki riwayat pencairan berhasil di awal namun bermasalah di instalasi kedua (seperti penarikan nominal besar tertahan/pending atau tidak bisa tarik). Disarankan mencoba penarikan nominal kecil terlebih dahulu.

<div style="overflow-x: auto;">

| No. | Game | Package `com` | Instalasi Pertama | Instalasi Kedua | Saran instalasi |
|---:|---|---|---|---|---|
| 1 | Blade Slice Master Fruit | `com.diancutter.bladeslicemasterfruit` | Ada pencairan sekitar Rp3.000, tetapi data juga mencatat pencairan lain Rp396 dan Rp531. | Instalasi kedua tidak bisa tarik padahal 14 rb. | Coba tarik kecil dulu. |
| 2 | Cut Fruit Blade Master | `com.goodgamecut.cutfruitblademaster` | Ada pencairan sekitar Rp2.000, tetapi 1 penarikan sekitar Rp2.000 tidak cair. | 18 rb pending. | Coba tarik kecil dulu. |
| 3 | LuckyScrewSort | Belum diketahui | Perlu dicek. | Penarikan 6 rb dua kali gagal, kemungkinan tidak bisa rekening sama (DANA). | Coba tarik kecil dulu. |

</div>

## Rekomendasi Instalasi

Urutan ini dibuat dari catatan penarikan yang sudah ada. **Tidak ada data yang membuktikan cair semua sampai Rp10.000.** Zoo Tile adalah catatan paling kuat karena 15 kali penarikan disebut lancar semua dengan maksimum Rp8.022. Bus Jam memiliki nominal sekitar Rp10.000, tetapi nominal terbesar tersebut belum cair. Dalam kelompok analisis yang sama, game yang bot-nya tersedia ditempatkan lebih atas. Game Blocked tidak dimasukkan dalam rekomendasi instalasi.

<div style="overflow-x: auto;">

| Prioritas | Game | Package `com` | Instalasi Pertama | Instalasi Kedua | Saran instalasi |
|---:|---|---|---|---|---|
| 1 | [Lucky Arrow Escape](lucky-arrow-escaper/) | `com.starlightgame.luckyarrowescaper` | Tersedia bot guardian otomatis. | Penarikan 25 dan 27 aman DANA. | **Instal paling pertama.** Coba tunggu gede dulu atau 25k baru tarik. |
| 2 | Tangkap Hewan Lucu / Zoo Tile | `com.zoo.tile.cute.animal.elephant.mouse.fox` | **15 kali lancar semua**, maksimum Rp8.022. | Restart kedua 3.000 dan masih DANA aman pencairan. | Instal setelah Lucky Arrow Escape. |
| 3 | Bus Jam Parking Master | `com.busjam.parking.master` | 29 kali penarikan; banyak nominal Rp2.000–Rp7.000. Target terbesar sekitar Rp10.000 belum cair. | Di restart kedua: pencairan bisa pending 2 hari dan tidak bisa rekening yang sama. | Instal setelah prioritas atas; pantau nominal besar. Bot paling aman tapi kurang maksimal. |
| 4 | Magic Ocean Tile Crush | `com.starlightgame.magicoceantilecrush` | Masuk kelompok pemantauan nominal di atas Rp5.000 tetapi pending; data nominal dan pending belum tercatat. **Rawan terblokir.** | Pencairan DANA aman. | Pantau ketat. Bot tidak aman tapi pencairan DANA aman, tinggal perbaiki bot. |
| 5 | Woodland Tile Match | `com.starlightgame.woodlandtilematcher` | Masuk kelompok pemantauan nominal di atas Rp5.000 tetapi pending; data nominal dan pending belum tercatat. **Rawan terblokir.** | Aman seperti Magic Ocean (pencairan DANA aman). | Pantau ketat. |
| 6 | [Crazy Fruit Blade Winner](crazy-fruit-blade-winner/) | `com.starlightgame.crazyfruitbladewinner` | Belum ada catatan penarikan. **Sekitar Rp200 per hari di awal, tetapi langsung turun setelahnya; lumayan, tetapi rawan block iklan.** | Tetap DANA dan awalnya bisa capai Rp15.000. | Rekomendasi menengah. |
| 7 | [Color Power Pop](color-power-pop/) | `com.giraffeeapp.power` | 19 kali penarikan; Rp1.000 sebanyak 4 kali dan Rp4.000 sekali. | DANA aman tapi cuma sedikit karena kemungkinan instalnya di akhir. | Rekomendasi menengah. |
| 8 | [Snake Out Jam](snake-out-jam/) | `com.wiwvitsugeh.snack` | Ada penarikan Rp9.237. Setelah penarikan sekitar Rp9.000, proses terasa susah. | Instalasi kedua susah iklan slotnya. | Instal berikutnya dengan target kecil dulu. ([Panduan Instalasi & Bypass Lisensi](snake-out-jam/README.md)) |
| 9 | [Magical Gems Match 3](magic-gems-match/) | `com.glow.magical.match3` | 13 kali penarikan; ada nominal Rp1.050. | DANA normal tapi sedikit kemungkinan karena terakhir. | Instal dengan target kecil. |
| 10 | Color Sand Blast | `com.xteleremobilecompanyltd.ColorSandBlast` | 11 kali penarikan; maksimum Rp2.311. Tidak ada gagal yang dicatat. | DANA aman dan stabil. | Rekomendasi setelah prioritas utama. |
| 11 | [Coin Sort Dash](coin-dash-shot/) | `com.coin.sortdash.remove` | 3 kali penarikan; ada Rp1.017. **Rawan terblokir iklan.** | DANA normal tapi sedikit kemungkinan karena terakhir. | Instal setelah prioritas utama. |
| 12 | Veg Cup Blast | `com.xteleremobilecompanyltd.VegCupBlast` | 5 kali penarikan; maksimum Rp2.191. | DANA tetap aman, tapi cuma dapat sedikit karena kemungkinan di akhir. | Rekomendasi setelah prioritas utama. |
| 13 | Toy Drop | `com.NAMMUNIS.ToyDrop` | 4 kali penarikan; maksimum Rp1.670. | DANA aman, paling banyak Rp1.300. | Rekomendasi setelah prioritas utama. |
| 14 | Planet Slice Master | `com.smartgames.planetslicemaster` | Belum pernah dicoba. | DANA aman, penarikan kecil sekitar 5.900-an sebanyak 3 kali. | Rekomendasi setelah prioritas utama; coba target penarikan kecil dulu (Rp5.900-an). |
| 15 | [Soda Jam Puzzle](soda-jam-puzzle/) | `com.armg.sodajam` | Tidak ikut tercatat. | Penarikan 700 aman DANA. | Instalasi kedua aman penarikan 700. |
| 16 | Harvest Block Crush | `com.harvest.block.crush` | Tidak ikut tercatat. | DANA aman tapi cuma 400. | Instalasi kedua aman tapi nominal kecil (Rp400). |
| 17 | Mahjong Ajaib *(Magic Mahjong)* | `com.Lucinda.MagicMahjong` | Tidak ikut tercatat. | DANA masih aman 300-an. | Coba target penarikan kecil (sekitar Rp300-an). |
| 18 | Magic Merge | `com.xteleremobilecompanyltd.MagicMerge` | Belum ada catatan awal. | DANA masih aman 300-an. | Coba target penarikan kecil (sekitar Rp300-an). |
| 19 | [Soda Pack Puzzle](soda-pack-puzzle/) | `com.soda.pack.puzzle` | Ada bot otomatis (belum dites botnya). | DANA masih aman 200-an. | Coba target penarikan kecil (sekitar Rp200-an); bot belum dites. |
| 20 | Magic Star Crush Journey **[RAWAN TERBLOKIR]** | `com.starlightgame.magicstarcrushjourney` | 1 kali penarikan Rp951; rawan terblokir. | Penarikan kedua DANA masih aman 600-an. | Pantau ketat (rawan terblokir); target kedua sekitar Rp600-an aman DANA. |
| 21 | Panah Penghasil Uang *(Panah Lepas)* | `com.pelangiarena.panahlepas` | Tidak ada catatan awal. | DANA aman 200-an. | Coba target penarikan kecil (sekitar Rp200-an). |
| 22 | Tangkap Tile Zoo *(Catch Zoo Tiles)* | `com.agmalik.CatchZooTiles` | Belum ada catatan (kosong). | DANA aman 300-an. | Coba target penarikan kecil (sekitar Rp300-an). |
| 23 | Cuan Maze | Belum dicatat | Belum ada catatan (kosong). | DANA aman 300-an. | Coba target penarikan kecil (sekitar Rp300-an). |
| 24 | Panah Sentuh *(Arrow Tap)* | Belum dicatat | Belum ada catatan (kosong). | DANA aman 800-an. | Target kedua lumayan (sekitar Rp800-an aman DANA). |

</div>

## Tabel Semi Rekomendasi

Game semi rekomendasi dengan opsi pencairan alternatif atau ketentuan akun/rekening khusus.

<div style="overflow-x: auto;">

| No. | Game | Package `com` | Instalasi Pertama | Instalasi Kedua / Catatan | Saran instalasi |
|---:|---|---|---|---|---|
| 1 | [Bus Parking Dash](bus-parking-dash/) | `com.bus.parking.dash` | Tersedia bot otomatis. | Instalasi kedua cuma bisa selain rekening yang sudah (seperti Bus Jam Parking), atau bisa OVO. | Semi rekomendasi; gunakan opsi OVO atau rekening baru. |
| 2 | [Fruit Blade Pop Crush](fruit-blade-pop-crush/) **[RAWAN TERBLOKIR]** | `com.starlightgame.fruitbladepopcrush` | Tersedia bot guardian otomatis; rawan terblokir. | Penarikan kedua perlu pakai OVO atau tidak bisa rekening yang sama. | Semi rekomendasi; gunakan opsi OVO atau rekening baru di instalasi kedua. |

</div>

## Lucky Match - DEVVVS 0043

**Pengembang/perusahaan:** DEVVVS 0043 / **SUKRIATI**.
Keterangan kategori: game-game ini terasa paling cepat, tetapi relatif mudah terblokir. Gunakan target awal maksimal **Rp500** pada sesi siang dan pantau 1–2 hari. Reward tidak dijamin dan dapat berubah menurut akun, perangkat, iklan, jaringan, serta kebijakan aplikasi.

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Blade Slice Master Fruit | `com.diancutter.bladeslicemasterfruit` | DEVVVS 0043 / SUKRIATI | **Peringkat pertama.** Cepat, tetapi mudah terblokir. Laporan penarikan cair 4 kali: Rp65, Rp144, Rp785, dan sekitar Rp3.000; tercatat 2 pencairan: Rp396 dan Rp531. Instalasi kedua tidak bisa tarik padahal 14 rb. | Lumayan | [ ] |
| 2 | Cut Fruit Blade Master | `com.goodgamecut.cutfruitblademaster` | DEVVVS 0043 / SUKRIATI | **Peringkat kedua.** Laporan penarikan cair 8 kali: Rp67, Rp68, Rp563, Rp632, sekitar Rp1.000, dan sekitar Rp2.000 sebanyak 3 kali; tidak cair 1 kali: sekitar Rp2.000. Instalasi kedua 18 rb pending. | Lumayan | [ ] |
| 3 | Tile Match Crush Frenzy | `com.tilegamer.tilematchcrushfrenzy` | DEVVVS 0043 / SUKRIATI | Cepat, tetapi mudah terblokir. Laporan penarikan cair 4 kali: Rp79, Rp167, Rp202, dan Rp541; pending 1 kali: Rp41. | Belum dicatat | [ ] |
| 4 | [Juicy Slash Blade Fruit](juicy-slash-blade-fruit/) | `com.dudufun.juicyslashbladefruit` | DEVVVS 0043 / SUKRIATI | Cepat, tetapi mudah terblokir. Laporan penarikan cair 2 kali: Rp114 dan Rp132; tidak cair 1 kali: Rp33. | Belum dicatat | [x] |
| 5 | Lucky Match Path Journey | `com.smallclickergamer.luckymatchpathjourney` | DEVVVS 0043 / SUKRIATI | Cepat, tetapi mudah terblokir. Laporan penarikan cair 2 kali: Rp51 dan Rp98; tidak cair 2 kali: Rp35 dan Rp116. | Belum dicatat | [ ] |
| 6 | Tiny Blast Magic Land | `com.kuaifastfa.tinyblastmagicland` | DEVVVS 0043 / SUKRIATI | Laporan penarikan cair 10 kali (9 nominal tercatat): Rp117, Rp159, Rp239, Rp346, Rp824, sekitar Rp1.000 sebanyak 3 kali, dan sekitar Rp3.000; tidak cair 2 kali: Rp62 dan Rp104. Instalasi kedua tidak bisa tarik. | Lumayan | [ ] |

## Magic Ocean & Woodland Tile Match — ACM PROJECTS & AUTOMATION LTD / Elias Galvin

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Magic Ocean Tile Crush **[RAWAN TERBLOKIR]** | `com.starlightgame.magicoceantilecrush` | ACM PROJECTS & AUTOMATION LTD / Elias Galvin | Belum ada catatan penarikan; rawan terblokir. | Belum dicatat | [x] |
| 2 | Woodland Tile Match **[RAWAN TERBLOKIR]** | `com.starlightgame.woodlandtilematcher` | ACM PROJECTS & AUTOMATION LTD / Elias Galvin | Belum ada catatan penarikan; rawan terblokir. | Belum dicatat | [x] |
| 3 | Crazy Tile Match Winner | `com.moonshotcube.crazytilematchwinner` | Elias Galvin | Penarikan 500 cair DANA. | Belum dicatat | [ ] |
| 4 | Lucky Pop Crush | `com.starlightgame.luckypopcrusher` | ACM PROJECTS & AUTOMATION LTD / Elias Galvin | Penarikan 300 cair DANA. | Belum dicatat | [ ] |

## Lucky Food

Keterangan kategori: game-game ini **cukup cepat setelah Lucky Match, tetapi jarang terdeteksi**. Nama developer/perusahaan dicocokkan dari metadata Google Play. Urutan di bawah ini disusun berdasarkan nominal penarikan tertinggi.

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | [Tangkap Hewan Lucu: Permainan Tile *(Zoo Tile: Win Mega Rewards!)*](zoo-tile/) | `com.zoo.tile.cute.animal.elephant.mouse.fox` | Faisal Developers / Salman Khan | **15 kali penarikan dan lancar semua.** Nominal dari kecil ke besar: Rp20, Rp50, Rp70, Rp104, Rp214, Rp279, Rp307, Rp597, Rp639, Rp964, Rp1.226, Rp1.594, Rp1.772, Rp1.866, dan Rp8.022. | Mudah | [x] |
| 2 | Color Sand Blast | `com.xteleremobilecompanyltd.ColorSandBlast` | Sporting 2024 / محمد السيد عبدالرحيم محمود | **11 kali penarikan:** Rp20, Rp296, Rp662, Rp2.311, Rp124, Rp315, Rp368, Rp479, Rp537, Rp664, dan Rp924 (Maks Rp2.311). Cukup cepat setelah Lucky Match, tetapi jarang terdeteksi. | Lumayan | [ ] |
| 3 | Veg Cup Blast | `com.xteleremobilecompanyltd.VegCupBlast` | Sporting 2024 / محمد السيد عبدالرحيم محمود | **5 kali penarikan:** Rp179, Rp2.191, Rp242, Rp208, dan Rp269 (Maks Rp2.191). Cukup cepat setelah Lucky Match, tetapi jarang terdeteksi. | Mendingan | [ ] |
| 4 | Toy Drop | `com.NAMMUNIS.ToyDrop` | Tidak tercantum / Ekanayake Mudiyanselage Prasanna Dilshan Ekanayake | **4 kali penarikan:** Rp20, Rp65, Rp1.670, dan Rp254 (Maks Rp1.670). Cukup cepat setelah Lucky Match, tetapi jarang terdeteksi. | Lumayan | [ ] |
| 5 | Cup Babe Block | `com.xteleremobilecompanyltd.CupBabeBlock` | Sporting 2024 / محمد السيد عبدالرحيم محمود | **11 kali penarikan:** Rp20, Rp78, Rp73, Rp170, Rp504, Rp73, Rp71, Rp176, Rp553, Rp210, dan Rp310 (Maks Rp553). Cukup cepat setelah Lucky Match, tetapi jarang terdeteksi. Instalasi kedua masih aman (DANA masih aman). | **Susah** | [ ] |
| 6 | Fortune Merge World | `com.NAMMUNIS.FortuneMergeWorld` | NAMMUNIS / Ekanayake Mudiyanselage Prasanna Dilshan Ekanayake | Developer sama dengan Toy Drop. Tema merge puzzle. **500 aman.** | Belum dicatat | [ ] |
| 7 | Belle Bolt Jam | `com.NAMMUNIS.BelleBoltJam` | NAMMUNIS / Ekanayake Mudiyanselage Prasanna Dilshan Ekanayake | Developer sama dengan Toy Drop. Tema baut/screw jam puzzle. **300 aman.** | Belum dicatat | [ ] |
| 8 | Fish Flow | `com.NAMMUNIS.FishFlow` | NAMMUNIS / Ekanayake Mudiyanselage Prasanna Dilshan Ekanayake | Developer sama dengan Toy Drop. Tema flow puzzle ikan. **300 penarikan aman.** | Belum dicatat | [ ] |
| 9 | Fortune Tile Mahjong | `com.NAMMUNIS.FortuneTileMahjong` | Tidak tercantum / Ekanayake Mudiyanselage Prasanna Dilshan Ekanayake | Developer sama dengan Toy Drop. **3 kali penarikan:** Rp212, Rp60, dan Rp20 (Maks Rp212). | Belum dicatat | [ ] |
| 10 | Mahjong Master: Win Real Cash! | `com.mahong.master.tours.blossom.mingle` | Faisal Developers / Salman Khan | Developer sama dengan Zoo Tile. **1 kali penarikan:** Rp105. | Belum dicatat | [ ] |
| 11 | Fruit Block-More Gifts | `com.xteleremobilecompanyltd.FruitBlock` | Sporting 2024 / محمد السيد عبدالرحيم محمود | Data penarikan belum tercatat valid/error, tetapi performanya sepertinya lumayan. | Lumayan | [ ] |
| 12 | Magic Merge | `com.xteleremobilecompanyltd.MagicMerge` | Sporting 2024 / محمد السيد عبدالرحيم محمود | **Kemungkinan Lucky Food.** Cukup cepat setelah Lucky Match, tetapi jarang terdeteksi. **Instalasi kedua DANA masih aman 300-an.** | Belum dicatat | [ ] |
| 13 | Animal Blast: Win Prize Game | `com.jungle.bear.tiger.wild.animal.eliminate` | Faisal Developers / Salman Khan | Developer sama dengan Zoo Tile. **1 kali penarikan:** Rp397. Keblokir koneksi, tetapi awalnya aman. | Belum dicatat | [x] |

## Spider Rope

Keterangan kategori: game-game ini **susah, tetapi tetap cair**. Data pencairan dapat berbeda menurut akun, perangkat, iklan, jaringan, dan kebijakan aplikasi. Urutan di bawah ini disusun berdasarkan nominal penarikan tertinggi.

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Bus Jam Parking Master | `com.busjam.parking.master` | Tidak tercantum / أحمد البكري خميس موسي | **Peringkat pertama.** 29 kali penarikan; banyak nominal Rp2.000, Rp3.000, Rp6.000, dan Rp7.000 (Maks Rp7.000). Terbesar sekitar Rp10.000, tetapi belum cair. | Belum dicatat | [x] |
| 2 | Bus Jam Escape Frenzy | `com.busjam.escape.frenzy` | DKSHUBDeveloper / Ghulam Yaseen | Developer sama dengan Magical Gems Match 3. Tema bus jam puzzle. **Penarikan 5.000 aman DANA (Maks Rp5.000).** | Belum dicatat | [ ] |
| 3 | Mahjong Pop Frenzy | `com.mahjong.pop.frenzy` | Freelancer Jibon | Developer sama dengan Bus Parking Dash. Tema mahjong pop. **Penarikan 2.000 aman DANA (Maks Rp2.000).** | Belum dicatat | [ ] |
| 4 | Cute Fish Link Fun | `com.xteleremobilecompanyltd.FishLink` | Sporting 2024 / محمد السيد عبدالرحيم محمود | Aman, penarikan 1100 (Maks Rp1.100). | Belum dicatat | [ ] |
| 5 | Magical Gems Match 3 | `com.glow.magical.match3` | DKSHUBDeveloper / Ghulam Yaseen | **13 kali penarikan:** Rp20, Rp89, Rp51, Rp81, Rp210, Rp107, Rp182, Rp1.050, Rp354, Rp531, Rp206, Rp273, dan Rp290 (Maks Rp1.050). Susah, tetapi tetap cair. | Lumayan | [x] |
| 6 | Coin Sort Dash [RAWAN TERBLOKIR IKLAN] | `com.coin.sortdash.remove` | أحمد البكري خميس موسي | Developer sama dengan Bus Jam Parking. **3 kali penarikan:** Rp1.017, Rp627, dan Rp20 (Maks Rp1.017). Lumayan, tetapi rawan terblokir iklan. | Lumayan | [x] |
| 7 | Soccer Tap Guard | `goal.soccertap.guardfrenzy` | MIC3 / Michael Jones | Perlu waspada; developer sama dengan Soda Pack Sort (Daftar Blocked). **Penarikan 1.000 aman.** | Belum dicatat | [ ] |
| 8 | Pyramid Gem Blast | `com.pyramid.gem.blast` | أحمد البكري خميس موسي | Developer sama dengan Bus Jam Parking. **2 kali penarikan:** Rp490 dan Rp20 (Maks Rp490). | Belum dicatat | [ ] |
| 9 | Fresh Veggie Pop | `com.fresh.veggie.pop` | Tidak tercantum / BAE Publishing LLC | **4 kali penarikan:** Rp20, Rp95, Rp256, dan Rp74 (Maks Rp256). Susah, tetapi tetap cair. | Belum dicatat | [ ] |
| 10 | Bottle Jam Solver | `com.bottle.jam.solver` | Tidak tercantum / UNJIBBED LTD | Game susah, penarikan sedikit. **4 kali penarikan:** Rp206, Rp108, Rp200, dan Rp202 (Maks Rp206). | Belum dicatat | [ ] |
| 11 | Gold Gems Journey | `com.gems.adventure.journey` | DKSHUBDeveloper / Ghulam Yaseen | Developer sama dengan Magical Gems Match 3. Tema match gems. **Penarikan 200 aman DANA.** | Belum dicatat | [ ] |
| 12 | Bus Escape: Traffic Puzzle | `sb.ad.hyper.busflow` | MIC3 / Michael Jones | Perlu waspada; developer sama dengan Soda Pack Sort (di Daftar Blocked). Tema bus escape/traffic. **Penarikan 200 aman.** | Belum dicatat | [ ] |
| 13 | [Bus Parking Dash](bus-parking-dash/) | `com.bus.parking.dash` | Freelancer Jibon | Tema bus parking. Tersedia bot otomatis. Instalasi kedua cuma bisa selain rekening yang sudah (seperti Bus Jam Parking), atau bisa OVO. | Lumayan | [x] |

## Bubble Crush

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Color Power Pop | `com.giraffeeapp.power` | Giraffee App / Muhammad Ahsan Saleem | **19 kali penarikan:** Rp1.000 sebanyak 4 kali dan Rp4.000 sekali; nominal 14 penarikan lainnya belum dirinci. | Lumayan | [x] |
| 2 | [Snake Out Jam](snake-out-jam/) | `com.wiwvitsugeh.snack` | Belum ditemukan di listing publik | **4 kali penarikan:** Rp147, Rp9.237, Rp288, dan Rp51. Setelah penarikan sekitar Rp9.000, proses terasa susah. ([Panduan Instalasi](snake-out-jam/README.md)) | Mudah | [ ] |
| 3 | Beach Soda Sort | `com.apnabankshop.beach` | ApnaBankShop / MRS BLAISE HELEN HAWLEY | **14 kali penarikan (15 nominal tercatat):** Rp642, Rp532, Rp88, Rp17, Rp47, Rp103, Rp93, Rp604, Rp546, Rp1.061, Rp530, Rp136, Rp68, Rp158, dan Rp89. Instalasi kedua tidak bisa DANA lagi dan cuma dikit juga. | Lumayan | [ ] |
| 4 | **NEW — Color Soda Pack** | `com.apnabankshop.soda` | ApnaBankShop / MRS BLAISE HELEN HAWLEY | Developer sama dengan Beach Soda Sort. Game susah; **2 kali penarikan:** Rp58 dan Rp288. | Belum dicatat | [ ] |

## Arrow Unblock

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Power Bank Blast | `com.power.pack.game` | Tidak tercantum / Junaid Hameed | **1 kali penarikan:** Rp537. | Belum dicatat | [ ] |
| 2 | Soda Pop Sort | `com.frenzy.sort.pack` | Tidak tercantum / Junaid Hameed | **3 kali penarikan:** Rp29, Rp3.026, dan Rp88. Instalasi kedua sudah dikit tidak bisa DANA ulang. | Lumayan | [ ] |

## Magic Star Crush Journey — Elias Galvin / ACM PROJECTS & AUTOMATION LTD [RAWAN TERBLOKIR]

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Magic Star Crush Journey **[RAWAN TERBLOKIR]** | `com.starlightgame.magicstarcrushjourney` | ACM PROJECTS & AUTOMATION LTD / Elias Galvin | **1 kali penarikan:** Rp951. Rawan terblokir. **Penarikan kedua DANA masih aman 600-an.** | Belum dicatat | [ ] |

## Fruit Blade Pop Crush — Elias Galvin / ACM PROJECTS & AUTOMATION LTD [RAWAN TERBLOKIR]

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | [Fruit Blade Pop Crush](fruit-blade-pop-crush/) **[RAWAN TERBLOKIR]** | `com.starlightgame.fruitbladepopcrush` | ACM PROJECTS & AUTOMATION LTD / Elias Galvin | Belum ada catatan penarikan; rawan terblokir. **Penarikan kedua perlu pakai OVO atau tidak bisa rekening yang sama.** | Belum dicatat | [x] |

## Developer Baru dengan Koleksi Multi-Game di HP

### ALEXANDER DEJARNETTE

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Global Carnival Arrow | `com.Lucinda.GlobalCarnivalArrow` | ALEXANDER DEJARNETTE | Tema panah karnaval. **Penarikan 1.000 dua kali DANA aman.** | Belum dicatat | [ ] |
| 2 | Mahjong Ajaib *(Magic Mahjong)* | `com.Lucinda.MagicMahjong` | ALEXANDER DEJARNETTE | Tema mahjong tile match. Instalasi pertama tidak ikut tercatat. **Instalasi kedua DANA masih aman 300-an.** | Belum dicatat | [ ] |

### arlon studio

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Bus Parking Frenzy | `com.arlonstudio.bus` | arlon studio | Game parkir bus. **Penarikan 500 DANA aman.** | Belum dicatat | [ ] |

### nazer gaming studio

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Sunny Bus Jam | `com.nazer.gaming.busjam` | nazer gaming studio | Game puzzle bus jam. **Penarikan 500 aman.** | Belum dicatat | [ ] |

### Jalebi Apps

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Ruins of Gold | `com.ruins.of.gold` | Jalebi Apps | Game puzzle/eksplorasi emas. **Penarikan 2.000 aman DANA.** | Belum dicatat | [ ] |
| 2 | Bunny Dream Night | `com.bunny.dream.night` | Jalebi Apps | Game kasual tema kelinci. **Penarikan 500 aman.** | Belum dicatat | [ ] |

## Lança Sites

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Cozy Flora Sort | `com.lancasites.sweetflowersort` | Lança Sites | Game sortir bunga/flora. **Penarikan 1.000 aman dan beberapa ratus aman.** | Belum dicatat | [ ] |
| 2 | Mafia Honor | `com.fatbrandsinc.mafiahonor` | Lança Sites | Game kasual/strategi mafia. **Penarikan cuma 100 tapi aman.** | Belum dicatat | [ ] |

## Kategori Panah & Jam Escape (Arrow & Jam - Studio Tunggal)

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Arrow Jam | `com.arrow.jam.hlyj` | sho never | Game panah macet / unblock arrow. **Penarikan 500 aman.** | Belum dicatat | [ ] |
| 2 | Snail Arrows Twist | `com.factoid.snailarrows` | factoid | Game panah putar model siput. **Penarikan 500 aman.** | Belum dicatat | [ ] |
| 3 | Arrow Zen Cash | `com.goods.admin.arrow.zen.cash` | Goods Administration | Game panah bertema reward / cash. **Penarikan 200 aman.** | Belum dicatat | [ ] |
| 4 | Bus Jam Rush | `putulive.app.bus` | StudyPort | Game bus jam penumpang warna. **Penarikan 200 aman.** | Belum dicatat | [ ] |
| 5 | [Soda Jam Puzzle](soda-jam-puzzle/) | `com.armg.sodajam` | Muhammad Armghan Abbas | Game soda jam puzzle. Tersedia bot otomatis. Instalasi pertama tidak ikut tercatat. **Instalasi kedua penarikan 700 aman DANA.** | Belum dicatat | [x] |
| 6 | Panah Penghasil Uang *(Panah Lepas)* | `com.pelangiarena.panahlepas` | Sub Akademi Game | Puzzle panah / arrow unblock penghasil saldo. Instalasi pertama tidak ada catatan. **Instalasi kedua DANA aman 200-an.** | Belum dicatat | [ ] |
| 7 | Cuan Maze | Belum dicatat | Belum dicatat | Game puzzle labirin/maze cuan. Instalasi pertama tidak ada catatan. **Instalasi kedua DANA aman 300-an.** | Belum dicatat | [ ] |
| 8 | Panah Sentuh *(Arrow Tap)* | Belum dicatat | Belum dicatat | Game ketuk panah / tap arrow puzzle. Instalasi pertama belum ada catatan. **Instalasi kedua DANA aman 800-an.** | Belum dicatat | [ ] |

## Kategori Tile, Match & Sort (Studio Tunggal)

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Sweet Block Puzzle Clear | `com.sweet.bloco.quebra` | AS_ZR | Game block puzzle bertema manis. **Penarikan 1.200 sukses DANA.** | Belum dicatat | [ ] |
| 2 | Fruit Block Sort | `com.fruitblocksort.sortpack.gp` | Bejodev | Game sortir blok buah ke dalam pack. **Penarikan 400 sukses DANA.** | Belum dicatat | [ ] |
| 3 | Harvest Block Crush | `com.harvest.block.crush` | Muhammad Shabbir Hussain | Game block crush puzzle. Instalasi pertama tidak ikut tercatat. **Instalasi kedua DANA aman tapi cuma 400.** | Belum dicatat | [ ] |
| 4 | [Soda Pack Puzzle](soda-pack-puzzle/) | `com.soda.pack.puzzle` | AbkAppStore / Abubakar Ahmad Yusuf | Game sortir soda pack. Ada bot otomatis tetapi belum dites botnya. **Instalasi kedua DANA masih aman 200-an.** | Belum dicatat | [x] |
| 5 | Tangkap Tile Zoo *(Catch Zoo Tiles)* | `com.agmalik.CatchZooTiles` | Agmalik006 | Game match 3 tile tema hewan zoo. Instalasi pertama kosong / belum dicatat. **Instalasi kedua DANA aman 300-an.** | Belum dicatat | [ ] |

## Kategori Merge & Block 2048 (Studio Tunggal)

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Blossom Merge 2048 | `com.garden.merge.blossom` | EasyFrete | Gabungan puzzle 2048 tema bunga mekar. **Penarikan 200 aman.** | Belum dicatat | [ ] |
| 2 | Wood Block Merge 2048 | `com.wood.block.merge2048` | SLEEKSHIFT LIMITED | Gabungan balok kayu dengan aturan 2048. **Penarikan 200 aman.** | Belum dicatat | [ ] |

## Kategori Kasual Lainnya (Shooter, Snake, Spin - Studio Tunggal)

| No. | Game | Package `com` | Developer / perusahaan | Keterangan | Iklan Slot | Bot |
|---:|---|---|---|---|---|:---:|
| 1 | Fortuna Bubble Shooter | `com.fortuna.bubble` | UniteGrand Auto | Game tembak gelembung warna. **Penarikan 700 DANA aman.** | Belum dicatat | [ ] |
| 2 | Orchard Trio | `com.wiwitsugeh.orchardtrio` | M.S Max | Package mirip awalan com.wiwvitsugeh.snack (Snake Out Jam). **Penarikan 500 aman.** | Belum dicatat | [ ] |
| 3 | Planet Slice Master | `com.smartgames.planetslicemaster` | Go Bananas Studio | Game potong planet / slice. **Penarikan kecil sekitar 5.900-an (3 kali) aman DANA di instalasi kedua.** | Belum dicatat | [ ] |

## Daftar Blocked

| No. | Game | Package `com` | Developer / perusahaan | Keterangan |
|---:|---|---|---|---|
| 1 | Fruit Slice Rush | `com.fruit.slicerush` | MNJJ Ventures / MNJJ Enterprises LLC | **Tidak cair; kemungkinan ikut terblokir.** |
| 2 | Mine Sweeper: Jewel Puzzle | `com.mine.sweeper.magicstick.games` | YounEXE / YOUNES MOUMENE | **Tidak cair; kemungkinan ikut terblokir.** |
| 3 | Juicy Tile | `com.spiritbreaker.games.tilejuicy` | Modhon Soft IT / meher sarkar | **Tidak cair; kemungkinan ikut terblokir.** |
| 4 | Ocean Tile: Match 3 Puzzle | `com.shadowgames.dev.ocean.tile` | VPLibros Group / ayo hanafi | **Tidak cair; kemungkinan ikut terblokir.** |
| 5 | Sweet Woodland Match | `com.sweet.woodlandmatch` | FunTech Technology / FunTech Technology Limited | **Tidak cair; kemungkinan ikut terblokir.** |
| 6 | Lucky Sort: Water Puzzle | `com.Lucky.Sort.Water.Puzzle` | Ranat Studio / youssra touilta | **Tidak cair; kemungkinan ikut terblokir.** |
| 7 | Monster Clear | `com.antiboom.puzzle.monster.clear.game` | Cano YH / Fouad Andaloussi | **Tidak cair; kemungkinan ikut terblokir.** |
| 8 | Universe Match - Puzzle Game | `com.shadowgames.dev.universe.match` | VPLibros Group / ayo hanafi | **Tidak cair; kemungkinan ikut terblokir.** |
| 9 | Bubble Crush | `com.bubble.crush.stick.magicgames` | YounEXE / YOUNES MOUMENE | Dipindahkan ke daftar Blocked; data penarikan belum dicatat. |
| 10 | Gem Mine: Jewel Puzzle | `com.gem.mine.stick.magicgames` | YounEXE / YOUNES MOUMENE | **Pernah cair 2 kali:** Rp200 dan Rp50; setelah itu tidak cair lagi. |
| 11 | Dessert Crush | `com.magicgames.dessert.crush.stick` | YounEXE / YOUNES MOUMENE | **Penarikan Rp50 tidak cair.** |
| 12 | Happy Blocks | `com.xteleremobilecompanyltd.HappyBlocks` | Sporting 2024 / محمد السيد عبدالرحيم محمود | Kemungkinan cair, tetapi status tidak berubah setelah 2 kali penarikan sekitar Rp20-an. |
| 13 | Pet Plush Link | `com.NAMMUNIS.PetPlushLink` | Tidak tercantum / Ekanayake Mudiyanselage Prasanna Dilshan Ekanayake | Dipindahkan ke daftar Blocked; data penarikan belum dicatat. |
| 14 | Candy Tile: Sweet Puzzle | `org.beastcoast.major.tilegame.candy` | Cano YH / Fouad Andaloussi | Dipindahkan ke daftar Blocked; data penarikan belum dicatat. |
| 15 | Tasty Tile | Belum diketahui | CLEMMIE INDUSTRY LIMITED | **Pernah menarik Rp10 dan Rp50; setelah itu pengajuan Rp50 tidak cair/lama.** |
| 16 | Fruit Blast | Belum diketahui | Funny Video Collections | Dipindahkan ke daftar Blocked; data penarikan belum dicatat. |
| 17 | Treasure Elimination | Belum diketahui | Funny Video Collections | Dipindahkan ke daftar Blocked; data penarikan belum dicatat. |
| 18 | Orb Quest | Belum diketahui | Belum diketahui | Tidak ditemukan di HP saat pengecekan; dimasukkan ke daftar Blocked sesuai permintaan. |
| 19 | Patch Panic | `com.match3.game.patch.panic.terraform` | Belum diketahui | Ditemukan di HP; dimasukkan ke daftar Blocked sesuai permintaan. |
| 20 | Sea Synth | `com.waterworld.games.tap.seasynth` | Belum diketahui | Ditemukan di HP; dimasukkan ke daftar Blocked sesuai permintaan. |
| 21 | Garden Badges | `com.paldev.production.game.garden` | Belum diketahui | Ditemukan di HP; dimasukkan ke daftar Blocked sesuai permintaan. |
| 22 | Soda Pack Sort | `com.mobiroller.soda.pack` | MIC3 / Michael Jones | Tidak bisa tonton iklan. |
| 23 | MagicDreamStarCrush | `com.luckystarter.magicdreamstarcrush` | DEVVVS 0043 | Penarikan 600 tidak cair. |
| 24 | SliceBladeSplash | `com.suncollecter.slicebladesplash` | DEVVVS 0043 | Penarikan 2rb tidak cair dan rawan terblokir iklannya. |
| 25 | Arrow Soccer Beauty | `com.xteleremobilecompanyltd.ArrowSoccerBeauty` | Sporting 2024 / محمد السيد عبدالرحيم محمود | Aplikasi tidak bisa dibuka, terdeteksi jaringan. Satu developer dengan Veg Cup Blast & Color Sand Blast; belum ada catatan penarikan. |
| 26 | Greenfield Merge | `com.xteleremobilecompanyltd.GreenfieldMerge` | Sporting 2024 / محمد السيد عبدالرحيم محمود | Terdeteksi jaringan. Satu developer dengan Color Sand Blast; belum ada catatan penarikan. |
| 27 | Crystal Blast | `com.shadowgames.dev.crystal.blast` | VPLibros Group / ayo hanafi | Tarik cuma 100 tidak cair. Satu developer dengan Ocean Tile dan Universe Match. |
| 28 | Arrow Claw | `com.gungamefire.ArrowClaw` | GunGameFire | Blocked jaringan; belum ada catatan penarikan. |
| 29 | Happy Bird Sort | `com.kingu.birdsort` | Kingu Studio | Cuma 150 cair lama, kemungkinan tidak cair. |
| 30 | Lucky Gem Merge | `com.luckygem.merge` | ADC Link | Riwayat penarikan tidak ada. |
| 31 | Snaky Go | `com.terraform.snakygo` | Bigiku.com | Baru 200, iklan sudah tidak bisa dibuka. Package terraform (mirip Patch Panic). |
| 32 | Golden Cup Spin | `com.goldencup.happyday` | Applied Data Company LLC | Tidak jelas, mungkin terdeteksi sistem jaringan. |
| 33 | Magic Tile Match Joy | `com.tilefunyou.magictilematchjoy` | DEVVVS 0043 / SUKRIATI | Awal-awal aman tapi sekarang sudah terblokir, kemungkinannya karena tidak bisa rekening yang sama. Ada pencairan sekitar Rp1.000, tetapi 3 penarikan gagal. |
| 34 | Lucky Block Mathwin | Belum diketahui | Belum diketahui | Penarikan kedua gagal, kemungkinan tidak bisa rekening yang sama. Belum ada catatan penarikan valid dan package belum terverifikasi. |
| 35 | Lucky Fruit Bubble Dodge | `com.newgameclick.luckyfruitbubbledodge` | DEVVVS 0043 / SUKRIATI | Instalasi kedua tidak cair, kemungkinan tidak bisa rekening sama dan cuma 1 rb. |
| 36 | Pop Crush Fever | `com.duyifun.popcrushfever` | Duyifun | Instalasi kedua tidak bisa cair, baru penginstalan pertama yang bisa; sama dengan game lain, tidak bisa cair karena rekening harus baru. |
| 37 | Lucky Fruit Sniper | `com.smallclicker.luckyfruitsniper` | DEVVVS 0043 / SUKRIATI | Sudah dikit tidak cair. |
| 38 | Gem Pet Blast *(Pets Blast)* | `com.lucky.petsblast` | Tidak tercantum | Sudah susah cair, perlu nonton iklan malah tidak cair. |
| 39 | Fruit Quest Master | `com.lucky.fruit.quest` | Tidak tercantum | Sudah susah cair, sama seperti Gem Pet Blast (perlu nonton iklan tapi tidak cair). |

## 🏢 Kategori Game Berdasarkan Pengembang

> Nama pengembang/perusahaan dan package di bawah ini berdasarkan metadata Google Play serta konfigurasi bot yang ada di repository. Nama perusahaan dapat berbeda dari nama brand pengembang.

### ACM PROJECTS & AUTOMATION LTD — Elias Galvin

- [Magic Ocean Tile Crush](magic-ocean-tile-crush/) **[RAWAN TERBLOKIR]** — `com.starlightgame.magicoceantilecrush`
- [Woodland Tile Match](woodland-tile-matcher/) **[RAWAN TERBLOKIR]** — `com.starlightgame.woodlandtilematcher`
- [Crazy Fruit Blade Winner](crazy-fruit-blade-winner/) **[RAWAN BLOCK IKLAN]** — `com.starlightgame.crazyfruitbladewinner` — Sekitar Rp200 per hari di awal, tetapi langsung turun setelahnya; lumayan, tetapi rawan block iklan.
- [Fruit Blade Pop Crush](fruit-blade-pop-crush/) — `com.starlightgame.fruitbladepopcrush`
- [Lucky Arrow Escape](lucky-arrow-escaper/) — `com.starlightgame.luckyarrowescaper`

### DEVVVS 0043 — SUKRIATI

- [Juicy Slash Blade Fruit](juicy-slash-blade-fruit/) — `com.dudufun.juicyslashbladefruit`
- [Lucky Fruit Bubble Dodge](lucky-fruit-bubble-dodge/) **[BLOCKED]** — `com.newgameclick.luckyfruitbubbledodge` — Instalasi kedua tidak cair, kemungkinan tidak bisa rekening sama dan cuma 1 rb.

### أحمد البكري خميس موسي

- [Bus Jam Parking Master](bus-jam-parking/) — `com.busjam.parking.master`
- [Coin Sort Dash](coin-dash-shot/) **[RAWAN TERBLOKIR IKLAN]** — `com.coin.sortdash.remove` — Lumayan, tetapi rawan terblokir iklan.

### Pengembang lain

- [Soda Pack Puzzle](soda-pack-puzzle/) — AbkAppStore / Abubakar Ahmad Yusuf — `com.soda.pack.puzzle`
- [Soda Jam Puzzle](soda-jam-puzzle/) — Muhammad Armghan Abbas — `com.armg.sodajam`
- [Lucky Mahjong Blast!](lucky-mahjong/) — DongYing SmartEnergy — `com.lucky.mahjong2`
- [Juice Pack Frenzy](juice-pack/) — ApnaBankShop — `com.apnabankshop.juice`
- [Bus Parking Dash](bus-parking-dash/) — Freelancer Jibon — `com.bus.parking.dash`
- [Crazy Cans Sort](can-sort/) — BAE Publishing LLC — `com.cans.game.crazy`
- [Color Power Pop](color-power-pop/) — Giraffee App — `com.giraffeeapp.power`
- [Animal Blast: Win Prize Game](jungle-animal-eliminate/) — Faisal Developers — `com.jungle.bear.tiger.wild.animal.eliminate`
- [Magical Gems Match 3](magic-gems-match/) — DKSHUBDeveloper — `com.glow.magical.match3`
- Planet Slice Master — Go Bananas Studio — `com.smartgames.planetslicemaster`
- Harvest Block Crush — Muhammad Shabbir Hussain — `com.harvest.block.crush`
- Mahjong Ajaib — ALEXANDER DEJARNETTE — `com.Lucinda.MagicMahjong`
- Panah Penghasil Uang *(Panah Lepas)* — Sub Akademi Game — `com.pelangiarena.panahlepas`
- Tangkap Tile Zoo *(Catch Zoo Tiles)* — Agmalik006 — `com.agmalik.CatchZooTiles`

### Belum terverifikasi

- [Dragon Arrow Escape](dragon-arrow-escape/) — package lokal `com.dragonarrowescape.game`; pengembang/perusahaan belum ditemukan pada listing Google Play publik.
- [Candy Crush](candy-crush/) — package dan pengembang belum teridentifikasi dari file bot yang ada.
- Cuan Maze — package dan pengembang belum dicatat di listing publik.
- Panah Sentuh — package dan pengembang belum dicatat di listing publik.

## 🏆 Peringkat Game Rekomendasi

> Catatan lapangan: peringkat ini berdasarkan pengamatan lokal dari log/bot yang sudah dicoba. Angka bisa berubah mengikuti reset harian, stok iklan, akun, device, dan kondisi jaringan.

| Peringkat | Game | Status Bot | Catatan Utama |
|-----------|------|------------|---------------|
| 1 | **Magic Ocean Tile Crush** | **Paling direkomendasikan** | Reward iklan terlihat paling besar dan paling konsisten. Setelah reset harian biasanya peluang reward besar lebih bagus. Fitur **DOBEL** relatif mudah muncul dan lebih mudah diproses bot. Bot guardian sudah aman untuk: buka game, cari DOBEL, tap bubble, tutup iklan, balik ke game, dan kirim Telegram. |
| 2 | **Woodland Tile Matcher** | Bagus, masih perlu tuning bubble | Satu keluarga pola dengan Magic Ocean dan punya reward DOBEL/bubble, tetapi deteksi/klik bubble masih lebih sensitif dan perlu pemantauan. Cocok sebagai alternatif/rotasi dengan Magic Ocean. |
| 3 | **Soda Pack Puzzle** | Stabil untuk saldo kecil-menengah | Auto play dan laporan Telegram sudah ada. Cocok untuk jalan lama, tetapi reward per iklan tidak setinggi Magic Ocean. |
| 4 | **Coin Dash Shot** | Sudah ada Telegram, kandidat test | Bot sudah punya notifikasi Telegram dan alur withdraw. Perlu uji lagi untuk memastikan reward iklan dan flow withdraw saat ini. |
| 5 | **Bus Jam Parking** | Aman, tetapi reward kecil | Bot berjalan dan Telegram aktif, tapi penghasilan per iklan terpantau kecil sehingga bukan prioritas utama. |

### Catatan Strategi

- **Prioritas utama saat ini: Magic Ocean Tile Crush.**
- Dugaan terbaik dari hasil pantauan: **setelah reset harian, reward cenderung lebih besar dan peluang DOBEL lebih menarik**, jadi Magic Ocean sebaiknya dicoba/diutamakan setelah reset harian.
- Jangan jalankan banyak bot game sekaligus di satu HP. Pakai salah satu: Magic Ocean, Woodland, atau rotator.
- Bot Magic Ocean saat ini sudah relatif aman untuk operasional: ada guardian foreground, penutup Play Store/Chrome redirect, deteksi iklan, fallback tombol BACK, log file, dan notifikasi Telegram.
- Jika iklan mulai macet atau reward turun, hentikan bot lalu jalankan ulang game prioritas atau gunakan rotator Magic-Woodland.


## 🎮 Daftar Bot

### 1. Magic Ocean Tile Crush Guardian Bot (`magic-ocean-tile-crush/`)
Bot prioritas utama saat ini. Guardian untuk Magic Ocean Tile Crush: buka game otomatis, cari reward DOBEL/bubble, tutup Chrome/Play Store jika ter-redirect, handle iklan, lalu kembali ke game.

**Status:** paling direkomendasikan, bot sudah aman untuk dipakai dengan monitoring log dan Telegram.

### 2. Soda Pack Puzzle Bot (`soda-pack-puzzle/`)
Bot otomatis untuk game Soda Pack Puzzle dengan fitur:
- ✅ Auto play game (tap botol sesuai warna)
- ✅ Auto klik bubble reward (Kado, Koin, Balon Iklan)
- ✅ Anti bot-detect (5 detik tap random saat iklan)
- ✅ Auto handle iklan dengan BACK otomatis
- ✅ Auto tarik saldo ke DANA (minimal Rp 500)
- ✅ Telegram notification
- ✅ Multi-device support

**Performa:** ~Rp 100-200 per jam

### 3. Lucky Mahjong Bot (`lucky-mahjong/`)
Bot otomatis untuk game Lucky Mahjong dengan auto-click dan reward collection.

### 4. Juice Pack Bot (`juice-pack/`)
Bot otomatis untuk game Juice Pack dengan pattern recognition.

### 5. Coin Dash Shot Bot (`coin-dash-shot/`)
Bot otomatis untuk game Coin Dash Shot dengan auto-aim.

### 6. Bus Parking Dash Bot (`bus-parking-dash/`)
Bot otomatis untuk game Bus Parking Dash dengan path optimization.

### 7. Bus Jam Parking Bot (`bus-jam-parking/`)
Bot otomatis untuk game Bus Jam Parking dengan smart parking logic.

### 8. Color Power Pop Bot (`color-power-pop/`)
Bot otomatis untuk game Color Power Pop dengan color matching.

### 9. Soda Jam Puzzle Bot (`soda-jam-puzzle/`)
Bot otomatis untuk game Soda Jam Puzzle dengan puzzle solver.

### 10. Can Sort Bot (`can-sort/`)
Bot otomatis untuk game Can Sort dengan sorting algorithm.

### 11. Jungle Animal Eliminate Bot (`jungle-animal-eliminate/`)
Bot otomatis untuk game Jungle Animal Eliminate dengan pattern matching.

### 12. Dragon Arrow Escape Bot (`dragon-arrow-escape/`)
Bot otomatis untuk game Dragon Arrow Escape dengan obstacle detection.

### 13. Candy Crush Bot (`candy-crush/`)
Bot otomatis untuk game Candy Crush dengan advanced pattern recognition.

### 14. Auto Click Bot (`auto-click/`)
Bot universal untuk auto-clicking dengan customizable coordinates.

### 15. Telegram Helper Bot (`telegram-helper/`)
Helper bot untuk notifikasi Telegram dan monitoring saldo.

### 16. Crazy Fruit Blade Winner Guardian Bot (`crazy-fruit-blade-winner/`) — **[RAWAN BLOCK IKLAN]**
Clone dari Fruit Blade Pop Crush untuk game Crazy Fruit Blade Winner. Package: `com.starlightgame.crazyfruitbladewinner`. Keterangan: sekitar Rp200 per hari di awal, tetapi langsung turun setelahnya; lumayan, tetapi rawan block iklan.



## 📋 Requirements

- macOS / Linux
- Python 3.8+
- ADB (Android Debug Bridge)
- scrcpy
- Android device dengan USB debugging enabled

## 🚀 Instalasi

```bash
# Clone repository
git clone git@github.com:duwianjar/android-game-bots.git
cd android-game-bots

# Install dependencies
pip3 install opencv-python pytesseract numpy Pillow requests

# Install ADB & scrcpy (macOS)
brew install android-platform-tools scrcpy

# Sambungkan HP Android via USB
adb devices
```

## 📱 Setup HP Android

1. Enable Developer Options
2. Enable USB Debugging
3. Sambungkan ke Mac/PC via USB
4. Izinkan USB debugging saat prompt muncul

## 🎯 Cara Pakai

### Soda Pack Puzzle Bot

```bash
cd soda-pack-puzzle
./run_soda_pack_puzzle_bot.sh
```

Bot akan otomatis:
1. Buka game Soda Pack Puzzle
2. Main game (tap botol)
3. Klik bubble reward
4. Handle iklan (5 detik anti bot-detect + auto BACK)
5. Tarik saldo ke DANA saat >= Rp 500

### Monitoring

```bash
# Lihat bot real-time
tmux attach -t soda_pack_bot

# Keluar: Ctrl+B lalu D

# Cek saldo
cat soda_telegram_reporter_state.json

# Stop bot
./stop_soda_pack_puzzle_bot.sh
```

## ⚙️ Konfigurasi

Edit file `soda_pack_puzzle_bot.py`:

```python
# Minimum saldo untuk auto tarik
MIN_WITHDRAW_RP = 500

# Waktu tunggu iklan (detik)
AD_WAIT_SECONDS = 15

# Telegram bot token (opsional)
TELEGRAM_BOT_TOKEN = "your_token"
TELEGRAM_CHAT_ID = "your_chat_id"
```

## 🔧 Optimasi Yang Sudah Diterapkan

1. **Anti Bot-Detect:** Tap random 5 detik saat iklan untuk hindari deteksi
2. **Auto BACK:** Tidak tunggu tombol X, langsung BACK setelah 5 detik
3. **Skip Verification:** Skip verifikasi saldo, fokus ke gameplay
4. **Speed Boost:** Semua delay dikurangi 50%
5. **Smart Detection:** Deteksi bubble yang sudah lewat/statis
6. **No Restart Loop:** Tidak restart jika saldo tidak naik (karena iklan bukan sumber utama)

## 📊 Performa

| Game | Peringkat | Status Performa | Target Minimal | Metode Penarikan |
|------|-----------|------------------|----------------|------------------|
| Magic Ocean Tile Crush | 1 | Terbaik saat ini; reward iklan/DOBEL paling menarik dari hasil pantauan | fleksibel / sesuai bot | DANA / saldo game |
| Woodland Tile Matcher | 2 | Potensial tinggi, tetapi klik bubble masih perlu tuning | fleksibel / sesuai bot | DANA / saldo game |
| Soda Pack Puzzle | 3 | Stabil untuk saldo kecil-menengah | Rp 500 | DANA |
| Coin Dash Shot | 4 | Sudah ada Telegram, perlu test ulang performa terbaru | Rp 200-500 | DANA |
| Bus Jam Parking | 5 | Aman tetapi reward per iklan kecil | Rp 200 | DANA |
| Lucky Mahjong | - | Belum jadi prioritas | Rp 300 | DANA |
| Juice Pack | - | Belum jadi prioritas | Rp 500 | DANA |
| Color Power Pop | - | Belum jadi prioritas | Rp 300 | DANA |
| Jungle Animal Eliminate | - | Belum jadi prioritas | Rp 500 | DANA |

## 📁 Struktur Folder

```
android-game-bots/
├── _assets/                 # Aset bersama (logs, screenshots)
│   ├── logs/               # Log dari semua bot
│   └── screenshots/        # Screenshot debugging
├── auto-click/             # Bot universal auto-click
├── bus-jam-parking/        # Bot Bus Jam Parking
├── bus-parking-dash/       # Bot Bus Parking Dash
├── can-sort/               # Bot Can Sort
├── candy-crush/            # Bot Candy Crush
├── coin-dash-shot/         # Bot Coin Dash Shot
├── color-power-pop/        # Bot Color Power Pop
├── crazy-fruit-blade-winner/ # Guardian Crazy Fruit Blade Winner
├── dragon-arrow-escape/    # Bot Dragon Arrow Escape
├── juice-pack/             # Bot Juice Pack
├── jungle-animal-eliminate/# Bot Jungle Animal Eliminate
├── lucky-mahjong/          # Bot Lucky Mahjong
├── soda-jam-puzzle/        # Bot Soda Jam Puzzle
├── soda-pack-puzzle/       # Bot Soda Pack Puzzle
├── telegram-helper/        # Bot helper Telegram
├── magic-ocean-tile-crush/ # Guardian Magic Ocean Tile Crush
└── README.md              # Dokumentasi lengkap
```

## 🛡️ Anti-Ban Features

- ✅ Random tap timing (tidak fix interval)
- ✅ Human-like movement simulation
- ✅ Anti bot-detect saat iklan (5 detik tap random)
- ✅ Variasi koordinat tap (±10px random offset)
- ✅ Sleep random delay antara aksi

## 📝 Log & Debugging

```bash
# Lihat log lengkap
tail -f ~/soda_pack_puzzle_bot.log

# Cek error
grep ERROR ~/soda_pack_puzzle_bot.log

# Monitor saldo real-time
watch -n 5 'cat ~/soda_telegram_reporter_state.json'
```

## 🤝 Contributing

Pull requests welcome! Untuk perubahan besar, buka issue dulu untuk diskusi.

## ⚠️ Disclaimer

Bot ini untuk educational purposes. Gunakan dengan bijak dan ikuti terms of service dari masing-masing game.

## 📜 License

MIT License - bebas digunakan dan dimodifikasi.

## 👨‍💻 Author

**Duwi Anjar**
- GitHub: [@duwianjar](https://github.com/duwianjar)

---

**⭐ Star repo ini jika berguna!**
