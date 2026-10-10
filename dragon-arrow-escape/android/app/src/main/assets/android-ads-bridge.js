/**
 * Android Ads Bridge - JavaScript Interface
 * Gunakan file ini untuk memanggil iklan dari game HTML5
 * 
 * MONETIZATION STRATEGY:
 * 1. Rewarded Ads ($10-$30 CPM) - bonus, continue, unlock
 * 2. Interstitial Ads ($3-$8 CPM) - level complete, menu transitions
 * 3. Banner Ads ($0.5-$2 CPM) - menu screens only
 */

class AndroidAdsBridge {
    constructor() {
        this.isAndroid = typeof window.AndroidAds !== 'undefined';
        this.isAndroidGame = typeof window.AndroidGame !== 'undefined';
        this.callbacks = {};
        
        // Setup global callbacks untuk dipanggil dari Android
        this._setupGlobalCallbacks();
        
        console.log(`📱 Platform: ${this.isAndroid ? 'Android' : 'Web'}`);
    }

    _setupGlobalCallbacks() {
        // Callback saat Android Ads ready
        window.onAndroidAdsReady = () => {
            console.log('✅ Android Ads Ready');
            if (this.callbacks.onAdsReady) {
                this.callbacks.onAdsReady();
            }
        };

        // Callback saat user dapat reward dari rewarded ad
        window.onAdRewardEarned = (rewardType, rewardAmount) => {
            console.log(`💎 Reward Earned: ${rewardType} x${rewardAmount}`);
            if (this.callbacks.onRewardEarned) {
                this.callbacks.onRewardEarned(rewardType, rewardAmount);
            }
        };

        // Callback saat ad ditutup (interstitial)
        window.onAdClosed = () => {
            console.log('✅ Ad Closed');
            if (this.callbacks.onAdClosed) {
                this.callbacks.onAdClosed();
            }
        };
    }

    // ========== REWARDED ADS ==========
    
    /**
     * Tampilkan rewarded ad untuk bonus coins, continue game, dll
     * @param {function} onRewardCallback - Dipanggil saat user dapat reward
     * @returns {boolean} true jika ad ditampilkan
     */
    showRewardedAd(onRewardCallback) {
        if (!this.isAndroid) {
            console.warn('⚠️ Rewarded ad hanya tersedia di Android');
            // Simulate reward untuk testing di browser
            if (onRewardCallback) {
                setTimeout(() => onRewardCallback('coin', 100), 1000);
            }
            return false;
        }

        if (this.isRewardedAdReady()) {
            console.log('📺 Showing rewarded ad...');
            this.callbacks.onRewardEarned = onRewardCallback;
            window.AndroidAds.showRewardedAd();
            return true;
        } else {
            console.log('⏳ Rewarded ad not ready yet');
            window.AndroidAds.loadRewardedAd();
            return false;
        }
    }

    /**
     * Cek apakah rewarded ad siap ditampilkan
     * @returns {boolean}
     */
    isRewardedAdReady() {
        if (!this.isAndroid) return false;
        return window.AndroidAds.isRewardedAdReady();
    }

    /**
     * Load rewarded ad (dipanggil otomatis, tapi bisa manual juga)
     */
    loadRewardedAd() {
        if (this.isAndroid) {
            window.AndroidAds.loadRewardedAd();
            console.log('🔄 Loading rewarded ad...');
        }
    }

    // ========== INTERSTITIAL ADS ==========
    
    /**
     * Tampilkan interstitial ad (level complete, menu transition)
     * PENTING: Otomatis ada cooldown 3 menit
     * @param {function} onClosedCallback - Dipanggil saat ad ditutup
     * @returns {boolean} true jika ad ditampilkan
     */
    showInterstitialAd(onClosedCallback) {
        if (!this.isAndroid) {
            console.warn('⚠️ Interstitial ad hanya tersedia di Android');
            // Simulate untuk testing
            if (onClosedCallback) {
                setTimeout(() => onClosedCallback(), 1000);
            }
            return false;
        }

        console.log('📺 Attempting to show interstitial ad...');
        this.callbacks.onAdClosed = onClosedCallback;
        window.AndroidAds.showInterstitialAd();
        return true;
    }

    /**
     * Cek apakah interstitial ad siap (dan cooldown sudah lewat)
     * @returns {boolean}
     */
    isInterstitialAdReady() {
        if (!this.isAndroid) return false;
        return window.AndroidAds.isInterstitialAdReady();
    }

    /**
     * Load interstitial ad
     */
    loadInterstitialAd() {
        if (this.isAndroid) {
            window.AndroidAds.loadInterstitialAd();
            console.log('🔄 Loading interstitial ad...');
        }
    }

    // ========== BANNER ADS ==========
    
    /**
     * Tampilkan banner ad (di menu, leaderboard, shop)
     * JANGAN tampilkan saat gameplay aktif!
     */
    showBannerAd() {
        if (this.isAndroid) {
            window.AndroidAds.showBannerAd();
            console.log('📺 Banner ad shown');
        }
    }

    /**
     * Sembunyikan banner ad (saat mulai gameplay)
     */
    hideBannerAd() {
        if (this.isAndroid) {
            window.AndroidAds.hideBannerAd();
            console.log('🙈 Banner ad hidden');
        }
    }

    /**
     * Cek apakah banner ad sedang visible
     * @returns {boolean}
     */
    isBannerVisible() {
        if (!this.isAndroid) return false;
        return window.AndroidAds.isBannerVisible();
    }

    // ========== UTILITY ==========
    
    /**
     * Load semua jenis ads sekaligus
     */
    loadAllAds() {
        if (this.isAndroid) {
            window.AndroidAds.loadAllAds();
            console.log('🔄 Loading all ads...');
        }
    }

