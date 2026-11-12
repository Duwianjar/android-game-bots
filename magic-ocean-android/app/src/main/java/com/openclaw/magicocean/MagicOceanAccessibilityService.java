package com.openclaw.magicocean;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.Intent;
import android.graphics.Path;
import android.graphics.Rect;
import android.os.Handler;
import android.os.Looper;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class MagicOceanAccessibilityService extends AccessibilityService {
    public static final String TAG = "MagicOceanBot";
    public static final String GAME_PACKAGE = "com.starlightgame.magicoceantilecrush";

    private static volatile MagicOceanAccessibilityService sInstance;
    private static volatile boolean sBotActive = false;
    private static LogListener sLogListener;

    private final Handler mMainHandler = new Handler(Looper.getMainLooper());
    private Thread mBotWorkerThread;
    private volatile boolean mWorkerRunning = false;

    private int mScreenWidth = 720;
    private int mScreenHeight = 1640;

    private String mCurrentPackage = "";
    private String mCurrentClass = "";
    private long mLastActionTs = 0;
    private int mTileGridIndex = 0;

    public interface LogListener {
        void onLogMessage(String message);
        void onBotStateChanged(boolean active);
    }

    public static void setLogListener(LogListener listener) {
        sLogListener = listener;
        if (listener != null) {
            listener.onBotStateChanged(sBotActive);
        }
    }

    public static MagicOceanAccessibilityService getInstance() {
        return sInstance;
    }

    public static boolean isBotActive() {
        return sBotActive;
    }

    public static void setBotActive(boolean active) {
        sBotActive = active;
        if (sInstance != null) {
            if (active) {
                sInstance.startWorkerLoop();
            } else {
                sInstance.stopWorkerLoop();
            }
        }
        if (sLogListener != null) {
            sLogListener.onBotStateChanged(active);
        }
    }

    public static void log(String message) {
        String time = new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date());
        String line = "[" + time + "] " + message;
        Log.i(TAG, line);
        if (sLogListener != null) {
            new Handler(Looper.getMainLooper()).post(() -> {
                if (sLogListener != null) sLogListener.onLogMessage(line);
            });
        }
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        sInstance = this;
        DisplayMetrics dm = getResources().getDisplayMetrics();
        mScreenWidth = dm.widthPixels;
        mScreenHeight = dm.heightPixels;
        log("Magic Ocean Accessibility Service TERHUBUNG (" + mScreenWidth + "x" + mScreenHeight + ")");
        if (sBotActive) {
            startWorkerLoop();
        }
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        stopWorkerLoop();
        sInstance = null;
        log("Magic Ocean Accessibility Service DIMATIKAN");
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null) return;
        int type = event.getEventType();
        if (type == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            CharSequence pkg = event.getPackageName();
            CharSequence cls = event.getClassName();
            if (pkg != null) mCurrentPackage = pkg.toString();
            if (cls != null) mCurrentClass = cls.toString();

            // Auto-return jika terlempar ke Play Store atau Browser
            if (sBotActive && isBlockedRedirectPackage(mCurrentPackage)) {
                log("Redirect terdeteksi (" + mCurrentPackage + ") -> Menutup dan kembali ke game");
                performGlobalAction(GLOBAL_ACTION_BACK);
                mMainHandler.postDelayed(this::bringGameToFront, 400);
            }
        }
    }

    @Override
    public void onInterrupt() {
        stopWorkerLoop();
    }

    public void startWorkerLoop() {
        if (mWorkerRunning) return;
        mWorkerRunning = true;
        mBotWorkerThread = new Thread(this::runBotLoop, "MagicOceanWorkerThread");
        mBotWorkerThread.start();
        log("▶ BOT DIMULAI: Mode ultra cepat mandiri aktif");
    }

    public void stopWorkerLoop() {
        mWorkerRunning = false;
        if (mBotWorkerThread != null) {
            mBotWorkerThread.interrupt();
            mBotWorkerThread = null;
        }
        log("⏹ BOT DISTOP");
    }

    private void runBotLoop() {
        while (mWorkerRunning && sBotActive) {
            try {
                processSingleStep();
                // Loop ultra cepat: 35ms per cycle (hampir 30 FPS)
                Thread.sleep(35);
            } catch (InterruptedException e) {
                break;
            } catch (Exception e) {
                log("Error di loop bot: " + e.getMessage());
            }
        }
    }

    private void processSingleStep() {
        AccessibilityNodeInfo root = getRootInActiveWindow();

        // 1. Cek tombol popup penting: DOBEL, BUKA, NOW NOT, CONTINUE, TUTUP
        if (root != null) {
            boolean handled = checkAndClickImportantNodes(root);
            root.recycle();
            if (handled) {
                return;
            }
        }

        // 2. Jika sedang di iklan layar penuh
        if (isAdActive()) {
            handleAdScreen();
            return;
        }

        // 3. Jika sedang di halaman game Magic Ocean
        if (GAME_PACKAGE.equals(mCurrentPackage)) {
            doGameplayActions();
        } else if (!isBlockedRedirectPackage(mCurrentPackage) && !isAdActive()) {
            // Jika di launcher / app lain, buka game
            long now = System.currentTimeMillis();
            if (now - mLastActionTs > 4000) {
                mLastActionTs = now;
                bringGameToFront();
            }
        }
    }

    private boolean checkAndClickImportantNodes(AccessibilityNodeInfo node) {
        if (node == null) return false;

        // Cek tombol DOBEL
        List<AccessibilityNodeInfo> dobelNodes = findNodesByTextInsensitive(node, "dobel");
        if (!dobelNodes.isEmpty()) {
            for (AccessibilityNodeInfo n : dobelNodes) {
                if (clickNodeOrParent(n)) {
                    log("KLIK TOMBOL DOBEL via Accessibility");
                    tap(mScreenWidth / 2f, 1115f); // fallback tap tengah tombol
                    return true;
                }
            }
        }

        // Cek tombol BUKA
        List<AccessibilityNodeInfo> bukaNodes = findNodesByTextInsensitive(node, "buka");
        for (AccessibilityNodeInfo n : bukaNodes) {
            CharSequence desc = n.getContentDescription();
            CharSequence txt = n.getText();
            String full = ((desc != null ? desc : "") + " " + (txt != null ? txt : "")).toLowerCase();
            if (!full.contains("toko") && !full.contains("store") && !full.contains("play")) {
                if (clickNodeOrParent(n)) {
                    log("KLIK TOMBOL BUKA via Accessibility");
                    tap(mScreenWidth / 2f, 1115f);
                    return true;
                }
            }
        }

        // Cek tombol NOW NOT / Nanti Saja
        List<AccessibilityNodeInfo> nowNotNodes = findNodesByTextInsensitive(node, "now not");
        if (nowNotNodes.isEmpty()) {
            nowNotNodes = findNodesByTextInsensitive(node, "not now");
        }
        if (!nowNotNodes.isEmpty()) {
            for (AccessibilityNodeInfo n : nowNotNodes) {
                if (clickNodeOrParent(n)) {
                    log("KLIK TOMBOL NOW NOT via Accessibility");
                    tap(mScreenWidth / 2f, 1210f);
                    return true;
                }
            }
        }

        // Cek tombol Close / Tutup / Skip iklan
        String[] closeWords = {"close", "tutup", "skip", "lewati", "lanjutkan", "continue", "hidup kembali"};
        for (String word : closeWords) {
            List<AccessibilityNodeInfo> targets = findNodesByTextInsensitive(node, word);
            for (AccessibilityNodeInfo n : targets) {
                if (clickNodeOrParent(n)) {
                    log("KLIK TOMBOL AKSI: '" + word + "'");
                    return true;
                }
            }
        }

        return false;
    }

    private void handleAdScreen() {
        long now = System.currentTimeMillis();
        if (now - mLastActionTs < 200) return;
        mLastActionTs = now;

        // Tembak titik tombol close umum pojok atas
        tap(mScreenWidth - 55f, 135f);  // Pojok kanan atas umum
        tap(mScreenWidth - 67f, 195f);  // AppLovin/Mintegral endcard X
        tap(48f, 136f);                 // Pojok kiri atas
    }

    private void doGameplayActions() {
        // Tap kotak board ubin Magic Ocean (4x4 board: x: 140..580, y: 550..850)
        float colW = (580f - 140f) / 4.0f;
        float rowH = (850f - 550f) / 4.0f;

        int curIdx = mTileGridIndex % 16;
        int col = curIdx % 4;
        int row = curIdx / 4;
        float tileX = 140f + (col + 0.5f) * colW;
        float tileY = 550f + (row + 0.5f) * rowH;
        mTileGridIndex = (mTileGridIndex + 1) % 16;

        tap(tileX, tileY);

        // Tap area gelembung melayang di bagian bawah/tengah (y: 900..1350)
        float bubbleX = 180f + ((System.currentTimeMillis() / 80) % 4) * 110f;
        float bubbleY = 950f + ((System.currentTimeMillis() / 200) % 3) * 120f;
        tap(bubbleX, bubbleY);
    }

    public boolean tap(float x, float y) {
        Path path = new Path();
        path.moveTo(x, y);
        GestureDescription.Builder builder = new GestureDescription.Builder();
        builder.addStroke(new GestureDescription.StrokeDescription(path, 0, 15));
        return dispatchGesture(builder.build(), null, null);
    }

    private boolean clickNodeOrParent(AccessibilityNodeInfo node) {
        if (node == null) return false;
        if (node.isClickable()) {
            return node.performAction(AccessibilityNodeInfo.ACTION_CLICK);
        }
        AccessibilityNodeInfo parent = node.getParent();
        while (parent != null) {
            if (parent.isClickable()) {
                boolean res = parent.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                parent.recycle();
                return res;
            }
            AccessibilityNodeInfo next = parent.getParent();
            parent.recycle();
            parent = next;
        }
        // Fallback jika tidak clickable: tap koordinat tengah bounds
        Rect bounds = new Rect();
        node.getBoundsInScreen(bounds);
        if (!bounds.isEmpty()) {
            return tap(bounds.centerX(), bounds.centerY());
        }
        return false;
    }

    private List<AccessibilityNodeInfo> findNodesByTextInsensitive(AccessibilityNodeInfo root, String query) {
        List<AccessibilityNodeInfo> result = new ArrayList<>();
        if (root == null || query == null) return result;
        searchNodesRecursive(root, query.toLowerCase(), result);
        return result;
    }

    private void searchNodesRecursive(AccessibilityNodeInfo node, String q, List<AccessibilityNodeInfo> out) {
        if (node == null) return;
        CharSequence txt = node.getText();
        CharSequence desc = node.getContentDescription();
        if (txt != null && txt.toString().toLowerCase().contains(q)) {
            out.add(node);
        } else if (desc != null && desc.toString().toLowerCase().contains(q)) {
            out.add(node);
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child != null) {
                searchNodesRecursive(child, q, out);
            }
        }
    }

    private boolean isAdActive() {
        String cls = mCurrentClass.toLowerCase();
        String pkg = mCurrentPackage.toLowerCase();
        return cls.contains("adactivity") || cls.contains("fullscreenwebviewdisplay")
                || cls.contains("mbrewardvideoactivity") || cls.contains("applovin")
                || cls.contains("vungle") || cls.contains("inmobi")
                || cls.contains("unity3d.ads") || pkg.contains("vending");
    }

    private boolean isBlockedRedirectPackage(String pkg) {
        if (pkg == null) return false;
        return pkg.equals("com.android.vending") || pkg.equals("com.android.chrome")
                || pkg.equals("com.google.android.apps.chrome") || pkg.equals("org.chromium.chrome");
    }

    public void bringGameToFront() {
        Intent intent = getPackageManager().getLaunchIntentForPackage(GAME_PACKAGE);
        if (intent != null) {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
            startActivity(intent);
        }
    }
}
