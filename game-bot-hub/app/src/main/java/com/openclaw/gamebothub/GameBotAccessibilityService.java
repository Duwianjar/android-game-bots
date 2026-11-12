package com.openclaw.gamebothub;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.graphics.Path;
import android.graphics.Rect;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.DisplayMetrics;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;

public class GameBotAccessibilityService extends AccessibilityService {
    private static volatile GameBotAccessibilityService instance;
    private static volatile String foregroundPackage = "";
    private static volatile long lastForegroundChangeAt = 0;

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final Random random = new Random();
    private DisplayMetrics metrics;
    private BotItem currentBot;

    private Thread engineThread;
    private volatile boolean engineRunning = false;
    private long lastAdDismissAt = 0;
    private long lastRedirectBackAt = 0;
    private long lastRelaunchAt = 0;
    private long lastActionAt = 0;
    private int actionCycle = 0;

    private static final Set<String> REDIRECT_PACKAGES = new HashSet<>(Arrays.asList(
            "com.android.chrome",
            "com.chrome.beta",
            "com.chrome.dev",
            "com.google.android.apps.chrome",
            "com.android.vending",
            "com.shopee.id",
            "com.shopee.app",
            "com.lazada.android",
            "com.tokopedia.tkpd",
            "com.zhiliaoapp.musically",
            "com.instagram.android",
            "com.facebook.katana",
            "com.transsion.phoenix",
            "com.transsion.palmpay"
    ));

    private static final List<String> AD_CLOSE_KEYWORDS = Arrays.asList(
            "close", "tutup", "skip", "lewati", "lompati", "✕", "x", "×", "reward",
            "hadiah", "no thanks", "klaim", "claim", "ambil", "continue",
            "lanjutkan", "lanjut", "terima", "double", "koleksi", "ok", "gratis", "buka"
    );

    public static GameBotAccessibilityService getInstance() {
        return instance;
    }

    public static boolean isServiceRunning() {
        return instance != null;
    }

    public void setCurrentBot(BotItem bot) {
        this.currentBot = bot;
        this.actionCycle = 0;
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        metrics = getResources().getDisplayMetrics();
        BotLogger.log("ACCESSIBILITY", "Layanan Otomasi Aksesibilitas terhubung dan siap.");

        startEngine();
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null) return;

        CharSequence pkgSeq = event.getPackageName();
        if (pkgSeq != null) {
            String pkg = pkgSeq.toString();
            // Abaikan overlay bar kita sendiri agar tidak menimpa foreground game
            if (!pkg.equals(getPackageName()) && !pkg.equals("com.openclaw.gamebothub")) {
                foregroundPackage = pkg;
                lastForegroundChangeAt = SystemClock.elapsedRealtime();
            }
        }

        RotationManager rm = RotationManager.getInstance();
        if (!rm.isRunning() || rm.isPaused() || currentBot == null) {
            return;
        }

        // 1. Anti-redirect check
        if (isBlockedRedirect(foregroundPackage)) {
            handleRedirect();
            return;
        }

