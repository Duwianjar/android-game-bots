package com.openclaw.colorpowerpop;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.media.projection.MediaProjectionManager;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final int REQUEST_CAPTURE = 3501;
    private TextView status;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (BotForegroundService.isBotRunning()) {
            setStatus("Bot sedang berjalan.");
        } else {
            setStatus("Belum berjalan / dihentikan.");
        }
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28, 30, 28, 24);

        TextView title = new TextView(this);
        title.setText("Color Power Pop Bot");
        title.setTextSize(26);
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(title, new LinearLayout.LayoutParams(-1, -2));

        TextView info = new TextView(this);
        info.setText(
                "\nBot berjalan langsung di HP Android tanpa ADB/laptop.\n" +
                "Target game: com.giraffeeapp.power\n\n" +
                "1. Aktifkan Accessibility satu kali.\n" +
                "2. Tekan Mulai Bot dan izinkan screen capture."
        );
        info.setTextSize(15);
        root.addView(info, new LinearLayout.LayoutParams(-1, -2));

        Button accessibility = new Button(this);
        accessibility.setText("1. Aktifkan Accessibility");
        accessibility.setOnClickListener(v ->
                startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)));
        root.addView(accessibility, new LinearLayout.LayoutParams(-1, -2));

        Button start = new Button(this);
        start.setText("2. Mulai Bot");
        start.setOnClickListener(v -> requestScreenCapture());
        root.addView(start, new LinearLayout.LayoutParams(-1, -2));

        Button stop = new Button(this);
        stop.setText("Hentikan Bot");
        stop.setOnClickListener(v -> {
            stopService(new Intent(this, BotForegroundService.class));
            BotAccessibilityService.removeBotLog();
            sendBroadcast(new Intent(BotAccessibilityService.ACTION_DISMISS_POPUP));
            BotAccessibilityService service = BotAccessibilityService.getInstance();
            if (service != null) {
                service.pressBack();
            }
            setStatus("Bot dihentikan.");
        });
        root.addView(stop, new LinearLayout.LayoutParams(-1, -2));

        status = new TextView(this);
        status.setText("\nStatus: belum berjalan");
        status.setTextSize(15);
        root.addView(status, new LinearLayout.LayoutParams(-1, -2));

        TextView log = new TextView(this);
        log.setText(
                "\nFitur Bot:\n" +
                "- Deteksi warna kartu atas dan pencocokan ke wadah bawah otomatis.\n" +
                "- Klaim & koleksi reward otomatis.\n" +
                "- Deteksi & tutup popup Report Ads via tombol X di kanan teks.\n" +
                "- Tutup iklan otomatis setelah waktu tunggu selesai.\n" +
                "- Floating log overlay di layar game."
        );
        log.setTextSize(13);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(log);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));

        setContentView(root);
    }

    private void requestScreenCapture() {
        if (BotAccessibilityService.getInstance() == null) {
            Toast.makeText(this, "Aktifkan Accessibility terlebih dahulu.", Toast.LENGTH_LONG).show();
            return;
        }
        MediaProjectionManager manager =
                (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        startActivityForResult(manager.createScreenCaptureIntent(), REQUEST_CAPTURE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_CAPTURE || data == null || resultCode != RESULT_OK) {
            setStatus("Izin screen capture dibatalkan.");
            return;
        }
        Intent service = new Intent(this, BotForegroundService.class);
        service.putExtra(BotForegroundService.EXTRA_RESULT_CODE, resultCode);
        service.putExtra(BotForegroundService.EXTRA_RESULT_DATA, data);
        if (android.os.Build.VERSION.SDK_INT >= 26) {
            startForegroundService(service);
        } else {
            startService(service);
        }
        setStatus("Bot dimulai. Membuka game Color Power Pop...");
        Intent game = getPackageManager().getLaunchIntentForPackage(BotForegroundService.GAME_PACKAGE);
        if (game != null) {
            startActivity(game);
        }
    }

    private void setStatus(String text) {
        if (status != null) {
            status.setText("\nStatus: " + text);
        }
    }
}
