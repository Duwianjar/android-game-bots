package com.openclaw.colorpowerpop;

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
import android.os.SystemClock;
import android.util.DisplayMetrics;
import android.view.WindowManager;

import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;

public class BotForegroundService extends Service {
    public static final String EXTRA_RESULT_CODE = "result_code";
    public static final String EXTRA_RESULT_DATA = "result_data";
    public static final String GAME_PACKAGE = "com.giraffeeapp.power";
    public static final String ACTION_STOP = "com.openclaw.colorpowerpop.ACTION_STOP";
    private static final String CHANNEL_ID = "color_power_pop_bot";
    private static final int NOTIFICATION_ID = 8055;

    private MediaProjection projection;
    private VirtualDisplay virtualDisplay;
    private ImageReader imageReader;
    private HandlerThread captureThread;
    private Handler captureHandler;
    private Thread botThread;
    private volatile Bitmap latestBitmap;
    private final Object bitmapLock = new Object();
    private volatile boolean running;
    private static volatile boolean runningInstance = false;

    private PowerManager.WakeLock wakeLock;
    private AdTimerReader adTimerReader;
    private long adStartedAt = 0;
    private boolean adWaitDone = false;
    private boolean rewardClickedPendingAd = false;
    private long rewardClickedAt = 0;
    private int consecutiveBlankCount = 0;
    private long gameLaunchedAt = 0;
    private long lastScreenSignature = 0;
    private long lastScreenChangeAt = 0;
    private int noMatchCount = 0;

    private int captureWidth = 0;
    private int captureHeight = 0;
    private int captureDensity = 0;

