package com.openclaw.colorpowerpop;

import android.graphics.Bitmap;
import android.graphics.Rect;
import android.os.SystemClock;

import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Membaca countdown iklan, skip button (>>, >, >>|, >|), close X, Report Ads,
 * dan popup reward via on-device ML Kit OCR pada posisi pojok kanan atas, kiri atas, dan kanan bawah.
 */
public final class AdTimerReader {
    private static final Pattern TIMER = Pattern.compile(
            "(?i)(?:^|\\D)([0-9]{1,2})\\s*(?:s|sec(?:onds?)?|detik|left|remaining|tersisa)\\b"
                    + "|(?:skip|lewati|tutup)\\s*(?:in)?\\s*([0-9]{1,2})\\b");
    private static final Pattern STANDALONE_TIMER = Pattern.compile("^\\s*([0-9]{1,2})\\s*$");
    private static final Pattern SKIP_BTN = Pattern.compile(
            "^\\s*(?:>{1,2}[|Il1]?|[|Il1]?>{1,2}|»|›|→|skip(?:\\s*(?:>{1,2}[|Il1]?|»|›|→|[0-9]{1,2}))?|next(?:\\s*(?:>{1,2}[|Il1]?|»|›|→|[0-9]{1,2}))?|lewati|lanjut)\\s*$",
            Pattern.CASE_INSENSITIVE
    );
    private static final Pattern CLOSE_BTN = Pattern.compile(
            "^\\s*(?:[x×✕✖+]|close|tutup)\\s*$",
            Pattern.CASE_INSENSITIVE
    );

    private static final long READ_INTERVAL_MS = 1_000L;
    private static final long FRESH_RESULT_MS = 3_500L;

