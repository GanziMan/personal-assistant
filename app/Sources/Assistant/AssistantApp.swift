import AppKit
import Combine
import SwiftUI

/// 메뉴바에 상주하고, 플로팅 패널을 띄운다.
///
/// 앱은 두뇌를 갖지 않는다 (ADR-004). 입력을 소켓 너머로 넘기고
/// 스트리밍을 그리는 일만 한다.
@main
struct AssistantApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate

    var body: some Scene {
        MenuBarExtra {
            Button("비서 열기 / 숨기기") { delegate.togglePanel() }
                .keyboardShortcut(" ", modifiers: .option)

            Divider()

            Toggle("항상 위에 표시", isOn: Binding(
                get: { delegate.panel.isPinned },
                set: { delegate.panel.isPinned = $0 }
            ))

            Button("접기 / 펼치기") { delegate.panel.isCompact.toggle() }
                .keyboardShortcut("j", modifiers: .command)

            Button("대화 비우기") { delegate.conversation.clear() }
                .keyboardShortcut("k", modifiers: .command)

            Divider()
            Text("빌드 \(AppInfo.buildStamp)")
            Button("종료") { NSApp.terminate(nil) }
        } label: {
            // 아이콘이 상태를 말한다. 패널을 안 열어도 보인다.
            Image(systemName: delegate.iconSymbol)
        }
    }
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, ObservableObject {
    let conversation = ConversationModel()
    let status = StatusModel()
    let panel = PanelController()

    /// 메뉴바 아이콘. 일정이 임박하거나 알릴 것이 있으면 달라진다.
    @Published private(set) var iconSymbol = "sparkle"

    private var hotKey: HotKey?
    private var watch: AnyCancellable?

    func applicationDidFinishLaunching(_ notification: Notification) {
        hotKey = HotKey { [weak self] in self?.togglePanel() }
        hotKey?.register()

        Notifier.shared.start()
        Notifier.shared.onOpen = { [weak self] in self?.showPanel() }

        watch = status.$status.sink { [weak self] payload in
            self?.apply(payload)
        }

        status.start()
        togglePanel()  // 첫 실행에서 바로 보이게
    }

    private func apply(_ payload: StatusPayload) {
        iconSymbol = Self.symbol(for: payload)
        Notifier.shared.deliver(notes: payload.notes)
    }

    /// 급한 순서대로 고른다.
    static func symbol(for payload: StatusPayload) -> String {
        if payload.capabilities.contains(where: { !$0.ok }) { return "sparkle.slash" }
        if let minutes = payload.nextEventMinutes, minutes <= 15 { return "clock.badge.exclamationmark" }
        if !payload.notes.isEmpty { return "sparkle.magnifyingglass" }
        return "sparkle"
    }

    func togglePanel() {
        panel.toggle {
            AssistantView(conversation: conversation, status: status, panel: panel)
        }
    }

    func showPanel() {
        panel.show {
            AssistantView(conversation: conversation, status: status, panel: panel)
        }
    }
}

enum AppInfo {
    /// 실행 파일의 수정 시각. 번들을 다시 조립할 때마다 바뀐다.
    static let buildStamp: String = {
        let path = Bundle.main.executablePath ?? ""
        let date = (try? FileManager.default.attributesOfItem(atPath: path)[.modificationDate]) as? Date
        let formatter = DateFormatter()
        formatter.dateFormat = "MM/dd HH:mm"
        return date.map(formatter.string(from:)) ?? "?"
    }()
}
