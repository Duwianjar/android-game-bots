package com.openclaw.blockeddetector;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MainActivity extends Activity {
    private LinearLayout listContainer;
    private TextView summaryTv;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Jalankan background service
        Intent serviceIntent = new Intent(this, WatchdogService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }

        NotificationHelper.ensureChannel(this);

        ScrollView scrollView = new ScrollView(this);
        scrollView.setBackgroundColor(Color.parseColor("#121212"));
        scrollView.setFillViewport(true);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(36, 48, 36, 48);

        // Header Shield
        GradientDrawable headerBg = new GradientDrawable();
        headerBg.setColor(Color.parseColor("#1B5E20"));
        headerBg.setCornerRadius(24);

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.VERTICAL);
        header.setBackground(headerBg);
        header.setPadding(36, 36, 36, 36);
        header.setGravity(Gravity.CENTER);

        TextView title = new TextView(this);
        title.setText("🛡️ OPENCLAW BLOCKED DETECTOR");
        title.setTextColor(Color.WHITE);
        title.setTextSize(18);
        title.setTypeface(null, Typeface.BOLD);
        title.setGravity(Gravity.CENTER);

        TextView subTitle = new TextView(this);
        subTitle.setText("Status: Perlindungan Aktif di Latar Belakang\nMemantau 21 Game Terblokir / Tidak Cair");
        subTitle.setTextColor(Color.parseColor("#C8E6C9"));
        subTitle.setTextSize(13);
        subTitle.setGravity(Gravity.CENTER);
        subTitle.setPadding(0, 10, 0, 0);

        header.addView(title);
        header.addView(subTitle);
        root.addView(header);

        // Tombol Scan Sekarang
        GradientDrawable btnScanBg = new GradientDrawable();
        btnScanBg.setColor(Color.parseColor("#1976D2"));
        btnScanBg.setCornerRadius(16);

        Button btnScan = new Button(this);
        btnScan.setText("🔍 PINDAI HP SEKARANG");
        btnScan.setTextColor(Color.WHITE);
        btnScan.setTextSize(15);
        btnScan.setTypeface(null, Typeface.BOLD);
        btnScan.setBackground(btnScanBg);
        btnScan.setPadding(20, 28, 20, 28);
        LinearLayout.LayoutParams btnParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        btnParams.setMargins(0, 28, 0, 16);
        btnScan.setLayoutParams(btnParams);

        btnScan.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                refreshScan();
            }
        });
        root.addView(btnScan);

        // Summary Text
        summaryTv = new TextView(this);
        summaryTv.setTextColor(Color.parseColor("#E0E0E0"));
        summaryTv.setTextSize(14);
        summaryTv.setTypeface(null, Typeface.BOLD);
        summaryTv.setPadding(0, 8, 0, 16);
        root.addView(summaryTv);

        // Container daftar game
        listContainer = new LinearLayout(this);
        listContainer.setOrientation(LinearLayout.VERTICAL);
        root.addView(listContainer);

        scrollView.addView(root);
        setContentView(scrollView);

        refreshScan();
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshScan();
    }

    private void refreshScan() {
        listContainer.removeAllViews();
        List<BlockedRegistry.DetectedApp> detected = BlockedRegistry.scanInstalled(this);
        Map<Integer, BlockedRegistry.DetectedApp> detectedMap = new HashMap<>();
        for (BlockedRegistry.DetectedApp d : detected) {
            detectedMap.put(d.item.id, d);
        }

        if (detected.isEmpty()) {
            summaryTv.setText("✅ HP Bersih: 0 game blocked ditemukan dari " + BlockedRegistry.ITEMS.size() + " game.");
            summaryTv.setTextColor(Color.parseColor("#81C784"));
        } else {
            summaryTv.setText("⚠️ PERINGATAN: " + detected.size() + " game blocked terpasang di HP!");
            summaryTv.setTextColor(Color.parseColor("#FF5252"));
        }

        for (final BlockedItem item : BlockedRegistry.ITEMS) {
            boolean isInstalled = detectedMap.containsKey(item.id);
            final BlockedRegistry.DetectedApp app = detectedMap.get(item.id);

            GradientDrawable itemBg = new GradientDrawable();
            itemBg.setColor(isInstalled ? Color.parseColor("#2E1010") : Color.parseColor("#1A1A1A"));
            itemBg.setCornerRadius(16);
            itemBg.setStroke(isInstalled ? 3 : 1, isInstalled ? Color.parseColor("#D32F2F") : Color.parseColor("#2A2A2A"));

            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.VERTICAL);
            row.setBackground(itemBg);
            row.setPadding(28, 24, 28, 24);
            LinearLayout.LayoutParams rowParams = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            rowParams.setMargins(0, 0, 0, 16);
            row.setLayoutParams(rowParams);

            // Baris atas: Nomor & Nama Game + Badge Status
            LinearLayout topRow = new LinearLayout(this);
            topRow.setOrientation(LinearLayout.HORIZONTAL);
            topRow.setGravity(Gravity.CENTER_VERTICAL);

            TextView nameTv = new TextView(this);
            nameTv.setText(item.id + ". " + item.name);
            nameTv.setTextColor(isInstalled ? Color.parseColor("#FF5252") : Color.WHITE);
            nameTv.setTextSize(15);
            nameTv.setTypeface(null, Typeface.BOLD);
            LinearLayout.LayoutParams nameParams = new LinearLayout.LayoutParams(
                    0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f);
            nameTv.setLayoutParams(nameParams);
            topRow.addView(nameTv);

            TextView badgeTv = new TextView(this);
            badgeTv.setText(isInstalled ? "TERPASANG!" : "Aman");
            badgeTv.setTextColor(isInstalled ? Color.WHITE : Color.parseColor("#81C784"));
            badgeTv.setTextSize(11);
            badgeTv.setTypeface(null, Typeface.BOLD);
            badgeTv.setPadding(14, 6, 14, 6);

            GradientDrawable badgeBg = new GradientDrawable();
            badgeBg.setColor(isInstalled ? Color.parseColor("#C62828") : Color.parseColor("#1B5E20"));
            badgeBg.setCornerRadius(8);
            badgeTv.setBackground(badgeBg);
            topRow.addView(badgeTv);

            row.addView(topRow);

            // Package Name
            TextView pkgTv = new TextView(this);
            pkgTv.setText("Package: " + (!item.packageName.isEmpty() ? item.packageName : "(keyword match)"));
            pkgTv.setTextColor(Color.parseColor("#78909C"));
            pkgTv.setTextSize(12);
            pkgTv.setPadding(0, 6, 0, 2);
            row.addView(pkgTv);

            // Dev & Catatan
            TextView notesTv = new TextView(this);
            notesTv.setText("Alasan: " + item.notes);
            notesTv.setTextColor(Color.parseColor("#B0BEC5"));
            notesTv.setTextSize(11);
            row.addView(notesTv);

            // Jika terpasang, tambahkan tombol Hapus
            if (isInstalled && app != null) {
                GradientDrawable delBtnBg = new GradientDrawable();
                delBtnBg.setColor(Color.parseColor("#D32F2F"));
                delBtnBg.setCornerRadius(10);

                Button delBtn = new Button(this);
                delBtn.setText("🗑️ HAPUS SEKARANG");
                delBtn.setTextColor(Color.WHITE);
                delBtn.setTextSize(12);
                delBtn.setTypeface(null, Typeface.BOLD);
                delBtn.setBackground(delBtnBg);
                delBtn.setPadding(20, 14, 20, 14);
                LinearLayout.LayoutParams delParams = new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                delParams.setMargins(0, 12, 0, 0);
                delBtn.setLayoutParams(delParams);

                delBtn.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        Intent delIntent = new Intent(Intent.ACTION_DELETE);
                        delIntent.setData(Uri.parse("package:" + app.actualPackage));
                        startActivity(delIntent);
                    }
                });
                row.addView(delBtn);
            }

            listContainer.addView(row);
        }
    }
}
