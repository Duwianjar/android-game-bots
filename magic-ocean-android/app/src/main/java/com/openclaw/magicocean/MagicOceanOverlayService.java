package com.openclaw.magicocean;

import android.app.Service;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.IBinder;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;

public class MagicOceanOverlayService extends Service {
    private WindowManager mWindowManager;
    private Button mFloatingButton;
    private WindowManager.LayoutParams mParams;

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        mWindowManager = (WindowManager) getSystemService(WINDOW_SERVICE);

        mFloatingButton = new Button(this);
        updateButtonAppearance(MagicOceanAccessibilityService.isBotActive());

        int layoutType = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE;

        mParams = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                layoutType,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT
        );

        mParams.gravity = Gravity.TOP | Gravity.START;
        mParams.x = 20;
        mParams.y = 350;

        // Sentuhan & Dragging
        mFloatingButton.setOnTouchListener(new View.OnTouchListener() {
            private int initialX, initialY;
            private float initialTouchX, initialTouchY;
            private boolean isClick;

            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        initialX = mParams.x;
                        initialY = mParams.y;
                        initialTouchX = event.getRawX();
                        initialTouchY = event.getRawY();
                        isClick = true;
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        int dx = (int) (event.getRawX() - initialTouchX);
                        int dy = (int) (event.getRawY() - initialTouchY);
                        if (Math.abs(dx) > 15 || Math.abs(dy) > 15) {
                            isClick = false;
                        }
                        mParams.x = initialX + dx;
                        mParams.y = initialY + dy;
                        mWindowManager.updateViewLayout(mFloatingButton, mParams);
                        return true;
                    case MotionEvent.ACTION_UP:
                        if (isClick) {
                            boolean newState = !MagicOceanAccessibilityService.isBotActive();
                            MagicOceanAccessibilityService.setBotActive(newState);
                            updateButtonAppearance(newState);
                        }
                        return true;
                }
                return false;
            }
        });

        try {
            mWindowManager.addView(mFloatingButton, mParams);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void updateButtonAppearance(boolean active) {
        if (mFloatingButton == null) return;
        GradientDrawable shape = new GradientDrawable();
        shape.setCornerRadius(30f);
        if (active) {
            shape.setColor(Color.parseColor("#D32F2F")); // Merah stop
            mFloatingButton.setText("⏹ STOP BOT");
        } else {
            shape.setColor(Color.parseColor("#0288D1")); // Biru start
            mFloatingButton.setText("▶ START BOT");
        }
        mFloatingButton.setTextColor(Color.WHITE);
        mFloatingButton.setPadding(25, 15, 25, 15);
        mFloatingButton.setTextSize(13f);
        mFloatingButton.setBackground(shape);
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (mFloatingButton != null && mWindowManager != null) {
            mWindowManager.removeView(mFloatingButton);
        }
    }
}
