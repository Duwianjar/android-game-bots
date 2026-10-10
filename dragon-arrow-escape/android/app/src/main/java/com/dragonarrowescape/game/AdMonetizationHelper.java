package com.dragonarrowescape.game;

import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.util.Log;

/**
 * Helper class untuk verifikasi dan troubleshooting monetisasi
 */
public class AdMonetizationHelper {
    private static final String TAG = "AdMonetizationHelper";
    
    /**
     * Verifikasi konfigurasi AdMob di AndroidManifest
     */
    public static boolean verifyAdMobConfiguration(Context context) {
        try {
            ApplicationInfo ai = context.getPackageManager()
                .getApplicationInfo(context.getPackageName(), PackageManager.GET_META_DATA);
            
            if (ai.metaData != null) {
                String appId = ai.metaData.getString("com.google.android.gms.ads.APPLICATION_ID");
                
                if (appId == null || appId.isEmpty()) {
                    Log.e(TAG, "❌ AdMob App ID tidak ditemukan di AndroidManifest!");
                    return false;
                }
                
                Log.d(TAG, "✅ AdMob App ID found: " + appId);
                
                // Check jika masih TEST ID
                if (appId.contains("3940256099942544")) {
                    Log.w(TAG, "⚠️ WARNING: Menggunakan TEST App ID!");
                    Log.w(TAG, "⚠️ Iklan TIDAK akan menghasilkan revenue nyata!");
                    Log.w(TAG, "⚠️ Ganti dengan Production ID dari https://admob.google.com");
                    return true; // Valid tapi test
                }
                
                Log.i(TAG, "✅ Production App ID detected");
                return true;
            }
            
            Log.e(TAG, "❌ Metadata tidak ditemukan");
            return false;
            
        } catch (PackageManager.NameNotFoundException e) {
            Log.e(TAG, "❌ Error reading manifest: " + e.getMessage());
            return false;
        }
    }
    
    /**
     * Print monetization status untuk debugging
     */
    public static void printMonetizationStatus(AdsManager adsManager) {
        if (adsManager == null) {
            Log.e(TAG, "❌ AdsManager is null!");
            return;
        }
        
        Log.d(TAG, "\n=== MONETIZATION STATUS ===");
        Log.d(TAG, "Rewarded Ad Ready: " + adsManager.isRewardedAdReady());
        Log.d(TAG, "Interstitial Ad Ready: " + adsManager.isInterstitialAdReady());
        Log.d(TAG, "Banner Visible: " + adsManager.isBannerVisible());
        Log.d(TAG, "Ad Status: " + adsManager.getAdStatus());
        Log.d(TAG, "=========================\n");
    }
    
    /**
     * Get estimated RPM ranges untuk berbagai jenis ads
     */
    public static String getEstimatedRPM() {
        return "RPM Estimates (USD):\n" +
               "• Rewarded Ads: $10-$30 per 1000 views\n" +
               "• Interstitial Ads: $3-$8 per 1000 views\n" +
               "• Banner Ads: $0.5-$2 per 1000 impressions";
    }
    
    /**
     * Hitung estimasi revenue berdasarkan stats
     */
    public static String calculateEstimatedRevenue(
        long rewardedShown, 
        long interstitialShown, 
        long bannerImpressions
    ) {
        // Conservative estimates (lower end)
        double rewardedRPM = 10.0;  // $10 per 1000
        double interstitialRPM = 3.0;  // $3 per 1000
        double bannerRPM = 0.5;  // $0.5 per 1000
        
        double rewardedRevenue = (rewardedShown / 1000.0) * rewardedRPM;
        double interstitialRevenue = (interstitialShown / 1000.0) * interstitialRPM;
        double bannerRevenue = (bannerImpressions / 1000.0) * bannerRPM;
        
        double totalRevenue = rewardedRevenue + interstitialRevenue + bannerRevenue;
        
        return String.format(
            "Estimated Revenue (Conservative):\n" +
            "• Rewarded: $%.2f (%d views)\n" +
            "• Interstitial: $%.2f (%d views)\n" +
            "• Banner: $%.2f (%d impressions)\n" +
            "• TOTAL: $%.2f",
            rewardedRevenue, rewardedShown,
            interstitialRevenue, interstitialShown,
            bannerRevenue, bannerImpressions,
            totalRevenue
        );
    }
}
