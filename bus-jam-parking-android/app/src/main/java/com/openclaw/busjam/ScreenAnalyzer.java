package com.openclaw.busjam;

import android.graphics.Bitmap;
import android.graphics.Color;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Deteksi ringan tanpa OpenCV/komputer. Koordinat game dikalibrasi untuk layar 720x1640
 * dan diskalakan ke ukuran layar aktual.
 */
public final class ScreenAnalyzer {
    private ScreenAnalyzer() {
    }

    public static final String[] COLORS = {
            "Red", "Orange", "Yellow", "Green", "Cyan", "Blue", "Pink"
    };

    public static final class Bus {
        public final String color;
        public final int x;
        public final int y;
        public final int width;
        public final int height;
        public final int area;

        Bus(String color, int x, int y, int width, int height, int area) {
            this.color = color;
            this.x = x;
            this.y = y;
            this.width = width;
            this.height = height;
            this.area = area;
        }
    }

    public static final class Result {
        public String frontColor;
        public final List<Bus> buses = new ArrayList<>();
        public int width;
        public int height;
        public boolean collectRewardVisible;
        public boolean playAgainVisible;
        public boolean adScreenLikely;
        public boolean adCloseButtonVisible;
        public int adCloseButtonY = -1;
        public boolean adSkipButtonVisible;
        public boolean adSeeNextVisible;
        public int parkingAdX = -1;
        public int parkingAdY = -1;
    }

    public static Result analyze(Bitmap bitmap) {
        Result result = new Result();
        result.width = bitmap.getWidth();
        result.height = bitmap.getHeight();
        float sx = result.width / 720f;
        float sy = result.height / 1640f;

        // Kontrol iklan hanya akan dipakai oleh BotForegroundService saat activity/screen
        // iklan terkonfirmasi. Menghitungnya di awal membuat varian iklan yang tidak
        // punya letterbox hitam tetap dapat ditutup.
        result.adCloseButtonY = findAdCloseButtonY(bitmap, sx, sy);
        result.adCloseButtonVisible = result.adCloseButtonY > 0;
        result.adSkipButtonVisible = hasAdSkipButton(bitmap, sx, sy);
        result.adSeeNextVisible = hasAdSeeNextButton(bitmap, sx, sy);
        result.adScreenLikely = looksLikeAdScreen(bitmap);
        // Popup game dapat sangat gelap sehingga mirip iklan secara visual. Status ini
        // dipakai BotForegroundService bersama activity yang sedang aktif.
        result.playAgainVisible = hasPlayAgainButton(bitmap, sx, sy);
        // Saat layar iklan visual terdeteksi, berhenti total di sini. Jangan sampai
        // warna tombol/ilustrasi iklan dianggap sebagai bus, Koleksi, atau Main lagi.
        if (result.adScreenLikely || result.playAgainVisible) return result;

        // Deteksi popup game hanya dilakukan setelah layar dipastikan bukan iklan.
        result.collectRewardVisible = hasCollectRewardButton(bitmap, sx, sy);
        if (result.collectRewardVisible) {
            return result;
        }
        int[] parkingAd = findParkingAdButton(bitmap, sx, sy);
        result.parkingAdX = parkingAd[0];
        result.parkingAdY = parkingAd[1];
        result.frontColor = detectFrontColor(bitmap, sx, sy);
        // Bus pada deretan parkir atas sudah keluar dari papan dan tidak boleh diklik
        // lagi. Hanya kendaraan pada papan permainan bawah yang masuk daftar aksi.
        result.buses.addAll(detectBuses(bitmap, sx, sy));
        return result;
    }

