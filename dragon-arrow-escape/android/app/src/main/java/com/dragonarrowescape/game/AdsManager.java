package com.dragonarrowescape.game;

import android.content.Context;
import android.util.Log;
import android.app.Activity;
import android.widget.RelativeLayout;

import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.rewarded.RewardedAd;
import com.google.android.gms.ads.rewarded.RewardedAdLoadCallback;
import com.google.android.gms.ads.OnUserEarnedRewardListener;
import com.google.android.gms.ads.FullScreenContentCallback;
import com.google.android.gms.ads.AdError;
import com.google.android.gms.ads.interstitial.InterstitialAd;
import com.google.android.gms.ads.interstitial.InterstitialAdLoadCallback;
import com.google.android.gms.ads.AdView;
import com.google.android.gms.ads.AdSize;
import com.google.android.gms.ads.AdListener;

/**
 * Manager untuk mengelola semua jenis iklan di dalam game
 * Mendukung: Rewarded Ads, Interstitial Ads, dan Banner Ads
 * 
 * MONETIZATION STRATEGY:
 * 1. Rewarded Ads (RPM tertinggi $10-$30) - user triggered untuk rewards
 * 2. Interstitial Ads (RPM sedang $3-$8) - setiap 2-3 level atau 3-5 menit
 * 3. Banner Ads (RPM rendah $0.5-$2) - always on di menu
 * 
 * PENTING: Ganti semua AD UNIT IDs dengan ID asli dari AdMob untuk production
 */
public class AdsManager {
    private static final String TAG = "AdsManager";
    
    // ========== PRODUCTION AD UNIT IDs ==========
    // ⚠️ WAJIB GANTI DENGAN IDs PRODUCTION DARI ADMOB! ⚠️
    // TEST IDs di bawah TIDAK menghasilkan uang nyata!
    // Panduan lengkap: baca PRODUCTION_SETUP.md
    
    // Rewarded Ad - untuk bonus coins, continue game, unlock items
    // RPM: $10-$30, Best revenue per view
    private static final String REWARDED_AD_UNIT_ID = "ca-app-pub-3940256099942544/5224354917"; // ⚠️ TEST ID
    
    // Interstitial Ad - untuk transisi level, menu utama
    // RPM: $3-$8, Auto cooldown 3 menit
    private static final String INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712"; // ⚠️ TEST ID
    
    // Banner Ad - untuk menu, leaderboard, shop
    // RPM: $0.5-$2, Low per view tapi cumulative high
    private static final String BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/6300978111"; // ⚠️ TEST ID
    
    // PRODUCTION IDs (ganti TEST IDs di atas dengan ini):
    // 1. Buat akun AdMob: https://admob.google.com
    // 2. Daftarkan app: Dragon Arrow Escape
    // 3. Buat 3 Ad Units (Rewarded, Interstitial, Banner)
    // 4. Copy Ad Unit IDs ke sini
    // Format: "ca-app-pub-XXXXXXXXXXXXXXXX/1234567890"
    // ============================================
    
    private Context context;
    private MainActivity mainActivity;
    private AdRevenueTracker revenueTracker;
    
    // Rewarded Ad
    private RewardedAd mRewardedAd;
    private boolean isRewardedAdLoading = false;
    private OnUserEarnedRewardListener rewardListener;
    
    // Interstitial Ad
    private InterstitialAd mInterstitialAd;
    private boolean isInterstitialAdLoading = false;
    private long lastInterstitialShowTime = 0;
    private static final long INTERSTITIAL_COOLDOWN = 180000; // 3 menit
    
    // Banner Ad
    private AdView mBannerAdView;
    private boolean isBannerVisible = false;

    public AdsManager(Context context) {
        this.context = context;
        this.revenueTracker = new AdRevenueTracker(context);
        
        // Reset daily counters jika hari baru
        revenueTracker.resetDailyCounters();
        
        // Log current ad unit IDs untuk verifikasi
        logAdConfiguration();
        
        Log.d(TAG, "✅ AdsManager initialized with revenue tracking");
    }
    
    /**
     * Log konfigurasi ads untuk debugging/verifikasi
     */
    private void logAdConfiguration() {
        Log.d(TAG, "=== AD CONFIGURATION ===");
        Log.d(TAG, "Rewarded ID: " + REWARDED_AD_UNIT_ID);
        Log.d(TAG, "Interstitial ID: " + INTERSTITIAL_AD_UNIT_ID);
        Log.d(TAG, "Banner ID: " + BANNER_AD_UNIT_ID);
        
        // Warn jika masih pakai TEST IDs
        if (REWARDED_AD_UNIT_ID.contains("3940256099942544")) {
            Log.w(TAG, "⚠️⚠️⚠️ WARNING: USING TEST AD IDs - NO REAL REVENUE! ⚠️⚠️⚠️");
            Log.w(TAG, "Ganti dengan Production IDs dari AdMob untuk menghasilkan uang!");
        } else {
            Log.i(TAG, "✅ Production Ad IDs detected");
        }
        Log.d(TAG, "=====================");
    }

