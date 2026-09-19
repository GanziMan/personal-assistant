import Foundation
import SwiftUI

/// 화면에 보이는 한 줄.
struct Turn: Identifiable {
    enum Role { case user, assistant, tool, error }

    let id = UUID()
    let role: Role
    var text: String
}

@MainActor
final class ConversationModel: ObservableObject {
    @Published var turns: [Turn] = []
    @Published var input: String = ""
    @Published var isWorking = false
    @Published var daemonDown = false

    private let client = AgentClient()
    private let sessionId = UUID().uuidString.prefix(12).lowercased()
    private var currentTask: Task<Void, Never>?

    func checkDaemon() async {
        daemonDown = await !client.daemonIsRunning
    }

    func submit() {
        let prompt = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !prompt.isEmpty, !isWorking else { return }

        input = ""
        turns.append(Turn(role: .user, text: prompt))
        turns.append(Turn(role: .assistant, text: ""))
        isWorking = true

        currentTask = Task {
            defer { isWorking = false }
            do {
                let stream = await client.send(prompt: prompt, sessionId: String(sessionId))
                for try await event in stream {
                    apply(event)
                }
            } catch {
                appendError(error.localizedDescription)
            }
        }
    }

    func cancel() {
        currentTask?.cancel()
        isWorking = false
    }

    func clear() {
        cancel()
        turns.removeAll()
    }

    private func apply(_ event: AgentEvent) {
        switch event.type {
        case .text:
            // 스트리밍 조각은 마지막 assistant 줄에 이어붙인다
            if let idx = turns.lastIndex(where: { $0.role == .assistant }) {
                turns[idx].text += event.text
            }
        case .toolCall:
            turns.insert(Turn(role: .tool, text: event.text), at: max(turns.count - 1, 0))
        case .error:
            appendError(event.text)
        case .thinking, .toolResult, .confirm, .done, .pong:
            break
        }
    }

    private func appendError(_ message: String) {
        // 빈 assistant 자리를 남겨두면 화면이 어색하다
        if let idx = turns.lastIndex(where: { $0.role == .assistant }), turns[idx].text.isEmpty {
            turns.remove(at: idx)
        }
        turns.append(Turn(role: .error, text: message))
        daemonDown = message.contains("데몬")
    }
}
