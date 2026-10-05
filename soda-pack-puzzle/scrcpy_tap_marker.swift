import AppKit
import CoreGraphics

func markerColorFromName(_ name: String) -> NSColor {
    switch name.lowercased() {
    case "green", "hijau", "detect", "deteksi": return NSColor.systemGreen.withAlphaComponent(0.78)
    case "red", "merah": return NSColor.systemRed.withAlphaComponent(0.78)
    case "yellow", "kuning": return NSColor.systemYellow.withAlphaComponent(0.82)
    case "orange", "oren": return NSColor.systemOrange.withAlphaComponent(0.80)
    case "purple", "ungu", "pink": return NSColor.systemPurple.withAlphaComponent(0.78)
    case "blue", "biru", "cyan", "tap": fallthrough
    default: return NSColor.systemBlue.withAlphaComponent(0.78)
    }
}

final class MarkerView: NSView {
    let fillColor: NSColor
    init(frame frameRect: NSRect, fillColor: NSColor) {
        self.fillColor = fillColor
        super.init(frame: frameRect)
    }
    required init?(coder: NSCoder) {
        self.fillColor = NSColor.systemBlue.withAlphaComponent(0.78)
        super.init(coder: coder)
    }
    override var isFlipped: Bool { true }
    override func draw(_ dirtyRect: NSRect) {
        NSColor.clear.setFill()
        dirtyRect.fill()
        let inset: CGFloat = 5
        let circle = bounds.insetBy(dx: inset, dy: inset)
        fillColor.setFill()
        NSBezierPath(ovalIn: circle).fill()
        NSColor.white.withAlphaComponent(0.95).setStroke()
        let border = NSBezierPath(ovalIn: circle)
        border.lineWidth = 3
        border.stroke()
    }
}

struct MarkerSpec {
    let x: Double
    let y: Double
    let color: String
    let duration: Double
    let diameter: Double
}

func scrcpyBounds() -> CGRect? {
    let options = CGWindowListOption(arrayLiteral: .optionOnScreenOnly, .excludeDesktopElements)
    guard let infoList = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] else { return nil }
    let candidates = infoList.compactMap { info -> CGRect? in
        guard let owner = info[kCGWindowOwnerName as String] as? String,
              owner.lowercased().contains("scrcpy"),
              let boundsObj = info[kCGWindowBounds as String],
              let bounds = CGRect(dictionaryRepresentation: boundsObj as! CFDictionary) else { return nil }
        return bounds.width > 150 && bounds.height > 300 ? bounds : nil
    }
    return candidates.max(by: { $0.width * $0.height < $1.width * $1.height })
}

func parseSpecs() -> [MarkerSpec] {
    let args = Array(CommandLine.arguments.dropFirst())
    guard args.count >= 2 else { return [] }

    // Batch mode: x y color duration diameter repeated.
    if args.count >= 10 && args.count % 5 == 0 {
        var specs: [MarkerSpec] = []
        var i = 0
        while i + 4 < args.count {
            if let x = Double(args[i]), let y = Double(args[i+1]) {
                let color = args[i+2]
                let duration = max(0.2, Double(args[i+3]) ?? 3.0)
                let diameter = max(12.0, Double(args[i+4]) ?? 54.0)
                specs.append(MarkerSpec(x: x, y: y, color: color, duration: duration, diameter: diameter))
            }
            i += 5
        }
        return specs
    }

    // Backward-compatible single mode: x y [color] [duration] [diameter].
    guard let x = Double(args[0]), let y = Double(args[1]) else { return [] }
    let color = args.count >= 3 ? args[2] : "blue"
    let duration = args.count >= 4 ? max(0.2, Double(args[3]) ?? 3.0) : 3.0
    let diameter = args.count >= 5 ? max(12.0, Double(args[4]) ?? 54.0) : ((color.lowercased().contains("green") || color.lowercased().contains("hijau")) ? 62.0 : 54.0)
    return [MarkerSpec(x: x, y: y, color: color, duration: duration, diameter: diameter)]
}

let specs = parseSpecs()
guard !specs.isEmpty, let bounds = scrcpyBounds(), let screen = NSScreen.main else { exit(0) }

let deviceWidth: CGFloat = 720
let deviceHeight: CGFloat = 1640
let titleHeight: CGFloat = min(34, max(22, bounds.height * 0.06))
let videoHeight = max(1, bounds.height - titleHeight)

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
var panels: [NSPanel] = []
let maxDuration = specs.map { $0.duration }.max() ?? 3.0

for spec in specs {
    let topX = bounds.origin.x + CGFloat(spec.x) * bounds.width / deviceWidth
    let topY = bounds.origin.y + titleHeight + CGFloat(spec.y) * videoHeight / deviceHeight
    let diameter: CGFloat = CGFloat(spec.diameter)
    let cocoaY = screen.frame.height - topY - diameter / 2
    let panel = NSPanel(
        contentRect: NSRect(x: topX - diameter / 2, y: cocoaY - diameter / 2, width: diameter, height: diameter),
        styleMask: [.borderless],
        backing: .buffered,
        defer: false
    )
    panel.isOpaque = false
    panel.backgroundColor = .clear
    panel.hasShadow = false
    panel.level = .floating
    panel.ignoresMouseEvents = true
    panel.collectionBehavior = [.canJoinAllSpaces, .transient, .ignoresCycle]
    panel.contentView = MarkerView(frame: NSRect(x: 0, y: 0, width: diameter, height: diameter), fillColor: markerColorFromName(spec.color))
    panel.alphaValue = 1.0
    panel.orderFrontRegardless()
    panels.append(panel)
}

let started = Date()
Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) { timer in
    let elapsed = Date().timeIntervalSince(started)
    for (idx, panel) in panels.enumerated() {
        let dur = specs[idx].duration
        let progress = elapsed / dur
        panel.alphaValue = max(0, 1.0 - progress)
    }
    if elapsed >= maxDuration {
        timer.invalidate()
        for panel in panels { panel.orderOut(nil) }
        app.terminate(nil)
    }
}
app.run()