    /**
     * Slot parkir iklan memiliki ikon kecil biru dengan label AD/play, di sisi kanan
     * deretan slot atas. Mengembalikan satu slot pertama agar bot tidak menekan beberapa
     * iklan sekaligus.
     */
    private static int[] findParkingAdButton(Bitmap bitmap, float sx, float sy) {
        int[] slotCenters = {450, 545, 640};
        float[] hsv = new float[3];
        for (int baseX : slotCenters) {
            int centerX = clamp((int) (baseX * sx), 0, bitmap.getWidth() - 1);
            int centerY = clamp((int) (520 * sy), 0, bitmap.getHeight() - 1);
            int blue = 0;
            int total = 0;
            int left = clamp(centerX - (int) (35 * sx), 0, bitmap.getWidth());
            int right = clamp(centerX + (int) (35 * sx), 0, bitmap.getWidth());
            int top = clamp(centerY - (int) (28 * sy), 0, bitmap.getHeight());
            int bottom = clamp(centerY + (int) (28 * sy), 0, bitmap.getHeight());
            for (int y = top; y < bottom; y += 2) {
                for (int x = left; x < right; x += 2) {
                    Color.colorToHSV(bitmap.getPixel(x, y), hsv);
                    total++;
                    if (hsv[0] >= 188f && hsv[0] <= 258f
                            && hsv[1] >= 0.42f && hsv[2] >= 0.30f) {
                        blue++;
                    }
                }
            }
            if (total > 0 && blue * 100 >= total * 12) {
                return new int[]{centerX, centerY};
            }
        }
        return new int[]{-1, -1};
    }

    private static boolean looksLikeAdScreen(Bitmap bitmap) {
        int width = bitmap.getWidth();
        int height = bitmap.getHeight();
        int top = Math.min(height, 200);
        int samples = 0;
        int dark = 0;
        int whiteText = 0;
        for (int y = 0; y < top; y += 4) {
            for (int x = 0; x < width; x += 4) {
                int pixel = bitmap.getPixel(x, y);
                int red = android.graphics.Color.red(pixel);
                int green = android.graphics.Color.green(pixel);
                int blue = android.graphics.Color.blue(pixel);
                samples++;
                if (red < 48 && green < 48 && blue < 48) dark++;
                if (red > 185 && green > 185 && blue > 185) whiteText++;
            }
        }
        // Iklan video dengan timer "Ns left to be rewarded".
        boolean videoAd = samples > 0
                && dark * 100 >= samples * 52
                && whiteText * 1000 >= samples * 2;

        // Sebagian iklan MBridge tidak menampilkan timer pada frame awal. Pada perangkat
        // ini iklan tersebut memiliki letterbox hitam di atas, strip legal/usia gelap di
        // bawah, dan tombol CTA putih/terang pada bagian paling bawah. Area permainan Bus
        // Jam tidak memiliki gabungan tiga ciri tersebut.
        boolean blackTop = darkRatio(bitmap, 0, 0, width, Math.max(64, height * 5 / 100)) >= 92;
        boolean darkLegalStrip = darkRatio(
                bitmap, 0, height * 76 / 100, width, height * 86 / 100) >= 28;
        boolean brightCta = brightRatio(
                bitmap, 0, height * 84 / 100, width, height) >= 18;
        return videoAd || (blackTop && (darkLegalStrip || brightCta));
    }

    private static int darkRatio(Bitmap bitmap, int left, int top, int right, int bottom) {
        int samples = 0;
        int dark = 0;
        for (int y = Math.max(0, top); y < Math.min(bitmap.getHeight(), bottom); y += 4) {
            for (int x = Math.max(0, left); x < Math.min(bitmap.getWidth(), right); x += 4) {
                int pixel = bitmap.getPixel(x, y);
                samples++;
                if (Color.red(pixel) < 48 && Color.green(pixel) < 48 && Color.blue(pixel) < 48) {
                    dark++;
                }
            }
        }
        return samples == 0 ? 0 : dark * 100 / samples;
    }

    private static int brightRatio(Bitmap bitmap, int left, int top, int right, int bottom) {
        int samples = 0;
        int bright = 0;
        for (int y = Math.max(0, top); y < Math.min(bitmap.getHeight(), bottom); y += 4) {
            for (int x = Math.max(0, left); x < Math.min(bitmap.getWidth(), right); x += 4) {
                int pixel = bitmap.getPixel(x, y);
                samples++;
                if (Color.red(pixel) > 185 && Color.green(pixel) > 185 && Color.blue(pixel) > 185) {
                    bright++;
                }
            }
        }
        return samples == 0 ? 0 : bright * 100 / samples;
    }