        // 2. Auto-close iklan pada window state changed
        int eventType = event.getEventType();
        if (eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED ||
            eventType == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED) {
            checkAndCloseAd(getRootInActiveWindow());
        }
    }

    private void handleRedirect() {
        long now = SystemClock.elapsedRealtime();
        if (now - lastRedirectBackAt > 2000) {
            lastRedirectBackAt = now;
            BotLogger.log("ANTI-REDIRECT", "Terdeteksi redirect ke " + foregroundPackage + ". Menekan tombol kembali...");
            performGlobalAction(GLOBAL_ACTION_BACK);

            // Jika masih berada di browser/Play Store setelah 4 detik, buka kembali game
            if (now - lastRelaunchAt > 4500) {
                lastRelaunchAt = now;
                mainHandler.postDelayed(() -> {
                    RotationManager.getInstance().relaunchCurrentGame(GameBotAccessibilityService.this);
                }, 1000);
            }
        }
    }

    private void checkAndCloseAd(AccessibilityNodeInfo root) {
        if (root == null) return;
        try {
            scanNodeTree(root, 0);
        } catch (Throwable ignored) {
        } finally {
            try {
                root.recycle();
            } catch (Throwable ignored) {}
        }
    }

    private boolean scanNodeTree(AccessibilityNodeInfo node, int depth) {
        if (node == null || depth > 20) return false;

        CharSequence textSeq = node.getText();
        CharSequence descSeq = node.getContentDescription();
        String text = textSeq != null ? textSeq.toString().toLowerCase().trim() : "";
        String desc = descSeq != null ? descSeq.toString().toLowerCase().trim() : "";

        for (String kw : AD_CLOSE_KEYWORDS) {
            if ((text.length() > 0 && (text.equals(kw) || text.contains(kw))) ||
                (desc.length() > 0 && (desc.equals(kw) || desc.contains(kw)))) {

                long now = SystemClock.elapsedRealtime();
                if (now - lastAdDismissAt > 1500) {
                    lastAdDismissAt = now;
                    String label = text.isEmpty() ? desc : text;
                    BotLogger.log("IKLAN", "Menutup pop-up/klaim: [" + label + "]");
                    if (node.isClickable()) {
                        node.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                    } else {
                        Rect rect = new Rect();
                        node.getBoundsInScreen(rect);
                        if (rect.width() > 0 && rect.height() > 0) {
                            dispatchTap(rect.centerX(), rect.centerY());
                        }
                    }
                    return true;
                }
            }
        }

        int childCount = node.getChildCount();
        for (int i = 0; i < childCount; i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child != null) {
                boolean closed = scanNodeTree(child, depth + 1);
                try {
                    child.recycle();
                } catch (Throwable ignored) {}
                if (closed) return true;
            }
        }
        return false;
    }

    private boolean isBlockedRedirect(String pkg) {
        if (pkg == null || pkg.isEmpty()) return false;
        return REDIRECT_PACKAGES.contains(pkg);
    }

    private boolean isLauncherOrSettings(String pkg) {
        if (pkg == null || pkg.isEmpty()) return false;
        String lower = pkg.toLowerCase();
        return lower.contains("launcher") || lower.contains("home") ||
               lower.contains("trebuchet") || pkg.equals("com.android.settings");
    }

    private boolean isTargetForeground() {
        if (currentBot == null) return false;
        String target = currentBot.getPackageName();
        if (target == null || target.isEmpty()) return false;

        // Cek root window aktif jika tersedia
        try {
            AccessibilityNodeInfo root = getRootInActiveWindow();
            if (root != null) {
                CharSequence rootPkg = root.getPackageName();
                if (rootPkg != null) {
                    String p = rootPkg.toString();
                    if (target.equals(p)) {
                        return true;
                    }
                    if (isBlockedRedirect(p)) {
                        return false;
                    }
                    if (isLauncherOrSettings(p)) {
                        return false;
                    }
                }
            }
        } catch (Throwable ignored) {}

        // Cek foregroundPackage dari event
        if (target.equals(foregroundPackage)) {
            return true;
        }

        // Jika foregroundPackage adalah aplikasi hub kita sendiri, keyboard, atau systemui,
        // berarti game target berada tepat di bawah overlay
        if (foregroundPackage.isEmpty() ||
            foregroundPackage.equals(getPackageName()) ||
            foregroundPackage.equals("com.openclaw.gamebothub") ||
            foregroundPackage.contains("inputmethod") ||
            foregroundPackage.equals("android") ||
            foregroundPackage.equals("com.android.systemui")) {
            return true;
        }

        // Jika terdeteksi di browser/store
        if (isBlockedRedirect(foregroundPackage)) {
            return false;
        }

        // Jika di home launcher
        if (isLauncherOrSettings(foregroundPackage)) {
            return false;
        }

        // Default: game Unity sering tidak memancarkan event, anggap target aktif
        return true;
    }

    private void startEngine() {
        if (engineRunning) return;
        engineRunning = true;
        engineThread = new Thread(() -> {
            while (engineRunning) {
                try {
                    Thread.sleep(400);

                    RotationManager rm = RotationManager.getInstance();
                    if (!rm.isRunning() || rm.isPaused() || currentBot == null) {
                        continue;
                    }

                    if (metrics == null) {
                        metrics = getResources().getDisplayMetrics();
                    }

                    int width = metrics != null ? metrics.widthPixels : 720;
                    int height = metrics != null ? metrics.heightPixels : 1640;

                    if (isTargetForeground()) {
                        performGameAction(currentBot.getGameplayType(), width, height);
                    } else {
                        // Terdeteksi di luar target (redirect atau stuck)
                        if (isBlockedRedirect(foregroundPackage)) {
                            handleRedirect();
                        } else {
                            long now = SystemClock.elapsedRealtime();
                            if (now - lastForegroundChangeAt > 14000 && now - lastActionAt > 4000) {
                                lastActionAt = now;
                                BotLogger.log("IKLAN", "Fallback tap sudut penutup iklan...");
                                dispatchTap(width * 0.91f, height * 0.07f);
                                Thread.sleep(600);
                                dispatchTap(width * 0.09f, height * 0.07f);
                            }
                        }
                    }

                } catch (InterruptedException e) {
                    break;
                } catch (Throwable t) {
                    // Ignore transient errors
                }
            }
        });
        engineThread.setName("GameBotEngine");
        engineThread.start();
    }

    private void performGameAction(BotItem.GameplayType type, int width, int height) {
        long now = SystemClock.elapsedRealtime();
        if (now - lastActionAt < 400) return;
        lastActionAt = now;
        actionCycle++;

        switch (type) {
            case TILE_MATCH:
                performTileMatchAction(width, height);
                break;

            case BUS_JAM:
                performBusJamAction(width, height);
                break;

            case BLADE_SLASH:
                performBladeSlashAction(width, height);
                break;

            case SODA_SORT:
                performSodaSortAction(width, height);
                break;

            case BUBBLE_POP:
                performBubblePopAction(width, height);
                break;

            case MERGE:
                performMergeAction(width, height);
                break;

            case ARROW_ESCAPE:
                performArrowEscapeAction(width, height);
                break;
        }
    }

    private void performTileMatchAction(int width, int height) {
        // 1. Cek tombol Start / Mainkan / Level di tengah layar (setiap 8 siklus)
        if (actionCycle % 8 == 1) {
            float startY = height * (actionCycle % 16 == 1 ? 0.55f : 0.62f);
            BotLogger.log("GAMEPLAY", "Mengetuk tombol Start / Level di (" + (int)(width * 0.50f) + ", " + (int)startY + ")");
            dispatchTap(width * 0.50f, startY);
            return;
        }

        // 2. Cek tombol Klaim / Lanjut / Hadiah di bawah layar (setiap 6 siklus)
        if (actionCycle % 6 == 3) {
            float claimY = height * (actionCycle % 12 == 3 ? 0.74f : 0.82f);
            BotLogger.log("GAMEPLAY", "Mengetuk area Klaim / Hadiah di (" + (int)(width * 0.50f) + ", " + (int)claimY + ")");
            dispatchTap(width * 0.50f, claimY);
            return;
        }

        // 3. Cek booster Shuffle / Magic Wand (setiap 28 siklus jika ubin macet)
        if (actionCycle % 28 == 0) {
            BotLogger.log("GAMEPLAY", "Mengacak ubin (Booster Shuffle) di (" + (int)(width * 0.80f) + ", " + (int)(height * 0.90f) + ")");
            dispatchTap(width * 0.80f, height * 0.90f);
            return;
        }

        // 4. Burst Tap 3 Ubin pada Grid (Match-3 Gameplay)
        // Area papan ubin Zoo Tile / Woodland: X: 120-600, Y: 520-1180
        float[] cols = {0.20f, 0.35f, 0.50f, 0.65f, 0.80f};
        float[] rows = {0.36f, 0.43f, 0.50f, 0.57f, 0.64f, 0.70f};

        int startColIdx = (actionCycle * 2) % cols.length;
        int startRowIdx = actionCycle % rows.length;

        for (int i = 0; i < 3; i++) {
            int c = (startColIdx + i) % cols.length;
            int r = (startRowIdx + (i % 2)) % rows.length;
            float jitterX = (random.nextFloat() * 0.04f - 0.02f);
            float jitterY = (random.nextFloat() * 0.03f - 0.015f);

            float tx = width * (cols[c] + jitterX);
            float ty = height * (rows[r] + jitterY);
            dispatchTap(tx, ty);

            try {
                Thread.sleep(60);
            } catch (Throwable ignored) {}
        }
    }

    private void performBusJamAction(int width, int height) {
        if (actionCycle % 8 == 1) {
            dispatchTap(width * 0.50f, height * 0.80f);
            return;
        }
        float busX = width * (0.22f + random.nextFloat() * 0.56f);
        float busY = height * (0.42f + random.nextFloat() * 0.32f);
        dispatchTap(busX, busY);
    }

    private void performBladeSlashAction(int width, int height) {
        if (actionCycle % 7 == 1) {
            dispatchTap(width * 0.50f, height * 0.82f);
            return;
        }
        float startX = width * (0.15f + random.nextFloat() * 0.35f);
        float startY = height * (0.45f + random.nextFloat() * 0.30f);
        float endX = width * (0.55f + random.nextFloat() * 0.35f);
        float endY = startY + (random.nextFloat() * 200 - 100);
        dispatchSwipe(startX, startY, endX, endY, 140);
    }

    private void performSodaSortAction(int width, int height) {
        if (actionCycle % 8 == 1) {
            dispatchTap(width * 0.50f, height * 0.78f);
            return;
        }
        float sortX = width * (0.20f + random.nextFloat() * 0.60f);
        float sortY = height * (0.35f + random.nextFloat() * 0.30f);
        dispatchTap(sortX, sortY);
    }

    private void performBubblePopAction(int width, int height) {
        if (actionCycle % 8 == 1) {
            dispatchTap(width * 0.50f, height * 0.80f);
            return;
        }
        float bX = width * (0.20f + random.nextFloat() * 0.60f);
        float bY = height * (0.30f + random.nextFloat() * 0.45f);
        dispatchTap(bX, bY);
    }

    private void performMergeAction(int width, int height) {
        if (actionCycle % 8 == 1) {
            dispatchTap(width * 0.50f, height * 0.80f);
            return;
        }
        float mX1 = width * (0.25f + random.nextFloat() * 0.25f);
        float mY1 = height * (0.45f + random.nextFloat() * 0.25f);
        float mX2 = mX1 + (random.nextBoolean() ? 120 : -120);
        float mY2 = mY1;
        dispatchSwipe(mX1, mY1, mX2, mY2, 220);
    }

    private void performArrowEscapeAction(int width, int height) {
        if (actionCycle % 8 == 1) {
            dispatchTap(width * 0.50f, height * 0.80f);
            return;
        }
        float aX = width * (0.20f + random.nextFloat() * 0.60f);
        float aY = height * (0.35f + random.nextFloat() * 0.40f);
        dispatchTap(aX, aY);
    }

    public void dispatchTap(float x, float y) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return;
        final float tapX = Math.max(10, Math.min(x, metrics != null ? metrics.widthPixels - 10 : 710));
        final float tapY = Math.max(10, Math.min(y, metrics != null ? metrics.heightPixels - 10 : 1630));

        mainHandler.post(() -> {
            try {
                Path path = new Path();
                path.moveTo(tapX, tapY);
                path.lineTo(tapX + 1.0f, tapY + 1.0f);
                GestureDescription.Builder builder = new GestureDescription.Builder();
                builder.addStroke(new GestureDescription.StrokeDescription(path, 0, 50));
                dispatchGesture(builder.build(), null, null);
            } catch (Throwable ignored) {
            }
        });
    }

    public void dispatchSwipe(float x1, float y1, float x2, float y2, long durationMs) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return;
        mainHandler.post(() -> {
            try {
                Path path = new Path();
                path.moveTo(x1, y1);
                path.lineTo(x2, y2);
                GestureDescription.Builder builder = new GestureDescription.Builder();
                builder.addStroke(new GestureDescription.StrokeDescription(path, 0, Math.max(50, durationMs)));
                dispatchGesture(builder.build(), null, null);
            } catch (Throwable ignored) {
            }
        });
    }

    @Override
    public void onInterrupt() {
        BotLogger.log("ACCESSIBILITY", "Layanan otomasi diinterupsi.");
    }

    @Override
    public void onDestroy() {
        engineRunning = false;
        if (engineThread != null) {
            engineThread.interrupt();
        }
        if (instance == this) {
            instance = null;
        }
        BotLogger.log("ACCESSIBILITY", "Layanan otomasi dinonaktifkan.");
        super.onDestroy();
    }
}