    public static boolean isBotRunning() {
        return runningInstance;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        runningInstance = true;
        adTimerReader = new AdTimerReader();
        createNotificationChannel();
        PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
        if (pm != null) {
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ColorPowerPop:WakeLock");
            wakeLock.acquire(12 * 60 * 60 * 1000L);
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopSelf();
            return START_NOT_STICKY;
        }

        int resultCode = intent != null ? intent.getIntExtra(EXTRA_RESULT_CODE, 0) : 0;
        Intent data = intent != null ? intent.getParcelableExtra(EXTRA_RESULT_DATA) : null;
        if (resultCode == 0 || data == null) {
            stopSelf();
            return START_NOT_STICKY;
        }

        startForeground(NOTIFICATION_ID, buildNotification("Bot Color Power Pop aktif"));

        MediaProjectionManager manager =
                (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        projection = manager.getMediaProjection(resultCode, data);

        captureThread = new HandlerThread("cpp-capture");
        captureThread.start();
        captureHandler = new Handler(captureThread.getLooper());

        setupCapture();

        running = true;
        botThread = new Thread(this::botLoop, "color-power-pop-worker");
        botThread.start();

        return START_STICKY;
    }

    private void setupCapture() {
        WindowManager wm = (WindowManager) getSystemService(WINDOW_SERVICE);
        DisplayMetrics metrics = new DisplayMetrics();
        if (wm != null) {
            wm.getDefaultDisplay().getRealMetrics(metrics);
            updateCaptureDimensions(metrics.widthPixels, metrics.heightPixels, metrics.densityDpi);
        }
    }

    private synchronized void updateCaptureDimensions(int newWidth, int newHeight, int newDensity) {
        if (newWidth <= 0 || newHeight <= 0) return;
        if (newWidth == captureWidth && newHeight == captureHeight && imageReader != null) return;

        captureWidth = newWidth;
        captureHeight = newHeight;
        captureDensity = newDensity > 0 ? newDensity : 320;

        if (imageReader != null) {
            try {
                imageReader.close();
            } catch (Throwable ignored) {
            }
        }

        imageReader = ImageReader.newInstance(captureWidth, captureHeight, PixelFormat.RGBA_8888, 2);
        imageReader.setOnImageAvailableListener(reader -> {
            Image image = null;
            try {
                image = reader.acquireLatestImage();
                if (image == null) return;
                Image.Plane plane = image.getPlanes()[0];
                ByteBuffer buffer = plane.getBuffer();
                int pixelStride = plane.getPixelStride();
                int rowStride = plane.getRowStride();
                int rowPadding = rowStride - pixelStride * captureWidth;
                Bitmap padded = Bitmap.createBitmap(
                        captureWidth + rowPadding / pixelStride, captureHeight, Bitmap.Config.ARGB_8888);
                padded.copyPixelsFromBuffer(buffer);
                Bitmap cropped = Bitmap.createBitmap(padded, 0, 0, captureWidth, captureHeight);
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

        if (virtualDisplay == null) {
            virtualDisplay = projection.createVirtualDisplay(
                    "ColorPowerPopCapture",
                    captureWidth,
                    captureHeight,
                    captureDensity,
                    DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                    imageReader.getSurface(),
                    null,
                    captureHandler
            );
        } else {
            virtualDisplay.resize(captureWidth, captureHeight, captureDensity);
            virtualDisplay.setSurface(imageReader.getSurface());
        }
    }

    private void botLoop() {
        sleep(1000);
        while (running) {
            // Periksa apakah orientasi layar berubah (misal iklan landscape)
            WindowManager wm = (WindowManager) getSystemService(WINDOW_SERVICE);
            if (wm != null) {
                DisplayMetrics metrics = new DisplayMetrics();
                wm.getDefaultDisplay().getRealMetrics(metrics);
                if (metrics.widthPixels != captureWidth || metrics.heightPixels != captureHeight) {
                    updateCaptureDimensions(metrics.widthPixels, metrics.heightPixels, metrics.densityDpi);
                    sleep(200);
                    continue;
                }
            }

            Bitmap screenshot = null;
            synchronized (bitmapLock) {
                if (latestBitmap != null && !latestBitmap.isRecycled()) {
                    screenshot = latestBitmap.copy(Bitmap.Config.ARGB_8888, false);
                }
            }

            if (screenshot != null && !screenshot.isRecycled()) {
                try {
                    // Jalankan pembaca OCR untuk mendeteksi countdown iklan, tombol skip/close, report ads, dan popup reward
                    adTimerReader.readIfDue(screenshot);
                    ScreenAnalyzer.Result result = ScreenAnalyzer.analyze(screenshot);
                    long signature = ScreenAnalyzer.computeScreenSignature(screenshot);

                    runOneStep(result, signature);
                } catch (Throwable ignored) {
                } finally {
                    screenshot.recycle();
                }
            }

            sleep(380);
        }
    }

    private void runOneStep(ScreenAnalyzer.Result result, long screenSignature) {
        BotAccessibilityService service = BotAccessibilityService.getInstance();
        if (service == null) return;

        // 0. Jika layar game hitam semua atau putih semua -> buka ulang game
        if (result.isBlankScreen) {
            consecutiveBlankCount++;
            BotAccessibilityService.showBotLog("Layar game " + result.blankReason + " (" + consecutiveBlankCount + "/4)...");
            if (consecutiveBlankCount >= 4) {
                BotAccessibilityService.showBotLog("Layar game " + result.blankReason + "! Membuka ulang game...");
                consecutiveBlankCount = 0;
                adStartedAt = 0;
                adWaitDone = false;
                rewardClickedPendingAd = false;
                lastScreenSignature = 0;
                lastScreenChangeAt = 0;
                restartGameFresh();
                sleep(2500);
            }
            return;
        } else {
            consecutiveBlankCount = 0;
        }

        // 0b. Deteksi layar stuck 2 menit (120 detik) tidak berubah:
        //     Jika layar tidak berubah selama 2 menit, bersihkan SEMUA riwayat aplikasi lalu buka game ulang!
        long nowTime = SystemClock.elapsedRealtime();
        if (lastScreenSignature == 0 || screenSignature != lastScreenSignature) {
            lastScreenSignature = screenSignature;
            lastScreenChangeAt = nowTime;
        } else {
            if (nowTime - lastScreenChangeAt >= 120_000L) {
                BotAccessibilityService.showBotLog("[!] Layar stuck 2 menit tidak berubah!\nMembersihkan SEMUA riwayat aplikasi & buka game ulang...");
                lastScreenSignature = 0;
                lastScreenChangeAt = nowTime;
                adStartedAt = 0;
                adWaitDone = false;
                rewardClickedPendingAd = false;
                service.clearAllRecents(result.width, result.height);
                sleep(1000);
                restartGameFresh();
                sleep(3000);
                return;
            }
        }

        String fgPkg = BotAccessibilityService.getForegroundPackage();
        String fgClass = BotAccessibilityService.getForegroundClass();

        // 1. Tangani jika terlempar ke Play Store atau Chrome
        if (fgPkg.contains("vending") || fgPkg.contains("chrome")) {
            BotAccessibilityService.showBotLog("Redirect ke " + fgPkg + "\nMenekan Back...");
            service.pressBack();
            sleep(350);
            if (BotAccessibilityService.getForegroundPackage().contains("vending")
                    || BotAccessibilityService.getForegroundPackage().contains("chrome")) {
                resumeGameWithoutRestart(result.width, result.height);
            }
            return;
        }

        // 2. PRIORITAS UTAMA: Tombol modal reward (Klaim / Koleksi / Bebas Klik / Menarik)
        //    PENTING: Harus dieksekusi SEBELUM loading check agar tombol klaim tidak pernah salah terdeteksi sebagai "game sedang memuat"!
        if (!result.isLandscape) {
            if (adTimerReader.hasRecentRewardModal()) {
                float rewX = adTimerReader.getRewardButtonX();
                float rewY = adTimerReader.getRewardButtonY();
                BotAccessibilityService.showBotLog("[★] Klik tombol Klaim/Koleksi di (" + (int)rewX + ", " + (int)rewY + ")");
                service.tap(rewX, rewY);
                sleep(400);
                adTimerReader.reset();
                rewardClickedPendingAd = true;
                rewardClickedAt = SystemClock.elapsedRealtime();
                return;
            } else if (service.clickRewardOrClaimNode()) {
                BotAccessibilityService.showBotLog("[★] Klik tombol Klaim/Koleksi via Accessibility Node");
                sleep(400);
                adTimerReader.reset();
                rewardClickedPendingAd = true;
                rewardClickedAt = SystemClock.elapsedRealtime();
                return;
            }
        }

        // 3. Setelah klik klaim / koleksi dan tombol klaim / koleksi sudah hilang, MAKA ITU HALAMAN IKLAN!
        if (rewardClickedPendingAd) {
            long elapsedSinceClaim = SystemClock.elapsedRealtime() - rewardClickedAt;
            if (!adTimerReader.hasRecentRewardModal() && elapsedSinceClaim >= 400) {
                rewardClickedPendingAd = false;
                adStartedAt = SystemClock.elapsedRealtime();
                adWaitDone = false;
                BotAccessibilityService.showBotLog("Tombol Klaim hilang -> Terkonfirmasi masuk halaman iklan!\nWajib tunggu 30s sebelum klik apa pun...");
                sleep(400);
                return;
            } else if (elapsedSinceClaim > 5000) {
                rewardClickedPendingAd = false;
            }
        }

        // 4. Tangani popup Report Ads (klik tombol X di sebelah kanan teks)
        if (adTimerReader.hasRecentReportAds()) {
            float rx = adTimerReader.getReportAdsCloseX();
            float ry = adTimerReader.getReportAdsCloseY();
            BotAccessibilityService.showBotLog("[★] Popup Report Ads terdeteksi!\nMengeklik tombol X di (" + (int)rx + ", " + (int)ry + ")");
            service.tap(rx, ry);
            sleep(200);
            service.tap(rx - 15, ry);
            sleep(400);
            adTimerReader.reset();
            return;
        }

        // 5. Tangani dialog Confirm to Close (klik Continue)
        if (adTimerReader.hasRecentConfirmClose()) {
            float cx = adTimerReader.getContinueButtonX();
            float cy = adTimerReader.getContinueButtonY();
            BotAccessibilityService.showBotLog("[★] Confirm to close -> Klik Continue");
            service.tap(cx, cy);
            sleep(400);
            adTimerReader.reset();
            return;
        }

        // 6. Game sedang memuat (loading screen / splash) -> tunggu halaman slot muncul dulu, JANGAN KLIK APAPUN!
        long currentTime = SystemClock.elapsedRealtime();
        boolean hasLoading = adTimerReader.hasRecentLoadingText();
        boolean justLaunched = gameLaunchedAt > 0 && (currentTime - gameLaunchedAt < 12000);
        if (fgPkg.equals(GAME_PACKAGE) && (hasLoading || justLaunched) && !result.boardVisible && adStartedAt == 0 && !rewardClickedPendingAd) {
            BotAccessibilityService.showBotLog("Game sedang memuat... Menunggu halaman slot & wadah muncul dulu tanpa klik apa pun.");
            sleep(600);
            return;
        }
        if (result.boardVisible) {
            gameLaunchedAt = 0;
        }

        // 7. Cek apakah activity saat ini adalah ad activity (Google AdActivity, Mintegral, Unity, Pangle, dll)
        boolean isAdActivity = fgPkg.toLowerCase().contains("reward")
                || fgPkg.toLowerCase().contains("adactivity")
                || fgPkg.toLowerCase().contains("mbridge")
                || fgPkg.toLowerCase().contains("applovin")
                || fgPkg.toLowerCase().contains("mintegral")
                || fgPkg.toLowerCase().contains("unity3d")
                || fgPkg.toLowerCase().contains("adcolony")
                || fgPkg.toLowerCase().contains("vungle")
                || fgPkg.toLowerCase().contains("ironsource")
                || fgPkg.toLowerCase().contains("pangle")
                || fgPkg.toLowerCase().contains("bytedance")
                || fgClass.toLowerCase().contains("adactivity")
                || fgClass.toLowerCase().contains("reward")
                || fgClass.toLowerCase().contains("mbridge")
                || fgClass.toLowerCase().contains("applovin")
                || fgClass.toLowerCase().contains("mintegral")
                || fgClass.toLowerCase().contains("unity3d")
                || fgClass.toLowerCase().contains("pangle")
                || fgClass.toLowerCase().contains("bytedance");

        boolean isGamePackage = fgPkg.equals(GAME_PACKAGE);
        boolean isBotPackage = fgPkg.equals(getPackageName());

        // 8. Berada di aplikasi lain selain game dan bukan iklan -> buka riwayat aplikasi (Recents) untuk kembali tanpa reload game
        if (!isGamePackage && !isBotPackage && !isAdActivity && !result.isLandscape) {
            BotAccessibilityService.showBotLog("Di aplikasi lain: " + fgPkg + "\nBuka riwayat aplikasi (Recents) untuk kembali tanpa reload game...");
            resumeGameWithoutRestart(result.width, result.height);
            sleep(600);
            return;
        }

        // 9. Cek apakah sedang di layar iklan:
        //    (activity iklan, landscape ad, board game tertutup, visual close tampak, atau masa wajib tunggu iklan)
        boolean isAd = (adStartedAt > 0 && !adWaitDone)
                || isAdActivity
                || result.isLandscape
                || result.adScreenLikely
                || (!result.boardVisible && !hasLoading && !justLaunched);

        if (isAd) {
            long now = SystemClock.elapsedRealtime();
            if (adStartedAt == 0) {
                adStartedAt = now;
                adWaitDone = false;
            }
            long adElapsedSec = (now - adStartedAt) / 1000;
            int remTimer = adTimerReader.recentRemainingSeconds();

            boolean hasSkip = adTimerReader.hasRecentSkipButton();
            boolean hasClose = adTimerReader.hasRecentCloseButton() || result.adCloseButtonVisible;
            boolean hasActionBtn = hasSkip || hasClose;

            // ATURAN WAJIB (INSTRUKSI USER): Tunggu penuh 30 detik sebelum klik apa pun!
            // JANGAN KLIK SLOT APAPUN SAAT DI HALAMAN IKLAN!
            if (adElapsedSec < 30 && !adWaitDone) {
                long sisaWajib = 30 - adElapsedSec;
                String status = "Iklan: wajib tunggu " + sisaWajib + "s lagi (total 30s) sebelum klik apa pun..."
                        + (remTimer > 0 ? " | Timer: " + remTimer + "s" : "")
                        + (result.isLandscape ? " [Landscape]" : " [Portrait]");
                BotAccessibilityService.showBotLog(status);
                sleep(400);
                return; // DIAM MUTLAK, TIDAK KLIK APAPUN!
            }

            // Setelah 30 detik selesai: jika masih ada countdown timer valid dan belum ada tombol aksi, tunggu countdown
            if (remTimer > 0 && !hasActionBtn && adElapsedSec < 45) {
                String status = "Iklan: 30s selesai, menunggu countdown " + remTimer + "s...";
                BotAccessibilityService.showBotLog(status);
                sleep(400);
                return;
            }

            adWaitDone = true;

            // EKSEKUSI PENUTUPAN IKLAN: Cari tombol x, >>, >, >>|, >| di:
            // 1. Pojok kanan atas
            // 2. Kiri atas
            // 3. Kanan bawah
            int w = result.width;
            int h = result.height;

            // Prioritas 1: Tombol Skip (>>, >, >>|, >|, skip, dll) via OCR
            if (hasSkip) {
                float sx = adTimerReader.getSkipButtonX();
                float sy = adTimerReader.getSkipButtonY();
                String txt = adTimerReader.getSkipButtonText();
                String corner = adTimerReader.getSkipCorner();
                BotAccessibilityService.showBotLog("[★] Tombol skip (" + txt + ") di " + corner + " diklik di (" + (int)sx + ", " + (int)sy + ")");
                service.tap(sx, sy);
                sleep(400);
                adTimerReader.reset();
                return;
            }

            // Prioritas 2: Tombol Close (X, close, tutup) via OCR
            if (adTimerReader.hasRecentCloseButton()) {
                float cx = adTimerReader.getCloseButtonX();
                float cy = adTimerReader.getCloseButtonY();
                String txt = adTimerReader.getCloseButtonText();
                String corner = adTimerReader.getCloseCorner();
                BotAccessibilityService.showBotLog("[★] Tombol close (" + txt + ") di " + corner + " diklik di (" + (int)cx + ", " + (int)cy + ")");
                service.tap(cx, cy);
                sleep(400);
                adTimerReader.reset();
                adStartedAt = 0;
                return;
            }

            // Prioritas 3: Tombol Close visual (X silang) via ScreenAnalyzer
            if (result.adCloseButtonVisible) {
                float cx = result.adCloseButtonX;
                float cy = result.adCloseButtonY;
                String corner = result.adCloseButtonCorner;
                BotAccessibilityService.showBotLog("[★] Tombol close visual (X) di " + corner + " diklik di (" + (int)cx + ", " + (int)cy + ")");
                service.tap(cx, cy);
                sleep(400);
                adTimerReader.reset();
                adStartedAt = 0;
                return;
            }

            // Prioritas 4: Fallback mengetuk 3 sudut target (kanan atas, kiri atas, kanan bawah) disesuaikan portrait/landscape
            BotAccessibilityService.showBotLog("[★] 30s selesai. Mengetuk tombol x / >> di pojok kanan atas, kiri atas, & kanan bawah...");
            if (result.isLandscape) {
                // Landscape: w > h
                service.tap(w - 65, 65);
                sleep(60);
                service.tap(w - 110, 65);
                sleep(60);
                service.tap(65, 65);
                sleep(60);
                service.tap(110, 65);
                sleep(60);
                service.tap(w - 65, h - 65);
                sleep(60);
                service.tap(w - 110, h - 65);
                sleep(150);
            } else {
                // Portrait: w <= h
                float sx = w / 720f;
                float sy = h / 1640f;
                service.tap(w - 55 * sx, 75 * sy);
                sleep(60);
                service.tap(w - 85 * sx, 80 * sy);
                sleep(60);
                service.tap(55 * sx, 75 * sy);
                sleep(60);
                service.tap(85 * sx, 80 * sy);
                sleep(60);
                service.tap(w - 55 * sx, h - 90 * sy);
                sleep(60);
                service.tap(w - 85 * sx, h - 110 * sy);
                sleep(150);
            }
            service.pressBack();
            adStartedAt = 0;
            adTimerReader.reset();
            sleep(600);
            return;
        }

        // 10. Gameplay aktif di HALAMAN UTAMA game:
        //     Jangan klik slot apapun saat di halaman iklan!
        //     Hanya klik slot setelah dipastikan benar-benar berada di halaman utama game Color Power Pop.
        boolean isMainGameBoard = isGamePackage
                && !isAdActivity
                && !result.isLandscape
                && result.boardVisible;

        if (isMainGameBoard) {
            adStartedAt = 0;
            adWaitDone = false;
            if (!result.matchingCardsToTap.isEmpty()) {
                noMatchCount = 0;
                StringBuilder sb = new StringBuilder();
                sb.append("Slot: ");
                for (ScreenAnalyzer.SlotCard s : result.topSlots) {
                    sb.append("S").append(s.slotIndex).append("=").append(s.color).append(" ");
                }
                sb.append("\n-> Tap: ");
                for (ScreenAnalyzer.SlotCard target : result.matchingCardsToTap) {
                    sb.append("S").append(target.slotIndex).append("[").append(target.color).append("] ");
                }
                BotAccessibilityService.showBotLog(sb.toString());

                // Tap semua kartu yang cocok berurutan
                for (ScreenAnalyzer.SlotCard target : result.matchingCardsToTap) {
                    service.tap(target.x, target.y);
                    sleep(160);
                }
            } else if (!result.topSlots.isEmpty()) {
                noMatchCount++;
                if (noMatchCount >= 5) {
                    // Fallback tap: jika kartu di slot atas ada tetapi belum cocok dengan baris 1 wadah bawah selama ~2 detik,
                    // ketuk kartu slot atas yang ada secara berurutan agar alur game tetap jalan!
                    int pickIdx = (noMatchCount - 5) % result.topSlots.size();
                    ScreenAnalyzer.SlotCard fallbackCard = result.topSlots.get(pickIdx);
                    BotAccessibilityService.showBotLog("Halaman utama: Fallback tap Slot " + fallbackCard.slotIndex + " (" + fallbackCard.color + ")");
                    service.tap(fallbackCard.x, fallbackCard.y);
                    sleep(200);
                } else {
                    BotAccessibilityService.showBotLog("Halaman utama (" + result.topSlots.size() + " slot): Menunggu kartu cocok / wadah...");
                    sleep(300);
                }
            } else {
                BotAccessibilityService.showBotLog("Halaman utama: Menunggu slot kartu muncul...");
                sleep(300);
            }
            return;
        } else {
            // Jika bukan di halaman utama game, JANGAN ketuk slot apa pun!
            if (!fgPkg.equals(GAME_PACKAGE)) {
                resumeGameWithoutRestart(result.width, result.height);
            } else {
                BotAccessibilityService.showBotLog("Menunggu halaman utama game kembali...");
                sleep(300);
            }
        }
    }

    private void resumeGameWithoutRestart(int width, int height) {
        gameLaunchedAt = SystemClock.elapsedRealtime();
        BotAccessibilityService service = BotAccessibilityService.getInstance();
        if (service != null) {
            boolean switched = service.switchToGameFromRecents(width, height);
            if (switched) {
                sleep(700);
                String currentPkg = BotAccessibilityService.getForegroundPackage();
                if (currentPkg.equals(GAME_PACKAGE)) {
                    return;
                }
            }
        }

        // Fallback: panggil intent dengan FLAG_ACTIVITY_REORDER_TO_FRONT (agar kembali ke game tanpa mulai ulang)
        try {
            Intent launch = getPackageManager().getLaunchIntentForPackage(GAME_PACKAGE);
            if (launch != null) {
                launch.removeFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
                launch.addFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT | Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(launch);
                sleep(700);
            }
        } catch (Throwable ignored) {
        }
    }

    private void restartGameFresh() {
        gameLaunchedAt = SystemClock.elapsedRealtime();
        try {
            Intent launch = getPackageManager().getLaunchIntentForPackage(GAME_PACKAGE);
            if (launch != null) {
                launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
                startActivity(launch);
            }
        } catch (Throwable ignored) {
        }
    }

    private void sleep(long ms) {

        try {
            Thread.sleep(ms);
        } catch (InterruptedException ignored) {
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(
                    CHANNEL_ID,
                    "Color Power Pop Bot Service",
                    NotificationManager.IMPORTANCE_LOW
            );
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(ch);
        }
    }

    private Notification buildNotification(String text) {
        Intent stopIntent = new Intent(this, BotForegroundService.class);
        stopIntent.setAction(ACTION_STOP);
        PendingIntent stopPi = PendingIntent.getService(
                this, 0, stopIntent,
                Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0
        );

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);

        return builder
                .setContentTitle("Color Power Pop Bot")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_media_play)
                .addAction(android.R.drawable.ic_delete, "Stop", stopPi)
                .setOngoing(true)
                .build();
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        running = false;
        runningInstance = false;
        if (botThread != null) botThread.interrupt();
        if (virtualDisplay != null) virtualDisplay.release();
        if (imageReader != null) imageReader.close();
        if (captureThread != null) captureThread.quitSafely();
        if (projection != null) projection.stop();
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        if (adTimerReader != null) adTimerReader.close();
        BotAccessibilityService.removeBotLog();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