    // ========== REWARDED ADS ==========
    
    /**
     * Load rewarded ad dari AdMob
     * Panggil setelah game dimulai dan setelah ads ditampilkan
     * Auto-retry on failure untuk maksimalkan availability
     */
    public void loadRewardedAd() {
        if (isRewardedAdLoading || mRewardedAd != null) {
            Log.d(TAG, "Rewarded ad already loading or loaded");
            return;
        }

        isRewardedAdLoading = true;
        AdRequest adRequest = new AdRequest.Builder().build();

        RewardedAd.load(context, REWARDED_AD_UNIT_ID,
            adRequest, new RewardedAdLoadCallback() {
            @Override
            public void onAdFailedToLoad(LoadAdError loadAdError) {
                Log.d(TAG, "Rewarded ad failed to load: " + loadAdError.getMessage());
                mRewardedAd = null;
                isRewardedAdLoading = false;
                
                // Track failure
                revenueTracker.onRewardedAdFailed(loadAdError.getMessage());
                
                // Retry setelah 30 detik
                new android.os.Handler().postDelayed(() -> {
                    loadRewardedAd();
                }, 30000);
            }

            @Override
            public void onAdLoaded(RewardedAd rewardedAd) {
                mRewardedAd = rewardedAd;
                isRewardedAdLoading = false;
                Log.d(TAG, "✅ Rewarded Ad Loaded Successfully");
                
                // Set fullscreen callback
                mRewardedAd.setFullScreenContentCallback(new FullScreenContentCallback() {
                    @Override
                    public void onAdDismissedFullScreenContent() {
                        Log.d(TAG, "Rewarded ad dismissed");
                        mRewardedAd = null;
                        
                        // Track completion
                        revenueTracker.onRewardedAdCompleted();
                        
                        // Load iklan berikutnya
                        loadRewardedAd();
                    }

                    @Override
                    public void onAdFailedToShowFullScreenContent(AdError adError) {
                        Log.e(TAG, "Rewarded ad failed to show: " + adError.getMessage());
                        mRewardedAd = null;
                        loadRewardedAd();
                    }

                    @Override
                    public void onAdShowedFullScreenContent() {
                        Log.d(TAG, "Rewarded ad showed fullscreen");
                        
                        // Track impression
                        revenueTracker.onRewardedAdShown();
                    }
                });
            }
        });
    }

    /**
     * Tampilkan rewarded ad kepada user
     * Callback ke JavaScript setelah user mendapat reward
     */
    public void showRewardedAd(MainActivity activity) {
        if (mRewardedAd != null) {
            this.mainActivity = activity;
            
            // Set reward listener
            this.rewardListener = new OnUserEarnedRewardListener() {
                @Override
                public void onUserEarnedReward(com.google.android.gms.ads.rewarded.RewardItem reward) {
                    int amount = reward.getAmount();
                    String type = reward.getType();
                    Log.d(TAG, "💎 User earned reward: " + type + " x" + amount);
                    
                    // Notify game tentang reward yang diperoleh - call both callbacks for compatibility
                    if (mainActivity != null && mainActivity.webView != null) {
                        String javascript = String.format(
                            "if (window.gameRewardCallback) window.gameRewardCallback('%s', %d);" +
                            "if (window.onAdRewardEarned) window.onAdRewardEarned('%s', %d);",
                            type, amount, type, amount
                        );
                        mainActivity.runOnUiThread(() -> {
                            mainActivity.webView.evaluateJavascript(javascript, null);
                            Log.d(TAG, "✅ Reward callback executed: " + javascript);
                        });
                    }
                }
            };
            
            mRewardedAd.show(activity, this.rewardListener);
        } else {
            Log.d(TAG, "Rewarded ad not ready. Loading...");
            loadRewardedAd();
        }
    }

    /**
     * Cek apakah rewarded ad sudah siap ditampilkan
     */
    public boolean isRewardedAdReady() {
        boolean ready = mRewardedAd != null;
        if (!ready && !isRewardedAdLoading) {
            // Auto-load jika belum ada dan tidak sedang loading
            loadRewardedAd();
        }
        return ready;
    }

    // ========== INTERSTITIAL ADS ==========
    