    /**
     * Tombol "Koleksi" bonus berada konsisten di tengah-bawah (sekitar 360, 995)
     * dan memiliki bidang hijau terang besar. Dengan ini bot tidak mencoba klik bus
     * ketika popup bonus sedang menutupi permainan.
     */
    private static boolean hasCollectRewardButton(Bitmap bitmap, float sx, float sy) {
        int left = clamp((int) (200 * sx), 0, bitmap.getWidth());
        int right = clamp((int) (520 * sx), 0, bitmap.getWidth());
        int top = clamp((int) (940 * sy), 0, bitmap.getHeight());
        int bottom = clamp((int) (1060 * sy), 0, bitmap.getHeight());
        int total = 0;
        int brightGreen = 0;
        float[] hsv = new float[3];

        for (int y = top; y < bottom; y += 4) {
            for (int x = left; x < right; x += 4) {
                Color.colorToHSV(bitmap.getPixel(x, y), hsv);
                total++;
                if (hsv[0] >= 72f && hsv[0] <= 155f &&
                        hsv[1] >= 0.58f && hsv[2] >= 0.45f) {
                    brightGreen++;
                }
            }
        }
        // Bus hijau yang tersebar di papan tidak boleh dianggap tombol. Popup asli
        // mengisi sebagian besar bidang tengah dengan hijau terang.
        return total > 0 && brightGreen * 100 >= total * 30;
    }

    /**
     * Tombol "Main lagi" pada dialog gagal berada lebih rendah daripada tombol Koleksi,
     * sekitar (360, 1210). Hanya bidang hijau lebar di area ini yang diterima agar bus
     * hijau di papan tidak memicu restart level.
     */
    private static boolean hasPlayAgainButton(Bitmap bitmap, float sx, float sy) {
        int left = clamp((int) (160 * sx), 0, bitmap.getWidth());
        int right = clamp((int) (560 * sx), 0, bitmap.getWidth());
        int top = clamp((int) (1100 * sy), 0, bitmap.getHeight());
        int bottom = clamp((int) (1320 * sy), 0, bitmap.getHeight());
        int total = 0;
        int brightGreen = 0;
        float[] hsv = new float[3];

        for (int y = top; y < bottom; y += 4) {
            for (int x = left; x < right; x += 4) {
                Color.colorToHSV(bitmap.getPixel(x, y), hsv);
                total++;
                if (hsv[0] >= 72f && hsv[0] <= 155f
                        && hsv[1] >= 0.58f && hsv[2] >= 0.45f) {
                    brightGreen++;
                }
            }
        }
        return total > 0 && brightGreen * 100 >= total * 25;
    }

    /**
     * Tombol X AppLovin yang aktif berada di kanan-atas, sekitar (650, 200).
     * Deteksi hanya dipakai setelah countdown selesai dan BACK sudah dicoba.
     */
    private static int findAdCloseButtonY(Bitmap bitmap, float sx, float sy) {
        int left = clamp((int) (620 * sx), 0, bitmap.getWidth());
        int right = clamp((int) (680 * sx), 0, bitmap.getWidth());
        int top = clamp((int) (125 * sy), 0, bitmap.getHeight());
        int bottom = clamp((int) (230 * sy), 0, bitmap.getHeight());
        int total = 0;
        int white = 0;
        int upperWhite = 0;
        int lowerWhite = 0;
        int middleY = (top + bottom) / 2;
        for (int y = top; y < bottom; y += 2) {
            for (int x = left; x < right; x += 2) {
                int pixel = bitmap.getPixel(x, y);
                total++;
                if (Color.red(pixel) > 190 && Color.green(pixel) > 190 && Color.blue(pixel) > 190) {
                    white++;
                    if (y < middleY) upperWhite++;
                    else lowerWhite++;
                }
            }
        }
        // X kecil pada iklan ByteDance hanya mengisi sekitar 1.5% area pemindai,
        // sedangkan X AppLovin lebih rendah. Keduanya dipilih berdasarkan kelompok
        // piksel putih terbesar, lalu klik tepat di pusat tombolnya.
        if (total == 0 || white * 100 < total) return -1;
        return upperWhite >= lowerWhite ? (int) (165 * sy) : (int) (200 * sy);
    }

