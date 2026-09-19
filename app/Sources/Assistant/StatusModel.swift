import Foundation
import SwiftUI

/// 대기 화면 내용을 주기적으로 받아온다.
///
/// 주기를 상황에 맞춘다. 다음 일정이 임박하면 카운트다운이 굼떠 보이면
/// 안 되고, 아무 일 없을 때 1분마다 깨울 이유도 없다.
@MainActor
final class StatusModel: ObservableObject {
    @Published private(set) var status = StatusPayload()
    @Published private(set) var daemonReachable = true
    @Published var briefExpanded = false

    private let client = AgentClient()
    private var timer: Task<Void, Never>?

    func start() {
        guard timer == nil else { return }
        timer = Task { [weak self] in
            while !Task.isCancelled {
                await self?.refresh()
                let seconds = self?.nextInterval() ?? 60
                try? await Task.sleep(for: .seconds(seconds))
            }
        }
    }

    func stop() {
        timer?.cancel()
        timer = nil
    }

    func refresh() async {
        if let fresh = await client.status() {
            status = fresh
            daemonReachable = true
        } else {
            daemonReachable = await client.daemonIsRunning
        }
    }

    private func nextInterval() -> Int {
        guard let minutes = status.nextEventMinutes else { return 120 }
        if minutes <= 15 { return 20 }
        if minutes <= 60 { return 60 }
        return 120
    }
}
