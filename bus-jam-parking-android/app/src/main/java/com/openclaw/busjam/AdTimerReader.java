package com.openclaw.busjam;

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
 * Membaca countdown iklan dan tombol skip (>, >>, >|) / close (X) di pojok atas dengan OCR on-device ML Kit.
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

    private static final long READ_INTERVAL_MS = 1_100L;
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
    private volatile long updatedAt;
    private long lastRequestAt;

    public void readIfDue(Bitmap fullScreen) {
        long now = SystemClock.elapsedRealtime();
        if (reading || now - lastRequestAt < READ_INTERVAL_MS || fullScreen == null) {
            return;
        }
        lastRequestAt = now;
        reading = true;

        int width = fullScreen.getWidth();
        int height = Math.min(fullScreen.getHeight(), Math.max(220, fullScreen.getHeight() / 4));
        Bitmap crop = Bitmap.createBitmap(fullScreen, 0, 0, width, height);
        recognizer.process(InputImage.fromBitmap(crop, 0))
                .addOnSuccessListener(result -> parse(result, crop.getWidth(), crop.getHeight()))
                .addOnCompleteListener(task -> {
                    if (!crop.isRecycled()) crop.recycle();
                    reading = false;
                });
    }

    private void parse(Text result, int cropWidth, int cropHeight) {
        int foundTimer = -1;
        boolean foundSkip = false;
        float sX = -1;
        float sY = -1;
        boolean foundClose = false;
        float cX = -1;
        float cY = -1;

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect box = block.getBoundingBox();
            if (box == null || box.centerY() > cropHeight) continue;
            String text = block.getText();
            Matcher matcher = TIMER.matcher(text);
            if (matcher.find()) {
                String group = matcher.group(1) != null ? matcher.group(1) : matcher.group(2);
                int value = Integer.parseInt(group);
                if (value >= 0 && value <= 90) {
                    foundTimer = value;
                    break;
                }
            }

            boolean atTopCorner = box.centerX() <= cropWidth * 0.40f
                    || box.centerX() >= cropWidth * 0.60f;

            Matcher singleNumber = STANDALONE_TIMER.matcher(text);
            if (atTopCorner && singleNumber.matches()) {
                int value = Integer.parseInt(singleNumber.group(1));
                if (value >= 0 && value <= 90) {
                    foundTimer = value;
                    break;
                }
            }

            // Deteksi tombol skip (>, >>, >|) atau close (X) di pojok kiri atas atau kanan atas
            if (atTopCorner) {
                String clean = text.trim();
                String lower = clean.toLowerCase();
                if (SKIP_BTN.matcher(clean).matches() || lower.startsWith("skip ") || lower.startsWith("next ")) {
                    foundSkip = true;
                    sX = box.centerX();
                    sY = box.centerY();
                } else if (CLOSE_BTN.matcher(clean).matches()) {
                    foundClose = true;
                    cX = box.centerX();
                    cY = box.centerY();
                }
            }
        }

        if (foundTimer >= 0) {
            remainingSeconds = foundTimer;
        }
        if (foundTimer >= 0 || foundSkip || foundClose) {
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
            updatedAt = SystemClock.elapsedRealtime();
        }
    }

    public int recentRemainingSeconds() {
        return SystemClock.elapsedRealtime() - updatedAt <= FRESH_RESULT_MS
                ? remainingSeconds
                : -1;
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

    public void reset() {
        remainingSeconds = -1;
        skipButtonVisible = false;
        skipButtonX = -1;
        skipButtonY = -1;
        closeButtonVisible = false;
        closeButtonX = -1;
        closeButtonY = -1;
        updatedAt = 0;
    }

    public void close() {
        recognizer.close();
    }
}
