import Foundation

/// 데몬이 흘려보내는 이벤트. core/src/assistant/protocol.py 와 짝이다.
///
/// `data` 필드는 임의 JSON 이라 여기서 디코딩하지 않는다. 앱이 쓰는 것은
/// 종류와 텍스트뿐이고, 스키마를 양쪽에서 맞추기 시작하면 프로토콜을
/// 고칠 때마다 앱이 깨진다.
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
    }

    let type: Kind
    let sessionId: String
    let text: String

    private enum CodingKeys: String, CodingKey {
        case type
        case sessionId = "session_id"
        case text
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        // 모르는 이벤트 종류가 와도 앱이 죽지 않게 한다
        type = (try? c.decode(Kind.self, forKey: .type)) ?? .text
        sessionId = (try? c.decode(String.self, forKey: .sessionId)) ?? ""
        text = (try? c.decode(String.self, forKey: .text)) ?? ""
    }
}

struct PromptRequest: Encodable {
    let type = "prompt"
    let sessionId: String
    let text: String

    private enum CodingKeys: String, CodingKey {
        case type
        case sessionId = "session_id"
        case text
    }
}
