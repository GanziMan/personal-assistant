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
                return "비서 데몬이 실행 중이 아닙니다."
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

    // MARK: - 저수준 연결

    private static func connect(to path: String) -> Int32? {
        let fd = socket(AF_UNIX, SOCK_STREAM, 0)
        guard fd >= 0 else { return nil }

        var addr = sockaddr_un()
        addr.sun_family = sa_family_t(AF_UNIX)
        let maxLen = MemoryLayout.size(ofValue: addr.sun_path)
        guard path.utf8.count < maxLen else { close(fd); return nil }

        _ = withUnsafeMutablePointer(to: &addr.sun_path) { ptr in
            path.withCString { src in
                strncpy(UnsafeMutableRawPointer(ptr).assumingMemoryBound(to: CChar.self),
                        src, maxLen - 1)
            }
        }

        let size = socklen_t(MemoryLayout<sockaddr_un>.size)
        let ok = withUnsafePointer(to: &addr) { p in
            p.withMemoryRebound(to: sockaddr.self, capacity: 1) { connect(fd, $0, size) }
        }
        if ok != 0 { close(fd); return nil }
        return fd
    }

    private static func send(_ request: Request, on fd: Int32) -> Bool {
        guard var payload = try? JSONEncoder().encode(request) else { return false }
        payload.append(0x0A)  // 줄 단위 프레이밍
        return payload.withUnsafeBytes { write(fd, $0.baseAddress, $0.count) } > 0
    }

    /// 소켓에서 줄 단위로 이벤트를 읽어 처리한다.
    /// handler 가 false 를 돌려주면 읽기를 멈춘다.
    private static func readEvents(fd: Int32, handler: (AgentEvent) -> Bool) {
        var buffer = Data()
        var chunk = [UInt8](repeating: 0, count: 8192)
        let decoder = JSONDecoder()

        while true {
            let n = read(fd, &chunk, chunk.count)
            if n <= 0 { return }
            buffer.append(contentsOf: chunk[0..<n])

            while let newline = buffer.firstIndex(of: 0x0A) {
                let line = buffer[buffer.startIndex..<newline]
                buffer = buffer[buffer.index(after: newline)...]
                guard !line.isEmpty,
                      let event = try? decoder.decode(AgentEvent.self, from: Data(line))
                else { continue }
                if !handler(event) { return }
            }
        }
    }

    // MARK: - 공개 API

    /// 한 턴을 보내고 이벤트를 받는다. 연결은 턴마다 새로 연다 —
    /// 데몬이 재시작돼도 다음 질문이 그냥 되는 편이 낫다.
    func send(prompt: String, sessionId: String) -> AsyncThrowingStream<AgentEvent, Error> {
        let path = socketPath
        return AsyncThrowingStream { continuation in
            let task = Task.detached(priority: .userInitiated) {
                guard let fd = AgentClient.connect(to: path) else {
                    continuation.finish(throwing: Failure.notRunning)
                    return
                }
                defer { close(fd) }

                guard AgentClient.send(.prompt(prompt, session: sessionId), on: fd) else {
                    continuation.finish(throwing: Failure.connectionFailed(errno))
                    return
                }

                AgentClient.readEvents(fd: fd) { event in
                    continuation.yield(event)
                    return event.type != .done && event.type != .error
                }
                continuation.finish()
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    /// 대기 화면용 요약. 모델을 거치지 않으므로 자주 불러도 된다.
    func status() async -> StatusPayload? {
        let path = socketPath
        return await withCheckedContinuation { continuation in
            Task.detached(priority: .utility) {
                guard let fd = AgentClient.connect(to: path) else {
                    continuation.resume(returning: nil)
                    return
                }
                defer { close(fd) }

                guard AgentClient.send(.status, on: fd) else {
                    continuation.resume(returning: nil)
                    return
                }

                var result: StatusPayload?
                AgentClient.readEvents(fd: fd) { event in
                    if event.type == .statusResult {
                        result = event.status
                        return false
                    }
                    return true
                }
                continuation.resume(returning: result)
            }
        }
    }
}
