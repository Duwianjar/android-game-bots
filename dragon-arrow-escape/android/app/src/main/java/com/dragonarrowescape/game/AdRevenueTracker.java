package com.dragonarrowescape.game;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.Log;
import org.json.JSONObject;
import org.json.JSONArray;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * Tracker untuk monitoring performa iklan
 * Membantu optimasi monetisasi dengan data analytics
 */
public class AdRevenueTracker {
    private static final String TAG = "AdRevenueTracker";
    private static final String PREFS_NAME = "AdRevenuePrefs";
    
    private SharedPreferences prefs;
    private Context context;
    
    // Counters untuk session saat ini
    private int sessionRewardedShown = 0;
    private int sessionRewardedCompleted = 0;
    private int sessionInterstitialShown = 0;
    private int sessionInterstitialCompleted = 0;
    private int sessionBannerImpressions = 0;
    
    public AdRevenueTracker(Context context) {
        this.context = context;
        this.prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        
        // Log session start
        logSessionStart();
    }
    
    // ========== SESSION TRACKING ==========
    
    private void logSessionStart() {
        long sessionCount = prefs.getLong("total_sessions", 0) + 1;
        prefs.edit().putLong("total_sessions", sessionCount).apply();
        
        String today = getTodayDate();
        prefs.edit().putString("last_session_date", today).apply();
        
        Log.d(TAG, "📊 Session #" + sessionCount + " started");
    }
    
    // ========== REWARDED ADS TRACKING ==========
    
    public void onRewardedAdShown() {
        sessionRewardedShown++;
        incrementCounter("rewarded_shown_total");
        incrementCounter("rewarded_shown_today");
        
        Log.d(TAG, "💎 Rewarded ad shown (session: " + sessionRewardedShown + ")");
    }
    
    public void onRewardedAdCompleted() {
        sessionRewardedCompleted++;
        incrementCounter("rewarded_completed_total");
        incrementCounter("rewarded_completed_today");
        
        // Calculate completion rate
        float completionRate = sessionRewardedShown > 0 ? 
            (float) sessionRewardedCompleted / sessionRewardedShown * 100 : 0;
        
        Log.d(TAG, "✅ Rewarded ad completed (rate: " + 
            String.format(Locale.US, "%.1f%%", completionRate) + ")");
    }
    
    public void onRewardedAdFailed(String reason) {
        incrementCounter("rewarded_failed_total");
        Log.w(TAG, "❌ Rewarded ad failed: " + reason);
    }
    
    // ========== INTERSTITIAL ADS TRACKING ==========
    
    public void onInterstitialAdShown() {
        sessionInterstitialShown++;
        incrementCounter("interstitial_shown_total");
        incrementCounter("interstitial_shown_today");
        
        Log.d(TAG, "📺 Interstitial ad shown (session: " + sessionInterstitialShown + ")");
    }
    
    public void onInterstitialAdCompleted() {
        sessionInterstitialCompleted++;
        incrementCounter("interstitial_completed_total");
        incrementCounter("interstitial_completed_today");
        
        Log.d(TAG, "✅ Interstitial ad completed");
    }
    
    public void onInterstitialAdFailed(String reason) {
        incrementCounter("interstitial_failed_total");
        Log.w(TAG, "❌ Interstitial ad failed: " + reason);
    }
    
    public void onInterstitialSkippedCooldown() {
        incrementCounter("interstitial_skipped_cooldown");
        Log.d(TAG, "⏭️ Interstitial skipped (cooldown)");
    }
    
    // ========== BANNER ADS TRACKING ==========
    
    public void onBannerAdLoaded() {
        incrementCounter("banner_loaded_total");
        Log.d(TAG, "✅ Banner ad loaded");
    }
    
    public void onBannerAdImpression() {
        sessionBannerImpressions++;
        incrementCounter("banner_impressions_total");
        incrementCounter("banner_impressions_today");
        
        Log.d(TAG, "💰 Banner impression (session: " + sessionBannerImpressions + ")");
    }
    
    public void onBannerAdClicked() {
        incrementCounter("banner_clicks_total");
        
        // Calculate CTR
        long impressions = prefs.getLong("banner_impressions_total", 0);
        long clicks = prefs.getLong("banner_clicks_total", 0);
        float ctr = impressions > 0 ? (float) clicks / impressions * 100 : 0;
        
        Log.d(TAG, "👆 Banner clicked (CTR: " + 
            String.format(Locale.US, "%.2f%%", ctr) + ")");
    }
    
    public void onBannerAdFailed(String reason) {
        incrementCounter("banner_failed_total");
        Log.w(TAG, "❌ Banner ad failed: " + reason);
    }
    
    // ========== UTILITY METHODS ==========
    
    private void incrementCounter(String key) {
        long current = prefs.getLong(key, 0);
        prefs.edit().putLong(key, current + 1).apply();
    }
    
    private String getTodayDate() {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        return sdf.format(new Date());
    }
    
    /**
     * Reset daily counters (panggil setiap hari baru)
     */
    public void resetDailyCounters() {
        String today = getTodayDate();
        String lastDate = prefs.getString("last_session_date", "");
        
        if (!today.equals(lastDate)) {
            Log.d(TAG, "📅 New day detected, resetting daily counters");
            
            prefs.edit()
                .putLong("rewarded_shown_today", 0)
                .putLong("rewarded_completed_today", 0)
                .putLong("interstitial_shown_today", 0)
                .putLong("interstitial_completed_today", 0)
                .putLong("banner_impressions_today", 0)
                .putString("last_session_date", today)
                .apply();
        }
    }
    
