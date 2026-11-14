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
    private long lastActionAt = 0;

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
        setupCapture();

        running = true;
        botThread = new Thread(this::botLoop, "color-power-pop-worker");
        botThread.start();

        return START_STICKY;
    }

    private void setupCapture() {
        WindowManager wm = (WindowManager) getSystemService(WINDOW_SERVICE);
        android.util.DisplayMetrics metrics = new android.util.DisplayMetrics();
        wm.getDefaultDisplay().getRealMetrics(metrics);
        int width = metrics.widthPixels;
        int height = metrics.heightPixels;
        int density = metrics.densityDpi;

        captureThread = new HandlerThread("cpp-capture");
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
                "ColorPowerPopCapture",
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
        sleep(1000);
        while (running) {
            Bitmap screenshot = null;
            synchronized (bitmapLock) {
                if (latestBitmap != null && !latestBitmap.isRecycled()) {
                    screenshot = latestBitmap.copy(Bitmap.Config.ARGB_8888, false);
                }
            }

            if (screenshot != null && !screenshot.isRecycled()) {
                try {
                    // Jalankan pembaca OCR untuk mendeteksi ad timer, report ads, dan popup reward
                    adTimerReader.readIfDue(screenshot);
                    ScreenAnalyzer.Result result = ScreenAnalyzer.analyze(screenshot);

                    runOneStep(result, screenshot);
                } catch (Throwable ignored) {
                } finally {
                    screenshot.recycle();
                }
            }

            sleep(400);
        }
    }

    private void runOneStep(ScreenAnalyzer.Result result, Bitmap screenshot) {
        BotAccessibilityService service = BotAccessibilityService.getInstance();
        if (service == null) return;

        String fgPkg = BotAccessibilityService.getForegroundPackage();

        // 1. Tangani Play Store / Chrome yang terbuka oleh iklan
        if (fgPkg.contains("vending") || fgPkg.contains("chrome")) {
            BotAccessibilityService.showBotLog("Redirect ke " + fgPkg + "\nMenekan Back...");
            service.pressBack();
            sleep(400);
            bringGameToFront();
            return;
        }

        // 2. Tangani popup Report Ads (klik tombol X di sebelah kanan teks)
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

        // 3. Tangani dialog Confirm to Close (klik Continue)
        if (adTimerReader.hasRecentConfirmClose()) {
            float cx = adTimerReader.getContinueButtonX();
            float cy = adTimerReader.getContinueButtonY();
            BotAccessibilityService.showBotLog("[★] Confirm to close -> Klik Continue");
            service.tap(cx, cy);
            sleep(400);
            adTimerReader.reset();
            return;
        }

        // 4. Tangani tombol modal reward (Klaim / Koleksi / Bebas Klik / Menarik)
        if (adTimerReader.hasRecentRewardModal()) {
            float rewX = adTimerReader.getRewardButtonX();
            float rewY = adTimerReader.getRewardButtonY();
            BotAccessibilityService.showBotLog("[★] Klaim / Koleksi Hadiah di (" + (int)rewX + ", " + (int)rewY + ")");
            service.tap(rewX, rewY);
            sleep(300);
            // Tap kartu slot 1 sekali cepat pasca-klaim agar flow game berlanjut
            float sx = result.width / 720f;
            float sy = result.height / 1640f;
            service.tap(188 * sx, 764 * sy);
            sleep(500);
            adTimerReader.reset();
            return;
        }

        // 5. Cek apakah sedang di layar iklan
        boolean isAdActivity = fgPkg.toLowerCase().contains("reward")
                || fgPkg.toLowerCase().contains("adactivity")
                || fgPkg.toLowerCase().contains("mbridge")
                || fgPkg.toLowerCase().contains("applovin")
                || fgPkg.toLowerCase().contains("mintegral");

        if (isAdActivity || result.adScreenLikely || !result.boardVisible) {
            long now = SystemClock.elapsedRealtime();
            if (adStartedAt == 0) {
                adStartedAt = now;
            }
            long adElapsedSec = (now - adStartedAt) / 1000;
            int remTimer = adTimerReader.recentRemainingSeconds();

            String status = "Iklan (" + adElapsedSec + "s)" + (remTimer >= 0 ? " Sisa: " + remTimer + "s" : "");
            BotAccessibilityService.showBotLog(status);

            // Jika masih ada countdown timer dan belum ada tombol skip/close, jangan sentuh layar
            boolean hasActionBtn = adTimerReader.hasRecentSkipButton()
                    || adTimerReader.hasRecentCloseButton()
                    || result.adCloseButtonVisible;

            if (remTimer > 0 && !hasActionBtn) {
                return; // Menunggu countdown selesai tanpa klik
            }

            // Waktu tunggu minimal 15 detik sebelum menutup iklan
            if (adElapsedSec >= 15 || (remTimer == 0 && adElapsedSec >= 8) || (hasActionBtn && adElapsedSec >= 15)) {
                // 1. Klik skip jika ada (>>, >|, dll)
                if (adTimerReader.hasRecentSkipButton()) {
                    BotAccessibilityService.showBotLog("[★] Klik tombol Skip (>>)");
                    service.tap(adTimerReader.getSkipButtonX(), adTimerReader.getSkipButtonY());
                    sleep(300);
                }
                // 2. Klik tombol close X yang terdeteksi OCR
                if (adTimerReader.hasRecentCloseButton()) {
                    BotAccessibilityService.showBotLog("[★] Klik tombol Close (X)");
                    service.tap(adTimerReader.getCloseButtonX(), adTimerReader.getCloseButtonY());
                    sleep(300);
                } else if (result.adCloseButtonVisible) {
                    BotAccessibilityService.showBotLog("[★] Klik tombol Close (X Visual)");
                    service.tap(result.adCloseButtonX, result.adCloseButtonY);
                    sleep(300);
                } else {
                    // Fallback multi-tap posisi tombol X umum (kanan atas, kiri atas, kanan bawah)
                    float sx = result.width / 720f;
                    float sy = result.height / 1640f;
                    service.tap(665 * sx, 75 * sy);
                    sleep(50);
                    service.tap(635 * sx, 80 * sy);
                    sleep(50);
                    service.tap(55 * sx, 75 * sy);
                    sleep(50);
                    service.tap(665 * sx, 1550 * sy);
                    sleep(150);
                    service.pressBack();
                }
                adStartedAt = 0;
                sleep(600);
                bringGameToFront();
            }
            return;
        }

        // 6. Gameplay aktif: Layar kartu dan wadah terdeteksi
        adStartedAt = 0;
        if (result.boardVisible) {
            if (!result.matchingCardsToTap.isEmpty()) {
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
            } else {
                BotAccessibilityService.showBotLog("Menunggu kartu cocok / reward...");
                sleep(300);
            }
        } else {
            // Pastikan game ada di layar depan
            if (!fgPkg.equals(GAME_PACKAGE)) {
                bringGameToFront();
            }
        }
    }

    private void bringGameToFront() {
        try {
            Intent launch = getPackageManager().getLaunchIntentForPackage(GAME_PACKAGE);
            if (launch != null) {
                launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
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
