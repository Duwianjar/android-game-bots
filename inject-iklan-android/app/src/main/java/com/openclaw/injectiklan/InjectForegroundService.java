package com.openclaw.injectiklan;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;

public class InjectForegroundService extends Service {
    public static final String ACTION_RUN_ONCE = "com.openclaw.injectiklan.RUN_ONCE";
    public static final String ACTION_START_LOOP = "com.openclaw.injectiklan.START_LOOP";
    public static final String ACTION_STOP = "com.openclaw.injectiklan.STOP";

    private static final String CHANNEL_ID = "inject_iklan_service";
    private static final int NOTIF_ID = 2026;
    private static final long DEFAULT_LOOP_INTERVAL_MS = 300_000L; // 5 menit

    private PowerManager.WakeLock mWakeLock;
    private final Handler mLoopHandler = new Handler(Looper.getMainLooper());
    private boolean mIsLooping = false;
    private int mCycleCount = 0;

    private final Runnable mLoopRunnable = new Runnable() {
        @Override
        public void run() {
            if (!mIsLooping) return;
            mCycleCount++;
            updateNotification("Menjalankan siklus #" + mCycleCount + "...");
            InjectAccessibilityService service = InjectAccessibilityService.getInstance();
            if (service != null) {
                service.startCycle(() -> {
                    updateNotification("Siklus #" + mCycleCount + " selesai. Jeda 5 menit...");
                    if (mIsLooping) {
                        mLoopHandler.postDelayed(mLoopRunnable, DEFAULT_LOOP_INTERVAL_MS);
                    }
                });
            } else {
                updateNotification("Accessibility belum aktif! Menunggu...");
                if (mIsLooping) {
                    mLoopHandler.postDelayed(mLoopRunnable, 30_000L);
                }
            }
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        if (pm != null) {
            mWakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "InjectIklan::ServiceWakeLock");
            mWakeLock.acquire(12 * 3600 * 1000L); // 12 jam
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) return START_NOT_STICKY;
        String action = intent.getAction();

        if (ACTION_STOP.equals(action)) {
            stopLoop();
            stopForeground(true);
            stopSelf();
            return START_NOT_STICKY;
        }

        startForeground(NOTIF_ID, buildNotification("Bot Inject Iklan siap..."));

        if (ACTION_RUN_ONCE.equals(action)) {
            stopLoop();
            updateNotification("Menjalankan 1 siklus...");
            InjectAccessibilityService service = InjectAccessibilityService.getInstance();
            if (service != null) {
                service.startCycle(() -> {
                    updateNotification("Siklus selesai. Kembali ke game.");
                });
            }
        } else if (ACTION_START_LOOP.equals(action)) {
            if (!mIsLooping) {
                mIsLooping = true;
                mCycleCount = 0;
                mLoopHandler.post(mLoopRunnable);
            }
        }
        return START_STICKY;
    }

    private void stopLoop() {
        mIsLooping = false;
        mLoopHandler.removeCallbacks(mLoopRunnable);
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Layanan Inject Iklan",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Notifikasi aktif saat bot sedang berjalan");
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) {
                nm.createNotificationChannel(channel);
            }
        }
    }

    private Notification buildNotification(String text) {
        Intent notifIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, notifIntent,
                Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0
        );

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }

        return builder
                .setContentTitle("Inject Iklan Active")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .build();
    }

    private void updateNotification(String text) {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.notify(NOTIF_ID, buildNotification(text));
        }
    }

    @Override
    public void onDestroy() {
        stopLoop();
        if (mWakeLock != null && mWakeLock.isHeld()) {
            mWakeLock.release();
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
