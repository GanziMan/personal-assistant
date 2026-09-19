import Foundation

/// 대화를 디스크에 남긴다.
///
/// 앱을 껐다 켜면 화면이 비는 게 지금까지의 동작이었다. 비서라면
/// 어제 하던 얘기가 남아 있어야 한다. 데몬의 기억(SQLite)과는 별개다 —
/// 저쪽은 "무엇이 있었나"를 쌓는 곳이고, 여기는 화면 복원용이다.
struct ConversationStore {
    private let url: URL
    private let limit: Int

    init(
        url: URL = URL(fileURLWithPath: NSHomeDirectory())
            .appendingPathComponent(".assistant/panel-conversation.json"),
        limit: Int = 60
    ) {
        self.url = url
        self.limit = limit
    }

    struct Record: Codable {
        let role: String
        let text: String
    }

    func load() -> [Turn] {
        guard let data = try? Data(contentsOf: url),
              let records = try? JSONDecoder().decode([Record].self, from: data)
        else { return [] }

        return records.compactMap { record in
            guard let role = Turn.Role(storageKey: record.role) else { return nil }
            // 도구 줄은 복원하지 않는다 — 이미 끝난 호출을 다시 보여줄 이유가 없다
            guard role != .tool else { return nil }
            return Turn(role: role, text: record.text)
        }
    }

    func save(_ turns: [Turn]) {
        let records = turns
            .filter { $0.role != .tool }
            .suffix(limit)
            .map { Record(role: $0.role.storageKey, text: $0.text) }

        try? FileManager.default.createDirectory(
            at: url.deletingLastPathComponent(), withIntermediateDirectories: true
        )
        guard let data = try? JSONEncoder().encode(Array(records)) else { return }
        try? data.write(to: url, options: .atomic)
    }

    func clear() {
        try? FileManager.default.removeItem(at: url)
    }
}

extension Turn.Role {
    var storageKey: String {
        switch self {
        case .user: return "user"
        case .assistant: return "assistant"
        case .tool: return "tool"
        case .error: return "error"
        }
    }

    init?(storageKey: String) {
        switch storageKey {
        case "user": self = .user
        case "assistant": self = .assistant
        case "tool": self = .tool
        case "error": self = .error
        default: return nil
        }
    }
}
