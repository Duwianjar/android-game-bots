import SwiftUI
import AppKit
import Foundation

// MARK: - Shell Helper
struct Shell {
    @discardableResult
    static func run(_ command: String) -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/zsh")
        process.arguments = ["-l", "-c", command]
        var env = ProcessInfo.processInfo.environment
        env["PATH"] = "/opt/homebrew/bin:/opt/homebrew/sbin:/Users/macbookair/Library/Android/sdk/platform-tools:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        process.environment = env
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            return String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        } catch {
            return ""
        }
    }

    static func runAsync(_ command: String, completion: ((String) -> Void)? = nil) {
        DispatchQueue.global(qos: .userInitiated).async {
            let res = run(command)
            DispatchQueue.main.async {
                completion?(res)
            }
        }
    }
}

// MARK: - Log Reader
class LogReader: ObservableObject {
    static let shared = LogReader()
    @Published var logText: String = "Menunggu log bot...\n"
    @Published var autoScroll: Bool = true
    @Published var isReading: Bool = false

    private var timer: Timer?
    private var lastFileSize: UInt64 = 0
    let logPath = "/Users/macbookair/woodland_guardian_bot.log"

    init() {
        start()
    }

    func start() {
        refresh()
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 0.6, repeats: true) { [weak self] _ in
            self?.refresh()
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    func refresh() {
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: logPath),
              let size = attrs[.size] as? UInt64 else {
            return
        }
        if size != lastFileSize {
            lastFileSize = size
            readTail()
        }
    }

    func readTail() {
        guard let handle = try? FileHandle(forReadingFrom: URL(fileURLWithPath: logPath)) else { return }
        defer { try? handle.close() }
        let maxBytes: UInt64 = 80000 // Baca 80KB terakhir untuk performa instan
        if lastFileSize > maxBytes {
            try? handle.seek(toOffset: lastFileSize - maxBytes)
        } else {
            try? handle.seek(toOffset: 0)
        }
        let data = handle.readDataToEndOfFile()
        if let str = String(data: data, encoding: .utf8) {
            DispatchQueue.main.async {
                self.logText = str
            }
        }
    }

    func clear() {
        logText = "Tampilan log dibersihkan.\n"
    }

    func copyAll() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(logText, forType: .string)
    }

    func openLogFile() {
        NSWorkspace.shared.open(URL(fileURLWithPath: logPath))
    }
}

// MARK: - Bot Manager
class BotManager: ObservableObject {
    static let shared = BotManager()

    @Published var isRunning: Bool = false
    @Published var botPID: String = "-"
    @Published var deviceStatus: String = "Mengecek perangkat..."
    @Published var isDeviceConnected: Bool = false
    @Published var isInjectEnabled: Bool {
        didSet {
            UserDefaults.standard.set(isInjectEnabled, forKey: "woodland_inject_enabled")
        }
    }
    @Published var autoOpenLogOnPlay: Bool {
        didSet {
            UserDefaults.standard.set(autoOpenLogOnPlay, forKey: "woodland_auto_open_log")
        }
    }
    @Published var lastActionStatus: String = "Siap dijalankan"

    private var pollTimer: Timer?

    init() {
        self.isInjectEnabled = UserDefaults.standard.object(forKey: "woodland_inject_enabled") as? Bool ?? false
        self.autoOpenLogOnPlay = UserDefaults.standard.object(forKey: "woodland_auto_open_log") as? Bool ?? true
        checkStatus()
        pollTimer = Timer.scheduledTimer(withTimeInterval: 1.5, repeats: true) { [weak self] _ in
            self?.checkStatus()
        }
    }

    func checkStatus() {
        DispatchQueue.global(qos: .background).async {
            // Cek PID bot
            let pidOutput = Shell.run("pgrep -f '[w]oodland_guardian_bot.py' | head -n 1")
            let running = !pidOutput.isEmpty

            // Cek Device ADB
            let adbOut = Shell.run("adb devices | grep -E '^[a-zA-Z0-9_-]+\\s+device' | head -n 1")
            let deviceConnected = !adbOut.isEmpty
            let serial = deviceConnected ? (adbOut.components(separatedBy: "\t").first ?? "Device") : "Tidak Ada HP"

            DispatchQueue.main.async {
                self.isRunning = running
                self.botPID = running ? pidOutput : "-"
                self.isDeviceConnected = deviceConnected
                self.deviceStatus = deviceConnected ? "\(serial) (Online)" : "Tidak ada HP terdeteksi"
            }
        }
    }

    func startBot() {
        lastActionStatus = "Memulai Bot Woodland..."
        let injectArg = isInjectEnabled ? "--inject" : "--no-inject"

        Shell.runAsync("/Users/macbookair/android-game-bots/game-switcher/show_woodland.sh \(injectArg)") { [weak self] _ in
            self?.lastActionStatus = "Bot Woodland aktif (Inject: \(self?.isInjectEnabled == true ? "ON" : "OFF"))"
            self?.checkStatus()
            if self?.autoOpenLogOnPlay == true {
                LogWindowManager.shared.showLogWindow()
            }
        }
    }