    /**
     * Get comprehensive ad performance stats
     */
    public String getPerformanceReport() {
        long rewardedTotal = prefs.getLong("rewarded_shown_total", 0);
        long rewardedCompleted = prefs.getLong("rewarded_completed_total", 0);
        long interstitialTotal = prefs.getLong("interstitial_shown_total", 0);
        long interstitialCompleted = prefs.getLong("interstitial_completed_total", 0);
        long bannerImpressions = prefs.getLong("banner_impressions_total", 0);
        long bannerClicks = prefs.getLong("banner_clicks_total", 0);
        long sessions = prefs.getLong("total_sessions", 0);
        
        float rewardedRate = rewardedTotal > 0 ? 
            (float) rewardedCompleted / rewardedTotal * 100 : 0;
        float interstitialRate = interstitialTotal > 0 ? 
            (float) interstitialCompleted / interstitialTotal * 100 : 0;
        float bannerCTR = bannerImpressions > 0 ? 
            (float) bannerClicks / bannerImpressions * 100 : 0;
        
        StringBuilder report = new StringBuilder();
        report.append("=== AD PERFORMANCE REPORT ===\n");
        report.append(String.format(Locale.US, "Total Sessions: %d\n", sessions));
        report.append(String.format(Locale.US, "\nRewarded Ads:\n"));
        report.append(String.format(Locale.US, "  Shown: %d\n", rewardedTotal));
        report.append(String.format(Locale.US, "  Completed: %d (%.1f%%)\n", 
            rewardedCompleted, rewardedRate));
        report.append(String.format(Locale.US, "\nInterstitial Ads:\n"));
        report.append(String.format(Locale.US, "  Shown: %d\n", interstitialTotal));
        report.append(String.format(Locale.US, "  Completed: %d (%.1f%%)\n", 
            interstitialCompleted, interstitialRate));
        report.append(String.format(Locale.US, "\nBanner Ads:\n"));
        report.append(String.format(Locale.US, "  Impressions: %d\n", bannerImpressions));
        report.append(String.format(Locale.US, "  Clicks: %d (CTR: %.2f%%)\n", 
            bannerClicks, bannerCTR));
        report.append("============================");
        
        return report.toString();
    }
    
    /**
     * Get stats sebagai JSON untuk analytics
     */
    public JSONObject getStatsAsJSON() {
        try {
            JSONObject stats = new JSONObject();
            
            // Session stats
            stats.put("total_sessions", prefs.getLong("total_sessions", 0));
            stats.put("last_session_date", prefs.getString("last_session_date", ""));
            
            // Rewarded ads
            JSONObject rewarded = new JSONObject();
            rewarded.put("shown_total", prefs.getLong("rewarded_shown_total", 0));
            rewarded.put("completed_total", prefs.getLong("rewarded_completed_total", 0));
            rewarded.put("failed_total", prefs.getLong("rewarded_failed_total", 0));
            rewarded.put("shown_today", prefs.getLong("rewarded_shown_today", 0));
            rewarded.put("completed_today", prefs.getLong("rewarded_completed_today", 0));
            stats.put("rewarded", rewarded);
            
            // Interstitial ads
            JSONObject interstitial = new JSONObject();
            interstitial.put("shown_total", prefs.getLong("interstitial_shown_total", 0));
            interstitial.put("completed_total", prefs.getLong("interstitial_completed_total", 0));
            interstitial.put("failed_total", prefs.getLong("interstitial_failed_total", 0));
            interstitial.put("skipped_cooldown", prefs.getLong("interstitial_skipped_cooldown", 0));
            interstitial.put("shown_today", prefs.getLong("interstitial_shown_today", 0));
            interstitial.put("completed_today", prefs.getLong("interstitial_completed_today", 0));
            stats.put("interstitial", interstitial);
            
            // Banner ads
            JSONObject banner = new JSONObject();
            banner.put("loaded_total", prefs.getLong("banner_loaded_total", 0));
            banner.put("impressions_total", prefs.getLong("banner_impressions_total", 0));
            banner.put("clicks_total", prefs.getLong("banner_clicks_total", 0));
            banner.put("failed_total", prefs.getLong("banner_failed_total", 0));
            banner.put("impressions_today", prefs.getLong("banner_impressions_today", 0));
            stats.put("banner", banner);
            
            // Current session
            JSONObject session = new JSONObject();
            session.put("rewarded_shown", sessionRewardedShown);
            session.put("rewarded_completed", sessionRewardedCompleted);
            session.put("interstitial_shown", sessionInterstitialShown);
            session.put("interstitial_completed", sessionInterstitialCompleted);
            session.put("banner_impressions", sessionBannerImpressions);
            stats.put("current_session", session);
            
            return stats;
            
        } catch (Exception e) {
            Log.e(TAG, "Error creating stats JSON: " + e.getMessage());
            return new JSONObject();
        }
    }
    
    /**
     * Print performance report ke logcat
     */
    public void printReport() {
        Log.i(TAG, "\n" + getPerformanceReport());
    }
    
    /**
     * Reset semua stats (untuk testing)
     */
    public void resetAllStats() {
        prefs.edit().clear().apply();
        sessionRewardedShown = 0;
        sessionRewardedCompleted = 0;
        sessionInterstitialShown = 0;
        sessionInterstitialCompleted = 0;
        sessionBannerImpressions = 0;
        Log.w(TAG, "⚠️ All stats reset!");
    }
}
