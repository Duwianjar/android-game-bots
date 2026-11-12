package com.openclaw.injectiklan;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.graphics.Path;
import android.graphics.Rect;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.net.URLEncoder;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public class InjectAccessibilityService extends AccessibilityService {
    private static final String TAG = "InjectAccessibility";

    private static volatile InjectAccessibilityService sInstance;
    private final ExecutorService mExecutor = Executors.newSingleThreadExecutor();
    private final Handler mMainHandler = new Handler(Looper.getMainLooper());
    private boolean mIsRunningCycle = false;

    public interface LogListener {
        void onLogMessage(String message);
    }
    private static LogListener sLogListener;

    public static void setLogListener(LogListener listener) {
        sLogListener = listener;
    }

    public static InjectAccessibilityService getInstance() {
        return sInstance;
    }

    public static void log(String message) {
        String time = new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date());
        String formatted = "[" + time + "] " + message;
        Log.i(TAG, formatted);
        if (sLogListener != null) {
            new Handler(Looper.getMainLooper()).post(() -> {
                if (sLogListener != null) sLogListener.onLogMessage(formatted);
            });
        }
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        sInstance = this;
        log("Layanan Accessibility Inject Iklan TERHUBUNG.");
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        sInstance = null;
        log("Layanan Accessibility Inject Iklan DIHENTIKAN.");
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // Event listener pasif
    }

    @Override
    public void onInterrupt() {
        log("Accessibility terinterupsi.");
    }

    public boolean isRunningCycle() {
        return mIsRunningCycle;
    }

    // --- SINKRONISASI GESTUR TAP & SWIPE FISIK ---

    public boolean dispatchTapSync(float x, float y, long timeoutMs) {
        final CountDownLatch latch = new CountDownLatch(1);
        Path path = new Path();
        path.moveTo(x, y);
        GestureDescription.Builder builder = new GestureDescription.Builder();
        builder.addStroke(new GestureDescription.StrokeDescription(path, 0, 90));
        boolean dispatched = dispatchGesture(builder.build(), new GestureResultCallback() {
            @Override
            public void onCompleted(GestureDescription gestureDescription) {
                latch.countDown();
            }
            @Override
            public void onCancelled(GestureDescription gestureDescription) {
                latch.countDown();
            }
        }, null);
        if (!dispatched) return false;
        try {
            latch.await(timeoutMs, TimeUnit.MILLISECONDS);
        } catch (InterruptedException ignored) {}
        return true;
    }

    public boolean dispatchSwipeSync(float x1, float y1, float x2, float y2, long durationMs) {
        final CountDownLatch latch = new CountDownLatch(1);
        Path path = new Path();
        path.moveTo(x1, y1);
        path.lineTo(x2, y2);
        GestureDescription.Builder builder = new GestureDescription.Builder();
        builder.addStroke(new GestureDescription.StrokeDescription(path, 0, durationMs));
        boolean dispatched = dispatchGesture(builder.build(), new GestureResultCallback() {
            @Override
            public void onCompleted(GestureDescription gestureDescription) {
                latch.countDown();
            }
            @Override
            public void onCancelled(GestureDescription gestureDescription) {
                latch.countDown();
            }
        }, null);
        if (!dispatched) return false;
        try {
            latch.await(durationMs + 400, TimeUnit.MILLISECONDS);
        } catch (InterruptedException ignored) {}
        return true;
    }

    // --- RANDOM KEYWORDS ---

    public String generateRandomSlotKeyword() {
        String[][] groups = {
            {"toto", "slot", "judi", "casino"},
            {"gacor", "maxwin", "rtp live", "bonus", "rollingan"},
            {"zeus", "pragmatic", "spaceman", "gates of olympus", "mahjong"},
            {"deposit dana", "resmi indonesia", "bonus member", "terpercaya", "hari ini"}
        };
        Random r = new Random();
        StringBuilder sb = new StringBuilder();
        for (String[] group : groups) {
            if (sb.length() > 0) sb.append(" ");
            sb.append(group[r.nextInt(group.length)]);
        }
        return sb.toString();
    }

    // --- NORMALISASI TEKS & REGEX ---

    private String normalize(String text) {
        if (text == null) return "";
        return text.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
    }

    private String matchFieldType(String raw) {
        String norm = normalize(raw);
        if (norm.length() < 2) return null;

        // 1. Confirm Password
        if (norm.contains("konfirmasikatasandi") || norm.contains("konfirmasisandi") || norm.contains("konfirmasipassword")
                || norm.contains("ulangikatasandi") || norm.contains("ulangisandi") || norm.contains("confirmpassword")
                || norm.contains("repeatpassword") || (norm.contains("konfirmasi") && norm.contains("sandi"))
                || (norm.contains("confirm") && norm.contains("password"))) {
            return "confirm_password";
        }
        // 2. Password
        if (norm.contains("katasandi") || norm.contains("password") || norm.contains("sandi")
                || norm.contains("passw") || norm.contains("passwd") || norm.contains("pwd")) {
            if (!norm.contains("konfirmasi") && !norm.contains("confirm") && !norm.contains("ulangi")) {
                return "password";
            }
        }
        // 3. Rekening
        if (norm.contains("nomorrekening") || norm.contains("norekening") || norm.contains("norek")
                || norm.contains("nomorakun") || norm.contains("nomorewallet") || norm.contains("rekening")) {
            return "rek";
        }
        // 4. Nama Rekening
        if (norm.contains("namarekening") || norm.contains("namapemilik") || norm.contains("pemilikrekening")
                || (norm.contains("rekening") && norm.contains("nama"))) {
            return "nama_rek";
        }
        // 5. Bank / Pembayaran
        if (norm.contains("pilihbank") || norm.contains("namabank") || norm.contains("jenisbank")
                || norm.contains("metodepembayaran") || norm.contains("ewallet") || norm.equals("bank")) {
            return "bank";
        }
        // 6. Phone / HP / WhatsApp
        if (norm.contains("nomortelepon") || norm.contains("notelepon") || norm.contains("nomorhp")
                || norm.contains("nohp") || norm.contains("telepon") || norm.contains("whatsapp")
                || norm.contains("nowa") || norm.contains("kontak") || norm.contains("ponsel")) {
            return "phone";
        }
        // 7. Email
        if (norm.contains("email") || norm.contains("alamatemail") || norm.contains("surel") || raw.contains("@")) {
            return "email";
        }
        // 8. Username
        if (norm.contains("namapengguna") || norm.contains("username") || norm.contains("userid")
                || norm.contains("namaakun") || norm.contains("idpengguna") || norm.contains("loginid")
                || norm.equals("user") || norm.equals("nama")) {
            return "username";
        }
        return null;
    }

    private String getInputLabel(AccessibilityNodeInfo input) {
        StringBuilder sb = new StringBuilder();
        if (input.getText() != null) sb.append(" ").append(input.getText());
        if (input.getHintText() != null) sb.append(" ").append(input.getHintText());
        if (input.getContentDescription() != null) sb.append(" ").append(input.getContentDescription());
        if (input.getViewIdResourceName() != null) sb.append(" ").append(input.getViewIdResourceName());

        if (input.getParent() != null) {
            AccessibilityNodeInfo parent = input.getParent();
            for (int j = 0; j < parent.getChildCount(); j++) {
                AccessibilityNodeInfo sibling = parent.getChild(j);
                if (sibling != null && sibling != input) {
                    if (sibling.getText() != null) sb.append(" ").append(sibling.getText());
                    if (sibling.getContentDescription() != null) sb.append(" ").append(sibling.getContentDescription());
                }
            }
        }
        return sb.toString().trim();
    }

    private void findAllInputNodes(AccessibilityNodeInfo node, List<AccessibilityNodeInfo> list) {
        if (node == null) return;
        CharSequence cls = node.getClassName();
        boolean isEditable = node.isEditable();
        boolean isEditClass = cls != null && (cls.toString().contains("EditText") || cls.toString().contains("AutoCompleteTextView"));
        if (isEditable || isEditClass) {
            Rect r = new Rect();
            node.getBoundsInScreen(r);
            if (r.top > 200 && r.bottom < 1600 && r.height() > 30) {
                list.add(node);
            }
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            findAllInputNodes(node.getChild(i), list);
        }
    }

    // --- FORM SCANNING & AUTOFILL ---

    public void fillFormFields() {
        log("  [FORM]: Memindai dan mengisi data formulir pendaftaran...");
        Map<String, String> values = new HashMap<>();
        values.put("username", "Wahyu91123");
        values.put("password", "Wahyu123*");
        values.put("confirm_password", "Wahyu123*");
        values.put("email", "wahyu91123@gmail.com");
        values.put("phone", "085157993801");
        values.put("bank", "OVO");
        values.put("rek", "085157993801");
        values.put("nama_rek", "Wahyu");

        String[] positionalFallback = {"username", "password", "confirm_password", "email", "phone", "bank", "rek", "nama_rek"};
        Set<String> filled = new HashSet<>();
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);

        // Lakukan 3 pass scanning & scroll agar field atas dan bawah terisi
        for (int pass = 1; pass <= 3; pass++) {
            AccessibilityNodeInfo root = getRootInActiveWindow();
            if (root == null) break;

            List<AccessibilityNodeInfo> inputs = new ArrayList<>();
            findAllInputNodes(root, inputs);

            for (int i = 0; i < inputs.size(); i++) {
                AccessibilityNodeInfo input = inputs.get(i);
                String label = getInputLabel(input);
                String fieldType = matchFieldType(label);

                // Fallback berdasarkan posisi jika label tidak terdeteksi
                if (fieldType == null && i < positionalFallback.length) {
                    String candidate = positionalFallback[i];
                    if (!filled.contains(candidate)) {
                        fieldType = candidate;
                    }
                }

                if (fieldType != null && !filled.contains(fieldType)) {
                    String val = values.get(fieldType);
                    if (val != null) {
                        Rect r = new Rect();
                        input.getBoundsInScreen(r);
                        int cx = r.centerX();
                        int cy = r.centerY();

                        if (cx > 0 && cy > 0) {
                            // 1. Tap fisik pada field input agar fokus
                            dispatchTapSync(cx, cy, 350);
                            SystemClock.sleep(200);
                        }

                        // 2. Set text via Accessibility API
                        Bundle args = new Bundle();
                        args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, val);
                        boolean ok = input.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);

                        // 3. Fallback: Paste via Clipboard jika ACTION_SET_TEXT gagal
                        if (!ok && cm != null) {
                            ClipData clip = ClipData.newPlainText("inject_val", val);
                            cm.setPrimaryClip(clip);
                            input.performAction(AccessibilityNodeInfo.ACTION_PASTE);
                        }

                        log("  [FORM]: Field '" + fieldType + "' diisi -> '" + val + "'");
                        filled.add(fieldType);
                        SystemClock.sleep(300);
                    }
                }
            }

            if (filled.size() >= 5) {
                break;
            }

            // Scroll turun sedikit untuk field berikutnya
            DisplayMetrics dm = getResources().getDisplayMetrics();
            dispatchSwipeSync(dm.widthPixels / 2f, dm.heightPixels * 0.70f, dm.widthPixels / 2f, dm.heightPixels * 0.45f, 350);
            SystemClock.sleep(800);
        }

        // Tutup virtual keyboard agar layar kembali bersih
        performGlobalAction(GLOBAL_ACTION_BACK);
        SystemClock.sleep(400);

        log("  [FORM]: Formulir selesai diisi. Field terisi: " + filled);
    }

    // --- DETEKSI & PENEKANAN TOMBOL DAFTAR ---

    private void findAllDaftarCandidates(AccessibilityNodeInfo node, List<AccessibilityNodeInfo> list) {
        if (node == null) return;
        String text = node.getText() != null ? node.getText().toString() : "";
        String desc = node.getContentDescription() != null ? node.getContentDescription().toString() : "";
        String combined = (text + " " + desc).trim().toLowerCase(Locale.ROOT);
        String norm = normalize(combined);

        if (!norm.isEmpty() && norm.length() <= 35) {
            boolean isNegative = norm.contains("cara") || norm.contains("syarat") || norm.contains("panduan")
                    || norm.contains("tentang") || norm.contains("about") || norm.contains("hasil");
            if (!isNegative) {
                if (norm.contains("daftar") || norm.contains("register") || norm.contains("registrasi")
                        || norm.contains("signup") || norm.contains("sign up") || norm.contains("gabung")
                        || norm.contains("buatakun") || norm.contains("bukaakun") || norm.contains("join")) {
                    Rect r = new Rect();
                    node.getBoundsInScreen(r);
                    if (r.width() > 0 && r.height() > 0 && r.bottom > 160 && r.top < 1620) {
                        list.add(node);
                    }
                }
            }
        }

        for (int i = 0; i < node.getChildCount(); i++) {
            findAllDaftarCandidates(node.getChild(i), list);
        }
    }

    public boolean clickDaftarButton(int width, int height) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        List<AccessibilityNodeInfo> candidates = new ArrayList<>();
        findAllDaftarCandidates(root, candidates);

        if (!candidates.isEmpty()) {
            AccessibilityNodeInfo btn = candidates.get(0);
            Rect rect = new Rect();
            btn.getBoundsInScreen(rect);

            int tapX = rect.centerX();
            int tapY = rect.centerY();
            if (tapX <= 0 || tapY <= 0) {
                tapX = (int)(width * 0.25f);
                tapY = (int)(height * 0.65f);
            }

            String label = btn.getContentDescription() != null ? btn.getContentDescription().toString() : "";
            if (label.isEmpty() && btn.getText() != null) label = btn.getText().toString();

            log("  [WEB]: Tombol DAFTAR ditemukan ('" + label + "') di (" + tapX + ", " + tapY + ") -> Dispatch TAP fisik...");
            btn.performAction(AccessibilityNodeInfo.ACTION_CLICK);
            dispatchTapSync(tapX, tapY, 1500);
            return true;
        }
        return false;
    }

    // --- KLIK HASIL PENCARIAN GOOGLE ---

    private void findGoogleResultCandidates(AccessibilityNodeInfo node, List<AccessibilityNodeInfo> list) {
        if (node == null) return;
        Rect r = new Rect();
        node.getBoundsInScreen(r);
        String text = node.getText() != null ? node.getText().toString() : "";
        String desc = node.getContentDescription() != null ? node.getContentDescription().toString() : "";
        String combined = (text + " " + desc).trim().toLowerCase(Locale.ROOT);

        if (r.top >= 480 && r.bottom <= 1500 && r.width() >= 300 && r.height() >= 35) {
            boolean isFilterOrNav = combined.contains("mode ai") || combined.contains("semua")
                    || combined.contains("shopping") || combined.contains("gambar")
                    || combined.contains("video") || combined.contains("tentang hasil ini")
                    || combined.contains("penelusuran") || combined.contains("ke beranda");
            if (!isFilterOrNav) {
                if (combined.contains("http") || combined.contains(".com") || combined.contains("link")
                        || combined.contains("situs") || combined.contains("slot") || combined.contains("gacor")
                        || combined.contains("resmi") || text.length() > 20) {
                    list.add(node);
                }
            }
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            findGoogleResultCandidates(node.getChild(i), list);
        }
    }

    public boolean clickFirstSearchResult(int width, int height) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        List<AccessibilityNodeInfo> candidates = new ArrayList<>();
        findGoogleResultCandidates(root, candidates);

        int tapX = width / 2;
        int tapY = (int) (height * 0.42f); // default koordinat link teratas (~688 px)

        if (!candidates.isEmpty()) {
            AccessibilityNodeInfo best = candidates.get(0);
            Rect r = new Rect();
            best.getBoundsInScreen(r);
            if (r.centerX() > 0 && r.centerY() > 450) {
                tapX = r.centerX();
                tapY = r.centerY();
                log("  [SEARCH]: Link hasil Google terdeteksi di (" + tapX + ", " + tapY + ") -> Dispatch TAP fisik...");
            }
        } else {
            log("  [SEARCH]: Titik link hasil teratas di (" + tapX + ", " + tapY + ") -> Dispatch TAP fisik...");
        }

        dispatchTapSync(tapX, tapY, 1500);
        return true;
    }

    // --- APLIKASI SLOT ACAK & RETURN KE HOME ---

    public void openRandomSlotApp() {
        List<String> candidates = new ArrayList<>();
        candidates.add("casino.games.slot.machines.free");
        candidates.add("RR33.COM");
        candidates.add("com.k68.id.xulsfy");
        candidates.add("org.chromium.webapk.a1ffa4016fb2cda0c_v2");

        PackageManager pm = getPackageManager();
        List<String> eligible = new ArrayList<>();
        for (PackageInfo pi : pm.getInstalledPackages(0)) {
            String pkg = pi.packageName;
            if (candidates.contains(pkg)) {
                eligible.add(pkg);
            } else if (pkg.toLowerCase().contains("slot") || pkg.toLowerCase().contains("casino")) {
                if (!pkg.equals(getPackageName())) {
                    eligible.add(pkg);
                }
            }
        }

        String chosen = eligible.isEmpty() ? "casino.games.slot.machines.free" : eligible.get(new Random().nextInt(eligible.size()));
        log("[STEP 5]: Membuka aplikasi slot acak: " + chosen + "...");
        Intent launch = pm.getLaunchIntentForPackage(chosen);
        if (launch != null) {
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(launch);
        }

        SystemClock.sleep(3000);
        DisplayMetrics dm = getResources().getDisplayMetrics();
        dispatchSwipeSync(dm.widthPixels / 2f, dm.heightPixels * 0.6f, dm.widthPixels / 2f, dm.heightPixels * 0.4f, 300);
        SystemClock.sleep(1000);

        log("[STEP 5]: Aplikasi slot selesai diinteraksi, menutup aplikasi...");
        performGlobalAction(GLOBAL_ACTION_HOME);
        SystemClock.sleep(500);
    }

    public void goToHomeScreen() {
        log("[SELESAI]: Kembali ke halaman Home Android (bukan Magic Ocean)...");
        performGlobalAction(GLOBAL_ACTION_HOME);
    }

    // --- EKSEKUSI SIKLUS UTAMA ---

    public void startCycle(Runnable onComplete) {
        if (mIsRunningCycle) {
            log("Siklus sedang berjalan, lewati pemicu ganda.");
            return;
        }
        mIsRunningCycle = true;
        mExecutor.execute(() -> {
            try {
                log("==================================================");
                log("=== MEMULAI SIKLUS INJECT-IKLAN (LANGKAH 1 s/d 5) ===");
                log("==================================================");

                DisplayMetrics dm = getResources().getDisplayMetrics();
                int width = dm.widthPixels;
                int height = dm.heightPixels;

                // Step 1 & 2: Buat keyword dan buka Google Search di Chrome
                String query = generateRandomSlotKeyword();
                log("[STEP 1 & 2]: Membuka Chrome & Google Search query '" + query + "'");
                String url = "https://www.google.com/search?q=" + URLEncoder.encode(query, "UTF-8");
                Intent chromeIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                chromeIntent.setPackage("com.android.chrome");
                chromeIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(chromeIntent);

                // Tunggu Chrome termuat dan hasil Google tampil
                SystemClock.sleep(3500);

                // Step 3: Klik link hasil pencarian Google agar masuk ke web
                log("[STEP 3]: Menekan link hasil pencarian Google untuk masuk ke website...");
                clickFirstSearchResult(width, height);

                // Tunggu halaman website terbuka & termuat
                log("[STEP 3]: Menunggu halaman web termuat (4 detik)...");
                SystemClock.sleep(4000);

                // Cari dan klik tombol DAFTAR (dengan scroll jika diperlukan)
                boolean daftarFound = false;
                for (int attempt = 1; attempt <= 3; attempt++) {
                    log("[STEP 3]: Mencari tombol DAFTAR di web (percobaan #" + attempt + ")...");
                    daftarFound = clickDaftarButton(width, height);
                    if (daftarFound) {
                        break;
                    }
                    log("[STEP 3]: Scroll konten web ke bawah...");
                    dispatchSwipeSync(width / 2f, height * 0.65f, width / 2f, height * 0.35f, 350);
                    SystemClock.sleep(1500);
                }

                if (!daftarFound) {
                    log("  [FALLBACK]: Mencoba tap tombol DAFTAR di koordinat (" + (int)(width * 0.25f) + ", " + (int)(height * 0.65f) + ")...");
                    dispatchTapSync(width * 0.25f, height * 0.65f, 1500);
                    daftarFound = true;
                }

                if (daftarFound) {
                    // Tunggu form pendaftaran terbuka
                    log("[STEP 4]: Menunggu formulir pendaftaran termuat (3.5 detik)...");
                    SystemClock.sleep(3500);
                    // Isi formulir pendaftaran akun (tanpa submit)
                    fillFormFields();
                    SystemClock.sleep(1200);
                }

                // Tutup Chrome / Kembali ke HOME
                performGlobalAction(GLOBAL_ACTION_HOME);
                SystemClock.sleep(800);

                // Step 5: Buka aplikasi slot acak sesaat
                openRandomSlotApp();

                // Langkah Terakhir: Kembali ke Halaman HOME saja (Bukan Magic Ocean)
                SystemClock.sleep(500);
                goToHomeScreen();

                log("=== SIKLUS INJECT-IKLAN BERHASIL (SELESAI DI HOME) ===");
                log("==================================================");

            } catch (Exception e) {
                log("ERROR Siklus Inject Iklan: " + e.getMessage());
            } finally {
                mIsRunningCycle = false;
                if (onComplete != null) {
                    mMainHandler.post(onComplete);
                }
            }
        });
    }
}
