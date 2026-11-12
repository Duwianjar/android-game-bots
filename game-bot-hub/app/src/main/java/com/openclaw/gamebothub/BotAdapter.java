package com.openclaw.gamebothub;

import android.content.Context;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.LinearLayout;
import android.widget.Switch;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.List;

public class BotAdapter extends BaseAdapter {
    public interface OnBotToggleListener {
        void onBotToggled(BotItem item, boolean isEnabled);
    }

    private final Context context;
    private final List<BotItem> originalList;
    private final List<BotItem> displayList;
    private final OnBotToggleListener toggleListener;

    public BotAdapter(Context context, List<BotItem> items, OnBotToggleListener listener) {
        this.context = context;
        this.originalList = items;
        this.displayList = new ArrayList<>(items);
        this.toggleListener = listener;
    }

    public void filter(String query) {
        displayList.clear();
        if (query == null || query.trim().isEmpty()) {
            displayList.addAll(originalList);
        } else {
            String lower = query.toLowerCase().trim();
            for (BotItem b : originalList) {
                if (b.getName().toLowerCase().contains(lower) ||
                    b.getPackageName().toLowerCase().contains(lower) ||
                    b.getCategory().toLowerCase().contains(lower)) {
                    displayList.add(b);
                }
            }
        }
        notifyDataSetChanged();
    }

    @Override
    public int getCount() {
        return displayList.size();
    }

    @Override
    public BotItem getItem(int position) {
        return displayList.get(position);
    }

    @Override
    public long getItemId(int position) {
        return position;
    }

    @Override
    public View getView(int position, View convertView, ViewGroup parent) {
        BotItem bot = getItem(position);

        LinearLayout card;
        ViewHolder holder;

        if (convertView == null) {
            card = new LinearLayout(context);
            card.setOrientation(LinearLayout.HORIZONTAL);
            card.setGravity(Gravity.CENTER_VERTICAL);
            card.setPadding(28, 24, 28, 24);

            GradientDrawable cardBg = new GradientDrawable();
            cardBg.setColor(0xFF1E293B);
            cardBg.setCornerRadius(20);
            card.setBackground(cardBg);

            LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(-1, -2);
            cardParams.bottomMargin = 16;
            card.setLayoutParams(cardParams);

            // Left info layout
            LinearLayout infoLayout = new LinearLayout(context);
            infoLayout.setOrientation(LinearLayout.VERTICAL);
            infoLayout.setLayoutParams(new LinearLayout.LayoutParams(0, -2, 1));

            TextView tvName = new TextView(context);
            tvName.setTextColor(0xFFF8FAFC);
            tvName.setTextSize(15);
            infoLayout.addView(tvName);

            TextView tvPackage = new TextView(context);
            tvPackage.setTextColor(0xFF94A3B8);
            tvPackage.setTextSize(11);
            tvPackage.setPadding(0, 4, 0, 8);
            infoLayout.addView(tvPackage);

            // Badges row
            LinearLayout badgesRow = new LinearLayout(context);
            badgesRow.setOrientation(LinearLayout.HORIZONTAL);

            TextView tvInstallBadge = new TextView(context);
            tvInstallBadge.setTextSize(10);
            tvInstallBadge.setPadding(14, 4, 14, 4);
            badgesRow.addView(tvInstallBadge);

            TextView tvCategoryBadge = new TextView(context);
            tvCategoryBadge.setTextSize(10);
            tvCategoryBadge.setPadding(14, 4, 14, 4);
            LinearLayout.LayoutParams catParams = new LinearLayout.LayoutParams(-2, -2);
            catParams.leftMargin = 10;
            tvCategoryBadge.setLayoutParams(catParams);
            badgesRow.addView(tvCategoryBadge);

            infoLayout.addView(badgesRow);
            card.addView(infoLayout);

            // Switch on the right
            Switch sw = new Switch(context);
            sw.setPadding(16, 8, 8, 8);
            card.addView(sw);

            holder = new ViewHolder(tvName, tvPackage, tvInstallBadge, tvCategoryBadge, sw);
            card.setTag(holder);
        } else {
            card = (LinearLayout) convertView;
            holder = (ViewHolder) card.getTag();
        }

        holder.tvName.setText(bot.getName());
        holder.tvPackage.setText(bot.getPackageName());

        // Category Badge
        holder.tvCategory.setText(bot.getCategory() + " • " + bot.getGameplayType().getDisplay());
        holder.tvCategory.setTextColor(0xFF38BDF8);
        GradientDrawable catBg = new GradientDrawable();
        catBg.setColor(0xFF0C4A6E);
        catBg.setCornerRadius(12);
        holder.tvCategory.setBackground(catBg);

        // Install Badge
        if (bot.isInstalled()) {
            String ver = bot.getVersionName().isEmpty() ? "" : " (v" + bot.getVersionName() + ")";
            holder.tvInstall.setText("✓ Terinstall" + ver);
            holder.tvInstall.setTextColor(0xFF34D399);
            GradientDrawable instBg = new GradientDrawable();
            instBg.setColor(0xFF064E3B);
            instBg.setCornerRadius(12);
            holder.tvInstall.setBackground(instBg);
        } else {
            holder.tvInstall.setText("✗ Belum Terinstall");
            holder.tvInstall.setTextColor(0xFF94A3B8);
            GradientDrawable instBg = new GradientDrawable();
            instBg.setColor(0xFF334155);
            instBg.setCornerRadius(12);
            holder.tvInstall.setBackground(instBg);
        }

        // Switch
        holder.swEnabled.setOnCheckedChangeListener(null);
        holder.swEnabled.setChecked(bot.isEnabled());
        holder.swEnabled.setOnCheckedChangeListener((buttonView, isChecked) -> {
            bot.setEnabled(isChecked);
            if (toggleListener != null) {
                toggleListener.onBotToggled(bot, isChecked);
            }
        });

        return card;
    }

    private static class ViewHolder {
        final TextView tvName;
        final TextView tvPackage;
        final TextView tvInstall;
        final TextView tvCategory;
        final Switch swEnabled;

        ViewHolder(TextView tvName, TextView tvPackage, TextView tvInstall, TextView tvCategory, Switch swEnabled) {
            this.tvName = tvName;
            this.tvPackage = tvPackage;
            this.tvInstall = tvInstall;
            this.tvCategory = tvCategory;
            this.swEnabled = swEnabled;
        }
    }
}
