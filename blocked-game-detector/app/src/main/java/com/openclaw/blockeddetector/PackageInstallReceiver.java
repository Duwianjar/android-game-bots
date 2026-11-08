package com.openclaw.blockeddetector;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.util.Log;

public class PackageInstallReceiver extends BroadcastReceiver {
    private static final String TAG = "BlockedDetector";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) return;
        String action = intent.getAction();

        if (Intent.ACTION_PACKAGE_ADDED.equals(action) || Intent.ACTION_PACKAGE_REPLACED.equals(action)) {
            Uri data = intent.getData();
            if (data == null) return;
            String packageName = data.getSchemeSpecificPart();
            if (packageName == null || packageName.isEmpty()) return;

            Log.d(TAG, "Aplikasi baru diinstall: " + packageName);
            PackageManager pm = context.getPackageManager();
            BlockedItem match = BlockedRegistry.checkPackage(pm, packageName);

            if (match != null) {
                Log.w(TAG, "⚠️ APLIKASI BLOCKED TERDETEKSI: " + match.name + " (" + packageName + ")");
                String label = packageName;
                try {
                    CharSequence cs = pm.getApplicationLabel(pm.getApplicationInfo(packageName, 0));
                    if (cs != null) label = cs.toString();
                } catch (Exception ignored) {}

                // 1. Tampilkan notifikasi sistem
                NotificationHelper.showAlertNotification(context, match, packageName, label);

                // 2. Tampilkan dialog layar penuh
                Intent alertIntent = new Intent(context, BlockedAlertActivity.class);
                alertIntent.putExtra("blocked_item", match);
                alertIntent.putExtra("actual_package", packageName);
                alertIntent.putExtra("actual_label", label);
                alertIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
                context.startActivity(alertIntent);
            }
        }
    }
}
