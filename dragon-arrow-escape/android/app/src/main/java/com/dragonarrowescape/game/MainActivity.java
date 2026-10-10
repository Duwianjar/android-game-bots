package com.dragonarrowescape.game;

import android.annotation.SuppressLint;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.JavascriptInterface;
import android.app.Activity;
import android.util.Log;
import android.widget.Toast;
import android.widget.RelativeLayout;

import com.google.android.gms.ads.MobileAds;
import com.google.android.gms.ads.initialization.InitializationStatus;
import com.google.android.gms.ads.initialization.OnInitializationCompleteListener;

/**
 * MainActivity - Entry point aplikasi game
 * Mengelola WebView untuk game HTML5 dan integrasi iklan AdMob
 * 
 * MONETIZATION FEATURES:
 * - Rewarded Ads: untuk bonus coins, continue game, unlock premium
 * - Interstitial Ads: setiap 2-3 level dengan cooldown 3 menit
 * - Banner Ads: di menu utama (hide saat gameplay)
 */
public class MainActivity extends Activity {
    private static final String TAG = "DragonArrowEscape";
    public WebView webView;  // public agar bisa diakses dari AdsManager
    private AdsManager adsManager;
    private RelativeLayout mainLayout;

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        Log.d(TAG, "🚀 Game starting...");
        Log.d(TAG, "Package: " + getPackageName());

        // Setup main layout untuk webview + banner ad
        mainLayout = new RelativeLayout(this);
        
        // Inisialisasi Google Mobile Ads SDK
        initializeAdMob();

        // Setup WebView
        setupWebView();
        
        // Inisialisasi AdsManager (after AdMob init)
        adsManager = new AdsManager(this);
        
        // Verifikasi konfigurasi monetisasi
        AdMonetizationHelper.verifyAdMobConfiguration(this);

        // Tambahkan JavaScript Interface untuk komunikasi dengan game
        webView.addJavascriptInterface(new AdsJavascriptInterface(), "AndroidAds");
        webView.addJavascriptInterface(new GameJavascriptInterface(), "AndroidGame");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                Log.d(TAG, "✅ Page loaded: " + url);
                
                // Load semua jenis ads setelah page selesai
                adsManager.loadAllAds();
                
