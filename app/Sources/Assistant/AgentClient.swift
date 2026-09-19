import Foundation

/// 데몬과의 유닉스 소켓 연결.
///
/// 포트가 아니라 소켓 파일을 쓴다 (ADR-003). 한 요청에 여러 이벤트가
/// 흘러나오므로 AsyncStream 으로 넘긴다.
actor AgentClient {
    enum Failure: LocalizedError {
        case notRunning
        case connectionFailed(Int32)

        var errorDescription: String? {
            switch self {
            case .notRunning:
                return "비서 데몬이 실행 중이 아닙니다.\nlaunchctl kickstart -k gui/$UID/com.assistant.daemon"
            case .connectionFailed(let code):
                return "데몬에 연결할 수 없습니다 (errno \(code))."
            }
        }
    }

    private let socketPath: String

    init(socketPath: String = NSHomeDirectory() + "/.assistant/agent.sock") {
        self.socketPath = socketPath
    }

    var daemonIsRunning: Bool {
        FileManager.default.fileExists(atPath: socketPath)
    }

    /// 한 턴을 보내고 이벤트를 받는다. 연결은 턴마다 새로 연다 —
    /// 데몬이 재시작돼도 다음 질문이 그냥 되는 편이 낫다.
    func send(prompt: String, sessionId: String) -> AsyncThrowingStream<AgentEvent, Error> {
        let path = socketPath
        return AsyncThrowingStream { continuation in
            let task = Task.detached(priority: .userInitiated) {
                var fd: Int32 = -1
                defer { if fd >= 0 { close(fd) } }

                fd = socket(AF_UNIX, SOCK_STREAM, 0)
                guard fd >= 0 else {
                    continuation.finish(throwing: Failure.connectionFailed(errno))
                    return
                }

                var addr = sockaddr_un()
                addr.sun_family = sa_family_t(AF_UNIX)
                let maxLen = MemoryLayout.size(ofValue: addr.sun_path)
                guard path.utf8.count < maxLen else {
                    continuation.finish(throwing: Failure.notRunning)
                    return
                }
                _ = withUnsafeMutablePointer(to: &addr.sun_path) { ptr in
                    path.withCString { src in
                        strncpy(UnsafeMutableRawPointer(ptr).assumingMemoryBound(to: CChar.self),
                                src, maxLen - 1)
                    }
                }

                let size = socklen_t(MemoryLayout<sockaddr_un>.size)
                let connected = withUnsafePointer(to: &addr) { ptr in
                    ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) { connect(fd, $0, size) }
                }
                guard connected == 0 else {
                    continuation.finish(throwing: Failure.notRunning)
                    return
                }

                // 요청 전송
                let request = PromptRequest(sessionId: sessionId, text: prompt)
                guard var payload = try? JSONEncoder().encode(request) else {
                    continuation.finish(throwing: Failure.connectionFailed(EINVAL))
                    return
                }
                payload.append(0x0A)  // 줄 단위 프레이밍
                let written = payload.withUnsafeBytes { buf in
                    write(fd, buf.baseAddress, buf.count)
                }
                guard written > 0 else {
                    continuation.finish(throwing: Failure.connectionFailed(errno))
                    return
                }

                // 응답 수신 — 줄 경계로 잘라 이벤트로 넘긴다
                var buffer = Data()
                var chunk = [UInt8](repeating: 0, count: 8192)
                let decoder = JSONDecoder()

                while !Task.isCancelled {
                    let n = read(fd, &chunk, chunk.count)
                    if n <= 0 { break }
                    buffer.append(contentsOf: chunk[0..<n])

                    while let newline = buffer.firstIndex(of: 0x0A) {
                        let line = buffer[buffer.startIndex..<newline]
                        buffer = buffer[buffer.index(after: newline)...]

                        guard !line.isEmpty,
                              let event = try? decoder.decode(AgentEvent.self, from: Data(line))
                        else { continue }

                        continuation.yield(event)
                        if event.type == .done || event.type == .error {
                            continuation.finish()
                            return
                        }
                    }
                }
                continuation.finish()
            }

            continuation.onTermination = { _ in task.cancel() }
        }
    }
}
