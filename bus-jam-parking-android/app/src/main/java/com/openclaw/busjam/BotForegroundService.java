package com.openclaw.busjam;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.PixelFormat;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.PowerManager;
import android.view.WindowManager;

import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Random;

public class BotForegroundService extends Service {
    public static final String EXTRA_RESULT_CODE = "result_code";
    public static final String EXTRA_RESULT_DATA = "result_data";
    public static final String GAME_PACKAGE = "com.busjam.parking.master";
    public static final String ACTION_STOP = "com.openclaw.busjam.ACTION_STOP";
    private static final String CHANNEL_ID = "bus_jam_bot";
    private static final int NOTIFICATION_ID = 7042;
    private static final long BUS_MOVE_WAIT_MS = 1_800L;
    private static final long STUCK_TIMEOUT_MS = 60_000L;

    private MediaProjection projection;
    private VirtualDisplay virtualDisplay;
    private ImageReader imageReader;
    private HandlerThread captureThread;
    private Handler captureHandler;
    private Thread botThread;
    private volatile Bitmap latestBitmap;
    private final Object bitmapLock = new Object();
    private volatile boolean running;
    private PowerManager.WakeLock wakeLock;
    private long nextActionAt;
    private long closeAdAt;
    private long lastGameBringToFrontAt;
    private long fullscreenAdSeenAt;
    private long adClosingStartedAt;
    private long lastAdBackAt;
    private long lastAdCloseButtonTapAt;
    private long lastAdNavigationTapAt;
    private int lastLoggedAdSeconds = -1;
    private boolean countdownWasSeen;
    private AdTimerReader adTimerReader;
    private int lastTapX = -1;
    private int lastTapY = -1;
    private long lastTapAt;
    private long lastParkingAdTapAt;
    private long lastProgressAt;
    private String lastProgressMessage = "";
    private final List<BlockedBus> blockedBuses = new ArrayList<>();
    private final Random random = new Random();

    private static final class BlockedBus {
        final int x;
        final int y;
        final long retryAfter;

