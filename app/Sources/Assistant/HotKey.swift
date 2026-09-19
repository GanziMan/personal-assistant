import AppKit
import Carbon.HIToolbox

/// 전역 단축키 (⌥Space).
///
/// NSEvent 전역 모니터 대신 Carbon 의 RegisterEventHotKey 를 쓴다.
/// 전자는 손쉬운 사용(Accessibility) 권한을 요구한다 — 비서를 부르려고
/// 키보드 입력 전체를 들여다볼 권한을 내주는 것은 과하다.
final class HotKey {
    private var ref: EventHotKeyRef?
    private var handler: EventHandlerRef?
    private let action: () -> Void

    private static var shared: HotKey?

    init(action: @escaping () -> Void) {
        self.action = action
    }

    func register() {
        HotKey.shared = self

        var spec = EventTypeSpec(
            eventClass: OSType(kEventClassKeyboard),
            eventKind: UInt32(kEventHotKeyPressed)
        )

        InstallEventHandler(
            GetApplicationEventTarget(),
            { _, _, _ in
                DispatchQueue.main.async { HotKey.shared?.action() }
                return noErr
            },
            1, &spec, nil, &handler
        )

        let id = EventHotKeyID(signature: OSType(0x4153_5354), id: 1)  // 'ASST'
        RegisterEventHotKey(
            UInt32(kVK_Space),
            UInt32(optionKey),
            id,
            GetApplicationEventTarget(),
            0,
            &ref
        )
    }

    deinit {
        if let ref { UnregisterEventHotKey(ref) }
        if let handler { RemoveEventHandler(handler) }
    }
}
