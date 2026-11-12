package com.openclaw.injectiklan;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity implements InjectAccessibilityService.LogListener {
    private TextView mStatusText;
    private TextView mLogTextView;
    private ScrollView mScrollView;
    private final StringBuilder mLogBuffer = new StringBuilder();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        InjectAccessibilityService.setLogListener(this);
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateStatus();
    }

    @Override
    protected void onDestroy() {
        InjectAccessibilityService.setLogListener(null);
        super.onDestroy();
    }

    private void updateStatus() {
        boolean active = InjectAccessibilityService.getInstance() != null;
        if (active) {
            mStatusText.setText("Status: Layanan Accessibility AKTIF (Siap dijalankan)");
            mStatusText.setTextColor(Color.parseColor("#10B981"));
        } else {
            mStatusText.setText("Status: Accessibility BELUM AKTIF (Tekan tombol 1 di bawah)");
            mStatusText.setTextColor(Color.parseColor("#EF4444"));
        }
    }

    private Button createButton(String text, int bgColor) {
        Button btn = new Button(this);
        btn.setText(text);
        btn.setTextSize(15);
        btn.setTextColor(Color.WHITE);
        btn.setTypeface(null, Typeface.BOLD);
        btn.setPadding(20, 24, 20, 24);

        GradientDrawable shape = new GradientDrawable();
        shape.setCornerRadius(16);
        shape.setColor(bgColor);
        btn.setBackground(shape);

        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.setMargins(0, 10, 0, 10);
        btn.setLayoutParams(params);
        return btn;
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(32, 40, 32, 32);
        root.setBackgroundColor(Color.parseColor("#0F172A"));

        // Header Title
        TextView title = new TextView(this);
        title.setText("INJECT IKLAN");
        title.setTextSize(26);
        title.setTextColor(Color.WHITE);
        title.setTypeface(null, Typeface.BOLD);
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("Injeksi profil Google slot/judi & kembali ke Home");
        subtitle.setTextSize(13);
        subtitle.setTextColor(Color.parseColor("#94A3B8"));
        subtitle.setGravity(Gravity.CENTER_HORIZONTAL);
        LinearLayout.LayoutParams subParams = new LinearLayout.LayoutParams(-1, -2);
        subParams.setMargins(0, 4, 0, 24);
        root.addView(subtitle, subParams);

        // Status
        mStatusText = new TextView(this);
        mStatusText.setTextSize(14);
        mStatusText.setTypeface(null, Typeface.BOLD);
        LinearLayout.LayoutParams statusParams = new LinearLayout.LayoutParams(-1, -2);
        statusParams.setMargins(0, 0, 0, 20);
        root.addView(mStatusText, statusParams);

        // Button 1: Accessibility
        Button btnAccess = createButton("1. Aktifkan Izin Accessibility", Color.parseColor("#3B82F6"));
        btnAccess.setOnClickListener(v -> {
            startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
            Toast.makeText(this, "Cari 'Inject Iklan' dan aktifkan", Toast.LENGTH_LONG).show();
        });
        root.addView(btnAccess);

        // Button 2: Run Once
        Button btnRunOnce = createButton("2. Jalankan 1 Siklus Sekarang", Color.parseColor("#10B981"));
        btnRunOnce.setOnClickListener(v -> {
            if (InjectAccessibilityService.getInstance() == null) {
                Toast.makeText(this, "Aktifkan Accessibility terlebih dahulu!", Toast.LENGTH_SHORT).show();
                return;
            }
            Intent s = new Intent(this, InjectForegroundService.class);
            s.setAction(InjectForegroundService.ACTION_RUN_ONCE);
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(s);
            else startService(s);
        });
        root.addView(btnRunOnce);

        // Button 3: Loop 5 Menit
        Button btnLoop = createButton("3. Jalankan Loop Otomatis (Tiap 5 Menit)", Color.parseColor("#F59E0B"));
        btnLoop.setOnClickListener(v -> {
            if (InjectAccessibilityService.getInstance() == null) {
                Toast.makeText(this, "Aktifkan Accessibility terlebih dahulu!", Toast.LENGTH_SHORT).show();
                return;
            }
            Intent s = new Intent(this, InjectForegroundService.class);
            s.setAction(InjectForegroundService.ACTION_START_LOOP);
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(s);
            else startService(s);
            Toast.makeText(this, "Loop berkala dimulai tiap 5 menit.", Toast.LENGTH_SHORT).show();
        });
        root.addView(btnLoop);

        // Button 4: Stop
        Button btnStop = createButton("Hentikan Bot", Color.parseColor("#EF4444"));
        btnStop.setOnClickListener(v -> {
            Intent s = new Intent(this, InjectForegroundService.class);
            s.setAction(InjectForegroundService.ACTION_STOP);
            startService(s);
            Toast.makeText(this, "Bot dihentikan.", Toast.LENGTH_SHORT).show();
        });
        root.addView(btnStop);

        // Console Log View
        TextView logTitle = new TextView(this);
        logTitle.setText("\nLog Aktivitas:");
        logTitle.setTextColor(Color.parseColor("#CBD5E1"));
        logTitle.setTextSize(14);
        logTitle.setTypeface(null, Typeface.BOLD);
        root.addView(logTitle);

        mScrollView = new ScrollView(this);
        mLogTextView = new TextView(this);
        mLogTextView.setText("Menunggu aktivitas bot...\n");
        mLogTextView.setTextSize(12);
        mLogTextView.setTextColor(Color.parseColor("#A7F3D0"));
        mLogTextView.setTypeface(Typeface.MONOSPACE);
        mLogTextView.setPadding(16, 16, 16, 16);

        GradientDrawable logBox = new GradientDrawable();
        logBox.setColor(Color.parseColor("#020617"));
        logBox.setCornerRadius(12);
        mLogTextView.setBackground(logBox);

        mScrollView.addView(mLogTextView);
        LinearLayout.LayoutParams scrollParams = new LinearLayout.LayoutParams(-1, 0, 1.0f);
        scrollParams.setMargins(0, 12, 0, 0);
        root.addView(mScrollView, scrollParams);

        setContentView(root);
    }

    @Override
    public void onLogMessage(String message) {
        mLogBuffer.append(message).append("\n");
        mLogTextView.setText(mLogBuffer.toString());
        mScrollView.post(() -> mScrollView.fullScroll(View.FOCUS_DOWN));
    }
}
