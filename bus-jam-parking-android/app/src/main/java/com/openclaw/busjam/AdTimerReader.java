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
 * Membaca countdown iklan di pojok atas dengan OCR on-device ML Kit.
 * Tidak ada gambar/teks yang dikirim ke laptop atau server bot.
 */
public final class AdTimerReader {
    private static final Pattern TIMER = Pattern.compile(
            "(?i)(?:^|\\D)([0-9]{1,2})\\s*(?:s|sec(?:onds?)?|detik|left|remaining|tersisa)\\b"
                    + "|(?:skip|lewati|tutup)\\s*(?:in)?\\s*([0-9]{1,2})\\b");
    private static final Pattern STANDALONE_TIMER = Pattern.compile("^\\s*([0-9]{1,2})\\s*$");
    private static final long READ_INTERVAL_MS = 1_300L;
    private static final long FRESH_RESULT_MS = 3_500L;

    private final com.google.mlkit.vision.text.TextRecognizer recognizer =
            TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
    private volatile boolean reading;
    private volatile int remainingSeconds = -1;
    private volatile long updatedAt;
    private long lastRequestAt;

    public void readIfDue(Bitmap fullScreen) {
        long now = SystemClock.elapsedRealtime();
        if (reading || now - lastRequestAt < READ_INTERVAL_MS || fullScreen == null) {
            return;
        }
        lastRequestAt = now;
        reading = true;

        // Countdown iklan muncul di salah satu pojok atas. Crop mengurangi false-positive
        // dari nominal uang/level game di bagian tengah layar.
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
        int found = -1;
        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect box = block.getBoundingBox();
            if (box == null || box.centerY() > cropHeight) continue;
            String text = block.getText();
            Matcher matcher = TIMER.matcher(text);
            if (matcher.find()) {
                String group = matcher.group(1) != null ? matcher.group(1) : matcher.group(2);
                int value = Integer.parseInt(group);
                if (value >= 0 && value <= 90) {
                    found = value;
                    break;
                }
            }
            // Sejumlah SDK hanya menampilkan angka kecil dalam lingkaran di salah satu
            // pojok atas. Jangan baca angka tengah layar seperti nominal hadiah/level.
            boolean atTopCorner = box.centerX() <= cropWidth * 0.38f
                    || box.centerX() >= cropWidth * 0.62f;
            Matcher singleNumber = STANDALONE_TIMER.matcher(text);
            if (atTopCorner && singleNumber.matches()) {
                int value = Integer.parseInt(singleNumber.group(1));
                if (value >= 0 && value <= 90) {
                    found = value;
                    break;
                }
            }
        }
        if (found >= 0) {
            remainingSeconds = found;
            updatedAt = SystemClock.elapsedRealtime();
        }
    }

    public int recentRemainingSeconds() {
        return SystemClock.elapsedRealtime() - updatedAt <= FRESH_RESULT_MS
                ? remainingSeconds
                : -1;
    }

    public void reset() {
        remainingSeconds = -1;
        updatedAt = 0;
    }

    public void close() {
        recognizer.close();
    }
}
