package com.openclaw.colorpowerpop;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Color;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Jembatan input Android untuk Color Power Pop Bot.
 */
public class BotAccessibilityService extends AccessibilityService {
    private static volatile BotAccessibilityService instance;
    private static volatile String foregroundPackage = "";
    private static volatile String foregroundClass = "";
    private static volatile long foregroundUpdatedAt;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    public static final String ACTION_DISMISS_POPUP = "com.openclaw.colorpowerpop.ACTION_DISMISS_POPUP";

    private WindowManager windowManager;
    private View popupView;
    private TextView tvStatusMessage;
    private WindowManager.LayoutParams popupParams;
    private boolean receiverRegistered = false;

    private final BroadcastReceiver dismissReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            removePopup();
        }
    };

    public static BotAccessibilityService getInstance() {
        return instance;
    }

    public static String getForegroundPackage() {
        return foregroundPackage;
    }

    public static String getForegroundClass() {
        return foregroundClass;
    }

    public static long getForegroundUpdatedAt() {
        return foregroundUpdatedAt;
    }

    public static void markGameForeground() {
        foregroundPackage = BotForegroundService.GAME_PACKAGE;
        foregroundClass = "";
        foregroundUpdatedAt = SystemClock.elapsedRealtime();
    }

    public static void showBotLog(String message) {
        BotAccessibilityService service = instance;
        if (service != null) service.showPopup(message);
    }

    public static void removeBotLog() {
        BotAccessibilityService service = instance;
        if (service != null) service.removePopup();
    }

    public static void stopBotAndRemovePopup() {
        BotAccessibilityService service = instance;
        if (service != null) {
            service.stopBot();
        }
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        try {
            IntentFilter filter = new IntentFilter(ACTION_DISMISS_POPUP);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                registerReceiver(dismissReceiver, filter, Context.RECEIVER_EXPORTED);
            } else {
                registerReceiver(dismissReceiver, filter);
            }
            receiverRegistered = true;
        } catch (Throwable ignored) {
        }
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event.getPackageName() != null) {
            foregroundPackage = event.getPackageName().toString();
        }
        if (event.getClassName() != null) {
            String cls = event.getClassName().toString();
            if (!cls.startsWith("android.view.") && !cls.startsWith("android.widget.")) {
                foregroundClass = cls;
            }
        }
        foregroundUpdatedAt = SystemClock.elapsedRealtime();
    }

    @Override
    public void onInterrupt() {
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (receiverRegistered) {
            try {
                unregisterReceiver(dismissReceiver);
            } catch (Throwable ignored) {
            }
            receiverRegistered = false;
        }
        removePopup();
        if (instance == this) {
            instance = null;
        }
    }

    private int dp(float value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }

    public void showPopup(String message) {
        mainHandler.post(() -> {
            try {
                if (windowManager == null) {
                    windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
                }
                if (windowManager == null) return;

                if (popupView == null) {
                    LinearLayout root = new LinearLayout(this);
                    root.setOrientation(LinearLayout.VERTICAL);
                    root.setPadding(dp(12), dp(10), dp(12), dp(10));

                    GradientDrawable bg = new GradientDrawable();
                    bg.setColor(Color.parseColor("#F0151B26"));
                    bg.setCornerRadius(dp(12));
                    bg.setStroke(dp(1.5f), Color.parseColor("#E91E63"));
                    root.setBackground(bg);

                    LinearLayout header = new LinearLayout(this);
                    header.setOrientation(LinearLayout.HORIZONTAL);
                    header.setGravity(Gravity.CENTER_VERTICAL);

                    TextView tvTitle = new TextView(this);
                    tvTitle.setText("COLOR POWER POP BOT");
                    tvTitle.setTextColor(Color.parseColor("#FF4081"));
                    tvTitle.setTextSize(12.5f);
                    tvTitle.setTypeface(Typeface.DEFAULT_BOLD);
                    LinearLayout.LayoutParams titleLp = new LinearLayout.LayoutParams(0, -2, 1f);
                    header.addView(tvTitle, titleLp);

                    Button btnStop = new Button(this);
                    btnStop.setText("Stop");
                    btnStop.setTextSize(11f);
                    btnStop.setTextColor(Color.WHITE);
                    GradientDrawable stopBg = new GradientDrawable();
                    stopBg.setColor(Color.parseColor("#D32F2F"));
                    stopBg.setCornerRadius(dp(6));
                    btnStop.setBackground(stopBg);
                    btnStop.setPadding(dp(10), dp(2), dp(10), dp(2));
                    btnStop.setOnClickListener(v -> stopBotAndRemovePopup());
                    LinearLayout.LayoutParams stopLp = new LinearLayout.LayoutParams(-2, dp(28));
                    header.addView(btnStop, stopLp);

                    root.addView(header, new LinearLayout.LayoutParams(-1, -2));

                    tvStatusMessage = new TextView(this);
                    tvStatusMessage.setTextColor(Color.parseColor("#ECEFF1"));
                    tvStatusMessage.setTextSize(11f);
                    tvStatusMessage.setLineSpacing(dp(2), 1.05f);
                    tvStatusMessage.setEllipsize(TextUtils.TruncateAt.END);
                    tvStatusMessage.setMaxLines(6);
                    LinearLayout.LayoutParams msgLp = new LinearLayout.LayoutParams(-1, -2);
                    msgLp.topMargin = dp(6);
                    root.addView(tvStatusMessage, msgLp);

                    int layoutType = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                            ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                            : WindowManager.LayoutParams.TYPE_PHONE;

                    popupParams = new WindowManager.LayoutParams(
                            dp(280),
                            WindowManager.LayoutParams.WRAP_CONTENT,
                            layoutType,
                            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                                    | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                            PixelFormat.TRANSLUCENT
                    );
                    popupParams.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL;
                    popupParams.y = dp(55);

                    root.setOnTouchListener(new View.OnTouchListener() {
                        private int initialX;
                        private int initialY;
                        private float initialTouchX;
                        private float initialTouchY;

                        @Override
                        public boolean onTouch(View v, MotionEvent event) {
                            if (popupParams == null || windowManager == null || popupView == null) {
                                return false;
                            }
                            switch (event.getAction()) {
                                case MotionEvent.ACTION_DOWN:
                                    initialX = popupParams.x;
                                    initialY = popupParams.y;
                                    initialTouchX = event.getRawX();
                                    initialTouchY = event.getRawY();
                                    return true;
                                case MotionEvent.ACTION_MOVE:
                                    int dx = (int) (event.getRawX() - initialTouchX);
                                    int dy = (int) (event.getRawY() - initialTouchY);
                                    popupParams.x = initialX + dx;
                                    popupParams.y = initialY - dy;
                                    try {
                                        windowManager.updateViewLayout(popupView, popupParams);
                                    } catch (Throwable ignored) {
                                    }
                                    return true;
                            }
                            return false;
                        }
                    });

                    windowManager.addView(root, popupParams);
                    popupView = root;
                }

                String display = message;
                if (display != null && display.startsWith("COLOR POWER POP BOT\n")) {
                    display = display.substring(20);
                }
                if (tvStatusMessage != null) {
                    tvStatusMessage.setText(display);
                }
            } catch (Throwable ignored) {
            }
        });
    }

    public void stopBot() {
        try {
            Intent stopIntent = new Intent(this, BotForegroundService.class);
            stopIntent.setAction(BotForegroundService.ACTION_STOP);
            startService(stopIntent);
            stopService(stopIntent);
        } catch (Throwable ignored) {
        }
        removePopup();
        try {
            Toast.makeText(this, "Bot Color Power Pop dihentikan", Toast.LENGTH_SHORT).show();
        } catch (Throwable ignored) {
        }
    }

    public void removePopup() {
        mainHandler.post(() -> {
            if (popupView == null) return;
            try {
                if (windowManager != null) {
                    windowManager.removeView(popupView);
                }
            } catch (Throwable ignored) {
            }
            popupView = null;
            tvStatusMessage = null;
            popupParams = null;
        });
    }

    public boolean tap(float x, float y) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            return false;
        }
        Path path = new Path();
        path.moveTo(x, y);
        GestureDescription.StrokeDescription stroke =
                new GestureDescription.StrokeDescription(path, 0, 50);
        return dispatchGesture(
                new GestureDescription.Builder().addStroke(stroke).build(),
                null,
                null
        );
    }

    public boolean pressBack() {
        return performGlobalAction(GLOBAL_ACTION_BACK);
    }

    public boolean pressHome() {
        return performGlobalAction(GLOBAL_ACTION_HOME);
    }
}
