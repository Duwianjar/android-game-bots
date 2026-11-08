package com.openclaw.blockeddetector;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.os.Build;

public class NotificationHelper {
    public static final String CHANNEL_ID = "blocked_game_alerts";
    public static final String CHANNEL_NAME = "Peringatan Game Blocked";

    public static void ensureChannel(Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null && nm.getNotificationChannel(CHANNEL_ID) == null) {
                NotificationChannel channel = new NotificationChannel(
                        CHANNEL_ID,
                        CHANNEL_NAME,
                        NotificationManager.IMPORTANCE_HIGH
                );
                channel.setDescription("Notifikasi peringatan jika aplikasi dari daftar blocked terdeteksi");
                channel.enableLights(true);
                channel.setLightColor(Color.RED);
                channel.enableVibration(true);
                channel.setVibrationPattern(new long[]{0, 500, 200, 500});
                nm.createNotificationChannel(channel);
            }
        }
    }

    public static void showAlertNotification(Context context, BlockedItem item, String actualPackage, String actualLabel) {
        ensureChannel(context);
        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;

        Intent alertIntent = new Intent(context, BlockedAlertActivity.class);
        alertIntent.putExtra("blocked_item", item);
        alertIntent.putExtra("actual_package", actualPackage);
        alertIntent.putExtra("actual_label", actualLabel);
        alertIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);

        PendingIntent pi = PendingIntent.getActivity(
                context,
                item.id,
                alertIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(context, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(context);
            builder.setPriority(Notification.PRIORITY_MAX);
        }

        builder.setContentTitle("⚠️ APLIKASI BLOCKED TERDETEKSI!")
                .setContentText(item.name + " (" + actualPackage + ") ada di HP!")
                .setSmallIcon(android.R.drawable.stat_notify_error)
                .setAutoCancel(true)
                .setContentIntent(pi);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN) {
            Notification.BigTextStyle style = new Notification.BigTextStyle()
                    .setBigContentTitle("⚠️ APLIKASI BLOCKED TERDETEKSI!")
                    .bigText("Game: " + item.name + "\nPackage: " + actualPackage + "\nAlasan: " + item.notes + "\n\nKetuk untuk menghapus aplikasi ini sekarang.");
            builder.setStyle(style);
        }

        nm.notify(item.id + 1000, builder.build());
    }
}
