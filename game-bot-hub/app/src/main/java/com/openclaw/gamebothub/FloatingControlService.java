package com.openclaw.gamebothub;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.provider.Settings;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.Locale;

public class FloatingControlService extends Service implements RotationManager.RotationListener, BotLogger.LogListener {
    private static final String CHANNEL_ID = "game_bot_hub_channel";
    private static final int NOTIF_ID = 9182;

    private WindowManager windowManager;
    private View floatingBarView;
    private View miniBubbleView;
    private View logPopupView;

    private WindowManager.LayoutParams barParams;
    private WindowManager.LayoutParams miniParams;
    private WindowManager.LayoutParams popupParams;

    private TextView tvStatusBot;
    private TextView tvTimer;
    private Button btnBarPlayPause;
    private Button btnPopupPlayPause;
    private TextView tvLogContent;
    private ScrollView svLogScroll;

    private boolean isBarVisible = true;
    private boolean isPopupVisible = false;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        startForeground(NOTIF_ID, buildNotification("Bot Rotator Aktif", "Menyiapkan layanan..."));

        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);

        RotationManager.getInstance().addListener(this);
        BotLogger.addListener(this);

        if (canDrawOverlay()) {
            buildFloatingBar();
            buildMiniBubble();
            buildLogPopup();
        }
    }

    private boolean canDrawOverlay() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            return Settings.canDrawOverlays(this);
        }
        return true;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Game Bot Hub Service",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Notifikasi kontrol rotasi bot");
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(channel);
        }
    }

    private Notification buildNotification(String title, String text) {
        Intent intent = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(this, 0, intent,
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0);

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }
        return builder.setContentTitle(title)
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_media_play)
                .setContentIntent(pi)
                .setOngoing(true)
                .build();
    }

    private int getOverlayType() {
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE;
    }

    private void buildFloatingBar() {
        barParams = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                getOverlayType(),
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT
        );
        barParams.gravity = Gravity.TOP | Gravity.START;
        barParams.x = 16;
        barParams.y = 160;

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.HORIZONTAL);
        layout.setGravity(Gravity.CENTER_VERTICAL);
        layout.setPadding(16, 10, 16, 10);

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0xF00F172A);
        bg.setCornerRadius(24);
        bg.setStroke(2, 0xFF38BDF8);
        layout.setBackground(bg);

        // Status & Bot Name
        tvStatusBot = new TextView(this);
        tvStatusBot.setTextColor(0xFF38BDF8);
        tvStatusBot.setTextSize(12);
        tvStatusBot.setText("🎮 Memuat...");
        layout.addView(tvStatusBot);

        // Timer
        tvTimer = new TextView(this);
        tvTimer.setTextColor(0xFF34D399);
        tvTimer.setTextSize(12);
        tvTimer.setPadding(12, 0, 12, 0);
        tvTimer.setText("⏱ 00:00");
        layout.addView(tvTimer);

        // Tombol Play / Pause
        btnBarPlayPause = createButton("⏸ Jeda", 0xFFD97706, 0xFFFFFFFF);
        btnBarPlayPause.setOnClickListener(v -> RotationManager.getInstance().togglePauseResume());
        layout.addView(btnBarPlayPause);

        // Tombol Next
        Button btnNext = createButton("⏭ Next", 0xFF1E293B, 0xFFF1F5F9);
        btnNext.setOnClickListener(v -> RotationManager.getInstance().nextGame(this));
        layout.addView(btnNext);

        // Tombol Pop-up Log
        Button btnLog = createButton("📋 Log", 0xFF1E293B, 0xFF38BDF8);
        btnLog.setOnClickListener(v -> toggleLogPopup());
        layout.addView(btnLog);

        // Tombol Stop
        Button btnStop = createButton("⏹ Stop", 0xFF7F1D1D, 0xFFFECACA);
        btnStop.setOnClickListener(v -> RotationManager.getInstance().stop());
        layout.addView(btnStop);

        // Tombol Sembunyikan Bar (Minimize ke mini bubble)
        Button btnHide = createButton("🙈 Sembunyi", 0xFF334155, 0xFF94A3B8);
        btnHide.setOnClickListener(v -> minimizeToBubble());
        layout.addView(btnHide);

        setupDragListener(layout, barParams);

        floatingBarView = layout;
        try {
            windowManager.addView(floatingBarView, barParams);
            isBarVisible = true;
        } catch (Throwable ignored) {
        }
    }

    private void buildMiniBubble() {
        miniParams = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                getOverlayType(),
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT
        );
        miniParams.gravity = Gravity.TOP | Gravity.START;
        miniParams.x = 16;
        miniParams.y = 160;

        TextView bubble = new TextView(this);
        bubble.setText("🎮 HUB");
        bubble.setTextColor(0xFFFFFFFF);
        bubble.setTextSize(11);
        bubble.setPadding(18, 12, 18, 12);
        bubble.setGravity(Gravity.CENTER);

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0xEE2563EB);
        bg.setCornerRadius(28);
        bg.setStroke(2, 0xFF60A5FA);
        bubble.setBackground(bg);

        bubble.setOnClickListener(v -> restoreFromBubble());
        setupDragListener(bubble, miniParams);

        miniBubbleView = bubble;
    }

    private void minimizeToBubble() {
        if (floatingBarView != null && isBarVisible) {
            try {
                windowManager.removeView(floatingBarView);
            } catch (Throwable ignored) {}
            isBarVisible = false;
        }
        if (miniBubbleView != null) {
            try {
                miniParams.x = barParams.x;
                miniParams.y = barParams.y;
                windowManager.addView(miniBubbleView, miniParams);
            } catch (Throwable ignored) {}
        }
        Toast.makeText(this, "Floating bar disembunyikan. Ketuk 🎮 HUB untuk membuka.", Toast.LENGTH_SHORT).show();
    }

    private void restoreFromBubble() {
        if (miniBubbleView != null) {
            try {
                windowManager.removeView(miniBubbleView);
            } catch (Throwable ignored) {}
        }
        if (floatingBarView != null && !isBarVisible) {
            try {
                barParams.x = miniParams.x;
                barParams.y = miniParams.y;
                windowManager.addView(floatingBarView, barParams);
                isBarVisible = true;
            } catch (Throwable ignored) {}
        }
    }

    private void buildLogPopup() {
        popupParams = new WindowManager.LayoutParams(
                (int) (getResources().getDisplayMetrics().widthPixels * 0.94),
                (int) (getResources().getDisplayMetrics().heightPixels * 0.52),
                getOverlayType(),
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT
        );
        popupParams.gravity = Gravity.CENTER;

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(22, 18, 22, 18);

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0xF80A0F1D);
        bg.setCornerRadius(28);
        bg.setStroke(3, 0xFF10B981);
        root.setBackground(bg);

        // Header Pop-up
        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);

        TextView tvTitle = new TextView(this);
        tvTitle.setText("📋 POP-UP LIVE LOG BOT");
        tvTitle.setTextColor(0xFF10B981);
        tvTitle.setTextSize(14);
        tvTitle.setLayoutParams(new LinearLayout.LayoutParams(0, -2, 1));
        header.addView(tvTitle);

        // Tombol Play / Pause di Pop-up
        btnPopupPlayPause = createButton("⏸ Jeda", 0xFFD97706, 0xFFFFFFFF);
        btnPopupPlayPause.setOnClickListener(v -> RotationManager.getInstance().togglePauseResume());
        header.addView(btnPopupPlayPause);

        // Tombol Stop di Pop-up
        Button btnPopStop = createButton("⏹ Stop", 0xFF7F1D1D, 0xFFFECACA);
        btnPopStop.setOnClickListener(v -> {
            hideLogPopup();
            RotationManager.getInstance().stop();
        });
        header.addView(btnPopStop);

        // Tombol Sembunyikan Pop-up
        Button btnClose = createButton("✕ Sembunyi", 0xFF334155, 0xFFFFFFFF);
        btnClose.setOnClickListener(v -> hideLogPopup());
        header.addView(btnClose);

        root.addView(header);

        // Scrollview Log
        svLogScroll = new ScrollView(this);
        LinearLayout.LayoutParams svParams = new LinearLayout.LayoutParams(-1, 0, 1);
        svParams.topMargin = 14;
        svParams.bottomMargin = 14;
        svLogScroll.setLayoutParams(svParams);

        tvLogContent = new TextView(this);
        tvLogContent.setTextColor(0xFFE2E8F0);
        tvLogContent.setTextSize(11);
        tvLogContent.setLineSpacing(3, 1.1f);
        tvLogContent.setText(BotLogger.getAllLogsAsString());
        svLogScroll.addView(tvLogContent);

        root.addView(svLogScroll);

        // Footer buttons
        LinearLayout footer = new LinearLayout(this);
        footer.setOrientation(LinearLayout.HORIZONTAL);
        footer.setGravity(Gravity.END);

        Button btnCopy = createButton("Salin Semua", 0xFF1E293B, 0xFF38BDF8);
        btnCopy.setOnClickListener(v -> {
            ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            ClipData clip = ClipData.newPlainText("Bot Log", BotLogger.getAllLogsAsString());
            if (cm != null) cm.setPrimaryClip(clip);
            Toast.makeText(this, "Log disalin ke clipboard", Toast.LENGTH_SHORT).show();
        });
        footer.addView(btnCopy);

        Button btnClear = createButton("Bersihkan", 0xFF1E293B, 0xFFEF4444);
        btnClear.setOnClickListener(v -> BotLogger.clearLogs());
        footer.addView(btnClear);

        Button btnDone = createButton("Tutup Pop-up", 0xFF2563EB, 0xFFFFFFFF);
        btnDone.setOnClickListener(v -> hideLogPopup());
        footer.addView(btnDone);

        root.addView(footer);

        logPopupView = root;
    }

    private void toggleLogPopup() {
        if (isPopupVisible) {
            hideLogPopup();
        } else {
            showLogPopup();
        }
    }

    public void showLogPopup() {
        if (logPopupView == null || isPopupVisible) return;
        try {
            updateLogView();
            updatePauseButtonLabels(RotationManager.getInstance().isPaused());
            windowManager.addView(logPopupView, popupParams);
            isPopupVisible = true;
            scrollToBottom();
        } catch (Throwable ignored) {
        }
    }

    public void hideLogPopup() {
        if (logPopupView == null || !isPopupVisible) return;
        try {
            windowManager.removeView(logPopupView);
            isPopupVisible = false;
        } catch (Throwable ignored) {
        }
    }

    private void updateLogView() {
        if (tvLogContent != null) {
            tvLogContent.setText(BotLogger.getAllLogsAsString());
        }
    }

    private void scrollToBottom() {
        if (svLogScroll != null) {
            svLogScroll.post(() -> svLogScroll.fullScroll(View.FOCUS_DOWN));
        }
    }

    private Button createButton(String text, int bgColor, int textColor) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextColor(textColor);
        b.setTextSize(11);
        b.setPadding(16, 6, 16, 6);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(bgColor);
        bg.setCornerRadius(16);
        b.setBackground(bg);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, -2);
        lp.leftMargin = 8;
        b.setLayoutParams(lp);
        return b;
    }

    private void setupDragListener(View view, WindowManager.LayoutParams params) {
        view.setOnTouchListener(new View.OnTouchListener() {
            private int initialX, initialY;
            private float initialTouchX, initialTouchY;

            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        initialX = params.x;
                        initialY = params.y;
                        initialTouchX = event.getRawX();
                        initialTouchY = event.getRawY();
                        return false;
                    case MotionEvent.ACTION_MOVE:
                        params.x = initialX + (int) (event.getRawX() - initialTouchX);
                        params.y = initialY + (int) (event.getRawY() - initialTouchY);
                        try {
                            windowManager.updateViewLayout(view, params);
                        } catch (Throwable ignored) {}
                        return true;
                }
                return false;
            }
        });
    }

    @Override
    public void onRotationStarted(BotItem initialBot) {
        updateBarInfo(initialBot, RotationManager.getInstance().getRemainingSeconds());
        updatePauseButtonLabels(false);
    }

    @Override
    public void onTick(BotItem currentBot, int remainingSeconds) {
        updateBarInfo(currentBot, remainingSeconds);
    }

    @Override
    public void onBotChanged(BotItem newBot, int index, int total) {
        updateBarInfo(newBot, RotationManager.getInstance().getRemainingSeconds());
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm != null) {
            nm.notify(NOTIF_ID, buildNotification("Bot: " + (newBot != null ? newBot.getName() : ""), "Rotasi " + (index + 1) + "/" + total));
        }
    }

    @Override
    public void onRotationStopped() {
        stopSelf();
    }

    @Override
    public void onRotationPaused() {
        updatePauseButtonLabels(true);
    }

    @Override
    public void onRotationResumed() {
        updatePauseButtonLabels(false);
    }

    private void updatePauseButtonLabels(boolean paused) {
        mainHandler.post(() -> {
            String text = paused ? "▶ Lanjut" : "⏸ Jeda";
            int color = paused ? 0xFF059669 : 0xFFD97706;

            if (btnBarPlayPause != null) {
                btnBarPlayPause.setText(text);
                GradientDrawable bg = new GradientDrawable();
                bg.setColor(color);
                bg.setCornerRadius(16);
                btnBarPlayPause.setBackground(bg);
            }
            if (btnPopupPlayPause != null) {
                btnPopupPlayPause.setText(text);
                GradientDrawable bg = new GradientDrawable();
                bg.setColor(color);
                bg.setCornerRadius(16);
                btnPopupPlayPause.setBackground(bg);
            }
        });
    }

    private void updateBarInfo(BotItem bot, int remainingSeconds) {
        mainHandler.post(() -> {
            if (tvStatusBot != null) {
                String name = bot != null ? bot.getName() : "Standby";
                if (name.length() > 14) name = name.substring(0, 14) + "..";
                tvStatusBot.setText("🎮 " + name);
            }
            if (tvTimer != null) {
                int mins = remainingSeconds / 60;
                int secs = remainingSeconds % 60;
                tvTimer.setText(String.format(Locale.getDefault(), "⏱ %02d:%02d", mins, secs));
            }
        });
    }

    @Override
    public void onNewLog(String logLine) {
        if (isPopupVisible && tvLogContent != null) {
            tvLogContent.append(logLine + "\n");
            scrollToBottom();
        }
    }

    @Override
    public void onLogsCleared() {
        if (tvLogContent != null) {
            tvLogContent.setText("");
        }
    }

    @Override
    public void onDestroy() {
        RotationManager.getInstance().removeListener(this);
        BotLogger.removeListener(this);
        hideLogPopup();

        if (miniBubbleView != null && windowManager != null) {
            try {
                windowManager.removeView(miniBubbleView);
            } catch (Throwable ignored) {}
        }
        if (floatingBarView != null && windowManager != null && isBarVisible) {
            try {
                windowManager.removeView(floatingBarView);
            } catch (Throwable ignored) {}
        }
        super.onDestroy();
    }
}
