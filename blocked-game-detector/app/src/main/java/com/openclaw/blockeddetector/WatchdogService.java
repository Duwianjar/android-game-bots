package com.openclaw.blockeddetector;

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
import android.util.Log;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class WatchdogService extends Service {
    private static final String TAG = "BlockedWatchdog";
    private static final String SERVICE_CHANNEL_ID = "watchdog_service_channel";
    private static final int SERVICE_NOTIFICATION_ID = 9999;
    private static final long SCAN_INTERVAL_MS = 25000; // scan setiap 25 detik

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Set<String> alreadyAlerted = new HashSet<>();
    private boolean isRunning = false;

    private final Runnable scanRunnable = new Runnable() {
        @Override
        public void run() {
            if (!isRunning) return;
            try {
                performScan();
            } catch (Exception e) {
                Log.e(TAG, "Error saat scan berkala", e);
            }
            handler.postDelayed(this, SCAN_INTERVAL_MS);
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        createServiceChannel();
        startForeground(SERVICE_NOTIFICATION_ID, buildForegroundNotification());
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (!isRunning) {
            isRunning = true;
            handler.post(scanRunnable);
            Log.i(TAG, "Watchdog Service dimulai.");
        }
        return START_STICKY;
    }

    private void performScan() {
        List<BlockedRegistry.DetectedApp> detected = BlockedRegistry.scanInstalled(this);
        for (BlockedRegistry.DetectedApp app : detected) {
            if (!alreadyAlerted.contains(app.actualPackage)) {
                alreadyAlerted.add(app.actualPackage);
                Log.w(TAG, "Ditemukan aplikasi blocked saat scan: " + app.item.name);
                NotificationHelper.showAlertNotification(this, app.item, app.actualPackage, app.actualLabel);

                Intent alertIntent = new Intent(this, BlockedAlertActivity.class);
                alertIntent.putExtra("blocked_item", app.item);
                alertIntent.putExtra("actual_package", app.actualPackage);
                alertIntent.putExtra("actual_label", app.actualLabel);
                alertIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
                startActivity(alertIntent);
            }
        }
        // Bersihkan cache jika aplikasi sudah di-uninstall
        alreadyAlerted.removeIf(pkg -> {
            try {
                getPackageManager().getPackageInfo(pkg, 0);
                return false;
            } catch (Exception e) {
                return true;
            }
        });
    }

    private void createServiceChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null && nm.getNotificationChannel(SERVICE_CHANNEL_ID) == null) {
                NotificationChannel channel = new NotificationChannel(
                        SERVICE_CHANNEL_ID,
                        "Perlindungan Blocked Detector",
                        NotificationManager.IMPORTANCE_LOW
                );
                channel.setDescription("Layanan pemantau aplikasi blocked di latar belakang");
                nm.createNotificationChannel(channel);
            }
        }
    }

    private Notification buildForegroundNotification() {
        Intent openIntent = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(
                this,
                0,
                openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, SERVICE_CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
            builder.setPriority(Notification.PRIORITY_LOW);
        }

        return builder.setContentTitle("🛡️ Blocked Game Detector Aktif")
                .setContentText("HP Anda sedang dipantau dari game daftar Blocked")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentIntent(pi)
                .setOngoing(true)
                .build();
    }

    @Override
    public void onDestroy() {
        isRunning = false;
        handler.removeCallbacks(scanRunnable);
        Log.i(TAG, "Watchdog Service dihentikan.");
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