        BlockedBus(int x, int y, long retryAfter) {
            this.x = x;
            this.y = y;
            this.retryAfter = retryAfter;
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        startForeground(NOTIFICATION_ID, notification("Bot aktif - menunggu layar game"));
        adTimerReader = new AdTimerReader();
        log("Layanan bot aktif.");
        PowerManager power = (PowerManager) getSystemService(POWER_SERVICE);
        wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "BusJamBot:Running");
        wakeLock.acquire(8 * 60 * 60 * 1000L);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            BotAccessibilityService.removeBotLog();
            stopSelf();
            return START_NOT_STICKY;
        }
        if (running) {
            return START_STICKY;
        }
        if (intent == null || !intent.hasExtra(EXTRA_RESULT_DATA)) {
            BotAccessibilityService.removeBotLog();
            stopSelf();
            return START_NOT_STICKY;
        }
        int resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0);
        Intent resultData = intent.getParcelableExtra(EXTRA_RESULT_DATA);
        MediaProjectionManager manager =
                (MediaProjectionManager) getSystemService(MEDIA_PROJECTION_SERVICE);
        projection = manager.getMediaProjection(resultCode, resultData);
        if (projection == null) {
            BotAccessibilityService.removeBotLog();
            stopSelf();
            return START_NOT_STICKY;
        }
        setupCapture();
        running = true;
        botThread = new Thread(this::botLoop, "bus-jam-bot-loop");
        botThread.start();
        return START_STICKY;
    }

    private void setupCapture() {
        WindowManager windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        android.util.DisplayMetrics metrics = new android.util.DisplayMetrics();
        windowManager.getDefaultDisplay().getRealMetrics(metrics);
        int width = metrics.widthPixels;
        int height = metrics.heightPixels;
        int density = metrics.densityDpi;

        captureThread = new HandlerThread("bus-jam-capture");
        captureThread.start();
        captureHandler = new Handler(captureThread.getLooper());
        imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2);
        imageReader.setOnImageAvailableListener(reader -> {
            Image image = null;
            try {
                image = reader.acquireLatestImage();
                if (image == null) return;
                Image.Plane plane = image.getPlanes()[0];
                ByteBuffer buffer = plane.getBuffer();
                int pixelStride = plane.getPixelStride();
                int rowStride = plane.getRowStride();
                int rowPadding = rowStride - pixelStride * width;
                Bitmap padded = Bitmap.createBitmap(
                        width + rowPadding / pixelStride, height, Bitmap.Config.ARGB_8888);
                padded.copyPixelsFromBuffer(buffer);
                Bitmap cropped = Bitmap.createBitmap(padded, 0, 0, width, height);
                padded.recycle();
                synchronized (bitmapLock) {
                    Bitmap old = latestBitmap;
                    latestBitmap = cropped;
                    if (old != null && !old.isRecycled()) old.recycle();
                }
            } catch (Throwable ignored) {
            } finally {
                if (image != null) image.close();
            }
        }, captureHandler);

        virtualDisplay = projection.createVirtualDisplay(
                "BusJamBotCapture",
                width,
                height,
                density,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader.getSurface(),
                null,
                captureHandler
        );
    }

    private void botLoop() {
        sleep(1200);
        while (running) {
            Bitmap screenshot = null;
            synchronized (bitmapLock) {
                if (latestBitmap != null && !latestBitmap.isRecycled()) {
                    // Analisis memakai salinan supaya callback capture boleh mengganti bitmap
                    // tanpa me-recycle buffer yang sedang dibaca.
                    screenshot = latestBitmap.copy(Bitmap.Config.ARGB_8888, false);
                }
            }
            if (screenshot != null && !screenshot.isRecycled()) {
                try {
                    ScreenAnalyzer.Result result = ScreenAnalyzer.analyze(screenshot);
                    if (!isGameActivityActive()
                            && (result.adScreenLikely || isFullscreenAd())) {
                        adTimerReader.readIfDue(screenshot);
                    }
                    runOneStep(result);
                    checkStuckWatchdog();
                } catch (Throwable ignored) {
                } finally {
                    screenshot.recycle();
                }
            }
            updateNotification("Bot aktif" +
                    (latestBitmap == null ? " - menunggu capture" : " - game dipantau"));
            sleep(850);
        }
    }

    private void runOneStep(ScreenAnalyzer.Result result) {
        BotAccessibilityService accessibility = BotAccessibilityService.getInstance();
        if (accessibility == null) {
            return;
        }
        long now = System.currentTimeMillis();
        float sx = result.width / 720f;
        float sy = result.height / 1640f;

        // PRIORITAS UTAMA: Deteksi tombol 'Main lagi' saat level gagal (dialog Habis Ruang / Anda Gagal)
        // Dialog ini adalah milik game (BUKAN IKLAN). Reset status iklan dan langsung ketuk Main lagi!
        if (result.playAgainVisible) {
            fullscreenAdSeenAt = 0;
            adClosingStartedAt = 0;
            lastAdCloseButtonTapAt = 0;
            lastAdNavigationTapAt = 0;
            countdownWasSeen = false;
            adTimerReader.reset();
            if (now >= nextActionAt) {
                accessibility.tap(360f * sx, 1225f * sy);
                nextActionAt = now + 2_500;
                log("Tombol 'Main lagi' terdeteksi! Memulai ulang level di (" + (int)(360f * sx) + "," + (int)(1225f * sy) + ").");
            }
            return;
        }

        // Activity utama game adalah pembeda utama antara popup game yang gelap dan
        // layar iklan. Jangan pernah menganggap popup Main lagi sebagai iklan.
        boolean gameActivity = isGameActivityActive();
        boolean adDetected = !gameActivity && (result.adScreenLikely || isFullscreenAd());
        if (adDetected || adClosingStartedAt > 0) {
            // Sinkronkan deteksi tombol skip (>, >>, >|) dan close (X) dari OCR AdTimerReader dan visual ScreenAnalyzer
            boolean skipVisible = result.adSkipButtonVisible || adTimerReader.hasRecentSkipButton();
            float skipTapX = adTimerReader.hasRecentSkipButton() && adTimerReader.getSkipButtonX() > 0
                    ? adTimerReader.getSkipButtonX() : result.adSkipButtonX;
            float skipTapY = adTimerReader.hasRecentSkipButton() && adTimerReader.getSkipButtonY() > 0
                    ? adTimerReader.getSkipButtonY() : result.adSkipButtonY;

            boolean closeVisible = result.adCloseButtonVisible || adTimerReader.hasRecentCloseButton();
            float closeTapX = adTimerReader.hasRecentCloseButton() && adTimerReader.getCloseButtonX() > 0
                    ? adTimerReader.getCloseButtonX() : result.adCloseButtonX;
            float closeTapY = adTimerReader.hasRecentCloseButton() && adTimerReader.getCloseButtonY() > 0
                    ? adTimerReader.getCloseButtonY() : (float) result.adCloseButtonY;

            boolean hasActionBtn = (skipVisible && skipTapX > 0) || (closeVisible && closeTapX > 0) || result.adSeeNextVisible;

            if (adDetected) {
                if (fullscreenAdSeenAt == 0) {
                    fullscreenAdSeenAt = now;
                    countdownWasSeen = false;
                    lastLoggedAdSeconds = -1;
                    adTimerReader.reset();
                    log("Halaman iklan terdeteksi. Menunggu wajib 30 detik tanpa klik...");
                }
                long elapsed = now - fullscreenAdSeenAt;
                int remainingSeconds = adTimerReader.recentRemainingSeconds();
                if (remainingSeconds > 0) {
                    countdownWasSeen = true;
                }

                // ATURAN 1 (INSTRUKSI USER): Jika masih ada countdown (> 0) dan BELUM ada tombol X atau > / >> / >|:
                // JANGAN TERKLIK APAPUN SAMA SEKALI! Layar dibiarkan tenang tanpa tap apapun.
                if (remainingSeconds > 0 && !hasActionBtn) {
                    updateNotification("Iklan: countdown " + remainingSeconds + "s | berjalan " + (elapsed / 1000) + "s / 30s");
                    if (remainingSeconds != lastLoggedAdSeconds) {
                        lastLoggedAdSeconds = remainingSeconds;
                        BotAccessibilityService.showBotLog(
                                "Countdown iklan " + remainingSeconds + " detik. Menunggu tanpa klik.");
                    }
                    return; // Diam mutlak, tidak klik apapun
                }

                // ATURAN 2 (INSTRUKSI USER): Wajib tunggu minimal 30 detik saat menemukan iklan
                long requiredWaitMs = 30_000L;
                if (elapsed < requiredWaitMs) {
                    long sisaDetik = (requiredWaitMs - elapsed + 999) / 1000;
                    updateNotification("Iklan: wajib tunggu " + sisaDetik + "s lagi (total 30s)");
                    // Hanya izinkan menutup jika ada tombol skip/close yang jelas dan countdown sudah habis
                    if (hasActionBtn && (remainingSeconds == 0 || elapsed >= 15_000L)) {
                        // Tombol skip / close di pojok atas siap diklik
                    } else {
                        // Belum 30 detik: DIAM TOTAL, tidak klik apapun di layar
                        return;
                    }
                }

                // ATURAN 3: Jika sudah 30s tetapi countdown masih ada (> 0) dan belum ada tombol skip/close:
                if (remainingSeconds > 0 && !hasActionBtn) {
                    updateNotification("Iklan: menunggu countdown selesai (" + remainingSeconds + "s)");
                    return;
                }

                if (adClosingStartedAt == 0) {
                    adClosingStartedAt = now;
                    lastAdBackAt = 0;
                    log("Waktu tunggu iklan 30s & countdown selesai. Menutup iklan...");
                }
            }

            // Setelah iklan hilang dan kembali ke game
            if (!adDetected && isGameActivityActive()) {
                fullscreenAdSeenAt = 0;
                adClosingStartedAt = 0;
                lastAdCloseButtonTapAt = 0;
                lastAdNavigationTapAt = 0;
                countdownWasSeen = false;
                adTimerReader.reset();
                nextActionAt = now + 1_200;
                log("Iklan ditutup. Kembali ke halaman utama game.");
                return;
            }

            // Iklan telah hilang tetapi BACK membawa ke launcher atau aplikasi lain
            if (!adDetected && (mustReturnToGame() || isBotActivityActive())) {
                fullscreenAdSeenAt = 0;
                adClosingStartedAt = 0;
                lastAdCloseButtonTapAt = 0;
                lastAdNavigationTapAt = 0;
                countdownWasSeen = false;
                adTimerReader.reset();
                bringGameToForeground();
                lastGameBringToFrontAt = now;
                nextActionAt = now + 2_500;
                log("Iklan selesai. Membuka kembali Bus Jam Parking.");
                return;
            }

            // EKSEKUSI PENUTUPAN IKLAN:
            // 1. Prioritas 1: Tombol skip (>, >>, >|) di pojok kanan atas atau kiri atas
            if (adDetected && skipVisible && skipTapX > 0 && skipTapY > 0 && now - lastAdNavigationTapAt >= 2_000) {
                accessibility.tap(skipTapX, skipTapY);
                lastAdNavigationTapAt = now;
                String corner = skipTapX < (result.width / 2f) ? "kiri atas" : "kanan atas";
                log("Tombol skip (>, >>, >|) terdeteksi di " + corner + " (" + (int)skipTapX + "," + (int)skipTapY + "). Mengetuk tombol.");
                return;
            }

            // 2. Prioritas 2: Tombol X (close) di pojok kanan atas atau kiri atas
            if (adDetected && closeVisible && closeTapX > 0 && closeTapY > 0 && now - lastAdCloseButtonTapAt >= 2_000) {
                accessibility.tap(closeTapX, closeTapY);
                lastAdCloseButtonTapAt = now;
                String corner = closeTapX < (result.width / 2f) ? "kiri atas" : "kanan atas";
                log("Tombol X (close) terdeteksi di " + corner + " (" + (int)closeTapX + "," + (int)closeTapY + "). Mengetuk tombol.");
                return;
            }

            // 3. Prioritas 3: Tombol See Next di tengah bawah iklan
            if (adDetected && result.adSeeNextVisible && now - lastAdNavigationTapAt >= 2_000) {
                float seeNextY = result.adSeeNextY > 0 ? result.adSeeNextY : (1105f * sy);
                accessibility.tap(360f * sx, seeNextY);
                lastAdNavigationTapAt = now;
                restartAdWait(now);
                log("Tombol 'See Next' terdeteksi di (" + (int)(360f * sx) + "," + (int)seeNextY + "). Mengetuk tombol See Next.");
                return;
            }

            // 4. Fallback: Hanya jika tidak ada tombol > / >> / >| / X / See Next setelah waktu 30s + countdown selesai, gunakan BACK
            if (now - lastAdBackAt >= 1_200) {
                accessibility.pressBack();
                lastAdBackAt = now;
                log("Waktu tunggu 30s & countdown selesai. Menekan tombol BACK.");
            }
            return;
        }
        if (fullscreenAdSeenAt > 0) {
            fullscreenAdSeenAt = 0;
            adClosingStartedAt = 0;
            lastAdCloseButtonTapAt = 0;
            lastAdNavigationTapAt = 0;
            countdownWasSeen = false;
            adTimerReader.reset();
            log("Kembali ke halaman utama game.");
        }

        // (Pemeriksaan playAgainVisible telah dipindahkan ke awal runOneStep untuk prioritas tertinggi)

        /*
        if (isFullscreenAd()) {
            if (fullscreenAdSeenAt == 0) {
                fullscreenAdSeenAt = now;
                adTimerReader.reset();
                log("Iklan terdeteksi. Menunggu countdown.");
            }
            int remainingSeconds = adTimerReader.recentRemainingSeconds();
            if (remainingSeconds > 0) {
                updateNotification("Iklan: sisa " + remainingSeconds + " detik");
                return;
            }
            // Jika countdown tidak terbaca, jangan pernah mencoba menutup sebelum 10 detik.
            // Jika terbaca 0, penutupan dapat langsung dilakukan.
            boolean waitComplete = remainingSeconds == 0
                    || now - fullscreenAdSeenAt >= 10_000;
            if (waitComplete && now >= nextActionAt) {
                accessibility.pressBack();
                accessibility.tap(665f * sx, 105f * sy);
                nextActionAt = now + 3_000;
                closeAdAt = 0;
                log("Countdown selesai. Menutup iklan.");
            }
            return;
        }
        fullscreenAdSeenAt = 0;
        adTimerReader.reset();
        */

        if (mustReturnToGame()) {
            if (now - lastGameBringToFrontAt >= 4_000) {
                bringGameToForeground();
                lastGameBringToFrontAt = now;
                nextActionAt = now + 3_000;
                closeAdAt = 0;
                log("Aplikasi lain terdeteksi. Kembali ke Bus Jam Parking.");
            }
            return;
        }

        // Popup bonus "Koleksi": klaim dulu dan tahan gerakan lain saat iklan berlangsung.
        if (result.collectRewardVisible) {
            if (now >= nextActionAt) {
                accessibility.tap(360f * sx, 995f * sy);
                nextActionAt = now + 2200;
                // Jika iklan muncul, jalur deteksi iklan di atas yang akan menanganinya.
                // Jangan membuat timer penutupan buta karena popup bonus dapat tidak
                // memunculkan iklan.
                closeAdAt = 0;
                log("Bonus dikoleksi. Memeriksa halaman berikutnya.");
            }
            return;
        }

        if (now < nextActionAt) {
            return;
        }

        // Slot AD biru di parkiran menghasilkan bus/slot tambahan. Sentuh hanya satu
        // ikon, lalu tunggu layar iklan; jangan mengganggu klik bus yang sedang bergerak.
        if (lastTapAt == 0 && result.parkingAdX > 0
                && now - lastParkingAdTapAt >= 4_000) {
            accessibility.tap(result.parkingAdX, result.parkingAdY);
            lastParkingAdTapAt = now;
            nextActionAt = now + 2_500;
            log("Kotak iklan biru di parkiran terdeteksi. Membuka iklan.");
            return;
        }

        // Jika bus yang baru diketuk tetap berada di titik yang sama, bus tidak dapat
        // bergerak/menabrak. Simpan sementara sebagai terhalang lalu pilih bus lain.
        if (lastTapAt > 0 && now - lastTapAt >= BUS_MOVE_WAIT_MS) {
            if (isBusStillAtLastTap(result.buses, sx, sy)) {
                // Jangan ulangi bus yang sama. Bot mencari kandidat lain dengan warna
                // yang sama sebelum mempertimbangkan warna bebas.
                markBusBlocked(lastTapX, lastTapY, now);
                log("Bus tidak bergerak. Mencoba bus warna sama lainnya.");
            }
            lastTapAt = 0;
        }

        removeExpiredBlockedBuses(now);
        ScreenAnalyzer.Bus chosen = result.buses.isEmpty()
                ? null : chooseBus(result.buses, result.frontColor, sx, sy);
        if (chosen == null) {
            if (!result.buses.isEmpty()) {
                // Hanya jika seluruh bus prioritas terhalang, pilih bus bebas yang
                // memang terdeteksi di papan. Jangan ketuk koordinat layar acak.
                chosen = result.buses.get(random.nextInt(result.buses.size()));
            }
            if (chosen == null) {
                nextActionAt = now + 1_200;
                log("Belum ada bus yang terbaca. Menunggu papan stabil.");
                return;
            }
            log("Semua bus prioritas terhalang. Mencoba bus bebas "
                    + chosen.color + ".");
        }
        accessibility.tap(chosen.x, chosen.y);
        lastTapX = chosen.x;
        lastTapY = chosen.y;
        lastTapAt = now;
        // Satu bus harus diberi waktu bergerak dahulu sebelum klik bus berikutnya.
        nextActionAt = now + BUS_MOVE_WAIT_MS;
        log("Klik bus " + chosen.color + ".");
    }

    private ScreenAnalyzer.Bus chooseBus(
            List<ScreenAnalyzer.Bus> buses, String targetColor, float sx, float sy) {
        List<ScreenAnalyzer.Bus> preferred = new ArrayList<>();
        List<ScreenAnalyzer.Bus> fallback = new ArrayList<>();
        for (ScreenAnalyzer.Bus bus : buses) {
            if (isTemporarilyBlocked(bus, sx, sy)) continue;
            if (targetColor != null && targetColor.equals(bus.color)) {
                preferred.add(bus);
            } else {
                fallback.add(bus);
            }
        }

        ScreenAnalyzer.Bus chosen = firstLikelyOpen(preferred, buses, sx);
        if (chosen != null) return chosen;
        chosen = firstLikelyOpen(fallback, buses, sx);
        if (chosen != null) return chosen;
        if (!preferred.isEmpty()) return preferred.get(0);
        return fallback.isEmpty() ? null : fallback.get(0);
    }

    private ScreenAnalyzer.Bus firstLikelyOpen(
            List<ScreenAnalyzer.Bus> candidates, List<ScreenAnalyzer.Bus> all, float sx) {
        Collections.sort(candidates, Comparator.comparingInt(bus -> bus.y));
        int laneTolerance = Math.max(38, (int) (42 * sx));
        for (ScreenAnalyzer.Bus candidate : candidates) {
            boolean blockedAbove = false;
            for (ScreenAnalyzer.Bus other : all) {
                if (other == candidate) continue;
                if (Math.abs(other.x - candidate.x) <= laneTolerance && other.y < candidate.y - 45) {
                    blockedAbove = true;
                    break;
                }
            }
            if (!blockedAbove) return candidate;
        }
        return null;
    }

    private boolean isBusStillAtLastTap(List<ScreenAnalyzer.Bus> buses, float sx, float sy) {
        // Bus pada level ini bisa berdekatan. Toleransi besar membuat bus tetangga
        // dianggap sebagai bus yang tadi dipilih, sehingga kandidat lain ikut diblokir.
        int tolerance = Math.max(32, (int) (38 * Math.min(sx, sy)));
        for (ScreenAnalyzer.Bus bus : buses) {
            if (Math.abs(bus.x - lastTapX) <= tolerance && Math.abs(bus.y - lastTapY) <= tolerance) {
                return true;
            }
        }
        return false;
    }

    private boolean isTemporarilyBlocked(ScreenAnalyzer.Bus bus, float sx, float sy) {
        int tolerance = Math.max(32, (int) (38 * Math.min(sx, sy)));
        long now = System.currentTimeMillis();
        for (BlockedBus blocked : blockedBuses) {
            if (blocked.retryAfter > now
                    && Math.abs(blocked.x - bus.x) <= tolerance
                    && Math.abs(blocked.y - bus.y) <= tolerance) {
                return true;
            }
        }
        return false;
    }

    private void markBusBlocked(int x, int y, long now) {
        int tolerance = 38;
        for (int index = blockedBuses.size() - 1; index >= 0; index--) {
            BlockedBus blocked = blockedBuses.get(index);
            if (Math.abs(blocked.x - x) <= tolerance && Math.abs(blocked.y - y) <= tolerance) {
                blockedBuses.remove(index);
            }
        }
        blockedBuses.add(new BlockedBus(x, y, now + 20_000));
    }

    private void removeExpiredBlockedBuses(long now) {
        for (int index = blockedBuses.size() - 1; index >= 0; index--) {
            if (blockedBuses.get(index).retryAfter <= now) {
                blockedBuses.remove(index);
            }
        }
    }

    private boolean mustReturnToGame() {
        String foreground = BotAccessibilityService.getForegroundPackage();
        // Setelah bot aktif, layar yang valid hanya game atau activity iklan game.
        // Jadi redirect ke Chrome, Play Store, browser lain, maupun aplikasi lain
        // langsung dipulihkan ke Bus Jam Parking.
        return foreground != null
                && !foreground.isEmpty()
                && !GAME_PACKAGE.equals(foreground)
                && !"com.openclaw.busjam".equals(foreground)
                && !"com.android.systemui".equals(foreground);
    }

    private boolean isFullscreenAd() {
        String activity = BotAccessibilityService.getForegroundClass().toLowerCase();
        // Unity/MBridge dapat meninggalkan event activity iklan lama. Activity utama
        // Bus Jam selalu HmeActivity dan tidak boleh dianggap iklan tanpa bukti visual.
        if (activity.contains("hmeactivity") || activity.contains("launcheraty")) {
            return false;
        }
        // Selama activity SDK iklan masih aktif, jangan pernah menjalankan pemindai bus.
        // HmeActivity di atas menjadi pemutus yang jelas ketika permainan sudah kembali.
        return activity.contains("applovin")
                || activity.contains("rewardvideo")
                || activity.contains("adactivity")
                || activity.contains("mbridge")
                || activity.contains("mintegral")
                || activity.contains("unityads")
                || activity.contains("bytedance")
                || activity.contains("ttreward")
                || activity.contains("pangle");
    }

    private boolean isGameActivityActive() {
        String foreground = BotAccessibilityService.getForegroundPackage();
        String activity = BotAccessibilityService.getForegroundClass();
        if (GAME_PACKAGE.equals(foreground)) {
            if (activity == null || activity.isEmpty()) return true;
            String actLower = activity.toLowerCase();
            if (actLower.contains("hmeactivity") || actLower.contains("launcheraty")) {
                return true;
            }
            return !isFullscreenAd();
        }
        return false;
    }

    private boolean isBotActivityActive() {
        return "com.openclaw.busjam".equals(BotAccessibilityService.getForegroundPackage());
    }

    private void restartAdWait(long now) {
        fullscreenAdSeenAt = now;
        adClosingStartedAt = 0;
        lastAdBackAt = 0;
        lastAdNavigationTapAt = now;
        countdownWasSeen = false;
        adTimerReader.reset();
    }

    private void bringGameToForeground() {
        Intent gameIntent = getPackageManager().getLaunchIntentForPackage(GAME_PACKAGE);
        if (gameIntent == null) {
            return;
        }
        gameIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        try {
            startActivity(gameIntent);
            BotAccessibilityService.markGameForeground();
        } catch (Throwable ignored) {
        }
    }

    /**
     * Bila pesan status tidak berubah selama satu menit saat halaman game aktif, game
     * dianggap macet (misalnya bonus/Koleksi menutup papan). Kembali ke Home lalu buka
     * task Bus Jam baru agar layar game dimuat ulang.
     */
    private void checkStuckWatchdog() {
        long now = System.currentTimeMillis();
        if (!isGameActivityActive() || lastProgressAt == 0
                || now - lastProgressAt < STUCK_TIMEOUT_MS) {
            return;
        }
        BotAccessibilityService accessibility = BotAccessibilityService.getInstance();
        if (accessibility != null) {
            accessibility.pressHome();
        }
        sleep(700);
        Intent gameIntent = getPackageManager().getLaunchIntentForPackage(GAME_PACKAGE);
        if (gameIntent != null) {
            gameIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                    | Intent.FLAG_ACTIVITY_CLEAR_TASK
                    | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            try {
                startActivity(gameIntent);
                BotAccessibilityService.markGameForeground();
            } catch (Throwable ignored) {
            }
        }
        nextActionAt = now + 3_000;
        lastProgressAt = now;
        lastProgressMessage = "watchdog";
        log("Game macet 60 detik. Menutup dan membuka ulang Bus Jam.");
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "Bus Jam Bot", NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("Status bot Bus Jam Parking");
            getSystemService(NotificationManager.class).createNotificationChannel(channel);
        }
    }

    private Notification notification(String text) {
        Intent stopIntent = new Intent(this, BotForegroundService.class);
        stopIntent.setAction(ACTION_STOP);
        PendingIntent stopPendingIntent = PendingIntent.getService(
                this, 1, stopIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Intent mainIntent = new Intent(this, MainActivity.class);
        PendingIntent mainPendingIntent = PendingIntent.getActivity(
                this, 0, mainIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Notification.Builder builder = new Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("Bus Jam Bot")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_media_play)
                .setContentIntent(mainPendingIntent)
                .setOngoing(true);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT_WATCH) {
            Notification.Action stopAction = new Notification.Action.Builder(
                    android.R.drawable.ic_menu_close_clear_cancel, "Hentikan Bot", stopPendingIntent
            ).build();
            builder.addAction(stopAction);
        }
        return builder.build();
    }

    private void updateNotification(String text) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getSystemService(NotificationManager.class).notify(NOTIFICATION_ID, notification(text));
        }
    }

    private void log(String text) {
        updateNotification(text);
        BotAccessibilityService.showBotLog(text);
        if (!text.equals(lastProgressMessage)) {
            lastProgressMessage = text;
            lastProgressAt = System.currentTimeMillis();
        }
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException ignored) {
            Thread.currentThread().interrupt();
        }
    }

    @Override
    public void onDestroy() {
        running = false;
        BotAccessibilityService.removeBotLog();
        if (botThread != null) botThread.interrupt();
        if (virtualDisplay != null) virtualDisplay.release();
        if (imageReader != null) imageReader.close();
        if (projection != null) projection.stop();
        if (adTimerReader != null) adTimerReader.close();
        if (captureThread != null) captureThread.quitSafely();
        synchronized (bitmapLock) {
            Bitmap old = latestBitmap;
            latestBitmap = null;
            if (old != null && !old.isRecycled()) old.recycle();
        }
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