    /**
     * Get status semua ads (untuk debugging)
     * @returns {string} "Rewarded: ✓ | Interstitial: ✓ | Banner: ✗"
     */
    getAdStatus() {
        if (!this.isAndroid) return 'Not Android';
        return window.AndroidAds.getAdStatus();
    }

    /**
     * Log ke Android logcat
     * @param {string} message
     */
    log(message) {
        if (this.isAndroid) {
            window.AndroidAds.log(message);
        }
        console.log(`[AndroidAds] ${message}`);
    }

    // ========== GAME UTILITIES ==========
    
    /**
     * Vibrate device (haptic feedback)
     * @param {number} duration - milliseconds
     */
    vibrate(duration = 50) {
        if (this.isAndroidGame) {
            window.AndroidGame.vibrate(duration);
        }
    }

    /**
     * Show Android toast message
     * @param {string} message
     */
    toast(message) {
        if (this.isAndroidGame) {
            window.AndroidGame.toast(message);
        } else {
            console.log(`[Toast] ${message}`);
        }
    }

    /**
     * Get device info
     * @returns {object} {model, android, sdk}
     */
    getDeviceInfo() {
        if (this.isAndroidGame) {
            try {
                return JSON.parse(window.AndroidGame.getDeviceInfo());
            } catch (e) {
                return null;
            }
        }
        return null;
    }
}

// ========== USAGE EXAMPLES ==========

/**
 * EXAMPLE 1: Rewarded Ad - Continue Game setelah Game Over
 */
function onGameOver() {
    const adsBridge = new AndroidAdsBridge();
    
    // Tampilkan tombol "Continue dengan nonton iklan"
    showContinueButton(() => {
        adsBridge.showRewardedAd((rewardType, rewardAmount) => {
            // User dapat reward!
            console.log(`Reward: ${rewardAmount} ${rewardType}`);
            
            // Berikan continue/revive
            continueGame();
            
            // Berikan bonus coins
            addCoins(rewardAmount);
            
            // Vibrate feedback
            adsBridge.vibrate(100);
        });
    });
}

/**
 * EXAMPLE 2: Interstitial Ad - Setelah Complete Level
 */
function onLevelComplete(levelNumber) {
    const adsBridge = new AndroidAdsBridge();
    
    // Show interstitial setiap 2-3 level
    if (levelNumber % 3 === 0) {
        adsBridge.showInterstitialAd(() => {
            // Ad selesai, lanjut ke level berikutnya
            loadNextLevel();
        });
    } else {
        // Langsung ke level berikutnya tanpa ad
        loadNextLevel();
    }
}

/**
 * EXAMPLE 3: Banner Ad - Show/Hide berdasarkan game state
 */
function onGameStateChange(newState) {
    const adsBridge = new AndroidAdsBridge();
    
    if (newState === 'MENU' || newState === 'SHOP' || newState === 'LEADERBOARD') {
        // Show banner di menu
        adsBridge.showBannerAd();
    } else if (newState === 'PLAYING') {
        // Hide banner saat gameplay
        adsBridge.hideBannerAd();
    }
}

/**
 * EXAMPLE 4: Rewarded Ad - Unlock Premium Item
 */
function unlockPremiumSkin(skinId) {
    const adsBridge = new AndroidAdsBridge();
    
    showConfirmDialog('Unlock dengan nonton iklan?', () => {
        adsBridge.showRewardedAd((rewardType, rewardAmount) => {
            // Unlock skin
            unlockSkin(skinId);
            
            // Show success message
            adsBridge.toast('Skin unlocked!');
            
            // Vibrate
            adsBridge.vibrate(200);
        });
    });
}

/**
 * EXAMPLE 5: Rewarded Ad - Double Coins
 */
function offerDoubleCoins(earnedCoins) {
    const adsBridge = new AndroidAdsBridge();
    
    showDoubleCoinsOffer(() => {
        adsBridge.showRewardedAd((rewardType, rewardAmount) => {
            // Double coins
            const bonusCoins = earnedCoins;
            addCoins(bonusCoins);
            
            // Show animation
            showCoinsAnimation(bonusCoins);
            
            adsBridge.toast(`+${bonusCoins} bonus coins!`);
        });
    });
}

/**
 * EXAMPLE 6: Check Ad Status - Before showing UI
 */
function updateUI() {
    const adsBridge = new AndroidAdsBridge();
    
    // Show "Watch Ad" button hanya jika ad ready
    if (adsBridge.isRewardedAdReady()) {
        showWatchAdButton();
    } else {
        hideWatchAdButton();
        // Preload untuk next time
        adsBridge.loadRewardedAd();
    }
    
    // Log status untuk debugging
    console.log('Ad Status:', adsBridge.getAdStatus());
}

/**
 * EXAMPLE 7: Initialize saat game start
 */
function initGame() {
    const adsBridge = new AndroidAdsBridge();
    
    // Load all ads di background
    adsBridge.loadAllAds();
    
    // Setup callbacks
    adsBridge.callbacks.onAdsReady = () => {
        console.log('✅ Ads system ready!');
        updateUI();
    };
    
    // Hide banner saat gameplay
    adsBridge.hideBannerAd();
    
    // Log device info
    const deviceInfo = adsBridge.getDeviceInfo();
    if (deviceInfo) {
        console.log('Device:', deviceInfo);
    }
}

// Export untuk digunakan di game
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AndroidAdsBridge;
}

// Global instance (optional)
window.AndroidAdsBridge = AndroidAdsBridge;

console.log('📱 AndroidAdsBridge loaded');