    /**
     * Load interstitial ad
     * Panggil di awal game dan setelah ditampilkan
     */
    public void loadInterstitialAd() {
        if (isInterstitialAdLoading || mInterstitialAd != null) {
            Log.d(TAG, "Interstitial ad already loading or loaded");
            return;
        }

        isInterstitialAdLoading = true;
        AdRequest adRequest = new AdRequest.Builder().build();

        InterstitialAd.load(context, INTERSTITIAL_AD_UNIT_ID, adRequest,
            new InterstitialAdLoadCallback() {
            @Override
            public void onAdLoaded(InterstitialAd interstitialAd) {
                mInterstitialAd = interstitialAd;
                isInterstitialAdLoading = false;
                Log.d(TAG, "✅ Interstitial Ad Loaded Successfully");

                mInterstitialAd.setFullScreenContentCallback(new FullScreenContentCallback() {
                    @Override
                    public void onAdDismissedFullScreenContent() {
                        Log.d(TAG, "Interstitial ad dismissed");
                        mInterstitialAd = null;
                        lastInterstitialShowTime = System.currentTimeMillis();
                        
                        // Track completion
                        revenueTracker.onInterstitialAdCompleted();
                        
                        // Notify game bahwa ads selesai
                        notifyGameAdClosed();
                        
                        // Load iklan berikutnya
                        loadInterstitialAd();
                    }

                    @Override
                    public void onAdFailedToShowFullScreenContent(AdError adError) {
                        Log.e(TAG, "Interstitial ad failed to show: " + adError.getMessage());
                        mInterstitialAd = null;
                        notifyGameAdClosed();
                        loadInterstitialAd();
                    }

                    @Override
                    public void onAdShowedFullScreenContent() {
                        Log.d(TAG, "Interstitial ad showed fullscreen");
                        
                        // Track impression
                        revenueTracker.onInterstitialAdShown();
                    }
                });
            }

            @Override
            public void onAdFailedToLoad(LoadAdError loadAdError) {
                Log.d(TAG, "Interstitial ad failed to load: " + loadAdError.getMessage());
                mInterstitialAd = null;
                isInterstitialAdLoading = false;
                
                // Track failure
                revenueTracker.onInterstitialAdFailed(loadAdError.getMessage());
                
                // Retry setelah 60 detik
                new android.os.Handler().postDelayed(() -> {
                    loadInterstitialAd();
                }, 60000);
            }
        });
    }

    /**
     * Tampilkan interstitial ad jika cooldown sudah lewat
     * @return true jika ad ditampilkan, false jika tidak
     */
    public boolean showInterstitialAd(MainActivity activity) {
        long currentTime = System.currentTimeMillis();
        long timeSinceLastShow = currentTime - lastInterstitialShowTime;
        
        if (timeSinceLastShow < INTERSTITIAL_COOLDOWN) {
            Log.d(TAG, "Interstitial ad on cooldown: " + (INTERSTITIAL_COOLDOWN - timeSinceLastShow) / 1000 + "s remaining");
            revenueTracker.onInterstitialSkippedCooldown();
            notifyGameAdClosed(); // Notify game untuk lanjut
            return false;
        }
        
        if (mInterstitialAd != null) {
            this.mainActivity = activity;
            mInterstitialAd.show(activity);
            return true;
        } else {
            Log.d(TAG, "Interstitial ad not ready");
            loadInterstitialAd();
            notifyGameAdClosed(); // Notify game untuk lanjut
            return false;
        }
    }

    /**
     * Cek apakah interstitial ad siap dan cooldown sudah lewat
     */
    public boolean isInterstitialAdReady() {
        long timeSinceLastShow = System.currentTimeMillis() - lastInterstitialShowTime;
        boolean ready = mInterstitialAd != null && timeSinceLastShow >= INTERSTITIAL_COOLDOWN;
        if (!ready && !isInterstitialAdLoading && timeSinceLastShow >= INTERSTITIAL_COOLDOWN) {
            // Auto-load jika belum ada dan cooldown sudah lewat
            loadInterstitialAd();
        }
        return ready;
    }

    // ========== BANNER ADS ==========
    
