package com.openclaw.colorpowerpop;

import android.graphics.Bitmap;
import android.graphics.Color;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Deteksi presisi warna kartu Color Power Pop (HSV), pencocokan slot atas ke wadah bawah,
 * serta deteksi visual tombol iklan & reward.
 */
public final class ScreenAnalyzer {
    private ScreenAnalyzer() {
    }

    public static final String[] COLORS = {
            "Red", "Orange", "Yellow", "Green", "Cyan", "Blue", "Pink"
    };

    public static final class SlotCard {
        public final int slotIndex;
        public final String color;
        public final int x;
        public final int y;

        public SlotCard(int slotIndex, String color, int x, int y) {
            this.slotIndex = slotIndex;
            this.color = color;
            this.x = x;
            this.y = y;
        }
    }

    public static final class BottomBox {
        public final int index;
        public final String color;
        public final int x;
        public final int y;

        public BottomBox(int index, String color, int x, int y) {
            this.index = index;
            this.color = color;
            this.x = x;
            this.y = y;
        }
    }

    public static final class Result {
        public int width;
        public int height;
        public final List<SlotCard> topSlots = new ArrayList<>();
        public final List<BottomBox> bottomBoxes = new ArrayList<>();
        public final List<SlotCard> matchingCardsToTap = new ArrayList<>();
        public boolean boardVisible;
        public boolean adScreenLikely;
        public boolean adCloseButtonVisible;
        public float adCloseButtonX = -1;
        public float adCloseButtonY = -1;
        public boolean adSkipButtonVisible;
        public float adSkipButtonX = -1;
        public float adSkipButtonY = -1;
    }

    public static Result analyze(Bitmap bitmap) {
        Result result = new Result();
        result.width = bitmap.getWidth();
        result.height = bitmap.getHeight();
        float sx = result.width / 720f;
        float sy = result.height / 1640f;

        // 1. Periksa tombol close X iklan visual
        float[] closeBtn = findAdCloseButton(bitmap, sx, sy);
        if (closeBtn != null) {
            result.adCloseButtonVisible = true;
            result.adCloseButtonX = closeBtn[0];
            result.adCloseButtonY = closeBtn[1];
        }

        // 2. Deteksi warna 6 wadah/kotak bawah
        int[][] baseBottom = {
                {160, 1235}, {360, 1235}, {560, 1235},
                {160, 1380}, {360, 1380}, {560, 1380}
        };
        Set<String> row1Colors = new HashSet<>();
        Set<String> allBottomColors = new HashSet<>();
        int halfW = (int) (35 * sx);
        int halfH = (int) (25 * sy);
        for (int i = 0; i < baseBottom.length; i++) {
            int bx = (int) (baseBottom[i][0] * sx);
            int by = (int) (baseBottom[i][1] * sy);
            String col = getPatchDominantColor(bitmap, bx, by, halfW, halfH);
            if (col != null) {
                result.bottomBoxes.add(new BottomBox(i + 1, col, bx, by));
                allBottomColors.add(col);
                if (i < 3) {
                    row1Colors.add(col);
                }
            }
        }

        // Target warna: prioritaskan wadah baris 1 (posisi 1-3)
        Set<String> targetColors = !row1Colors.isEmpty() ? row1Colors : allBottomColors;

        // 3. Deteksi warna kartu paling bawah pada 4 slot/tumpukan atas
        int[] baseSlotX = {188, 303, 418, 535};
        int[] scanOffsetsY = {764, 720, 680, 640, 600, 560, 520, 480, 440, 400};
        int slotHalfW = (int) (36 * sx);
        int slotHalfH = (int) (22 * sy);
        for (int i = 0; i < baseSlotX.length; i++) {
            int cx = (int) (baseSlotX[i] * sx);
            String foundCol = null;
            int foundY = (int) (764 * sy);
            for (int scanY : scanOffsetsY) {
                int cy = (int) (scanY * sy);
                String col = getPatchDominantColor(bitmap, cx, cy, slotHalfW, slotHalfH);
                if (col != null) {
                    foundCol = col;
                    foundY = cy;
                    break;
                }
            }
            if (foundCol != null) {
                SlotCard card = new SlotCard(i + 1, foundCol, cx, foundY);
                result.topSlots.add(card);
                if (colorsMatch(foundCol, targetColors)) {
                    result.matchingCardsToTap.add(card);
                }
            }
        }

        result.boardVisible = !result.bottomBoxes.isEmpty() || !result.topSlots.isEmpty();
        result.adScreenLikely = !result.boardVisible && (looksLikeAdScreen(bitmap) || result.adCloseButtonVisible);

        return result;
    }

    public static boolean colorsMatch(String cardColor, Set<String> targetColors) {
        if (targetColors == null || cardColor == null) return false;
        if (targetColors.contains(cardColor)) return true;
        if ("Cyan".equals(cardColor) && (targetColors.contains("Blue") || targetColors.contains("Cyan"))) return true;
        if ("Blue".equals(cardColor) && (targetColors.contains("Cyan") || targetColors.contains("Blue"))) return true;
        return false;
    }