    /** Tombol lewati/lanjut berbentuk ">>" pada iklan ByteDance di kanan-atas. */
    private static boolean hasAdSkipButton(Bitmap bitmap, float sx, float sy) {
        int left = clamp((int) (630 * sx), 0, bitmap.getWidth());
        int right = clamp((int) (690 * sx), 0, bitmap.getWidth());
        int top = clamp((int) (130 * sy), 0, bitmap.getHeight());
        int bottom = clamp((int) (185 * sy), 0, bitmap.getHeight());
        return brightRatio(bitmap, left, top, right, bottom) >= 4;
    }

    /** Tombol "See Next" adalah tombol abu-abu lebar di tengah-bawah iklan. */
    private static boolean hasAdSeeNextButton(Bitmap bitmap, float sx, float sy) {
        int left = clamp((int) (48 * sx), 0, bitmap.getWidth());
        int right = clamp((int) (672 * sx), 0, bitmap.getWidth());
        int top = clamp((int) (1065 * sy), 0, bitmap.getHeight());
        int bottom = clamp((int) (1145 * sy), 0, bitmap.getHeight());
        int total = 0;
        int neutralGray = 0;
        for (int y = top; y < bottom; y += 2) {
            for (int x = left; x < right; x += 2) {
                int pixel = bitmap.getPixel(x, y);
                int red = Color.red(pixel);
                int green = Color.green(pixel);
                int blue = Color.blue(pixel);
                total++;
                if (Math.abs(red - green) <= 10 && Math.abs(green - blue) <= 10
                        && red >= 115 && red <= 210) {
                    neutralGray++;
                }
            }
        }
        return total > 0 && neutralGray * 100 >= total * 55;
    }

    private static String detectFrontColor(Bitmap bitmap, float sx, float sy) {
        int left = clamp((int) (260 * sx), 0, bitmap.getWidth());
        int right = clamp((int) (345 * sx), 0, bitmap.getWidth());
        int top = clamp((int) (365 * sy), 0, bitmap.getHeight());
        int bottom = clamp((int) (420 * sy), 0, bitmap.getHeight());
        Map<String, Integer> counts = new HashMap<>();

        for (int y = top; y < bottom; y += 2) {
            for (int x = left; x < right; x += 2) {
                String color = classify(bitmap.getPixel(x, y));
                if (color != null) {
                    counts.put(color, counts.containsKey(color) ? counts.get(color) + 1 : 1);
                }
            }
        }
        String best = null;
        int bestCount = 0;
        for (Map.Entry<String, Integer> item : counts.entrySet()) {
            if (item.getValue() > bestCount) {
                best = item.getKey();
                bestCount = item.getValue();
            }
        }
        return bestCount >= 20 ? best : null;
    }

