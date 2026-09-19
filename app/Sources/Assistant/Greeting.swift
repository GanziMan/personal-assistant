import Foundation

/// 대기 화면 맨 위 한 줄.
///
/// 모델을 부르지 않는다 (ADR-008, ADR-017). 규칙으로 만든다 —
/// 이런 한 줄에 매번 AI 를 쓰면 화면이 갱신될 때마다 호출이 나간다.
enum Greeting {
    /// 상황에 맞는 한 줄. 급한 것부터 고른다.
    static func line(for status: StatusPayload, now: Date = Date()) -> String {
        if let minutes = status.nextEventMinutes, minutes <= 10 {
            return "곧 시작합니다. 준비되셨나요?"
        }
        if let minutes = status.nextEventMinutes, minutes <= 30 {
            return "다음 일정까지 여유가 많지 않습니다."
        }
        if status.todos.count >= 5 {
            return "할 일이 꽤 쌓였네요."
        }
        return timeOfDay(now)
    }

    static func timeOfDay(_ now: Date = Date()) -> String {
        switch Calendar.current.component(.hour, from: now) {
        case 5..<11: return "좋은 아침입니다."
        case 11..<14: return "점심 잘 챙기셨나요?"
        case 14..<18: return "오후도 힘내세요."
        case 18..<22: return "오늘도 고생하셨습니다."
        default: return "늦은 시간이네요."
        }
    }
}

/// 입력창 위에 뜨는 제안 버튼.
struct Suggestion: Identifiable, Equatable {
    let id = UUID()
    let label: String
    let icon: String
    let prompt: String

    /// 지금 상황에서 쓸 만한 것 2~3개.
    static func current(for status: StatusPayload, now: Date = Date()) -> [Suggestion] {
        var out: [Suggestion] = []
        let calendar = Calendar.current
        let hour = calendar.component(.hour, from: now)
        let weekday = calendar.component(.weekday, from: now)  // 1=일 … 7=토

        if status.nextEventMinutes != nil {
            out.append(Suggestion(
                label: "회의 준비",
                icon: "doc.text.magnifyingglass",
                prompt: "다음 일정 관련해서 참고할 자료나 지난 기록 찾아줘"
            ))
        }

        if hour < 11 {
            out.append(Suggestion(
                label: "오늘 브리핑",
                icon: "sun.horizon",
                prompt: "오늘 일정과 할 일, 새 소식 정리해줘"
            ))
        }

        // 금요일 오후엔 회고
        if weekday == 6 && hour >= 15 {
            out.append(Suggestion(
                label: "주간 회고",
                icon: "calendar.badge.clock",
                prompt: "이번 주 한 일 정리해줘"
            ))
        }

        out.append(Suggestion(
            label: "레포 상태",
            icon: "chevron.left.forwardslash.chevron.right",
            prompt: "손 놓은 브랜치나 커밋 안 한 변경 있는지 봐줘"
        ))

        out.append(Suggestion(
            label: "다운로드 정리",
            icon: "tray.full",
            prompt: "다운로드 폴더에 정리할 거 있는지 봐줘"
        ))

        return Array(out.prefix(3))
    }
}
