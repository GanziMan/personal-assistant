import AppKit
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
            Button("비서 열기 / 숨기기") {
                delegate.togglePanel()
            }
            .keyboardShortcut(" ", modifiers: .option)

            Divider()

            Toggle("항상 위에 표시", isOn: Binding(
                get: { delegate.panel.isPinned },
                set: { delegate.panel.isPinned = $0 }
            ))

            Button("대화 비우기") { delegate.conversation.clear() }

            Divider()
            Button("종료") { NSApp.terminate(nil) }
        } label: {
            Image(systemName: "sparkle")
        }
    }
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, ObservableObject {
    let conversation = ConversationModel()
    let status = StatusModel()
    let panel = PanelController()

    private var hotKey: HotKey?

    func applicationDidFinishLaunching(_ notification: Notification) {
        hotKey = HotKey { [weak self] in self?.togglePanel() }
        hotKey?.register()

        status.start()
        togglePanel()  // 첫 실행에서 바로 보이게
    }

    func togglePanel() {
        panel.toggle {
            AssistantView(conversation: conversation, status: status, panel: panel)
        }
    }
}