    public static String classifyHsv(float hDegrees, float s, float v) {
        float hCv = hDegrees / 2.0f;
        float sCv = s * 255.0f;
        float vCv = v * 255.0f;

        if (vCv < 60f || sCv < 35f) {
            return null;
        }
        if (hCv <= 8f || hCv >= 170f) {
            return "Red";
        }
        if (hCv >= 9f && hCv <= 19f) {
            return "Orange";
        }
        if (hCv >= 20f && hCv <= 38f) {
            return "Yellow";
        }
        if (hCv >= 39f && hCv <= 84f) {
            return "Green";
        }
        if (hCv >= 85f && hCv <= 104f) {
            return "Cyan";
        }
        if (hCv >= 105f && hCv <= 132f) {
            return "Blue";
        }
        if (hCv >= 133f && hCv <= 169f) {
            return "Pink";
        }
        return null;
    }

    public static String getPatchDominantColor(Bitmap bitmap, int cx, int cy, int halfW, int halfH) {
        int x1 = Math.max(0, cx - halfW);
        int x2 = Math.min(bitmap.getWidth() - 1, cx + halfW);
        int y1 = Math.max(0, cy - halfH);
        int y2 = Math.min(bitmap.getHeight() - 1, cy + halfH);

        int stepX = Math.max(1, (x2 - x1) / 12);
        int stepY = Math.max(1, (y2 - y1) / 10);

        Map<String, Integer> counts = new HashMap<>();
        float[] hsv = new float[3];
        int validCount = 0;

        for (int y = y1; y <= y2; y += stepY) {
            for (int x = x1; x <= x2; x += stepX) {
                int pixel = bitmap.getPixel(x, y);
                Color.colorToHSV(pixel, hsv);
                String c = classifyHsv(hsv[0], hsv[1], hsv[2]);
                if (c != null) {
                    counts.put(c, counts.getOrDefault(c, 0) + 1);
                    validCount++;
                }
            }
        }

        if (validCount < 5) return null;
        String bestColor = null;
        int maxVotes = 0;
        for (Map.Entry<String, Integer> e : counts.entrySet()) {
            if (e.getValue() > maxVotes) {
                maxVotes = e.getValue();
                bestColor = e.getKey();
            }
        }
        return (maxVotes >= validCount * 0.45f) ? bestColor : null;
    }

    private static float[] findAdCloseButton(Bitmap bitmap, float sx, float sy) {
        int w = bitmap.getWidth();
        int h = bitmap.getHeight();

        // Pojok kanan atas
        int rx1 = Math.max(0, w - (int) (120 * sx));
        int ry2 = Math.min(h, (int) (140 * sy));
        if (hasXCrossShape(bitmap, rx1, 0, w, ry2)) {
            return new float[]{(rx1 + w) / 2f, ry2 / 2f};
        }

        // Pojok kiri atas
        int lx2 = Math.min(w, (int) (120 * sx));
        if (hasXCrossShape(bitmap, 0, 0, lx2, ry2)) {
            return new float[]{lx2 / 2f, ry2 / 2f};
        }

        // Pojok kanan bawah (khusus landscape ad)
        if (w > h) {
            int brx1 = Math.max(0, w - (int) (140 * sx));
            int bry1 = Math.max(0, h - (int) (140 * sy));
            if (hasXCrossShape(bitmap, brx1, bry1, w, h)) {
                return new float[]{(brx1 + w) / 2f, (bry1 + h) / 2f};
            }
        }

        return null;
    }

    private static boolean hasXCrossShape(Bitmap bitmap, int x1, int y1, int x2, int y2) {
        int contrastCount = 0;
        int prevLum = -1;
        int step = Math.max(1, (x2 - x1) / 15);
        for (int y = y1 + 10; y < y2 - 10; y += step) {
            for (int x = x1 + 10; x < x2 - 10; x += step) {
                int p = bitmap.getPixel(x, y);
                int lum = (Color.red(p) + Color.green(p) + Color.blue(p)) / 3;
                if (prevLum >= 0 && Math.abs(lum - prevLum) > 130) {
                    contrastCount++;
                }
                prevLum = lum;
            }
        }
        return contrastCount >= 10;
    }

    private static boolean looksLikeAdScreen(Bitmap bitmap) {
        int w = bitmap.getWidth();
        int h = bitmap.getHeight();
        int darkPixels = 0;
        int total = 0;
        int step = Math.max(4, w / 40);

        for (int y = 0; y < h; y += step) {
            for (int x = 0; x < w; x += step) {
                int p = bitmap.getPixel(x, y);
                int r = Color.red(p), g = Color.green(p), b = Color.blue(p);
                if (r < 30 && g < 30 && b < 30) {
                    darkPixels++;
                }
                total++;
            }
        }
        return total > 0 && ((float) darkPixels / total) >= 0.45f;
    }
}
