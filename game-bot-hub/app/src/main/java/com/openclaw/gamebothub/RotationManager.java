package com.openclaw.gamebothub;

import android.content.Context;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

public class RotationManager {
    public interface RotationListener {
        void onRotationStarted(BotItem initialBot);
        void onTick(BotItem currentBot, int remainingSeconds);
        void onBotChanged(BotItem newBot, int index, int total);
        void onRotationStopped();
        void onRotationPaused();
        void onRotationResumed();
    }

    private static RotationManager instance;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final List<RotationListener> listeners = new CopyOnWriteArrayList<>();

    private volatile boolean running = false;
    private volatile boolean paused = false;
    private List<BotItem> activeQueue = new ArrayList<>();
    private int currentIndex = 0;
    private BotItem currentBot = null;
    private int remainingSeconds = 0;
    private Context appContext;

    private final Runnable tickRunnable = new Runnable() {
        @Override
        public void run() {
            if (!running) return;

            if (paused) {
                handler.postDelayed(this, 1000);
                return;
            }

            remainingSeconds--;
            if (currentBot != null) {
                currentBot.addRunSeconds(1);
            }

            for (RotationListener l : listeners) {
                try {
                    l.onTick(currentBot, remainingSeconds);
                } catch (Throwable ignored) {
                }
            }

            if (remainingSeconds <= 0) {
                BotLogger.log("ROTASI", "Waktu bermain " + (currentBot != null ? currentBot.getName() : "game") + " selesai. Berpindah ke bot berikutnya...");
                advanceToNext(appContext);
            } else {
                handler.postDelayed(this, 1000);
            }
        }
    };

    public static synchronized RotationManager getInstance() {
        if (instance == null) {
            instance = new RotationManager();
        }
        return instance;
    }

    private RotationManager() {}

    public synchronized boolean start(Context context) {
        if (running) return true;
        this.appContext = context.getApplicationContext();

        BotRegistry registry = BotRegistry.getInstance();
        registry.refreshInstalledStatus(appContext);
        activeQueue = registry.getActiveQueue();

        if (activeQueue.isEmpty()) {
            BotLogger.log("ERROR", "Tidak ada bot yang aktif & terinstall di HP!");
            return false;
        }

        running = true;
        paused = false;
        currentIndex = 0;
        BotLogger.log("HUB", "Memulai rotasi dengan " + activeQueue.size() + " game aktif. Durasi: " + registry.getDurationMinutes() + " menit/game.");

        // Mulai floating overlay
        try {
            Intent overlayIntent = new Intent(appContext, FloatingControlService.class);
            appContext.startService(overlayIntent);
        } catch (Throwable ignored) {
        }

        launchBotAtIndex(appContext, currentIndex);

        for (RotationListener l : listeners) {
            try {
                l.onRotationStarted(currentBot);
            } catch (Throwable ignored) {
            }
        }

        handler.removeCallbacks(tickRunnable);
        handler.postDelayed(tickRunnable, 1000);
        return true;
    }

    public synchronized void stop() {
        if (!running) return;
        running = false;
        paused = false;
        handler.removeCallbacks(tickRunnable);

        BotLogger.log("HUB", "Rotasi bot dihentikan pengguna.");
        currentBot = null;

        if (appContext != null) {
            try {
                Intent overlayIntent = new Intent(appContext, FloatingControlService.class);
                appContext.stopService(overlayIntent);
            } catch (Throwable ignored) {
            }
        }

        for (RotationListener l : listeners) {
            try {
                l.onRotationStopped();
            } catch (Throwable ignored) {
            }
        }
    }

    public synchronized void pause() {
        if (!running || paused) return;
        paused = true;
        BotLogger.log("HUB", "Rotasi bot dijeda (PAUSED).");
        for (RotationListener l : listeners) {
            try {
                l.onRotationPaused();
            } catch (Throwable ignored) {
            }
        }
    }

    public synchronized void resume() {
        if (!running || !paused) return;
        paused = false;
        BotLogger.log("HUB", "Rotasi bot dilanjutkan (RESUMED).");
        for (RotationListener l : listeners) {
            try {
                l.onRotationResumed();
            } catch (Throwable ignored) {
            }
        }
    }

    public synchronized void togglePauseResume() {
        if (paused) {
            resume();
        } else {
            pause();
        }
    }

    public synchronized void relaunchCurrentGame(Context context) {
        if (!running || currentBot == null || context == null) return;
        try {
            Intent launchIntent = context.getPackageManager().getLaunchIntentForPackage(currentBot.getPackageName());
            if (launchIntent != null) {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
                context.startActivity(launchIntent);
                BotLogger.log("GAME", "Membuka kembali " + currentBot.getName());
            }
        } catch (Throwable e) {
            BotLogger.log("WARN", "Gagal membuka kembali target: " + e.getMessage());
        }
    }

    public synchronized void nextGame(Context context) {
        if (!running) return;
        BotLogger.log("HUB", "Manual skip ke game berikutnya.");
        advanceToNext(context);
    }

    private synchronized void advanceToNext(Context context) {
        if (!running) return;
        currentIndex++;
        if (currentIndex >= activeQueue.size()) {
            if (BotRegistry.getInstance().isLoopMode()) {
                currentIndex = 0;
                BotLogger.log("ROTASI", "Siklus rotasi selesai. Memulai putaran baru dari awal...");
            } else {
                BotLogger.log("ROTASI", "Semua game dalam antrian telah selesai dijalankan.");
                stop();
                return;
            }
        }
        launchBotAtIndex(context, currentIndex);
    }

    private void launchBotAtIndex(Context context, int index) {
        if (index < 0 || index >= activeQueue.size()) return;
        currentBot = activeQueue.get(index);
        int durationMins = BotRegistry.getInstance().getDurationMinutes();
        remainingSeconds = durationMins * 60;

        BotLogger.log("GAME", "Aktif: " + currentBot.getName() + " (" + (index + 1) + "/" + activeQueue.size() + ") - Target: " + durationMins + " menit");

        // Inform accessibility service
        GameBotAccessibilityService service = GameBotAccessibilityService.getInstance();
        if (service != null) {
            service.setCurrentBot(currentBot);
        }

        // Luncurkan game
        try {
            Intent launchIntent = context.getPackageManager().getLaunchIntentForPackage(currentBot.getPackageName());
            if (launchIntent != null) {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
                context.startActivity(launchIntent);
            } else {
                BotLogger.log("WARN", "Tidak dapat meluncurkan " + currentBot.getPackageName());
            }
        } catch (Throwable e) {
            BotLogger.log("ERROR", "Gagal membuka " + currentBot.getName() + ": " + e.getMessage());
        }

        for (RotationListener l : listeners) {
            try {
                l.onBotChanged(currentBot, index, activeQueue.size());
            } catch (Throwable ignored) {
            }
        }
    }

    public boolean isRunning() {
        return running;
    }

    public boolean isPaused() {
        return paused;
    }

    public BotItem getCurrentBot() {
        return currentBot;
    }

    public int getRemainingSeconds() {
        return remainingSeconds;
    }

    public int getCurrentIndex() {
        return currentIndex;
    }

    public int getTotalQueueSize() {
        return activeQueue.size();
    }

    public void addListener(RotationListener l) {
        if (l != null && !listeners.contains(l)) {
            listeners.add(l);
        }
    }

    public void removeListener(RotationListener l) {
        listeners.remove(l);
    }
}