    private final com.google.mlkit.vision.text.TextRecognizer recognizer =
            TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);

    private volatile boolean reading;
    private volatile int remainingSeconds = -1;
    private volatile boolean skipButtonVisible;
    private volatile float skipButtonX = -1;
    private volatile float skipButtonY = -1;
    private volatile String skipButtonText = "";
    private volatile String skipCorner = "";

    private volatile boolean closeButtonVisible;
    private volatile float closeButtonX = -1;
    private volatile float closeButtonY = -1;
    private volatile String closeButtonText = "";
    private volatile String closeCorner = "";

    // Report Ads detection
    private volatile boolean reportAdsVisible;
    private volatile float reportAdsCloseX = -1;
    private volatile float reportAdsCloseY = -1;

    // Confirm to close detection
    private volatile boolean confirmCloseVisible;
    private volatile float continueButtonX = -1;
    private volatile float continueButtonY = -1;

    // Reward modal detection (Klaim / Koleksi / Menarik)
    private volatile boolean rewardModalVisible;
    private volatile float rewardButtonX = -1;
    private volatile float rewardButtonY = -1;

    // Game loading screen detection
    private volatile boolean loadingTextVisible;

    private volatile long updatedAt;
    private long lastRequestAt;

    public void readIfDue(Bitmap fullScreen) {
        long now = SystemClock.elapsedRealtime();
        if (reading || now - lastRequestAt < READ_INTERVAL_MS || fullScreen == null || fullScreen.isRecycled()) {
            return;
        }
        lastRequestAt = now;
        reading = true;

        final int width = fullScreen.getWidth();
        final int height = fullScreen.getHeight();
        final Bitmap copy = fullScreen.copy(Bitmap.Config.ARGB_8888, false);
        if (copy == null) {
            reading = false;
            return;
        }

        recognizer.process(InputImage.fromBitmap(copy, 0))
                .addOnSuccessListener(result -> parse(result, width, height))
                .addOnCompleteListener(task -> {
                    if (!copy.isRecycled()) {
                        copy.recycle();
                    }
                    reading = false;
                });
    }

    private void parse(Text result, int screenWidth, int screenHeight) {
        int foundTimer = -1;
        boolean foundSkip = false;
        float sX = -1, sY = -1;
        String sText = "";
        String sCorner = "";

        boolean foundClose = false;
        float cX = -1, cY = -1;
        String cText = "";
        String cCorner = "";

        boolean foundReport = false;
        float repX = -1, repY = -1;

        boolean hasConfirm = false;
        float contX = -1, contY = -1;

        boolean foundReward = false;
        float rewX = -1, rewY = -1;
        boolean foundLoading = false;

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect box = block.getBoundingBox();
            if (box == null) continue;
            String text = block.getText().trim();
            String lower = text.toLowerCase();

            boolean isLandscape = screenWidth > screenHeight;

            // Tentukan posisi sudut layar: kanan atas, kiri atas, atau kanan bawah (adaptif portrait & landscape)
            float topMaxY = isLandscape ? screenHeight * 0.40f : screenHeight * 0.28f;
            float bottomMinY = isLandscape ? screenHeight * 0.60f : screenHeight * 0.70f;
            float leftMaxX = isLandscape ? screenWidth * 0.38f : screenWidth * 0.45f;
            float rightMinX = isLandscape ? screenWidth * 0.62f : screenWidth * 0.55f;

            int edgeCornerX = isLandscape ? 240 : 200;
            int edgeCornerY = isLandscape ? 160 : 200;
            int edgeCornerBottomY = isLandscape ? 180 : 220;

            boolean edgeTopRight = box.centerX() >= screenWidth - edgeCornerX && box.centerY() <= edgeCornerY;
            boolean edgeTopLeft = box.centerX() <= edgeCornerX && box.centerY() <= edgeCornerY;
            boolean edgeBottomRight = box.centerX() >= screenWidth - edgeCornerX && box.centerY() >= screenHeight - edgeCornerBottomY;

            boolean atTopRight = edgeTopRight || (box.centerX() >= rightMinX && box.centerY() <= topMaxY);
            boolean atTopLeft = edgeTopLeft || (box.centerX() <= leftMaxX && box.centerY() <= topMaxY);
            boolean atBottomRight = edgeBottomRight || (box.centerX() >= rightMinX && box.centerY() >= bottomMinY);
            boolean inTargetCorner = atTopRight || atTopLeft || atBottomRight;
            String cornerLabel = atTopRight ? "kanan atas" : (atTopLeft ? "kiri atas" : (atBottomRight ? "kanan bawah" : ""));

            // 1. Countdown timer di bagian atas atau kanan bawah
            if (box.centerY() <= topMaxY || atBottomRight) {
                Matcher matcher = TIMER.matcher(text);
                if (matcher.find()) {
                    String group = matcher.group(1) != null ? matcher.group(1) : matcher.group(2);
                    try {
                        int value = Integer.parseInt(group);
                        if (value >= 0 && value <= 90) {
                            foundTimer = value;
                        }
                    } catch (Throwable ignored) {
                    }
                }

                Matcher singleNumber = STANDALONE_TIMER.matcher(text);
                if ((atTopRight || atTopLeft) && singleNumber.matches()) {
                    try {
                        int value = Integer.parseInt(singleNumber.group(1));
                        if (value >= 0 && value <= 90) {
                            foundTimer = value;
                        }
                    } catch (Throwable ignored) {
                    }
                }
            }

            // 2. Deteksi tombol skip (>>, >, >>|, >|, skip) & close (X, close) di:
            //    Pojok kanan atas, kiri atas, atau kanan bawah
            if (inTargetCorner) {
                if (isSkipMatch(text)) {
                    foundSkip = true;
                    sX = box.centerX();
                    sY = box.centerY();
                    sText = text;
                    sCorner = cornerLabel;
                } else if (isCloseMatch(text)) {
                    foundClose = true;
                    cX = box.centerX();
                    cY = box.centerY();
                    cText = text;
                    cCorner = cornerLabel;
                }
            }

            // 3. Report Ads / Feedback dialog detection
            if (lower.contains("report ad") || lower.contains("report ads") || lower.contains("feedback") || lower.contains("umpan balik")) {
                foundReport = true;
                float sxRatio = screenWidth / 720f;
                repX = Math.min(screenWidth - 40 * sxRatio, box.centerX() + 218 * sxRatio);
                repY = box.centerY();
            }

            // 4. Confirm to close dialog -> Continue
            if (lower.contains("confirm to close") || lower.contains("close it") || lower.contains("will not be rewarded")) {
                hasConfirm = true;
            }
            if (lower.contains("continue") || lower.contains("lanjutkan") || lower.contains("resume")) {
                if (box.centerY() > screenHeight * 0.40f) {
                    contX = box.centerX();
                    contY = box.centerY();
                }
            }

            // 5. Modal reward dialog (Klaim / Koleksi / Bebas Klik / Menarik / Gandakan / Dapatkan)
            //    Gunakan contains agar variasi seperti "Klaim (2000)" atau "Koleksi Hadiah" tetap cocok
            if (box.centerY() > screenHeight * 0.40f && !lower.contains("color power pop") && !lower.contains("bot") && !lower.contains("wajib tunggu")) {
                if (lower.contains("klaim") || lower.contains("claim")
                        || lower.contains("koleksi") || lower.contains("collect")
                        || lower.contains("bebas klik") || lower.contains("menarik")
                        || lower.contains("gandakan") || lower.contains("ganda")
                        || lower.contains("dapatkan") || lower.contains("ambil")
                        || lower.contains("terima")) {
                    foundReward = true;
                    rewX = box.centerX();
                    rewY = box.centerY();
                }
            }

            // 6. Teks loading / memuat game (HANYA jika bukan modal reward dan bukan tombol klaim)
            //    HAPUS regex persen sendirian agar bonus multiplier tidak salah terdeteksi loading!
            if (!foundReward && !lower.contains("klaim") && !lower.contains("koleksi") && !lower.contains("claim") && !lower.contains("collect")) {
                if (lower.contains("loading") || lower.contains("sedang memuat")
                        || (lower.contains("memuat") && !lower.contains("menarik"))
                        || lower.contains("please wait") || lower.contains("menghubungkan")) {
                    foundLoading = true;
                }
            }
        }

        if (foundTimer >= 0) {
            remainingSeconds = foundTimer;
        }
        if (foundSkip) {
            skipButtonVisible = true;
            skipButtonX = sX;
            skipButtonY = sY;
            skipButtonText = sText;
            skipCorner = sCorner;
        } else {
            skipButtonVisible = false;
        }
        if (foundClose) {
            closeButtonVisible = true;
            closeButtonX = cX;
            closeButtonY = cY;
            closeButtonText = cText;
            closeCorner = cCorner;
        } else {
            closeButtonVisible = false;
        }
        if (foundReport) {
            reportAdsVisible = true;
            reportAdsCloseX = repX;
            reportAdsCloseY = repY;
        } else {
            reportAdsVisible = false;
        }
        if (hasConfirm && contX > 0) {
            confirmCloseVisible = true;
            continueButtonX = contX;
            continueButtonY = contY;
        } else {
            confirmCloseVisible = false;
        }
        if (foundReward) {
            rewardModalVisible = true;
            rewardButtonX = rewX;
            rewardButtonY = rewY;
            loadingTextVisible = false; // Jika tombol klaim/reward muncul, JANGAN PERNAH anggap loading!
        } else {
            rewardModalVisible = false;
            loadingTextVisible = foundLoading;
        }
        updatedAt = SystemClock.elapsedRealtime();
    }

    private static boolean isSkipMatch(String raw) {
        if (raw == null) return false;
        String clean = raw.trim();
        if (SKIP_BTN.matcher(clean).matches()) return true;
        String nospaces = clean.replaceAll("\\s+", "").toLowerCase();
        if (clean.length() <= 12 && (clean.contains(">>|") || clean.contains(">|") || clean.contains(">>") || clean.contains(">"))) {
            return true;
        }
        return nospaces.equals(">") || nospaces.equals(">>") || nospaces.equals(">|") || nospaces.equals(">>|")
                || nospaces.equals(">i") || nospaces.equals(">>i") || nospaces.equals(">l") || nospaces.equals(">>l")
                || nospaces.equals(">1") || nospaces.equals(">>1") || nospaces.equals("|>") || nospaces.equals("|>>")
                || nospaces.equals("»") || nospaces.equals("›") || nospaces.equals("→")
                || nospaces.contains(">>") || nospaces.contains(">>|") || nospaces.contains(">|")
                || nospaces.startsWith("skip") || nospaces.startsWith("next")
                || nospaces.startsWith("lewati") || nospaces.startsWith("lanjut");
    }

    private static boolean isCloseMatch(String raw) {
        if (raw == null) return false;
        String clean = raw.trim();
        if (CLOSE_BTN.matcher(clean).matches()) return true;
        String nospaces = clean.replaceAll("\\s+", "").toLowerCase();
        if (clean.length() <= 8 && (clean.equalsIgnoreCase("x") || clean.contains("×") || clean.equalsIgnoreCase("close") || clean.equalsIgnoreCase("tutup"))) {
            return true;
        }
        return nospaces.equals("x") || nospaces.equals("×") || nospaces.equals("✕") || nospaces.equals("✖")
                || nospaces.equals("+") || nospaces.equals("close") || nospaces.equals("tutup");
    }

    public int recentRemainingSeconds() {
        return SystemClock.elapsedRealtime() - updatedAt <= FRESH_RESULT_MS ? remainingSeconds : -1;
    }

    public boolean hasRecentSkipButton() {
        return SystemClock.elapsedRealtime() - updatedAt <= FRESH_RESULT_MS && skipButtonVisible;
    }

    public float getSkipButtonX() {
        return skipButtonX;
    }

    public float getSkipButtonY() {
        return skipButtonY;
    }

    public String getSkipButtonText() {
        return skipButtonText;
    }

    public String getSkipCorner() {
        return skipCorner;
    }

    public boolean hasRecentCloseButton() {
        return SystemClock.elapsedRealtime() - updatedAt <= FRESH_RESULT_MS && closeButtonVisible;
    }

    public float getCloseButtonX() {
        return closeButtonX;
    }

    public float getCloseButtonY() {
        return closeButtonY;
    }

    public String getCloseButtonText() {
        return closeButtonText;
    }

    public String getCloseCorner() {
        return closeCorner;
    }

    public boolean hasRecentReportAds() {
        return SystemClock.elapsedRealtime() - updatedAt <= FRESH_RESULT_MS && reportAdsVisible;
    }

    public float getReportAdsCloseX() {
        return reportAdsCloseX;
    }

    public float getReportAdsCloseY() {
        return reportAdsCloseY;
    }

    public boolean hasRecentConfirmClose() {
        return SystemClock.elapsedRealtime() - updatedAt <= FRESH_RESULT_MS && confirmCloseVisible;
    }

    public float getContinueButtonX() {
        return continueButtonX;
    }

    public float getContinueButtonY() {
        return continueButtonY;
    }

    public boolean hasRecentRewardModal() {
        return SystemClock.elapsedRealtime() - updatedAt <= FRESH_RESULT_MS && rewardModalVisible;
    }

    public float getRewardButtonX() {
        return rewardButtonX;
    }

    public float getRewardButtonY() {
        return rewardButtonY;
    }

    public boolean hasRecentLoadingText() {
        return SystemClock.elapsedRealtime() - updatedAt <= FRESH_RESULT_MS && loadingTextVisible;
    }

    public void reset() {
        remainingSeconds = -1;
        skipButtonVisible = false;
        skipButtonX = -1;
        skipButtonY = -1;
        skipButtonText = "";
        skipCorner = "";
        closeButtonVisible = false;
        closeButtonX = -1;
        closeButtonY = -1;
        closeButtonText = "";
        closeCorner = "";
        reportAdsVisible = false;
        reportAdsCloseX = -1;
        reportAdsCloseY = -1;
        confirmCloseVisible = false;
        continueButtonX = -1;
        continueButtonY = -1;
        rewardModalVisible = false;
        rewardButtonX = -1;
        rewardButtonY = -1;
        loadingTextVisible = false;
        updatedAt = 0;
    }

    public void close() {
        recognizer.close();
    }
}
