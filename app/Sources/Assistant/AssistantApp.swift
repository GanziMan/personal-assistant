import AppKit
import SwiftUI

/// 메뉴바 상주 앱.
///
/// 두뇌를 갖지 않는다 (ADR-004). 입력을 소켓 너머로 넘기고 스트리밍을
/// 그리는 일만 한다. 모델 호출도 도구 실행도 여기 없다.
@main
struct AssistantApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @StateObject private var model = ConversationModel()

    var body: some Scene {
        MenuBarExtra {
            ConversationView(model: model)
                .onAppear { delegate.model = model }
        } label: {
            Image(systemName: model.isWorking ? "circle.dotted" : "sparkle")
        }
        .menuBarExtraStyle(.window)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var model: ConversationModel?
    private var hotKey: HotKey?

    func applicationDidFinishLaunching(_ notification: Notification) {
        hotKey = HotKey { Self.openMenuBarPanel() }
        hotKey?.register()
    }

    /// ⌥Space 로 메뉴바 패널을 연다.
    ///
    /// MenuBarExtra 는 패널을 직접 여는 API 를 내주지 않아서, 상태
    /// 아이템 버튼을 눌러준다. SwiftUI 가 심는 버튼을 찾는 방식이라
    /// OS 업데이트에 영향을 받을 수 있는 지점이다.
    private static func openMenuBarPanel() {
        for window in NSApp.windows {
            if let button = window.value(forKey: "statusItem") as? NSStatusItem {
                button.button?.performClick(nil)
                return
            }
        }
        NSApp.activate(ignoringOtherApps: true)
    }
}
