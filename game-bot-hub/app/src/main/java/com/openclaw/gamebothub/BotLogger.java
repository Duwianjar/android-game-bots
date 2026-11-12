package com.openclaw.gamebothub;

import android.os.Handler;
import android.os.Looper;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.LinkedList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.CopyOnWriteArrayList;

public class BotLogger {
    public interface LogListener {
        void onNewLog(String logLine);
        void onLogsCleared();
    }

    private static final int MAX_LOGS = 250;
    private static final LinkedList<String> logs = new LinkedList<>();
    private static final List<LogListener> listeners = new CopyOnWriteArrayList<>();
    private static final Handler mainHandler = new Handler(Looper.getMainLooper());
    private static final SimpleDateFormat timeFormat = new SimpleDateFormat("HH:mm:ss", Locale.getDefault());

    public static synchronized void log(String tag, String message) {
        String timestamp = timeFormat.format(new Date());
        String line = "[" + timestamp + "] [" + tag + "] " + message;
        synchronized (logs) {
            if (logs.size() >= MAX_LOGS) {
                logs.removeFirst();
            }
            logs.addLast(line);
        }

        mainHandler.post(() -> {
            for (LogListener l : listeners) {
                try {
                    l.onNewLog(line);
                } catch (Throwable ignored) {
                }
            }
        });
    }

    public static void log(String message) {
        log("HUB", message);
    }

    public static void addListener(LogListener listener) {
        if (listener != null && !listeners.contains(listener)) {
            listeners.add(listener);
        }
    }

    public static void removeListener(LogListener listener) {
        listeners.remove(listener);
    }

    public static List<String> getRecentLogs() {
        synchronized (logs) {
            return new ArrayList<>(logs);
        }
    }

    public static String getAllLogsAsString() {
        StringBuilder sb = new StringBuilder();
        synchronized (logs) {
            for (String l : logs) {
                sb.append(l).append("\n");
            }
        }
        return sb.toString();
    }

    public static void clearLogs() {
        synchronized (logs) {
            logs.clear();
        }
        mainHandler.post(() -> {
            for (LogListener l : listeners) {
                try {
                    l.onLogsCleared();
                } catch (Throwable ignored) {
                }
            }
        });
    }
}
