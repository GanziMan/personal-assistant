import AppKit
import UserNotifications

/// 시스템 알림.
///
/// 데몬이 아니라 앱이 띄운다. 데몬이 osascript 로 띄운 알림은 클릭해도
/// 아무 일도 일어나지 않는다 — 누를 수 없는 알림은 정보를 반만 준다.
/// 앱이 띄우면 눌렀을 때 패널을 열 수 있다 (ADR-036).
@MainActor
final class Notifier: NSObject, UNUserNotificationCenterDelegate {
    static let shared = Notifier()

    /// 눌렀을 때 실행할 것. AppDelegate 가 채운다.
    var onOpen: (() -> Void)?

    private var delivered: Set<String> = []
    private var authorized = false

    func start() {
        UNUserNotificationCenter.current().delegate = self
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) {
            [weak self] granted, _ in
            Task { @MainActor in self?.authorized = granted }
        }
    }

    /// 아직 안 띄운 쪽지만 알린다. 같은 내용을 두 번 띄우지 않는다.
    func deliver(notes: [String]) {
        guard authorized else { return }

        for note in notes where !delivered.contains(note) {
            delivered.insert(note)
            post(note)
        }

        // 사라진 쪽지는 기록에서도 지운다. 다시 생기면 다시 알린다.
        delivered.formIntersection(notes)
    }

    private func post(_ body: String) {
        let content = UNMutableNotificationContent()
        content.title = "비서"
        content.body = body
        content.sound = nil  // 소리까지 내면 방해가 된다

        UNUserNotificationCenter.current().add(
            UNNotificationRequest(
                identifier: UUID().uuidString, content: content, trigger: nil
            )
        )
    }

    // 앱이 앞에 있어도 알림을 보여준다 — 패널은 떠 있어도 안 보고 있을 수 있다
    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        completionHandler([.banner])
    }

    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        Task { @MainActor in
            Notifier.shared.onOpen?()
            completionHandler()
        }
    }
}
