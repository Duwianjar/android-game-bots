package com.openclaw.busjam;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.graphics.Color;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.Gravity;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.widget.TextView;

/**
 * Jembatan input Android. Ini menggantikan "adb shell input tap" pada bot laptop.
 */
public class BotAccessibilityService extends AccessibilityService {
    private static volatile BotAccessibilityService instance;
    private static volatile String foregroundPackage = "";
    private static volatile String foregroundClass = "";
    private static volatile long foregroundUpdatedAt;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private WindowManager windowManager;
    private TextView logPopup;

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
        foregroundClass = "com.busjam.parking.master.HmeActivity";
        foregroundUpdatedAt = SystemClock.elapsedRealtime();
    }

    public static void showBotLog(String message) {
        BotAccessibilityService service = instance;
        if (service != null) service.showPopup(message);
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event.getPackageName() != null) {
            foregroundPackage = event.getPackageName().toString();
        }
        if (event.getClassName() != null) {
            foregroundClass = event.getClassName().toString();
        }
        foregroundUpdatedAt = SystemClock.elapsedRealtime();
    }

    @Override
    public void onInterrupt() {
    }

    @Override
    public void onDestroy() {
        mainHandler.post(this::removePopup);
        if (instance == this) {
            instance = null;
        }
        foregroundPackage = "";
        foregroundClass = "";
        foregroundUpdatedAt = 0;
        super.onDestroy();
    }

    private void showPopup(String message) {
        mainHandler.post(() -> {
            try {
                if (logPopup == null) {
                    logPopup = new TextView(this);
                    logPopup.setTextColor(Color.WHITE);
                    logPopup.setTextSize(14);
                    logPopup.setGravity(Gravity.CENTER_VERTICAL);
                    logPopup.setPadding(28, 16, 28, 16);
                    GradientDrawable background = new GradientDrawable();
                    background.setColor(0xD9101820);
                    background.setCornerRadius(28);
                    logPopup.setBackground(background);

                    WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                            WindowManager.LayoutParams.MATCH_PARENT,
                            WindowManager.LayoutParams.WRAP_CONTENT,
                            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                                    | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                                    | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                            PixelFormat.TRANSLUCENT
                    );
                    params.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;
                    params.y = 115;
                    windowManager.addView(logPopup, params);
                }
                logPopup.setText("BUS JAM BOT\n" + message);
            } catch (Throwable ignored) {
            }
        });
    }

    private void removePopup() {
        if (logPopup == null) return;
        try {
            windowManager.removeView(logPopup);
        } catch (Throwable ignored) {
        }
        logPopup = null;
    }

    public boolean tap(float x, float y) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            return false;
        }
        Path path = new Path();
        path.moveTo(x, y);
        GestureDescription.StrokeDescription stroke =
                new GestureDescription.StrokeDescription(path, 0, 55);
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
