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
 * Membaca countdown iklan, skip button, close X, Report Ads, dan popup reward via on-device ML Kit OCR.
 */
public final class AdTimerReader {
    private static final Pattern TIMER = Pattern.compile(
            "(?i)(?:^|\\D)([0-9]{1,2})\\s*(?:s|sec(?:onds?)?|detik|left|remaining|tersisa)\\b"
                    + "|(?:skip|lewati|tutup)\\s*(?:in)?\\s*([0-9]{1,2})\\b");
    private static final Pattern STANDALONE_TIMER = Pattern.compile("^\\s*([0-9]{1,2})\\s*$");
    private static final Pattern SKIP_BTN = Pattern.compile(
            "^\\s*(?:>{1,2}\\|?|\\|?>{1,2}|»|›|→|skip|next|lewati|lanjut)\\s*$", Pattern.CASE_INSENSITIVE);
    private static final Pattern CLOSE_BTN = Pattern.compile(
            "^\\s*(?:[x×✕✖]|close|tutup)\\s*$", Pattern.CASE_INSENSITIVE);

    private static final long READ_INTERVAL_MS = 1_000L;
    private static final long FRESH_RESULT_MS = 3_500L;

    private final com.google.mlkit.vision.text.TextRecognizer recognizer =
            TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);

    private volatile boolean reading;
    private volatile int remainingSeconds = -1;
    private volatile boolean skipButtonVisible;
    private volatile float skipButtonX = -1;
    private volatile float skipButtonY = -1;
    private volatile boolean closeButtonVisible;
    private volatile float closeButtonX = -1;
    private volatile float closeButtonY = -1;

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

    private volatile long updatedAt;
    private long lastRequestAt;

    public void readIfDue(Bitmap fullScreen) {
        long now = SystemClock.elapsedRealtime();
        if (reading || now - lastRequestAt < READ_INTERVAL_MS || fullScreen == null) {
            return;
        }
        lastRequestAt = now;
        reading = true;

        recognizer.process(InputImage.fromBitmap(fullScreen, 0))
                .addOnSuccessListener(result -> parse(result, fullScreen.getWidth(), fullScreen.getHeight()))
                .addOnCompleteListener(task -> reading = false);
    }

    private void parse(Text result, int screenWidth, int screenHeight) {
        int foundTimer = -1;
        boolean foundSkip = false;
        float sX = -1, sY = -1;
        boolean foundClose = false;
        float cX = -1, cY = -1;

        boolean foundReport = false;
        float repX = -1, repY = -1;

        boolean hasConfirm = false;
        float contX = -1, contY = -1;

        boolean foundReward = false;
        float rewX = -1, rewY = -1;

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect box = block.getBoundingBox();
            if (box == null) continue;
            String text = block.getText().trim();
            String lower = text.toLowerCase();

            // 1. Countdown timer di bagian atas
            if (box.centerY() < screenHeight * 0.35f) {
                Matcher matcher = TIMER.matcher(text);
                if (matcher.find()) {
                    String group = matcher.group(1) != null ? matcher.group(1) : matcher.group(2);
                    int value = Integer.parseInt(group);
                    if (value >= 0 && value <= 90) {
                        foundTimer = value;
                    }
                }

                boolean atTopCorner = box.centerX() <= screenWidth * 0.40f
                        || box.centerX() >= screenWidth * 0.60f;

                Matcher singleNumber = STANDALONE_TIMER.matcher(text);
                if (atTopCorner && singleNumber.matches()) {
                    int value = Integer.parseInt(singleNumber.group(1));
                    if (value >= 0 && value <= 90) {
                        foundTimer = value;
                    }
                }

                if (atTopCorner) {
                    if (SKIP_BTN.matcher(text).matches() || lower.startsWith("skip ") || lower.startsWith("next ")) {
                        foundSkip = true;
                        sX = box.centerX();
                        sY = box.centerY();
                    } else if (CLOSE_BTN.matcher(text).matches()) {
                        foundClose = true;
                        cX = box.centerX();
                        cY = box.centerY();
                    }
                }
            }

            // Skip atau Close di pojok kanan bawah (iklan landscape / bottom action)
            boolean atBottomRight = box.centerY() >= screenHeight * 0.70f && box.centerX() >= screenWidth * 0.60f;
            if (atBottomRight) {
                if (SKIP_BTN.matcher(text).matches() || lower.startsWith("skip ") || lower.startsWith("next ")) {
                    foundSkip = true;
                    sX = box.centerX();
                    sY = box.centerY();
                } else if (CLOSE_BTN.matcher(text).matches()) {
                    foundClose = true;
                    cX = box.centerX();
                    cY = box.centerY();
                }
            }

            // 2. Report Ads / Feedback dialog detection
            if (lower.contains("report ad") || lower.contains("report ads") || lower.contains("feedback") || lower.contains("umpan balik")) {
                foundReport = true;
                // Tombol X ada di sebelah kanan teks Report Ads: sekitar box.right + 115 atau 579 di layar 720
                float sxRatio = screenWidth / 720f;
                float syRatio = screenHeight / 1640f;
                repX = Math.min(screenWidth - 40 * sxRatio, box.centerX() + 218 * sxRatio);
                repY = box.centerY();
            }

            // 3. Confirm to close dialog -> Continue
            if (lower.contains("confirm to close") || lower.contains("close it") || lower.contains("will not be rewarded")) {
                hasConfirm = true;
            }
            if (lower.contains("continue") || lower.contains("lanjutkan") || lower.contains("resume")) {
                if (box.centerY() > screenHeight * 0.40f) {
                    contX = box.centerX();
                    contY = box.centerY();
                }
            }

            // 4. Modal reward dialog (Klaim / Koleksi / Bebas Klik / Menarik)
            if (box.centerY() > screenHeight * 0.50f) {
                if (lower.equals("klaim") || lower.equals("claim") || lower.equals("koleksi")
                        || lower.equals("collect") || lower.contains("bebas klik") || lower.equals("menarik")
                        || lower.contains("gandakan")) {
                    foundReward = true;
                    rewX = box.centerX();
                    rewY = box.centerY();
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
        }
        if (foundClose) {
            closeButtonVisible = true;
            closeButtonX = cX;
            closeButtonY = cY;
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
        } else {
            rewardModalVisible = false;
        }

        updatedAt = SystemClock.elapsedRealtime();
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

    public boolean hasRecentCloseButton() {
        return SystemClock.elapsedRealtime() - updatedAt <= FRESH_RESULT_MS && closeButtonVisible;
    }

    public float getCloseButtonX() {
        return closeButtonX;
    }

    public float getCloseButtonY() {
        return closeButtonY;
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

    public void reset() {
        remainingSeconds = -1;
        skipButtonVisible = false;
        skipButtonX = -1;
        skipButtonY = -1;
        closeButtonVisible = false;
        closeButtonX = -1;
        closeButtonY = -1;
        reportAdsVisible = false;
        reportAdsCloseX = -1;
        reportAdsCloseY = -1;
        confirmCloseVisible = false;
        continueButtonX = -1;
        continueButtonY = -1;
        rewardModalVisible = false;
        rewardButtonX = -1;
        rewardButtonY = -1;
        updatedAt = 0;
    }

    public void close() {
        recognizer.close();
    }
}
