package com.openclaw.gamebothub;

import android.app.Dialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public class LogPopupDialog extends Dialog implements BotLogger.LogListener, RotationManager.RotationListener {
    private final TextView tvLog;
    private final ScrollView scrollView;
    private final Button btnPlayPause;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    public LogPopupDialog(Context context) {
        super(context);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        if (getWindow() != null) {
            getWindow().setBackgroundDrawable(new ColorDrawable(Color.TRANSPARENT));
        }

        int width = (int) (context.getResources().getDisplayMetrics().widthPixels * 0.94);
        int height = (int) (context.getResources().getDisplayMetrics().heightPixels * 0.72);

        LinearLayout root = new LinearLayout(context);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28, 24, 28, 24);

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0xFF0F172A);
        bg.setCornerRadius(28);
        bg.setStroke(3, 0xFF3B82F6);
        root.setBackground(bg);

        // Header
        LinearLayout header = new LinearLayout(context);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);

        TextView title = new TextView(context);
        title.setText("📋 POP-UP LIVE LOG BOT");
        title.setTextColor(0xFF38BDF8);
        title.setTextSize(15);
        title.setLayoutParams(new LinearLayout.LayoutParams(0, -2, 1));
        header.addView(title);

        // Tombol Play / Pause di header
        btnPlayPause = createButton(context, "⏸ Jeda", 0xFFD97706, 0xFFFFFFFF);
        btnPlayPause.setOnClickListener(v -> {
            RotationManager rm = RotationManager.getInstance();
            if (rm.isRunning()) {
                rm.togglePauseResume();
            } else {
                Toast.makeText(context, "Mulai rotasi dari layar utama terlebih dahulu", Toast.LENGTH_SHORT).show();
            }
        });
        header.addView(btnPlayPause);

        // Tombol Stop di header
        Button btnStop = createButton(context, "⏹ Stop", 0xFF7F1D1D, 0xFFFECACA);
        btnStop.setOnClickListener(v -> {
            RotationManager.getInstance().stop();
            dismiss();
        });
        header.addView(btnStop);

        Button btnClose = createSmallButton(context, "✕", 0xFF334155, 0xFFFFFFFF);
        btnClose.setOnClickListener(v -> dismiss());
        header.addView(btnClose);

        root.addView(header);

        // Log Scroll View
        scrollView = new ScrollView(context);
        LinearLayout.LayoutParams svParams = new LinearLayout.LayoutParams(-1, 0, 1);
        svParams.topMargin = 16;
        svParams.bottomMargin = 16;
        scrollView.setLayoutParams(svParams);

        tvLog = new TextView(context);
        tvLog.setTextColor(0xFFE2E8F0);
        tvLog.setTextSize(11);
        tvLog.setLineSpacing(3, 1.15f);
        tvLog.setText(BotLogger.getAllLogsAsString());
        scrollView.addView(tvLog);

        root.addView(scrollView);

        // Footer buttons
        LinearLayout footer = new LinearLayout(context);
        footer.setOrientation(LinearLayout.HORIZONTAL);
        footer.setGravity(Gravity.END);

        Button btnCopy = createButton(context, "Salin Log", 0xFF1E293B, 0xFF38BDF8);
        btnCopy.setOnClickListener(v -> {
            ClipboardManager cm = (ClipboardManager) context.getSystemService(Context.CLIPBOARD_SERVICE);
            ClipData clip = ClipData.newPlainText("GameBotHub Log", BotLogger.getAllLogsAsString());
            if (cm != null) cm.setPrimaryClip(clip);
            Toast.makeText(context, "Log berhasil disalin", Toast.LENGTH_SHORT).show();
        });
        footer.addView(btnCopy);

        Button btnClear = createButton(context, "Bersihkan", 0xFF1E293B, 0xFFEF4444);
        btnClear.setOnClickListener(v -> BotLogger.clearLogs());
        footer.addView(btnClear);

        Button btnDone = createButton(context, "Tutup Pop-up", 0xFF2563EB, 0xFFFFFFFF);
        btnDone.setOnClickListener(v -> dismiss());
        footer.addView(btnDone);

        root.addView(footer);

        setContentView(root, new LinearLayout.LayoutParams(width, height));
        BotLogger.addListener(this);
        RotationManager.getInstance().addListener(this);

        updatePlayPauseButton();

        setOnDismissListener(dialog -> {
            BotLogger.removeListener(this);
            RotationManager.getInstance().removeListener(this);
        });
        scrollToBottom();
    }

    private void updatePlayPauseButton() {
        RotationManager rm = RotationManager.getInstance();
        if (!rm.isRunning()) {
            btnPlayPause.setVisibility(View.GONE);
        } else {
            btnPlayPause.setVisibility(View.VISIBLE);
            if (rm.isPaused()) {
                btnPlayPause.setText("▶ Lanjut");
                GradientDrawable bg = new GradientDrawable();
                bg.setColor(0xFF059669);
                bg.setCornerRadius(18);
                btnPlayPause.setBackground(bg);
            } else {
                btnPlayPause.setText("⏸ Jeda");
                GradientDrawable bg = new GradientDrawable();
                bg.setColor(0xFFD97706);
                bg.setCornerRadius(18);
                btnPlayPause.setBackground(bg);
            }
        }
    }

    private void scrollToBottom() {
        scrollView.post(() -> scrollView.fullScroll(View.FOCUS_DOWN));
    }

    private Button createButton(Context context, String text, int bgColor, int textColor) {
        Button b = new Button(context);
        b.setText(text);
        b.setTextColor(textColor);
        b.setTextSize(11);
        b.setPadding(18, 8, 18, 8);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(bgColor);
        bg.setCornerRadius(16);
        b.setBackground(bg);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, -2);
        lp.leftMargin = 8;
        b.setLayoutParams(lp);
        return b;
    }

    private Button createSmallButton(Context context, String text, int bgColor, int textColor) {
        Button b = new Button(context);
        b.setText(text);
        b.setTextColor(textColor);
        b.setTextSize(13);
        b.setPadding(14, 4, 14, 4);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(bgColor);
        bg.setCornerRadius(14);
        b.setBackground(bg);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, -2);
        lp.leftMargin = 8;
        b.setLayoutParams(lp);
        return b;
    }

    @Override
    public void onNewLog(String logLine) {
        mainHandler.post(() -> {
            if (tvLog != null) {
                tvLog.append(logLine + "\n");
                scrollToBottom();
            }
        });
    }

    @Override
    public void onLogsCleared() {
        mainHandler.post(() -> {
            if (tvLog != null) {
                tvLog.setText("");
            }
        });
    }

    @Override
    public void onRotationStarted(BotItem initialBot) {
        mainHandler.post(this::updatePlayPauseButton);
    }

    @Override
    public void onTick(BotItem currentBot, int remainingSeconds) {}

    @Override
    public void onBotChanged(BotItem newBot, int index, int total) {}

    @Override
    public void onRotationStopped() {
        mainHandler.post(this::updatePlayPauseButton);
    }

    @Override
    public void onRotationPaused() {
        mainHandler.post(this::updatePlayPauseButton);
    }

    @Override
    public void onRotationResumed() {
        mainHandler.post(this::updatePlayPauseButton);
    }
}