    func stopBot() {
        lastActionStatus = "Menghentikan Bot..."
        let cmd = """
        /Users/macbookair/android-game-bots/woodland-tile-matcher/stop_woodland_guardian_bot.sh
        tmux kill-session -t woodland_guardian 2>/dev/null || true
        adb shell am force-stop com.android.chrome 2>/dev/null || true
        """
        Shell.runAsync(cmd) { [weak self] _ in
            self?.lastActionStatus = "Bot telah distop"
            self?.checkStatus()
        }
    }

    func openScrcpy() {
        lastActionStatus = "Membuka SCRCPY..."
        Shell.runAsync("nohup scrcpy --window-title 'Woodland - Layar HP' >/tmp/scrcpy_woodland.log 2>&1 &") { [weak self] _ in
            self?.lastActionStatus = "SCRCPY dibuka"
        }
    }
}

// MARK: - Log Window Manager (Pop-Up)
class LogWindowManager: ObservableObject {
    static let shared = LogWindowManager()
    private var window: NSWindow?

    func showLogWindow() {
        if let win = window {
            win.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }

        let newWindow = NSWindow(
            contentRect: NSRect(x: 100, y: 100, width: 780, height: 500),
            styleMask: [.titled, .closable, .resizable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        newWindow.title = "Log Real-Time: Woodland Guardian Bot"
        newWindow.isReleasedWhenClosed = false
        newWindow.center()

        let hostingView = NSHostingView(rootView: LogPopUpView())
        newWindow.contentView = hostingView
        newWindow.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        self.window = newWindow
    }
}

// MARK: - AppKit TextView for Logs
struct LogTextView: NSViewRepresentable {
    @ObservedObject var logReader: LogReader

    func makeNSView(context: Context) -> NSScrollView {
        let scrollView = NSTextView.scrollableTextView()
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = true
        scrollView.autohidesScrollers = false

        guard let textView = scrollView.documentView as? NSTextView else {
            return scrollView
        }
        textView.isEditable = false
        textView.isSelectable = true
        textView.backgroundColor = NSColor(red: 0.08, green: 0.09, blue: 0.12, alpha: 1.0)
        textView.textColor = NSColor(calibratedRed: 0.85, green: 0.95, blue: 0.88, alpha: 1.0)
        textView.font = NSFont.monospacedSystemFont(ofSize: 11.5, weight: .regular)
        textView.textContainerInset = NSSize(width: 8, height: 8)
        return scrollView
    }

    func updateNSView(_ nsView: NSScrollView, context: Context) {
        guard let textView = nsView.documentView as? NSTextView else { return }
        if textView.string != logReader.logText {
            textView.string = logReader.logText
            if logReader.autoScroll {
                textView.scrollToEndOfDocument(nil)
            }
        }
    }
}

// MARK: - Log Pop-Up View
struct LogPopUpView: View {
    @ObservedObject var reader = LogReader.shared
    @ObservedObject var bot = BotManager.shared

    var body: some View {
        VStack(spacing: 0) {
            // Toolbar Log
            HStack(spacing: 12) {
                HStack(spacing: 6) {
                    Circle()
                        .fill(bot.isRunning ? Color.green : Color.gray)
                        .frame(width: 10, height: 10)
                    Text(bot.isRunning ? "Bot Berjalan (PID: \(bot.botPID))" : "Bot Berhenti")
                        .font(.system(size: 12, weight: .medium))
                }

                Spacer()

                Toggle("Auto-Scroll", isOn: $reader.autoScroll)
                    .toggleStyle(CheckboxToggleStyle())
                    .font(.system(size: 12))

                Button(action: { reader.copyAll() }) {
                    Label("Salin Log", systemImage: "doc.on.doc")
                }
                .controlSize(.small)

                Button(action: { reader.clear() }) {
                    Label("Bersihkan", systemImage: "trash")
                }
                .controlSize(.small)

                Button(action: { reader.openLogFile() }) {
                    Label("Buka File", systemImage: "arrow.up.right.square")
                }
                .controlSize(.small)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(Color(NSColor.windowBackgroundColor))

            Divider()

            // Area Tampilan Log Terminal
            LogTextView(logReader: reader)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(minWidth: 600, minHeight: 400)
    }
}

// MARK: - Main Control View
struct ContentView: View {
    @ObservedObject var bot = BotManager.shared
    @ObservedObject var logReader = LogReader.shared

    var body: some View {
        VStack(spacing: 18) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Woodland Tile Matcher Bot")
                        .font(.system(size: 20, weight: .bold))
                    Text("Guardian & Auto-Reward Control Panel")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }
                Spacer()
                // Status Badge Bot
                HStack(spacing: 6) {
                    Circle()
                        .fill(bot.isRunning ? Color.green : Color.red.opacity(0.8))
                        .frame(width: 10, height: 10)
                    Text(bot.isRunning ? "BERJALAN" : "BERHENTI")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(bot.isRunning ? .green : .secondary)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(bot.isRunning ? Color.green.opacity(0.12) : Color.gray.opacity(0.12))
                .cornerRadius(8)
            }
            .padding(.horizontal)
            .padding(.top, 16)

            Divider()

            // Info Box: Perangkat & Game
            VStack(spacing: 8) {
                HStack {
                    Label("HP / Perangkat ADB:", systemImage: "iphone")
                        .font(.system(size: 12, weight: .medium))
                    Spacer()
                    Text(bot.deviceStatus)
                        .font(.system(size: 12, weight: .bold, design: .monospaced))
                        .foregroundColor(bot.isDeviceConnected ? .primary : .red)
                }
                HStack {
                    Label("PID Proses Bot:", systemImage: "cpu")
                        .font(.system(size: 12, weight: .medium))
                    Spacer()
                    Text(bot.botPID)
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundColor(.secondary)
                }
            }
            .padding(12)
            .background(Color(NSColor.controlBackgroundColor))
            .cornerRadius(10)
            .padding(.horizontal)

            // KOTAK PENGATURAN INJEKSI IKLAN (SEBELUM PLAY)
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Inject Iklan Slot")
                            .font(.system(size: 14, weight: .semibold))
                        Text(bot.isInjectEnabled ? "AKTIF: Membuka Google, search slot & jalankan app slot setelah iklan ditonton" : "NONAKTIF: Bot hanya fokus game & reward tanpa injeksi web/app slot")
                            .font(.system(size: 11))
                            .foregroundColor(bot.isInjectEnabled ? .orange : .secondary)
                            .lineLimit(2)
                    }
                    Spacer()
                    Toggle("", isOn: $bot.isInjectEnabled)
                        .toggleStyle(SwitchToggleStyle(tint: .orange))
                }

                Text("💡 Atur sakelar ini sebelum menekan tombol Play.")
                    .font(.system(size: 10.5))
                    .foregroundColor(.secondary)
            }
            .padding(14)
            .background(bot.isInjectEnabled ? Color.orange.opacity(0.08) : Color(NSColor.controlBackgroundColor))
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(bot.isInjectEnabled ? Color.orange.opacity(0.4) : Color.gray.opacity(0.2), lineWidth: 1)
            )
            .cornerRadius(10)
            .padding(.horizontal)

