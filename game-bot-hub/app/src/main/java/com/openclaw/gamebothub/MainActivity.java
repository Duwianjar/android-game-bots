package com.openclaw.gamebothub;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import java.util.List;
import java.util.Locale;

public class MainActivity extends Activity implements RotationManager.RotationListener {
    private BotRegistry registry;
    private RotationManager rotationManager;
    private BotAdapter adapter;

    private TextView tvAccessibilityStatus;
    private TextView tvOverlayStatus;
    private EditText etDuration;
    private TextView tvSummary;
    private Button btnStartStop;
    private Button btnPauseResume;
    private Button btnStopBot;
    private TextView tvRunningTicker;
    private Switch swLoop;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        registry = BotRegistry.getInstance();
        rotationManager = RotationManager.getInstance();

        registry.refreshInstalledStatus(this);
        registry.loadPreferences(this);

        buildUi();
        rotationManager.addListener(this);
    }

    @Override
    protected void onResume() {
        super.onResume();
        registry.refreshInstalledStatus(this);
        if (adapter != null) {
            adapter.notifyDataSetChanged();
        }
        updatePermissionStatuses();
        updateSummary();
        updateRunningState();
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(0xFF0F172A);
        root.setPadding(24, 20, 24, 16);

        // Header Title
        TextView tvTitle = new TextView(this);
        tvTitle.setText("🎮 GAME BOT HUB");
        tvTitle.setTextColor(0xFF38BDF8);
        tvTitle.setTextSize(22);
        tvTitle.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(tvTitle);

        TextView tvSubtitle = new TextView(this);
        tvSubtitle.setText("Pusat Otomasi & Rotasi Bot Game Multi-App");
        tvSubtitle.setTextColor(0xFF94A3B8);
        tvSubtitle.setTextSize(12);
        tvSubtitle.setGravity(Gravity.CENTER_HORIZONTAL);
        tvSubtitle.setPadding(0, 4, 0, 16);
        root.addView(tvSubtitle);

        // Status Card Permissions
        LinearLayout permCard = new LinearLayout(this);
        permCard.setOrientation(LinearLayout.VERTICAL);
        permCard.setPadding(20, 16, 20, 16);
        GradientDrawable permBg = new GradientDrawable();
        permBg.setColor(0xFF1E293B);
        permBg.setCornerRadius(18);
        permCard.setBackground(permBg);

        tvAccessibilityStatus = new TextView(this);
        tvAccessibilityStatus.setTextSize(12);
        tvAccessibilityStatus.setPadding(0, 4, 0, 6);
        tvAccessibilityStatus.setOnClickListener(v -> openAccessibilitySettings());
        permCard.addView(tvAccessibilityStatus);

        tvOverlayStatus = new TextView(this);
        tvOverlayStatus.setTextSize(12);
        tvOverlayStatus.setPadding(0, 4, 0, 4);
        tvOverlayStatus.setOnClickListener(v -> openOverlaySettings());
        permCard.addView(tvOverlayStatus);

        root.addView(permCard);

        // Card Konfigurasi Rotasi
        LinearLayout configCard = new LinearLayout(this);
        configCard.setOrientation(LinearLayout.VERTICAL);
        configCard.setPadding(20, 16, 20, 16);
        GradientDrawable confBg = new GradientDrawable();
        confBg.setColor(0xFF1E293B);
        confBg.setCornerRadius(18);
        configCard.setBackground(confBg);
        LinearLayout.LayoutParams confParams = new LinearLayout.LayoutParams(-1, -2);
        confParams.topMargin = 14;
        confParams.bottomMargin = 14;
        configCard.setLayoutParams(confParams);

        // Baris Durasi
        LinearLayout durRow = new LinearLayout(this);
        durRow.setOrientation(LinearLayout.HORIZONTAL);
        durRow.setGravity(Gravity.CENTER_VERTICAL);

        TextView tvDurLabel = new TextView(this);
        tvDurLabel.setText("⏱ Durasi per Game:");
        tvDurLabel.setTextColor(0xFFF8FAFC);
        tvDurLabel.setTextSize(14);
        tvDurLabel.setLayoutParams(new LinearLayout.LayoutParams(0, -2, 1));
        durRow.addView(tvDurLabel);

        Button btnMinus = createSmallButton("-", 0xFF334155, 0xFFFFFFFF);
        btnMinus.setOnClickListener(v -> adjustDuration(-1));
        durRow.addView(btnMinus);

        etDuration = new EditText(this);
        etDuration.setInputType(InputType.TYPE_CLASS_NUMBER);
        etDuration.setText(String.valueOf(registry.getDurationMinutes()));
        etDuration.setTextColor(0xFF38BDF8);
        etDuration.setTextSize(16);
        etDuration.setGravity(Gravity.CENTER);
        etDuration.setWidth(130);
        etDuration.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void afterTextChanged(Editable s) {
                try {
                    int val = Integer.parseInt(s.toString().trim());
                    if (val > 0) {
                        registry.setDurationMinutes(val);
                        registry.savePreferences(MainActivity.this);
                        updateSummary();
                    }
                } catch (Throwable ignored) {}
            }
        });
        durRow.addView(etDuration);

        TextView tvMenit = new TextView(this);
        tvMenit.setText("Menit");
        tvMenit.setTextColor(0xFF94A3B8);
        tvMenit.setTextSize(13);
        tvMenit.setPadding(6, 0, 12, 0);
        durRow.addView(tvMenit);

        Button btnPlus = createSmallButton("+", 0xFF334155, 0xFFFFFFFF);
        btnPlus.setOnClickListener(v -> adjustDuration(1));
        durRow.addView(btnPlus);

        configCard.addView(durRow);

        // Quick Preset Chips (1m, 5m, 10m, 15m, 30m, 60m)
        HorizontalScrollView chipScroll = new HorizontalScrollView(this);
        chipScroll.setHorizontalScrollBarEnabled(false);
        LinearLayout chipRow = new LinearLayout(this);
        chipRow.setOrientation(LinearLayout.HORIZONTAL);
        chipRow.setPadding(0, 10, 0, 6);

        int[] presets = {1, 5, 10, 15, 30, 60};
        for (int p : presets) {
            String label = p == 1 ? "1m (Test Cepat)" : p + " Menit";
            Button chip = createChipButton(label, p);
            chipRow.addView(chip);
        }
        chipScroll.addView(chipRow);
        configCard.addView(chipScroll);

        // Loop Switch
        swLoop = new Switch(this);
        swLoop.setText("Ulangi Rotasi Terus Menerus (Loop Mode)");
        swLoop.setTextColor(0xFFE2E8F0);
        swLoop.setTextSize(13);
        swLoop.setChecked(registry.isLoopMode());
        swLoop.setOnCheckedChangeListener((btn, isChecked) -> {
            registry.setLoopMode(isChecked);
            registry.savePreferences(this);
        });
        swLoop.setPadding(0, 6, 0, 6);
        configCard.addView(swLoop);

        // Summary Text
        tvSummary = new TextView(this);
        tvSummary.setTextColor(0xFF34D399);
        tvSummary.setTextSize(12);
        tvSummary.setPadding(0, 4, 0, 0);
        configCard.addView(tvSummary);

        // Tombol Cepat: Pilih Semua Terinstall & Matikan Semua
        LinearLayout quickBtns = new LinearLayout(this);
        quickBtns.setOrientation(LinearLayout.HORIZONTAL);
        quickBtns.setPadding(0, 10, 0, 0);

        Button btnSelectAll = createActionButton("✓ Aktifkan Yang Terinstall", 0xFF065F46, 0xFF6EE7B7);
        btnSelectAll.setOnClickListener(v -> {
            registry.enableAllInstalled();
            registry.savePreferences(this);
            adapter.notifyDataSetChanged();
            updateSummary();
            Toast.makeText(this, "Semua game yang terinstall diaktifkan", Toast.LENGTH_SHORT).show();
        });
        quickBtns.addView(btnSelectAll);

        Button btnDeselectAll = createActionButton("✗ Matikan Semua", 0xFF334155, 0xFFE2E8F0);
        btnDeselectAll.setOnClickListener(v -> {
            registry.disableAll();
            registry.savePreferences(this);
            adapter.notifyDataSetChanged();
            updateSummary();
        });
        quickBtns.addView(btnDeselectAll);

        configCard.addView(quickBtns);
        root.addView(configCard);

        // Search Filter
        EditText etSearch = new EditText(this);
        etSearch.setHint("🔍 Cari nama bot atau kategori...");
        etSearch.setHintTextColor(0xFF64748B);
        etSearch.setTextColor(0xFFF8FAFC);
        etSearch.setTextSize(13);
        etSearch.setPadding(20, 12, 20, 12);
        GradientDrawable searchBg = new GradientDrawable();
        searchBg.setColor(0xFF1E293B);
        searchBg.setCornerRadius(14);
        etSearch.setBackground(searchBg);
        etSearch.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int count, int after) {
                if (adapter != null) adapter.filter(s.toString());
            }
            @Override public void afterTextChanged(Editable s) {}
        });
        LinearLayout.LayoutParams searchParams = new LinearLayout.LayoutParams(-1, -2);
        searchParams.bottomMargin = 8;
        etSearch.setLayoutParams(searchParams);
        root.addView(etSearch);

        // ListView Daftar Bot
        ListView listView = new ListView(this);
        listView.setDivider(null);
        listView.setDividerHeight(0);
        LinearLayout.LayoutParams lvParams = new LinearLayout.LayoutParams(-1, 0, 1);
        listView.setLayoutParams(lvParams);

        adapter = new BotAdapter(this, registry.getAllBots(), (item, isEnabled) -> {
            registry.savePreferences(this);
            updateSummary();
        });
        listView.setAdapter(adapter);
        root.addView(listView);

        // Running Ticker (jika sedang jalan)
        tvRunningTicker = new TextView(this);
        tvRunningTicker.setTextColor(0xFF38BDF8);
        tvRunningTicker.setTextSize(12);
        tvRunningTicker.setGravity(Gravity.CENTER_HORIZONTAL);
        tvRunningTicker.setPadding(0, 6, 0, 6);
        tvRunningTicker.setVisibility(View.GONE);
        root.addView(tvRunningTicker);

        // Bottom Sticky Control Bar
        LinearLayout bottomBar = new LinearLayout(this);
        bottomBar.setOrientation(LinearLayout.HORIZONTAL);
        bottomBar.setPadding(0, 8, 0, 4);

        btnStartStop = new Button(this);
        btnStartStop.setText("▶ MULAI ROTASI");
        btnStartStop.setTextColor(0xFFFFFFFF);
        btnStartStop.setTextSize(13);
        btnStartStop.setPadding(20, 14, 20, 14);
        GradientDrawable startBg = new GradientDrawable();
        startBg.setColor(0xFF10B981);
        startBg.setCornerRadius(18);
        btnStartStop.setBackground(startBg);
        LinearLayout.LayoutParams startParams = new LinearLayout.LayoutParams(0, -2, 1);
        btnStartStop.setLayoutParams(startParams);
        btnStartStop.setOnClickListener(v -> startRotation());
        bottomBar.addView(btnStartStop);

        btnPauseResume = new Button(this);
        btnPauseResume.setText("⏸ JEDA");
        btnPauseResume.setTextColor(0xFFFFFFFF);
        btnPauseResume.setTextSize(13);
        btnPauseResume.setPadding(20, 14, 20, 14);
        GradientDrawable pauseBg = new GradientDrawable();
        pauseBg.setColor(0xFFD97706);
        pauseBg.setCornerRadius(18);
        btnPauseResume.setBackground(pauseBg);
        LinearLayout.LayoutParams pauseParams = new LinearLayout.LayoutParams(0, -2, 1);
        btnPauseResume.setLayoutParams(pauseParams);
        btnPauseResume.setVisibility(View.GONE);
        btnPauseResume.setOnClickListener(v -> rotationManager.togglePauseResume());
        bottomBar.addView(btnPauseResume);

        btnStopBot = new Button(this);
        btnStopBot.setText("⏹ HENTIKAN");
        btnStopBot.setTextColor(0xFFFECACA);
        btnStopBot.setTextSize(13);
        btnStopBot.setPadding(20, 14, 20, 14);
        GradientDrawable stopBg = new GradientDrawable();
        stopBg.setColor(0xFF7F1D1D);
        stopBg.setCornerRadius(18);
        btnStopBot.setBackground(stopBg);
        LinearLayout.LayoutParams stopParams = new LinearLayout.LayoutParams(0, -2, 1);
        stopParams.leftMargin = 8;
        btnStopBot.setLayoutParams(stopParams);
        btnStopBot.setVisibility(View.GONE);
        btnStopBot.setOnClickListener(v -> stopRotation());
        bottomBar.addView(btnStopBot);

        Button btnLogPopup = new Button(this);
        btnLogPopup.setText("📋 LOG");
        btnLogPopup.setTextColor(0xFF38BDF8);
        btnLogPopup.setTextSize(13);
        btnLogPopup.setPadding(20, 14, 20, 14);
        GradientDrawable logBg = new GradientDrawable();
        logBg.setColor(0xFF1E293B);
        logBg.setCornerRadius(18);
        btnLogPopup.setBackground(logBg);
        LinearLayout.LayoutParams logParams = new LinearLayout.LayoutParams(-2, -2);
        logParams.leftMargin = 8;
        btnLogPopup.setLayoutParams(logParams);
        btnLogPopup.setOnClickListener(v -> showLogPopup());
        bottomBar.addView(btnLogPopup);

        root.addView(bottomBar);

        setContentView(root);
        updatePermissionStatuses();
        updateSummary();
    }

    private void adjustDuration(int delta) {
        int current = registry.getDurationMinutes();
        int updated = Math.max(1, current + delta);
        registry.setDurationMinutes(updated);
        registry.savePreferences(this);
        etDuration.setText(String.valueOf(updated));
        updateSummary();
    }

    private Button createChipButton(String label, int minutes) {
        Button chip = new Button(this);
        chip.setText(label);
        chip.setTextColor(0xFF38BDF8);
        chip.setTextSize(11);
        chip.setPadding(18, 6, 18, 6);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0xFF0F2642);
        bg.setCornerRadius(14);
        chip.setBackground(bg);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, -2);
        lp.rightMargin = 8;
        chip.setLayoutParams(lp);
        chip.setOnClickListener(v -> {
            registry.setDurationMinutes(minutes);
            registry.savePreferences(this);
            etDuration.setText(String.valueOf(minutes));
            updateSummary();
        });
        return chip;
    }

    private Button createSmallButton(String text, int bgColor, int textColor) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextColor(textColor);
        b.setTextSize(14);
        b.setWidth(80);
        b.setHeight(80);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(bgColor);
        bg.setCornerRadius(16);
        b.setBackground(bg);
        return b;
    }

    private Button createActionButton(String text, int bgColor, int textColor) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextColor(textColor);
        b.setTextSize(11);
        b.setPadding(16, 6, 16, 6);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(bgColor);
        bg.setCornerRadius(14);
        b.setBackground(bg);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, -2, 1);
        lp.rightMargin = 8;
        b.setLayoutParams(lp);
        return b;
    }

    private void updatePermissionStatuses() {
        boolean accOk = GameBotAccessibilityService.isServiceRunning();
        if (accOk) {
            tvAccessibilityStatus.setText("✓ Layanan Aksesibilitas: AKTIF");
            tvAccessibilityStatus.setTextColor(0xFF34D399);
        } else {
            tvAccessibilityStatus.setText("⚠ Layanan Aksesibilitas: BELUM AKTIF (Klik untuk Aktifkan)");
            tvAccessibilityStatus.setTextColor(0xFFFBBF24);
        }

        boolean overlayOk = true;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            overlayOk = Settings.canDrawOverlays(this);
        }
        if (overlayOk) {
            tvOverlayStatus.setText("✓ Izin Pop-Up Overlay: DIIZINKAN");
            tvOverlayStatus.setTextColor(0xFF34D399);
        } else {
            tvOverlayStatus.setText("⚠ Izin Pop-Up Overlay: BELUM DIIZINKAN (Klik untuk Izinkan)");
            tvOverlayStatus.setTextColor(0xFFFBBF24);
        }
    }

    private void updateSummary() {
        List<BotItem> queue = registry.getActiveQueue();
        int duration = registry.getDurationMinutes();
        int totalMinutes = queue.size() * duration;
        double totalHours = totalMinutes / 60.0;

        int installedCount = 0;
        for (BotItem b : registry.getAllBots()) {
            if (b.isInstalled()) installedCount++;
        }

        tvSummary.setText(String.format(Locale.getDefault(),
                "Terpilih: %d bot aktif (%d terinstall di HP) • Total 1 siklus: %d menit (%.1f jam)",
                queue.size(), installedCount, totalMinutes, totalHours));
    }

    private void startRotation() {
        if (!GameBotAccessibilityService.isServiceRunning()) {
            Toast.makeText(this, "Harap aktifkan Layanan Aksesibilitas terlebih dahulu!", Toast.LENGTH_LONG).show();
            openAccessibilitySettings();
            return;
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
            Toast.makeText(this, "Harap berikan izin Menampilkan di Atas Aplikasi Lain (Overlay)!", Toast.LENGTH_LONG).show();
            openOverlaySettings();
            return;
        }

        boolean ok = rotationManager.start(this);
        if (ok) {
            updateRunningState();
            Toast.makeText(this, "Rotasi bot dimulai!", Toast.LENGTH_SHORT).show();
        } else {
            Toast.makeText(this, "Pilih minimal 1 game terinstall yang diaktifkan!", Toast.LENGTH_LONG).show();
        }
    }

    private void stopRotation() {
        rotationManager.stop();
        updateRunningState();
        Toast.makeText(this, "Bot dan floating pop-up telah dihentikan", Toast.LENGTH_SHORT).show();
    }

    private void updateRunningState() {
        if (rotationManager.isRunning()) {
            btnStartStop.setVisibility(View.GONE);
            btnPauseResume.setVisibility(View.VISIBLE);
            btnStopBot.setVisibility(View.VISIBLE);

            if (rotationManager.isPaused()) {
                btnPauseResume.setText("▶ LANJUT");
                GradientDrawable resumeBg = new GradientDrawable();
                resumeBg.setColor(0xFF059669);
                resumeBg.setCornerRadius(18);
                btnPauseResume.setBackground(resumeBg);
            } else {
                btnPauseResume.setText("⏸ JEDA");
                GradientDrawable pauseBg = new GradientDrawable();
                pauseBg.setColor(0xFFD97706);
                pauseBg.setCornerRadius(18);
                btnPauseResume.setBackground(pauseBg);
            }

            tvRunningTicker.setVisibility(View.VISIBLE);
        } else {
            btnStartStop.setVisibility(View.VISIBLE);
            btnPauseResume.setVisibility(View.GONE);
            btnStopBot.setVisibility(View.GONE);
            tvRunningTicker.setVisibility(View.GONE);
        }
    }

    private void showLogPopup() {
        LogPopupDialog dialog = new LogPopupDialog(this);
        dialog.show();
    }

    private void openAccessibilitySettings() {
        Intent intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(intent);
    }

    private void openOverlaySettings() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:" + getPackageName()));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
        }
    }

    @Override
    public void onRotationStarted(BotItem initialBot) {
        runOnUiThread(this::updateRunningState);
    }

    @Override
    public void onTick(BotItem currentBot, int remainingSeconds) {
        runOnUiThread(() -> {
            if (tvRunningTicker != null && rotationManager.isRunning()) {
                int mins = remainingSeconds / 60;
                int secs = remainingSeconds % 60;
                String name = currentBot != null ? currentBot.getName() : "Game";
                tvRunningTicker.setText(String.format(Locale.getDefault(),
                        "⚡ Sedang Berjalan: %s • Sisa Waktu: %02d:%02d", name, mins, secs));
            }
        });
    }

    @Override
    public void onBotChanged(BotItem newBot, int index, int total) {
        runOnUiThread(this::updateRunningState);
    }

    @Override
    public void onRotationStopped() {
        runOnUiThread(this::updateRunningState);
    }

    @Override
    public void onRotationPaused() {
        runOnUiThread(this::updateRunningState);
    }

    @Override
    public void onRotationResumed() {
        runOnUiThread(this::updateRunningState);
    }

    @Override
    protected void onDestroy() {
        rotationManager.removeListener(this);
        super.onDestroy();
    }
}
