package com.openclaw.gamebothub;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class BotRegistry {
    private static final String PREF_NAME = "game_bot_hub_prefs";
    private static final String KEY_DURATION = "rotation_duration_minutes";
    private static final String KEY_LOOP = "rotation_loop";
    private static final String KEY_INITIALIZED = "prefs_initialized_v2";

    private static BotRegistry instance;
    private final List<BotItem> allBots = new ArrayList<>();
    private final Map<String, BotItem> packageMap = new LinkedHashMap<>();
    private int durationMinutes = 10;
    private boolean loopMode = true;

    public static synchronized BotRegistry getInstance() {
        if (instance == null) {
            instance = new BotRegistry();
        }
        return instance;
    }

    private BotRegistry() {
        initCatalog();
    }

    private void initCatalog() {
        // Prioritas Utama & Populer
        register("zoo_tile", "Zoo Tile / Tangkap Hewan Lucu", "com.zoo.tile.cute.animal.elephant.mouse.fox", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("woodland", "Woodland Tile Match", "com.starlightgame.woodlandtilematcher", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("magic_ocean", "Magic Ocean Tile Crush", "com.starlightgame.magicoceantilecrush", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("catch_zoo", "Catch Zoo Tiles", "com.agmalik.CatchZooTiles", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("bus_jam", "Bus Jam Parking Master", "com.busjam.parking.master", "Bus Jam / Parking", BotItem.GameplayType.BUS_JAM);
        register("greenfield", "Greenfield Merge", "com.xteleremobilecompanyltd.GreenfieldMerge", "Merge", BotItem.GameplayType.MERGE);
        register("crazy_fruit", "Crazy Fruit Blade Winner", "com.starlightgame.crazyfruitbladewinner", "Blade / Slash", BotItem.GameplayType.BLADE_SLASH);
        register("fruit_blade", "Fruit Blade Pop Crush", "com.starlightgame.fruitbladepopcrush", "Blade / Slash", BotItem.GameplayType.BLADE_SLASH);
        register("cut_fruit_winner", "Cut Fruit Winner", "com.starlightgame.cutfruitwinner", "Blade / Slash", BotItem.GameplayType.BLADE_SLASH);
        register("juicy_slash", "Juicy Slash Blade Fruit", "com.dudufun.juicyslashbladefruit", "Blade / Slash", BotItem.GameplayType.BLADE_SLASH);
        register("magic_gems", "Magical Gems Match 3", "com.glow.magical.match3", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("color_power", "Color Power Pop", "com.giraffeeapp.power", "Bubble / Pop", BotItem.GameplayType.BUBBLE_POP);
        register("animal_blast", "Animal Blast / Jungle Eliminate", "com.jungle.bear.tiger.wild.animal.eliminate", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("coin_sort", "Coin Sort Dash", "com.coin.sortdash.remove", "Can / Sort", BotItem.GameplayType.SODA_SORT);
        register("soda_pack", "Soda Pack Puzzle / Soda Pop", "com.soda.pack.puzzle", "Color / Sort", BotItem.GameplayType.SODA_SORT);
        register("lucky_arrow", "Lucky Arrow Escaper", "com.starlightgame.luckyarrowescaper", "Arrow / Puzzle", BotItem.GameplayType.ARROW_ESCAPE);
        register("dragon_arrow", "Dragon Arrow Escape", "com.dragonarrowescape.game", "Arrow / Puzzle", BotItem.GameplayType.ARROW_ESCAPE);
        register("tap_arrow", "Tap Arrow Fun", "com.taparrowfun.game", "Arrow / Puzzle", BotItem.GameplayType.ARROW_ESCAPE);
        register("lucky_fruit_bubble", "Lucky Fruit Bubble Dodge", "com.newgameclick.luckyfruitbubbledodge", "Bubble / Pop", BotItem.GameplayType.BUBBLE_POP);
        register("soda_jam", "Soda Jam Puzzle", "com.armg.sodajam", "Color / Sort", BotItem.GameplayType.SODA_SORT);
        register("tile_juicy", "Tile Juicy", "com.spiritbreaker.games.tilejuicy", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("catch_cute_pets", "Catch Cute Pets", "com.NAMMUNIS.CatchCutePets", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("can_sort", "Can Sort", "com.cans.game.crazy", "Can / Sort", BotItem.GameplayType.SODA_SORT);
        register("juice_pack", "Juice Pack", "com.apnabankshop.juice", "Color / Sort", BotItem.GameplayType.SODA_SORT);
        register("lucky_mahjong", "Lucky Mahjong", "com.lucky.mahjong2", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("fortune_mahjong", "Fortune Tile Mahjong", "com.NAMMUNIS.FortuneTileMahjong", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("magic_mahjong", "Magic Mahjong Lucinda", "com.Lucinda.MagicMahjong", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("crazy_tile", "Crazy Tile Match Winner", "com.moonshotcube.crazytilematchwinner", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("bus_parking_dash", "Bus Parking Dash", "com.bus.parking.dash", "Bus Jam / Parking", BotItem.GameplayType.BUS_JAM);
        register("tiny_blast", "Tiny Blast Magic Land", "com.kuaifastfa.tinyblastmagicland", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("blade_slice", "Blade Slice Master Fruit", "com.diancutter.bladeslicemasterfruit", "Blade / Slash", BotItem.GameplayType.BLADE_SLASH);
        register("cut_fruit", "Cut Fruit Blade Master", "com.goodgamecut.cutfruitblademaster", "Blade / Slash", BotItem.GameplayType.BLADE_SLASH);
        register("slice_blade", "Slice Blade Splash", "com.suncollecter.slicebladesplash", "Blade / Slash", BotItem.GameplayType.BLADE_SLASH);
        register("magic_tile_joy", "Magic Tile Match Joy", "com.tilefunyou.magictilematchjoy", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("magic_star_crush", "Magic Star Crush Journey", "com.starlightgame.magicstarcrushjourney", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("fortune_ocean", "Fortune Ocean Game", "com.fortune.ocean.game", "Tile Match", BotItem.GameplayType.TILE_MATCH);
        register("magic_merge", "Magic Merge", "com.xteleremobilecompanyltd.MagicMerge", "Merge", BotItem.GameplayType.MERGE);
    }

    private void register(String id, String name, String pkg, String cat, BotItem.GameplayType type) {
        BotItem bot = new BotItem(id, name, pkg, cat, type);
        allBots.add(bot);
        packageMap.put(pkg, bot);
    }

    public List<BotItem> getAllBots() {
        return Collections.unmodifiableList(allBots);
    }

    public BotItem getBotByPackage(String pkg) {
        return packageMap.get(pkg);
    }

    public void refreshInstalledStatus(Context context) {
        PackageManager pm = context.getPackageManager();
        for (BotItem bot : allBots) {
            try {
                PackageInfo info = pm.getPackageInfo(bot.getPackageName(), 0);
                bot.setInstalled(true);
                bot.setVersionName(info.versionName != null ? info.versionName : "");
            } catch (PackageManager.NameNotFoundException e) {
                bot.setInstalled(false);
                bot.setVersionName("");
            }
        }
    }

    public void loadPreferences(Context context) {
        SharedPreferences sp = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
        durationMinutes = sp.getInt(KEY_DURATION, 10);
        loopMode = sp.getBoolean(KEY_LOOP, true);

        boolean initialized = sp.getBoolean(KEY_INITIALIZED, false);
        for (BotItem bot : allBots) {
            if (!initialized) {
                // Pertama kali: aktifkan hanya yang terinstall di HP
                bot.setEnabled(bot.isInstalled());
            } else {
                bot.setEnabled(sp.getBoolean("bot_enabled_" + bot.getId(), bot.isInstalled()));
            }
        }
    }

    public void savePreferences(Context context) {
        SharedPreferences.Editor ed = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE).edit();
        ed.putInt(KEY_DURATION, durationMinutes);
        ed.putBoolean(KEY_LOOP, loopMode);
        ed.putBoolean(KEY_INITIALIZED, true);
        for (BotItem bot : allBots) {
            ed.putBoolean("bot_enabled_" + bot.getId(), bot.isEnabled());
        }
        ed.apply();
    }

    public void enableAllInstalled() {
        for (BotItem bot : allBots) {
            if (bot.isInstalled()) {
                bot.setEnabled(true);
            }
        }
    }

    public void disableAll() {
        for (BotItem bot : allBots) {
            bot.setEnabled(false);
        }
    }

    public List<BotItem> getActiveQueue() {
        List<BotItem> queue = new ArrayList<>();
        for (BotItem bot : allBots) {
            if (bot.isEnabled() && bot.isInstalled()) {
                queue.add(bot);
            }
        }
        return queue;
    }

    public int getDurationMinutes() {
        return durationMinutes;
    }

    public void setDurationMinutes(int durationMinutes) {
        this.durationMinutes = Math.max(1, durationMinutes);
    }

    public boolean isLoopMode() {
        return loopMode;
    }

    public void setLoopMode(boolean loopMode) {
        this.loopMode = loopMode;
    }
}
