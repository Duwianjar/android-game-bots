package com.openclaw.busjam;

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
 * Jembatan input Android. Ini menggantikan "adb shell input tap" pada bot laptop.
 */
public class BotAccessibilityService extends AccessibilityService {
    private static volatile BotAccessibilityService instance;
    private static volatile String foregroundPackage = "";
    private static volatile String foregroundClass = "";
    private static volatile long foregroundUpdatedAt;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    public static final String ACTION_DISMISS_POPUP = "com.openclaw.busjam.ACTION_DISMISS_POPUP";

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
        foregroundClass = "com.busjam.parking.master.HmeActivity";
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
            // Hanya perbarui foregroundClass jika event adalah pergantian window/activity
            // atau nama class berakhiran Activity/Aty, agar tidak tertimpa class View (FrameLayout, TextView, dll)
            if (event.getEventType() == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
                    || cls.endsWith("Activity") || cls.contains("Aty")) {
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
        if (receiverRegistered) {
            try {
                unregisterReceiver(dismissReceiver);
            } catch (Throwable ignored) {
            }
            receiverRegistered = false;
        }
        mainHandler.post(this::removePopup);
        if (instance == this) {
            instance = null;
        }
        foregroundPackage = "";
        foregroundClass = "";
        foregroundUpdatedAt = 0;
        super.onDestroy();
    }

    private int dp(float dp) {
        return (int) (dp * getResources().getDisplayMetrics().density + 0.5f);
    }

    private void showPopup(String message) {
        mainHandler.post(() -> {
            try {
                if (windowManager == null) {
                    windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
                }
                if (windowManager == null) return;

                if (popupView == null) {
                    LinearLayout root = new LinearLayout(this);
                    root.setOrientation(LinearLayout.HORIZONTAL);
                    root.setGravity(Gravity.CENTER_VERTICAL);
                    root.setPadding(dp(14), dp(8), dp(14), dp(8));

                    GradientDrawable background = new GradientDrawable();
                    background.setColor(0xE6101820);
                    background.setCornerRadius(dp(16));
                    background.setStroke(dp(1), 0x33FFFFFF);
                    root.setBackground(background);

                    LinearLayout textLayout = new LinearLayout(this);
                    textLayout.setOrientation(LinearLayout.VERTICAL);
                    textLayout.setGravity(Gravity.CENTER_VERTICAL);
                    LinearLayout.LayoutParams textLp = new LinearLayout.LayoutParams(
                            0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f);
                    textLp.setMargins(0, 0, dp(10), 0);
                    textLayout.setLayoutParams(textLp);

                    TextView tvTitle = new TextView(this);
                    tvTitle.setText("BUS JAM BOT");
                    tvTitle.setTextSize(11);
                    tvTitle.setTextColor(0xFF38BDF8);
                    tvTitle.setTypeface(Typeface.DEFAULT_BOLD);
                    textLayout.addView(tvTitle);

                    tvStatusMessage = new TextView(this);
                    tvStatusMessage.setTextColor(Color.WHITE);
                    tvStatusMessage.setTextSize(12.5f);
                    tvStatusMessage.setMaxLines(2);
                    tvStatusMessage.setEllipsize(TextUtils.TruncateAt.END);
                    tvStatusMessage.setMaxWidth(dp(205));
                    textLayout.addView(tvStatusMessage);

                    root.addView(textLayout);

                    Button btnStop = new Button(this);
                    btnStop.setText("Hentikan Bot");
                    btnStop.setTextSize(12);
                    btnStop.setTextColor(Color.WHITE);
                    btnStop.setTypeface(Typeface.DEFAULT_BOLD);
                    btnStop.setAllCaps(false);
                    btnStop.setPadding(dp(12), dp(6), dp(12), dp(6));
                    btnStop.setMinWidth(0);
                    btnStop.setMinHeight(0);
                    btnStop.setMinimumWidth(0);
                    btnStop.setMinimumHeight(0);

                    GradientDrawable btnBg = new GradientDrawable();
                    btnBg.setColor(0xFFDC2626);
                    btnBg.setCornerRadius(dp(12));
                    btnStop.setBackground(btnBg);

                    LinearLayout.LayoutParams btnLp = new LinearLayout.LayoutParams(
                            LinearLayout.LayoutParams.WRAP_CONTENT,
                            LinearLayout.LayoutParams.WRAP_CONTENT
                    );
                    btnStop.setLayoutParams(btnLp);
                    btnStop.setOnClickListener(v -> stopBot());
                    root.addView(btnStop);

                    popupParams = new WindowManager.LayoutParams(
                            WindowManager.LayoutParams.WRAP_CONTENT,
                            WindowManager.LayoutParams.WRAP_CONTENT,
                            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                                    | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                            PixelFormat.TRANSLUCENT
                    );
                    popupParams.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;
                    popupParams.y = dp(55);

                    // Dukungan geser (drag) bila pengguna ingin memindahkan popup ke area lain
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
                if (display != null && display.startsWith("BUS JAM BOT\n")) {
                    display = display.substring(12);
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
            Toast.makeText(this, "Bot Bus Jam dihentikan", Toast.LENGTH_SHORT).show();
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
