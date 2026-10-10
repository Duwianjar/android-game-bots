#!/bin/bash

echo "=== MONETIZATION STATUS CHECK ==="
echo ""

echo "📱 APK Build Status:"
if [ -f "android/app/build/outputs/apk/debug/app-debug.apk" ]; then
    echo "✅ Debug APK exists"
    ls -lh android/app/build/outputs/apk/debug/app-debug.apk
else
    echo "❌ Debug APK not found"
fi
echo ""

echo "🔑 Ad IDs Configuration:"
TEST_IDS=$(grep -r "3940256099942544" android/app/src/ 2>/dev/null | wc -l)
if [ "$TEST_IDS" -gt 0 ]; then
    echo "⚠️  Found $TEST_IDS TEST Ad IDs (need Production IDs)"
    grep -r "3940256099942544" android/app/src/ 2>/dev/null | cut -d: -f1 | sort -u
else
    echo "✅ No TEST IDs found - Production ready"
fi
echo ""

echo "📊 Code Components:"
echo "✅ AdsManager.java: $(wc -l < android/app/src/main/java/com/dragonarrowescape/game/AdsManager.java) lines"
echo "✅ AdRevenueTracker.java: $(wc -l < android/app/src/main/java/com/dragonarrowescape/game/AdRevenueTracker.java) lines"
echo "✅ MainActivity.java: $(wc -l < android/app/src/main/java/com/dragonarrowescape/game/MainActivity.java) lines"
echo "✅ Game HTML: $(wc -l < android/app/src/main/assets/index.html) lines"
echo ""

echo "🎮 Ad Integration Points:"
grep -c "AndroidAds\." android/app/src/main/assets/index.html 2>/dev/null && echo "ad calls in game" || echo "0 ad calls"
echo ""

echo "📦 Dependencies:"
grep "play-services-ads" android/app/build.gradle 2>/dev/null || echo "❌ AdMob SDK not found"
echo ""

echo "=== END STATUS CHECK ==="
