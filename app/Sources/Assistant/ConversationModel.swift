import Foundation
import SwiftUI

/// 화면에 보이는 한 줄.
struct Turn: Identifiable {
    enum Role { case user, assistant, tool, error }

    let id = UUID()
    let role: Role
    var text: String

    /// 도구 줄에서만 쓴다. 도는 동안 스피너, 끝나면 체크.
    var running: Bool = false
}

@MainActor
final class ConversationModel: ObservableObject {
    @Published var turns: [Turn] = []
    @Published var input: String = ""
    @Published var isWorking = false

    private let client = AgentClient()
    private let store = ConversationStore()

    /// 위 화살표로 되짚을 이전 질문들.
    private var history: [String] = []
    private var historyCursor: Int?
    // 데몬이 기동 시 "panel" 세션을 미리 예열해둔다. 매번 새 세션을
    // 만들면 그 예열이 버려지고 첫 질문이 다시 느려진다.
    private let sessionId = "panel"
    private var currentTask: Task<Void, Never>?

    init() {
        turns = store.load()
        history = turns.filter { $0.role == .user }.map(\.text)
    }

    /// ↑ / ↓ 로 이전 질문 되짚기.
    func recallPrevious() {
        guard !history.isEmpty else { return }
        let next = historyCursor.map { max(0, $0 - 1) } ?? history.count - 1
        historyCursor = next
        input = history[next]
    }

    func recallNext() {
        guard let cursor = historyCursor else { return }
        if cursor + 1 >= history.count {
            historyCursor = nil
            input = ""
        } else {
            historyCursor = cursor + 1
            input = history[cursor + 1]
        }
    }

    func submit() {
        let prompt = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !prompt.isEmpty, !isWorking else { return }

        input = ""
        history.append(prompt)
        historyCursor = nil
        turns.append(Turn(role: .user, text: prompt))
        turns.append(Turn(role: .assistant, text: ""))
        isWorking = true

        currentTask = Task {
            defer {
                isWorking = false
                store.save(turns)
            }
            do {
                let stream = await client.send(prompt: prompt, sessionId: sessionId)
                for try await event in stream {
                    apply(event)
                }
            } catch {
                appendError(error.localizedDescription)
            }
            finishRunningTools()
        }
    }

    func cancel() {
        currentTask?.cancel()
        isWorking = false
    }

    func clear() {
        cancel()
        turns.removeAll()
        historyCursor = nil
        store.clear()
    }

    private func apply(_ event: AgentEvent) {
        switch event.type {
        case .text:
            // 스트리밍 조각은 마지막 assistant 줄에 이어붙인다
            if let idx = turns.lastIndex(where: { $0.role == .assistant }) {
                turns[idx].text += event.text
            }

        case .toolCall:
            // 앞선 도구 호출은 끝난 것으로 본다 — SDK 가 완료 신호를
            // 따로 주지 않으므로, 다음 호출이나 턴 종료를 신호로 쓴다.
            finishRunningTools()
            turns.insert(
                Turn(role: .tool, text: event.text, running: true),
                at: max(turns.count - 1, 0)
            )

        case .confirm:
            turns.append(Turn(role: .error, text: event.text))

        case .error:
            appendError(event.text)

        case .done:
            finishRunningTools()

        case .thinking, .toolResult, .pong, .statusResult, .unknown:
            break
        }
    }

    private func finishRunningTools() {
        for index in turns.indices where turns[index].running {
            turns[index].running = false
        }
    }

    private func appendError(_ message: String) {
        // 빈 assistant 자리를 남겨두면 화면이 어색하다
        if let idx = turns.lastIndex(where: { $0.role == .assistant }), turns[idx].text.isEmpty {
            turns.remove(at: idx)
        }
        turns.append(Turn(role: .error, text: message))
    }
}
