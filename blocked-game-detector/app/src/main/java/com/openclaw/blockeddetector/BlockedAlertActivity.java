package com.openclaw.blockeddetector;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

public class BlockedAlertActivity extends Activity {
    private String targetPackage = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);

        // Pastikan muncul di layar bahkan jika layar terkunci/redup
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
        } else {
            getWindow().addFlags(
                    WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED |
                    WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON |
                    WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
            );
        }

        BlockedItem item = (BlockedItem) getIntent().getSerializableExtra("blocked_item");
        targetPackage = getIntent().getStringExtra("actual_package");
        String actualLabel = getIntent().getStringExtra("actual_label");

        if (item == null && targetPackage != null && !targetPackage.isEmpty()) {
            item = BlockedRegistry.checkPackage(getPackageManager(), targetPackage);
        }

        if (item == null && (targetPackage == null || targetPackage.isEmpty())) {
            finish();
            return;
        }

        String gameName = item != null ? item.name : (actualLabel != null ? actualLabel : targetPackage);
        String devName = item != null ? item.developer : "Tidak diketahui";
        String notes = item != null ? item.notes : "Aplikasi ini terdaftar di daftar Blocked.";

        // Root ScrollView
        ScrollView scrollView = new ScrollView(this);
        scrollView.setBackgroundColor(Color.parseColor("#121212"));
        scrollView.setFillViewport(true);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(40, 60, 40, 60);
        layout.setGravity(Gravity.CENTER_HORIZONTAL);

        // Header Merah Peringatan
        GradientDrawable headerBg = new GradientDrawable();
        headerBg.setColor(Color.parseColor("#B71C1C"));
        headerBg.setCornerRadius(24);

        LinearLayout headerLayout = new LinearLayout(this);
        headerLayout.setOrientation(LinearLayout.VERTICAL);
        headerLayout.setBackground(headerBg);
        headerLayout.setPadding(40, 40, 40, 40);
        headerLayout.setGravity(Gravity.CENTER);

        TextView iconText = new TextView(this);
        iconText.setText("⚠️");
        iconText.setTextSize(48);
        iconText.setGravity(Gravity.CENTER);

        TextView titleText = new TextView(this);
        titleText.setText("PERINGATAN APLIKASI BLOCKED!");
        titleText.setTextColor(Color.WHITE);
        titleText.setTextSize(20);
        titleText.setTypeface(null, Typeface.BOLD);
        titleText.setGravity(Gravity.CENTER);

        TextView subTitleText = new TextView(this);
        subTitleText.setText("Aplikasi tidak cair / terblokir terdeteksi di HP Anda!");
        subTitleText.setTextColor(Color.parseColor("#FFCDD2"));
        subTitleText.setTextSize(14);
        subTitleText.setGravity(Gravity.CENTER);
        subTitleText.setPadding(0, 8, 0, 0);

        headerLayout.addView(iconText);
        headerLayout.addView(titleText);
        headerLayout.addView(subTitleText);
        layout.addView(headerLayout);

        // Info Card
        GradientDrawable cardBg = new GradientDrawable();
        cardBg.setColor(Color.parseColor("#1E1E1E"));
        cardBg.setCornerRadius(20);
        cardBg.setStroke(2, Color.parseColor("#333333"));

        LinearLayout cardLayout = new LinearLayout(this);
        cardLayout.setOrientation(LinearLayout.VERTICAL);
        cardLayout.setBackground(cardBg);
        cardLayout.setPadding(36, 36, 36, 36);
        LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        cardParams.setMargins(0, 40, 0, 40);
        cardLayout.setLayoutParams(cardParams);

        addInfoRow(cardLayout, "Nama Game:", gameName, Color.parseColor("#FF5252"), true);
        addInfoRow(cardLayout, "Package Name:", targetPackage, Color.parseColor("#BBDEFB"), false);
        addInfoRow(cardLayout, "Developer:", devName, Color.parseColor("#E0E0E0"), false);
        addInfoRow(cardLayout, "Keterangan Masalah:", notes, Color.parseColor("#FFE082"), false);

        layout.addView(cardLayout);

        // Action Buttons
        GradientDrawable btnUninstallBg = new GradientDrawable();
        btnUninstallBg.setColor(Color.parseColor("#D32F2F"));
        btnUninstallBg.setCornerRadius(16);

        Button btnUninstall = new Button(this);
        btnUninstall.setText("🗑️ HAPUS / UNINSTALL SEKARANG");
        btnUninstall.setTextColor(Color.WHITE);
        btnUninstall.setTextSize(16);
        btnUninstall.setTypeface(null, Typeface.BOLD);
        btnUninstall.setBackground(btnUninstallBg);
        btnUninstall.setPadding(30, 36, 30, 36);
        LinearLayout.LayoutParams btnParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        btnParams.setMargins(0, 10, 0, 20);
        btnUninstall.setLayoutParams(btnParams);

        btnUninstall.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (targetPackage != null && !targetPackage.isEmpty()) {
                    Intent uninstallIntent = new Intent(Intent.ACTION_DELETE);
                    uninstallIntent.setData(Uri.parse("package:" + targetPackage));
                    startActivity(uninstallIntent);
                    finish();
                }
            }
        });
        layout.addView(btnUninstall);

        GradientDrawable btnCloseBg = new GradientDrawable();
        btnCloseBg.setColor(Color.parseColor("#424242"));
        btnCloseBg.setCornerRadius(16);

        Button btnClose = new Button(this);
        btnClose.setText("Tutup Peringatan");
        btnClose.setTextColor(Color.parseColor("#B0BEC5"));
        btnClose.setTextSize(14);
        btnClose.setBackground(btnCloseBg);
        btnClose.setPadding(20, 28, 20, 28);
        LinearLayout.LayoutParams btnCloseParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        btnClose.setLayoutParams(btnCloseParams);

        btnClose.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                finish();
            }
        });
        layout.addView(btnClose);

        scrollView.addView(layout);
        setContentView(scrollView);
    }

    private void addInfoRow(LinearLayout parent, String label, String value, int valueColor, boolean isBold) {
        TextView labelTv = new TextView(this);
        labelTv.setText(label);
        labelTv.setTextColor(Color.parseColor("#888888"));
        labelTv.setTextSize(12);
        labelTv.setPadding(0, 10, 0, 2);

        TextView valueTv = new TextView(this);
        valueTv.setText(value);
        valueTv.setTextColor(valueColor);
        valueTv.setTextSize(15);
        if (isBold) valueTv.setTypeface(null, Typeface.BOLD);
        valueTv.setPadding(0, 0, 0, 12);

        parent.addView(labelTv);
        parent.addView(valueTv);
    }
}