    private static List<Bus> detectBuses(Bitmap bitmap, float sx, float sy) {
        int left = 0;
        int right = bitmap.getWidth();
        int top = clamp((int) (700 * sy), 0, bitmap.getHeight());
        int bottom = clamp((int) (1300 * sy), 0, bitmap.getHeight());
        int step = Math.max(2, Math.round(Math.min(sx, sy) * 4));
        int cols = Math.max(1, (right - left + step - 1) / step);
        int rows = Math.max(1, (bottom - top + step - 1) / step);
        String[][] colors = new String[rows][cols];
        boolean[][] visited = new boolean[rows][cols];

        for (int gy = 0; gy < rows; gy++) {
            int y = Math.min(bottom - 1, top + gy * step);
            for (int gx = 0; gx < cols; gx++) {
                int x = Math.min(right - 1, left + gx * step);
                colors[gy][gx] = classify(bitmap.getPixel(x, y));
            }
        }

        List<Bus> buses = new ArrayList<>();
        int[] dx = {-1, 0, 1, -1, 1, -1, 0, 1};
        int[] dy = {-1, -1, -1, 0, 0, 1, 1, 1};
        for (int gy = 0; gy < rows; gy++) {
            for (int gx = 0; gx < cols; gx++) {
                if (visited[gy][gx] || colors[gy][gx] == null) {
                    continue;
                }
                String wanted = colors[gy][gx];
                ArrayDeque<int[]> queue = new ArrayDeque<>();
                queue.add(new int[]{gx, gy});
                visited[gy][gx] = true;
                int count = 0;
                int minX = gx, maxX = gx, minY = gy, maxY = gy;
                long sumX = 0, sumY = 0;

                while (!queue.isEmpty()) {
                    int[] cell = queue.removeFirst();
                    int x = cell[0], y = cell[1];
                    count++;
                    sumX += x;
                    sumY += y;
                    minX = Math.min(minX, x);
                    maxX = Math.max(maxX, x);
                    minY = Math.min(minY, y);
                    maxY = Math.max(maxY, y);

                    for (int i = 0; i < dx.length; i++) {
                        int nx = x + dx[i], ny = y + dy[i];
                        if (nx < 0 || ny < 0 || nx >= cols || ny >= rows ||
                                visited[ny][nx] || !wanted.equals(colors[ny][nx])) {
                            continue;
                        }
                        visited[ny][nx] = true;
                        queue.addLast(new int[]{nx, ny});
                    }
                }

                int pixelArea = count * step * step;
                int width = (maxX - minX + 1) * step;
                int height = (maxY - minY + 1) * step;
                int centerX = left + (int) ((sumX / (float) count) * step);
                int centerY = top + (int) ((sumY / (float) count) * step);
                boolean looksLikeBus = count >= 25 && pixelArea >= 400 &&
                        width >= 25 && height >= 25 && width <= 240 && height <= 240;
                boolean isBoosterArea = centerX >= 480 * sx && centerX <= 640 * sx &&
                        centerY >= 850 * sy && centerY <= 1050 * sy;
                if (looksLikeBus && !isBoosterArea) {
                    buses.add(new Bus(wanted, centerX, centerY, width, height, pixelArea));
                }
            }
        }
        Collections.sort(buses, Comparator.comparingInt(bus -> bus.y));
        return buses;
    }

    private static List<Bus> detectParkedBuses(Bitmap bitmap, float sx, float sy) {
        List<Bus> buses = new ArrayList<>();
        int[] slotCenters = {70, 165, 260, 355, 450, 545, 640};
        float[] hsv = new float[3];
        for (int baseX : slotCenters) {
            int centerX = clamp((int) (baseX * sx), 0, bitmap.getWidth() - 1);
            int top = clamp((int) (440 * sy), 0, bitmap.getHeight());
            int bottom = clamp((int) (595 * sy), 0, bitmap.getHeight());
            Map<String, Integer> counts = new HashMap<>();
            for (int y = top; y < bottom; y += 3) {
                for (int x = clamp(centerX - (int) (45 * sx), 0, bitmap.getWidth());
                     x < clamp(centerX + (int) (45 * sx), 0, bitmap.getWidth()); x += 3) {
                    Color.colorToHSV(bitmap.getPixel(x, y), hsv);
                    if (hsv[1] < 0.28f || hsv[2] < 0.22f) continue;
                    String color = classify(bitmap.getPixel(x, y));
                    if (color != null) {
                        counts.put(color, counts.containsKey(color) ? counts.get(color) + 1 : 1);
                    }
                }
            }
            String best = null;
            int bestCount = 0;
            for (Map.Entry<String, Integer> item : counts.entrySet()) {
                if (item.getValue() > bestCount) {
                    best = item.getKey();
                    bestCount = item.getValue();
                }
            }
            // Slot kosong/ad badge biasanya memiliki jauh lebih sedikit piksel warna.
            if (best != null && bestCount >= 120) {
                buses.add(new Bus(best, centerX, (int) (520 * sy), 80, 140, bestCount * 9));
            }
        }
        return buses;
    }

    public static String classify(int pixel) {
        float[] hsv = new float[3];
        Color.colorToHSV(pixel, hsv);
        if (hsv[1] < 0.18f || hsv[2] < 0.20f) {
            return null;
        }
        float h = hsv[0];
        if (h <= 10 || h >= 340) return "Red";
        if (h <= 32) return "Orange";
        if (h <= 68) return "Yellow";
        if (h <= 168) return "Green";
        if (h <= 208) return "Cyan";
        if (h <= 260) return "Blue";
        return "Pink";
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(value, max));
    }
}
