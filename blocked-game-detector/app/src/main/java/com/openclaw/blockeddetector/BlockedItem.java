package com.openclaw.blockeddetector;

import java.io.Serializable;

public class BlockedItem implements Serializable {
    public final int id;
    public final String name;
    public final String packageName;
    public final String developer;
    public final String notes;
    public final String[] keywords;

    public BlockedItem(int id, String name, String packageName, String developer, String notes, String... keywords) {
        this.id = id;
        this.name = name;
        this.packageName = packageName != null ? packageName.trim() : "";
        this.developer = developer;
        this.notes = notes;
        this.keywords = keywords != null ? keywords : new String[0];
    }

    public boolean matches(String pkg, String appLabel) {
        if (pkg == null || pkg.isEmpty()) return false;
        String cleanPkg = pkg.trim().toLowerCase();
        String cleanLabel = appLabel != null ? appLabel.trim().toLowerCase() : "";

        // Jangan pernah memblokir package sistem atau bot sendiri
        if (cleanPkg.startsWith("android") || cleanPkg.startsWith("com.android.") ||
            cleanPkg.startsWith("com.google.") || cleanPkg.startsWith("com.openclaw.")) {
            return false;
        }

        // Jika package name terdefinisi, cocokkan PERSIS dengan package name agar tidak salah blokir
        // game lain yang namanya mirip (misal: Ocean Tile vs Magic Ocean Tile Crush)
        if (!packageName.isEmpty()) {
            return cleanPkg.equalsIgnoreCase(packageName.toLowerCase());
        }

        // Untuk game yang package com belum diketahui: cocokkan label aplikasi secara ketat
        if (!name.isEmpty() && cleanLabel.equalsIgnoreCase(name.toLowerCase())) {
            return true;
        }

        for (String kw : keywords) {
            String cleanKw = kw.trim().toLowerCase();
            if (cleanLabel.equalsIgnoreCase(cleanKw)) {
                return true;
            }
            if (cleanPkg.equals(cleanKw) || cleanPkg.endsWith("." + cleanKw)) {
                return true;
            }
        }
        return false;
    }
}
