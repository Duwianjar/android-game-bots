package com.openclaw.blockeddetector;

import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class BlockedRegistry {
    public static final List<BlockedItem> ITEMS;

    static {
        List<BlockedItem> list = new ArrayList<>();
        list.add(new BlockedItem(1, "Fruit Slice Rush", "com.fruit.slicerush", "MNJJ Ventures / MNJJ Enterprises LLC", "Tidak cair; kemungkinan ikut terblokir.", "fruit.slicerush", "fruit slice rush"));
        list.add(new BlockedItem(2, "Mine Sweeper: Jewel Puzzle", "com.mine.sweeper.magicstick.games", "YounEXE / YOUNES MOUMENE", "Tidak cair; kemungkinan ikut terblokir.", "mine.sweeper.magicstick", "mine sweeper: jewel puzzle"));
        list.add(new BlockedItem(3, "Juicy Tile", "com.spiritbreaker.games.tilejuicy", "Modhon Soft IT / meher sarkar", "Tidak cair; kemungkinan ikut terblokir.", "games.tilejuicy", "juicy tile"));
        list.add(new BlockedItem(4, "Ocean Tile: Match 3 Puzzle", "com.shadowgames.dev.ocean.tile", "VPLibros Group / ayo hanafi", "Tidak cair; kemungkinan ikut terblokir.", "ocean.tile", "ocean tile"));
        list.add(new BlockedItem(5, "Sweet Woodland Match", "com.sweet.woodlandmatch", "FunTech Technology / FunTech Technology Limited", "Tidak cair; kemungkinan ikut terblokir.", "sweet.woodlandmatch", "sweet woodland match"));
        list.add(new BlockedItem(6, "Lucky Sort: Water Puzzle", "com.Lucky.Sort.Water.Puzzle", "Ranat Studio / youssra touilta", "Tidak cair; kemungkinan ikut terblokir.", "lucky.sort.water", "lucky sort"));
        list.add(new BlockedItem(7, "Monster Clear", "com.antiboom.puzzle.monster.clear.game", "Cano YH / Fouad Andaloussi", "Tidak cair; kemungkinan ikut terblokir.", "monster.clear", "monster clear"));
        list.add(new BlockedItem(8, "Universe Match - Puzzle Game", "com.shadowgames.dev.universe.match", "VPLibros Group / ayo hanafi", "Tidak cair; kemungkinan ikut terblokir.", "universe.match", "universe match"));
        list.add(new BlockedItem(9, "Bubble Crush", "com.bubble.crush.stick.magicgames", "YounEXE / YOUNES MOUMENE", "Dipindahkan ke daftar Blocked; data penarikan belum dicatat.", "bubble.crush.stick", "bubble crush"));
        list.add(new BlockedItem(10, "Gem Mine: Jewel Puzzle", "com.gem.mine.stick.magicgames", "YounEXE / YOUNES MOUMENE", "Pernah cair 2 kali: Rp200 dan Rp50; setelah itu tidak cair lagi.", "gem.mine.stick", "gem mine"));
        list.add(new BlockedItem(11, "Dessert Crush", "com.magicgames.dessert.crush.stick", "YounEXE / YOUNES MOUMENE", "Penarikan Rp50 tidak cair.", "dessert.crush.stick", "dessert crush"));
        list.add(new BlockedItem(12, "Happy Blocks", "com.xteleremobilecompanyltd.HappyBlocks", "Sporting 2024 / محمد السيد عبدالرحيم محمود", "Kemungkinan cair, tetapi status tidak berubah setelah 2 kali penarikan sekitar Rp20-an.", "happyblocks", "happy blocks"));
        list.add(new BlockedItem(13, "Pet Plush Link", "com.NAMMUNIS.PetPlushLink", "Ekanayake Mudiyanselage Prasanna Dilshan Ekanayake", "Dipindahkan ke daftar Blocked; data penarikan belum dicatat.", "petplushlink", "pet plush link"));
        list.add(new BlockedItem(14, "Candy Tile: Sweet Puzzle", "org.beastcoast.major.tilegame.candy", "Cano YH / Fouad Andaloussi", "Dipindahkan ke daftar Blocked; data penarikan belum dicatat.", "tilegame.candy", "candy tile"));
        list.add(new BlockedItem(15, "Tasty Tile", "", "CLEMMIE INDUSTRY LIMITED", "Pernah menarik Rp10 dan Rp50; setelah itu pengajuan Rp50 tidak cair/lama.", "tasty tile", "tastytile"));
        list.add(new BlockedItem(16, "Fruit Blast", "", "Funny Video Collections", "Dipindahkan ke daftar Blocked; data penarikan belum dicatat.", "fruit blast", "fruitblast"));
        list.add(new BlockedItem(17, "Treasure Elimination", "", "Funny Video Collections", "Dipindahkan ke daftar Blocked; data penarikan belum dicatat.", "treasure elimination", "treasureelimination"));
        list.add(new BlockedItem(18, "Orb Quest", "", "Belum diketahui", "Tidak ditemukan di HP saat pengecekan; dimasukkan ke daftar Blocked sesuai permintaan.", "orb quest", "orbquest"));
        list.add(new BlockedItem(19, "Patch Panic", "com.match3.game.patch.panic.terraform", "Belum diketahui", "Ditemukan di HP; dimasukkan ke daftar Blocked sesuai permintaan.", "patch.panic", "patch panic"));
        list.add(new BlockedItem(20, "Sea Synth", "com.waterworld.games.tap.seasynth", "Belum diketahui", "Ditemukan di HP; dimasukkan ke daftar Blocked sesuai permintaan.", "seasynth", "sea synth"));
        list.add(new BlockedItem(21, "Garden Badges", "com.paldev.production.game.garden", "Belum diketahui", "Ditemukan di HP; dimasukkan ke daftar Blocked sesuai permintaan.", "production.game.garden", "garden badges"));
        list.add(new BlockedItem(22, "Soda Pack Sort", "com.mobiroller.soda.pack", "MIC3 / Michael Jones", "Tidak bisa tonton iklan.", "mobiroller.soda.pack", "soda pack sort"));
        list.add(new BlockedItem(23, "MagicDreamStarCrush", "com.luckystarter.magicdreamstarcrush", "DEVVVS 0043", "Penarikan 600 tidak cair.", "magicdreamstarcrush", "magic dream star crush"));
        list.add(new BlockedItem(24, "SliceBladeSplash", "com.suncollecter.slicebladesplash", "DEVVVS 0043", "Penarikan 2rb tidak cair dan rawan terblokir iklannya.", "slicebladesplash", "slice blade splash"));
        list.add(new BlockedItem(25, "Arrow Soccer Beauty", "com.xteleremobilecompanyltd.ArrowSoccerBeauty", "Sporting 2024 / محمد السيد عبدالرحيم محمود", "Aplikasi tidak bisa dibuka terdeteksi jaringan. Satu developer dengan Veg Cup Blast & Color Sand Blast; belum ada catatan penarikan.", "arrowsoccerbeauty", "arrow soccer beauty"));
        list.add(new BlockedItem(26, "Greenfield Merge", "com.xteleremobilecompanyltd.GreenfieldMerge", "Sporting 2024 / محمد السيد عبدالرحيم محمود", "Terdeteksi jaringan. Satu developer dengan Color Sand Blast; belum ada catatan penarikan.", "greenfieldmerge", "greenfield merge"));
        list.add(new BlockedItem(27, "Crystal Blast", "com.shadowgames.dev.crystal.blast", "VPLibros Group / ayo hanafi", "Tarik cuma 100 tidak cair. Satu developer dengan Ocean Tile dan Universe Match.", "crystalblast", "crystal blast"));
        list.add(new BlockedItem(28, "Arrow Claw", "com.gungamefire.ArrowClaw", "GunGameFire", "Blocked jaringan; belum ada catatan penarikan.", "arrowclaw", "arrow claw"));
        list.add(new BlockedItem(29, "Happy Bird Sort", "com.kingu.birdsort", "Kingu Studio", "Cuma 150 cair lama, kemungkinan tidak cair.", "happybirdsort", "happy bird sort"));
        list.add(new BlockedItem(30, "Lucky Gem Merge", "com.luckygem.merge", "ADC Link", "Riwayat penarikan tidak ada.", "luckygemmerge", "lucky gem merge"));
        list.add(new BlockedItem(31, "Snaky Go", "com.terraform.snakygo", "Bigiku.com", "Baru 200, iklan sudah tidak bisa dibuka. Package terraform (mirip Patch Panic).", "snakygo", "snaky go"));
        list.add(new BlockedItem(32, "Golden Cup Spin", "com.goldencup.happyday", "Applied Data Company LLC", "Tidak jelas, mungkin terdeteksi sistem jaringan.", "goldencupspin", "golden cup spin"));
        list.add(new BlockedItem(33, "Magic Tile Match Joy", "com.tilefunyou.magictilematchjoy", "DEVVVS 0043 / SUKRIATI", "Awal-awal aman tapi sekarang sudah terblokir, kemungkinannya karena tidak bisa rekening yang sama. Ada pencairan sekitar Rp1.000, tetapi 3 penarikan gagal.", "magictilematchjoy", "magic tile match joy"));
        list.add(new BlockedItem(34, "Lucky Block Mathwin", "", "Belum diketahui", "Penarikan kedua gagal, kemungkinan tidak bisa rekening yang sama. Belum ada catatan penarikan valid dan package belum terverifikasi.", "lucky block mathwin", "luckyblockmathwin"));
        list.add(new BlockedItem(35, "Lucky Fruit Bubble Dodge", "com.newgameclick.luckyfruitbubbledodge", "DEVVVS 0043 / SUKRIATI", "Instalasi kedua tidak cair, kemungkinan tidak bisa rekening sama dan cuma 1 rb.", "luckyfruitbubbledodge", "lucky fruit bubble dodge"));
        list.add(new BlockedItem(36, "Pop Crush Fever", "com.duyifun.popcrushfever", "Duyifun", "Instalasi kedua tidak bisa cair, baru penginstalan pertama yang bisa; sama dengan game lain, tidak bisa cair karena rekening harus baru.", "popcrushfever", "pop crush fever"));
        list.add(new BlockedItem(37, "Lucky Fruit Sniper", "com.smallclicker.luckyfruitsniper", "DEVVVS 0043 / SUKRIATI", "Sudah dikit tidak cair.", "luckyfruitsniper", "lucky fruit sniper"));
        list.add(new BlockedItem(38, "Gem Pet Blast (Pets Blast)", "com.lucky.petsblast", "Tidak tercantum", "Sudah susah cair, perlu nonton iklan malah tidak cair.", "petsblast", "gem pet blast"));
        list.add(new BlockedItem(39, "Fruit Quest Master", "com.lucky.fruit.quest", "Tidak tercantum", "Sudah susah cair, sama seperti Gem Pet Blast (perlu nonton iklan tapi tidak cair).", "fruit.quest", "fruit quest master"));
        list.add(new BlockedItem(40, "Blade Slice Master Fruit", "com.diancutter.bladeslicemasterfruit", "Belum diketahui", "Instalasi kedua tidak bisa tarik meski saldo sekitar Rp14.000.", "bladeslicemasterfruit", "blade slice master fruit"));
        list.add(new BlockedItem(41, "Cut Fruit Blade Master", "com.goodgamecut.cutfruitblademaster", "Belum diketahui", "Instalasi kedua memiliki penarikan Rp18.000 yang pending.", "cutfruitblademaster", "cut fruit blade master"));
        list.add(new BlockedItem(42, "LuckyScrewSort", "", "Belum diketahui", "Penarikan Rp6.000 gagal dua kali; diduga tidak bisa memakai rekening DANA yang sama.", "luckyscrewsort", "lucky screw sort"));
        list.add(new BlockedItem(43, "Magic Star Crush Journey", "com.starlightgame.magicstarcrushjourney", "ACM PROJECTS & AUTOMATION LTD / Elias Galvin", "Instalasi pertama 951, kedua 600 aman, ketiga terblokir tidak bisa tarik.", "magicstarcrushjourney", "magic star crush journey"));
        list.add(new BlockedItem(44, "Soccer Tap Guard", "goal.soccertap.guardfrenzy", "MIC3 / Michael Jones", "Developer sama dengan Soda Pack Sort. Penarikan 1.000 aman di awal; dipindahkan ke daftar Blocked.", "soccertap.guardfrenzy", "soccer tap guard"));
        list.add(new BlockedItem(45, "Crazy Tile Match Winner", "com.moonshotcube.crazytilematchwinner", "Elias Galvin", "Penarikan 500 cair DANA di awal; dipindahkan ke daftar Blocked.", "crazytilematchwinner", "crazy tile match winner"));
        list.add(new BlockedItem(46, "Cute Fairy Blast Tale", "com.msxcleargamer.cutefairyblasttale", "DEVVVS 0043", "Penarikan Rp100 tidak cair.", "cutefairyblasttale", "cute fairy blast tale"));
        ITEMS = Collections.unmodifiableList(list);
    }

    public static BlockedItem checkPackage(PackageManager pm, String pkg) {
        if (pkg == null || pkg.isEmpty()) return null;
        String appLabel = "";
        try {
            ApplicationInfo ai = pm.getApplicationInfo(pkg, 0);
            CharSequence label = pm.getApplicationLabel(ai);
            if (label != null) appLabel = label.toString();
        } catch (Exception ignored) {
        }

        for (BlockedItem item : ITEMS) {
            if (item.matches(pkg, appLabel)) {
                return item;
            }
        }
        return null;
    }

    public static List<DetectedApp> scanInstalled(Context context) {
        PackageManager pm = context.getPackageManager();
        List<DetectedApp> detected = new ArrayList<>();
        List<PackageInfo> installed = pm.getInstalledPackages(0);
        for (PackageInfo pi : installed) {
            BlockedItem match = checkPackage(pm, pi.packageName);
            if (match != null) {
                String label = pi.packageName;
                try {
                    CharSequence cs = pm.getApplicationLabel(pi.applicationInfo);
                    if (cs != null) label = cs.toString();
                } catch (Exception ignored) {}
                detected.add(new DetectedApp(match, pi.packageName, label));
            }
        }
        return detected;
    }

    public static class DetectedApp {
        public final BlockedItem item;
        public final String actualPackage;
        public final String actualLabel;

        public DetectedApp(BlockedItem item, String actualPackage, String actualLabel) {
            this.item = item;
            this.actualPackage = actualPackage;
            this.actualLabel = actualLabel;
        }
    }
}
