import Foundation

/// 데몬이 흘려보내는 이벤트. core/src/assistant/protocol.py 와 짝이다.
struct AgentEvent: Decodable {
    enum Kind: String, Decodable {
        case text
        case thinking
        case toolCall = "tool_call"
        case toolResult = "tool_result"
        case confirm
        case done
        case error
        case pong
        case statusResult = "status_result"
        case unknown
    }

    let type: Kind
    let sessionId: String
    let text: String
    let status: StatusPayload?

    private enum CodingKeys: String, CodingKey {
        case type
        case sessionId = "session_id"
        case text
        case data
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        // 모르는 이벤트 종류가 와도 앱이 죽지 않게 한다
        type = (try? c.decode(Kind.self, forKey: .type)) ?? .unknown
        sessionId = (try? c.decode(String.self, forKey: .sessionId)) ?? ""
        text = (try? c.decode(String.self, forKey: .text)) ?? ""
        status = try? c.decode(StatusPayload.self, forKey: .data)
    }
}

/// 대기 화면 내용. 모델을 거치지 않고 도구에서 바로 온다.
struct StatusPayload: Decodable, Equatable {
    var nextEvent: String = ""
    var nextEventMinutes: Int?
    var todos: [String] = []
    var brief: String = ""
    var briefAt: Double = 0
    var toolsReady: Bool = false
    var notes: [String] = []

    private enum CodingKeys: String, CodingKey {
        case notes
        case nextEvent = "next_event"
        case nextEventMinutes = "next_event_minutes"
        case todos
        case brief
        case briefAt = "brief_at"
        case toolsReady = "tools_ready"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        nextEvent = (try? c.decode(String.self, forKey: .nextEvent)) ?? ""
        nextEventMinutes = try? c.decode(Int.self, forKey: .nextEventMinutes)
        todos = (try? c.decode([String].self, forKey: .todos)) ?? []
        brief = (try? c.decode(String.self, forKey: .brief)) ?? ""
        briefAt = (try? c.decode(Double.self, forKey: .briefAt)) ?? 0
        toolsReady = (try? c.decode(Bool.self, forKey: .toolsReady)) ?? false
        notes = (try? c.decode([String].self, forKey: .notes)) ?? []
    }

    init() {}

    var isEmpty: Bool { nextEvent.isEmpty && todos.isEmpty && brief.isEmpty && notes.isEmpty }

    /// "50분 뒤" 처럼 사람이 읽는 남은 시간.
    var countdown: String? {
        guard let m = nextEventMinutes else { return nil }
        if m < 1 { return "지금" }
        if m < 60 { return "\(m)분 뒤" }
        if m < 60 * 24 { return "\(m / 60)시간 \(m % 60)분 뒤" }
        return "\(m / (60 * 24))일 뒤"
    }

    /// 일정 제목만. 도구가 준 문장에서 시각·달력 이름을 걷어낸다.
    var eventTitle: String {
        guard let dash = nextEvent.range(of: " — ") else { return nextEvent }
        var rest = String(nextEvent[dash.upperBound...])
        // "09/20 14:00–15:00  제목  [달력]"
        let parts = rest.components(separatedBy: "  ").filter { !$0.isEmpty }
        if parts.count >= 2 { rest = parts[1] }
        if let bracket = rest.range(of: "  [") { rest = String(rest[..<bracket.lowerBound]) }
        return rest.trimmingCharacters(in: .whitespaces)
    }
}

struct Request: Encodable {
    let type: String
    var sessionId: String = ""
    var text: String = ""

    private enum CodingKeys: String, CodingKey {
        case type
        case sessionId = "session_id"
        case text
    }

    static func prompt(_ text: String, session: String) -> Request {
        Request(type: "prompt", sessionId: session, text: text)
    }

    static var status: Request { Request(type: "status") }
}