                // Inject JavaScript untuk notifikasi ke game
                injectAdStatusScript();
            }

            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                super.onReceivedError(view, errorCode, description, failingUrl);
                Log.e(TAG, "❌ WebView error: " + description);
            }
        });
        
        webView.setBackgroundColor(0xFF0A1929); // Dark blue background
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        
        // Load game HTML
        webView.loadUrl("file:///android_asset/index.html");

        // Tambahkan webview ke layout
        mainLayout.addView(webView);
        
        setContentView(mainLayout);
        
        Log.d(TAG, "✅ Game initialized");
    }

    /**
     * Inisialisasi AdMob SDK
     */
    private void initializeAdMob() {
        try {
            MobileAds.initialize(this, new OnInitializationCompleteListener() {
                @Override
                public void onInitializationComplete(InitializationStatus initializationStatus) {
                    Log.d(TAG, "✅ Google Mobile Ads SDK initialized");
                    Log.d(TAG, "AdMob Status: " + initializationStatus.getAdapterStatusMap().toString());
                }
            });
        } catch (Exception e) {
            Log.e(TAG, "❌ Error initializing MobileAds: " + e.getMessage());
        }
    }

    /**
     * Setup WebView dengan konfigurasi optimal untuk game
     */
    private void setupWebView() {
        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        
        // JavaScript & Storage
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        
        // File access
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        
        // Display
        settings.setLoadWithOverviewMode(false);
        settings.setUseWideViewPort(false);
        settings.setBuiltInZoomControls(false);
        settings.setSupportZoom(false);
        settings.setDisplayZoomControls(false);
        
        // Performance
        settings.setRenderPriority(WebSettings.RenderPriority.HIGH);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        
        // Mixed content (untuk dev)
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        
        // Layout
        RelativeLayout.LayoutParams webViewParams = new RelativeLayout.LayoutParams(
            RelativeLayout.LayoutParams.MATCH_PARENT,
            RelativeLayout.LayoutParams.MATCH_PARENT
        );
        webView.setLayoutParams(webViewParams);
    }

    /**
     * Inject JavaScript untuk notifikasi ad status ke game
     */
    private void injectAdStatusScript() {
        String script = 
            "console.log('🎮 Android Ads Interface Ready');" +
            "if (window.onAndroidAdsReady) window.onAndroidAdsReady();";
        
        webView.evaluateJavascript(script, null);
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) {
            webView.onResume();
        }
        Log.d(TAG, "📱 App resumed");
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (webView != null) {
            webView.onPause();
        }
        Log.d(TAG, "⏸️ App paused");
    }

    @Override
    protected void onDestroy() {
        if (adsManager != null) {
            adsManager.destroy();
        }
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
        Log.d(TAG, "🛑 App destroyed");
    }

    /**
     * JavaScript Interface untuk Ad Operations
     * Dipanggil dari JavaScript game: window.AndroidAds.methodName()
     */
    private class AdsJavascriptInterface {
        
        // ========== REWARDED ADS ==========
        
        @JavascriptInterface
        public void showRewardedAd() {
            runOnUiThread(() -> {
                if (adsManager.isRewardedAdReady()) {
                    Log.d(TAG, "📺 Showing rewarded ad");
                    adsManager.showRewardedAd(MainActivity.this);
                } else {
                    Toast.makeText(MainActivity.this, "Iklan sedang dimuat...", Toast.LENGTH_SHORT).show();
                    Log.d(TAG, "⏳ Rewarded ad not ready, loading...");
                    adsManager.loadRewardedAd();
                }
            });
        }

        @JavascriptInterface
        public boolean isRewardedAdReady() {
            return adsManager.isRewardedAdReady();
        }

        @JavascriptInterface
        public void loadRewardedAd() {
            adsManager.loadRewardedAd();
            Log.d(TAG, "🔄 Loading rewarded ad from JS");
        }

        // ========== INTERSTITIAL ADS ==========
        
        @JavascriptInterface
        public void showInterstitialAd() {
            runOnUiThread(() -> {
                Log.d(TAG, "📺 Attempting to show interstitial ad");
                boolean shown = adsManager.showInterstitialAd(MainActivity.this);
                if (!shown) {
                    Log.d(TAG, "⏳ Interstitial ad not shown (cooldown or not ready)");
                }
            });
        }

        @JavascriptInterface
        public boolean isInterstitialAdReady() {
            return adsManager.isInterstitialAdReady();
        }

        @JavascriptInterface
        public void loadInterstitialAd() {
            adsManager.loadInterstitialAd();
            Log.d(TAG, "🔄 Loading interstitial ad from JS");
        }

        // ========== BANNER ADS ==========
        
        @JavascriptInterface
        public void showBannerAd() {
            runOnUiThread(() -> {
                if (adsManager != null) {
                    if (!adsManager.isBannerVisible()) {
                        // Buat banner jika belum ada
                        adsManager.createBannerAd(MainActivity.this, mainLayout);
                    } else {
                        adsManager.showBannerAd();
                    }
                    Log.d(TAG, "📺 Banner ad shown");
                }
            });
        }

        @JavascriptInterface
        public void hideBannerAd() {
            runOnUiThread(() -> {
                adsManager.hideBannerAd();
                Log.d(TAG, "🙈 Banner ad hidden");
            });
        }

        @JavascriptInterface
        public boolean isBannerVisible() {
            return adsManager.isBannerVisible();
        }

        // ========== UTILITY ==========
        
        @JavascriptInterface
        public void loadAllAds() {
            adsManager.loadAllAds();
            Log.d(TAG, "🔄 Loading all ads from JS");
        }

        @JavascriptInterface
        public String getAdStatus() {
            String status = adsManager.getAdStatus();
            Log.d(TAG, "📊 Ad Status: " + status);
            return status;
        }

        @JavascriptInterface
        public void log(String message) {
            Log.d(TAG, "JS: " + message);
        }
    }

    /**
     * JavaScript Interface untuk Game Operations
     * Untuk fitur tambahan game seperti haptic, analytics, dll
     */
    private class GameJavascriptInterface {
        
        @JavascriptInterface
        public void vibrate(int duration) {
            runOnUiThread(() -> {
                try {
                    android.os.Vibrator vibrator = (android.os.Vibrator) getSystemService(VIBRATOR_SERVICE);
                    if (vibrator != null && vibrator.hasVibrator()) {
                        vibrator.vibrate(duration);
                    }
                } catch (Exception e) {
                    Log.e(TAG, "Vibrate error: " + e.getMessage());
                }
            });
        }

        @JavascriptInterface
        public void toast(String message) {
            runOnUiThread(() -> {
                Toast.makeText(MainActivity.this, message, Toast.LENGTH_SHORT).show();
            });
        }

        @JavascriptInterface
        public void log(String message) {
            Log.d(TAG, "Game: " + message);
        }

        @JavascriptInterface
        public String getDeviceInfo() {
            return String.format("{\"model\":\"%s\",\"android\":\"%s\",\"sdk\":%d}",
                android.os.Build.MODEL,
                android.os.Build.VERSION.RELEASE,
                android.os.Build.VERSION.SDK_INT
            );
        }
    }
}