            // TOMBOL-TOMBOL KONTROL
            VStack(spacing: 10) {
                HStack(spacing: 12) {
                    // Tombol PLAY
                    Button(action: { bot.startBot() }) {
                        HStack {
                            Image(systemName: "play.fill")
                            Text("PLAY / JALANKAN")
                                .fontWeight(.bold)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.green)
                    .controlSize(.large)
                    .disabled(!bot.isDeviceConnected)

                    // Tombol STOP
                    Button(action: { bot.stopBot() }) {
                        HStack {
                            Image(systemName: "stop.fill")
                            Text("STOP BOT")
                                .fontWeight(.bold)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.red)
                    .controlSize(.large)
                }

                HStack(spacing: 12) {
                    // Tombol POP UP LOG
                    Button(action: { LogWindowManager.shared.showLogWindow() }) {
                        HStack {
                            Image(systemName: "terminal.fill")
                            Text("Tampilkan Pop-up Log")
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .controlSize(.regular)

                    // Tombol SCRCPY (Layar HP)
                    Button(action: { bot.openScrcpy() }) {
                        HStack {
                            Image(systemName: "display")
                            Text("Buka Layar HP (Scrcpy)")
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .controlSize(.regular)
                }

                HStack {
                    Toggle("Otomatis buka Pop-up Log saat Play diklik", isOn: $bot.autoOpenLogOnPlay)
                        .font(.system(size: 11))
                        .toggleStyle(CheckboxToggleStyle())
                    Spacer()
                }
                .padding(.top, 2)
            }
            .padding(.horizontal)

            // MINI LOG PREVIEW
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text("Aktivitas Terbaru:")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(bot.lastActionStatus)
                        .font(.system(size: 10.5))
                        .foregroundColor(.blue)
                }
                Text(logReader.logText.suffix(280))
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundColor(Color(red: 0.8, green: 0.9, blue: 0.8))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(8)
                    .background(Color(red: 0.08, green: 0.09, blue: 0.12))
                    .cornerRadius(6)
            }
            .padding(.horizontal)
            .padding(.bottom, 16)
        }
        .frame(width: 480, height: 500)
    }
}

// MARK: - App Entry Point
@main
struct WoodlandApp: App {
    init() {
        NSApp.setActivationPolicy(.regular)
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowResizability(.contentSize)
    }
}
