package com.openclaw.gamebothub;

import java.io.Serializable;

public class BotItem implements Serializable {
    public enum GameplayType {
        TILE_MATCH("Tile Matcher"),
        BUS_JAM("Bus Jam Parking"),
        BLADE_SLASH("Blade Fruit Slash"),
        SODA_SORT("Color/Soda Sort"),
        BUBBLE_POP("Bubble Pop"),
        MERGE("Merge Item"),
        ARROW_ESCAPE("Arrow Escape");

        private final String display;
        GameplayType(String display) {
            this.display = display;
        }
        public String getDisplay() {
            return display;
        }
    }

    private final String id;
    private final String name;
    private final String packageName;
    private final String category;
    private final GameplayType gameplayType;
    private boolean installed;
    private String versionName = "";
    private boolean enabled;
    private long totalRunSeconds;

    public BotItem(String id, String name, String packageName, String category, GameplayType gameplayType) {
        this.id = id;
        this.name = name;
        this.packageName = packageName;
        this.category = category;
        this.gameplayType = gameplayType;
        this.installed = false;
        this.enabled = false;
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getPackageName() {
        return packageName;
    }

    public String getCategory() {
        return category;
    }

    public GameplayType getGameplayType() {
        return gameplayType;
    }

    public boolean isInstalled() {
        return installed;
    }

    public void setInstalled(boolean installed) {
        this.installed = installed;
    }

    public String getVersionName() {
        return versionName;
    }

    public void setVersionName(String versionName) {
        this.versionName = versionName;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public long getTotalRunSeconds() {
        return totalRunSeconds;
    }

    public void addRunSeconds(long seconds) {
        this.totalRunSeconds += seconds;
    }
}
