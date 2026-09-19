import AppKit
import SwiftUI

/// 항상 떠 있는 비서 패널.
///
/// NSWindow 가 아니라 NSPanel 을 쓴다. nonactivatingPanel 이면 패널을
/// 눌러도 앞 앱의 포커스를 빼앗지 않는다 — 코드를 보다가 비서에 한 줄
/// 물어보는 흐름에서, 편집기 포커스가 매번 날아가면 못 쓴다.
final class FloatingPanel: NSPanel {
    init(contentRect: NSRect) {
        super.init(
            contentRect: contentRect,
            styleMask: [.titled, .closable, .resizable, .fullSizeContentView, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )

        titleVisibility = .hidden
        titlebarAppearsTransparent = true
        isMovableByWindowBackground = true
        isOpaque = false
        backgroundColor = .clear
        hasShadow = true

        // 모든 스페이스에서 보이고, 전체 화면 앱 위에도 뜬다
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        isFloatingPanel = true
        level = .floating

        standardWindowButton(.miniaturizeButton)?.isHidden = true
        standardWindowButton(.zoomButton)?.isHidden = true

        minSize = NSSize(width: 280, height: 360)
        maxSize = NSSize(width: 520, height: 1400)
    }

    // 타이틀바가 없어도 키 입력을 받아야 한다
    override var canBecomeKey: Bool { true }
}

/// 패널 하나를 만들고 보여주고 숨긴다.
@MainActor
final class PanelController: ObservableObject {
    @Published private(set) var isVisible = false
    @Published var isPinned = true {
        didSet { applyLevel() }
    }

    /// 접힌 상태. 다음 일정 한 줄만 남는 얇은 바가 된다.
    @Published var isCompact = false {
        didSet { applyHeight() }
    }

    private var panel: FloatingPanel?
    private let frameKey = "panel.frame"
    private var expandedHeight: CGFloat = 620

    /// 헤더 실제 높이와 맞춘다. 남는 공간이 있으면 헤더가 위로 쏠린다.
    static let compactHeight: CGFloat = 64

    func toggle<Content: View>(@ViewBuilder content: () -> Content) {
        if isVisible { hide() } else { show(content: content) }
    }

    func show<Content: View>(@ViewBuilder content: () -> Content) {
        if panel == nil { panel = makePanel(content: content()) }
        panel?.orderFrontRegardless()
        panel?.makeKey()
        isVisible = true
    }

    func hide() {
        saveFrame()
        panel?.orderOut(nil)
        isVisible = false
    }

    private func makePanel<Content: View>(content: Content) -> FloatingPanel {
        // 처음 열 때는 화면 오른쪽에 세워둔다 — 좁고 긴 패널의 자리다
        let defaultRect = defaultFrame()
        let panel = FloatingPanel(contentRect: savedFrame() ?? defaultRect)

        let hosting = NSHostingView(rootView: content)
        panel.contentView = hosting
        panel.delegate = nil
        applyLevel(to: panel)
        return panel
    }

    private func defaultFrame() -> NSRect {
        let width: CGFloat = 340
        let inset: CGFloat = 24
        guard let screen = NSScreen.main?.visibleFrame else {
            return NSRect(x: 100, y: 100, width: width, height: 620)
        }
        let height = min(720, screen.height - inset * 2)
        return NSRect(
            x: screen.maxX - width - inset,
            y: screen.midY - height / 2,
            width: width,
            height: height
        )
    }

    private func applyLevel(to target: FloatingPanel? = nil) {
        (target ?? panel)?.level = isPinned ? .floating : .normal
    }

    /// 접고 펼 때 높이만 바꾼다.
    ///
    /// 위쪽 모서리를 고정해야 화면에서 튀어 오르지 않는다. 그리고
    /// 애니메이션을 쓰지 않는다 — 창 크기는 AppKit 이, 내용은 SwiftUI 가
    /// 각자 다른 커브로 움직여서 중간 프레임이 어긋나 보인다 (ADR-026).
    private func applyHeight() {
        guard let panel else { return }
        var frame = panel.frame
        let top = frame.maxY

        if isCompact {
            expandedHeight = max(frame.height, 360)
            frame.size.height = Self.compactHeight
        } else {
            frame.size.height = expandedHeight
        }
        frame.origin.y = top - frame.height

        // 접힌 동안에는 세로로 끌 수 없게 막는다. 늘리면 빈 칸만 생긴다.
        panel.minSize = NSSize(width: 280, height: isCompact ? Self.compactHeight : 360)
        panel.maxSize = NSSize(width: 520, height: isCompact ? Self.compactHeight : 1400)

        panel.setFrame(frame, display: true, animate: false)
    }

    // MARK: - 위치 기억

    private func saveFrame() {
        guard let panel else { return }
        UserDefaults.standard.set(NSStringFromRect(panel.frame), forKey: frameKey)
    }

    private func savedFrame() -> NSRect? {
        guard let raw = UserDefaults.standard.string(forKey: frameKey) else { return nil }
        let rect = NSRectFromString(raw)
        guard rect.width > 0, rect.height > 0 else { return nil }
        // 모니터 구성이 바뀌어 화면 밖에 저장돼 있으면 버린다
        let onScreen = NSScreen.screens.contains { $0.visibleFrame.intersects(rect) }
        return onScreen ? rect : nil
    }
}