    /**
     * Buat dan load banner ad
     * Panggil di onCreate atau saat masuk menu
     */
    public void createBannerAd(MainActivity activity, RelativeLayout layout) {
        if (mBannerAdView != null) {
            Log.d(TAG, "Banner ad already exists");
            return;
        }
        
        this.mainActivity = activity;
        
        // Buat AdView
        mBannerAdView = new AdView(context);
        mBannerAdView.setAdSize(AdSize.BANNER); // 320x50
        mBannerAdView.setAdUnitId(BANNER_AD_UNIT_ID);
        
        // Setup layout params - banner di bottom
        RelativeLayout.LayoutParams params = new RelativeLayout.LayoutParams(
            RelativeLayout.LayoutParams.WRAP_CONTENT,
            RelativeLayout.LayoutParams.WRAP_CONTENT
        );
        params.addRule(RelativeLayout.ALIGN_PARENT_BOTTOM);
        params.addRule(RelativeLayout.CENTER_HORIZONTAL);
        
        // Tambahkan ke layout
        layout.addView(mBannerAdView, params);
        
        // Set ad listener
        mBannerAdView.setAdListener(new AdListener() {
            @Override
            public void onAdLoaded() {
                Log.d(TAG, "✅ Banner ad loaded");
                isBannerVisible = true;
                revenueTracker.onBannerAdLoaded();
            }

            @Override
            public void onAdFailedToLoad(LoadAdError adError) {
                Log.d(TAG, "Banner ad failed to load: " + adError.getMessage());
                isBannerVisible = false;
                revenueTracker.onBannerAdFailed(adError.getMessage());
                
                // Retry setelah 60 detik
                new android.os.Handler().postDelayed(() -> {
                    if (mBannerAdView != null) {
                        loadBannerAd();
                    }
                }, 60000);
            }

            @Override
            public void onAdOpened() {
                Log.d(TAG, "Banner ad opened");
            }

            @Override
            public void onAdClicked() {
                Log.d(TAG, "Banner ad clicked");
                revenueTracker.onBannerAdClicked();
            }

            @Override
            public void onAdClosed() {
                Log.d(TAG, "Banner ad closed");
            }

            @Override
            public void onAdImpression() {
                Log.d(TAG, "💰 Banner ad impression recorded");
                revenueTracker.onBannerAdImpression();
            }
        });
        
        // Load ad
        loadBannerAd();
    }

    /**
     * Load banner ad
     */
    private void loadBannerAd() {
        if (mBannerAdView != null) {
            AdRequest adRequest = new AdRequest.Builder().build();
            mBannerAdView.loadAd(adRequest);
            Log.d(TAG, "Loading banner ad...");
        }
    }

    /**
     * Tampilkan banner ad
     */
    public void showBannerAd() {
        if (mBannerAdView != null && !isBannerVisible) {
            mBannerAdView.setVisibility(android.view.View.VISIBLE);
            isBannerVisible = true;
            Log.d(TAG, "Banner ad shown");
        }
    }

    /**
     * Sembunyikan banner ad
     */
    public void hideBannerAd() {
        if (mBannerAdView != null && isBannerVisible) {
            mBannerAdView.setVisibility(android.view.View.GONE);
            isBannerVisible = false;
            Log.d(TAG, "Banner ad hidden");
        }
    }

    /**
     * Destroy banner ad
     */
    public void destroyBannerAd() {
        if (mBannerAdView != null) {
            mBannerAdView.destroy();
            mBannerAdView = null;
            isBannerVisible = false;
            Log.d(TAG, "Banner ad destroyed");
        }
    }

    public boolean isBannerVisible() {
        return isBannerVisible;
    }

    // ========== UTILITY METHODS ==========
    
    /**
     * Notify game bahwa ads sudah selesai
     */
    private void notifyGameAdClosed() {
        if (mainActivity != null && mainActivity.webView != null) {
            mainActivity.runOnUiThread(() -> {
                mainActivity.webView.evaluateJavascript(
                    "if (window.onAdClosed) window.onAdClosed();",
                    null
                );
            });
        }
    }

    /**
     * Load semua jenis ads
     */
    public void loadAllAds() {
        Log.d(TAG, "Loading all ads...");
        loadRewardedAd();
        loadInterstitialAd();
    }

    /**
     * Cleanup semua ads
     */
    public void destroy() {
        destroyBannerAd();
        mRewardedAd = null;
        mInterstitialAd = null;
        Log.d(TAG, "AdsManager destroyed");
    }

    /**
     * Get ad readiness status untuk debugging
     */
    public String getAdStatus() {
        return String.format(
            "Rewarded: %s | Interstitial: %s | Banner: %s",
            isRewardedAdReady() ? "✓" : "✗",
            isInterstitialAdReady() ? "✓" : "✗",
            isBannerVisible ? "✓" : "✗"
        );
    }
    
    /**
     * Get revenue tracker untuk analytics
     */
    public AdRevenueTracker getRevenueTracker() {
        return revenueTracker;
    }
    
    /**
     * Print performance report
     */
    public void printPerformanceReport() {
        if (revenueTracker != null) {
            revenueTracker.printReport();
        }
    }
    
    /**
     * Get performance stats as JSON
     */
    public String getPerformanceStatsJSON() {
        if (revenueTracker != null) {
            return revenueTracker.getStatsAsJSON().toString();
        }
        return "{}";
    }
}
