import SwiftUI

/// 대화 중에도 헤더 아래 남는 한 줄.
///
/// 대기 화면은 대화가 시작되면 접힌다. 그런데 대화는 디스크에
/// 저장되므로 한 번 말을 걸면 다음 일정을 영영 못 보게 된다
/// (ADR-038). 그래서 접히더라도 한 줄은 남긴다.
///
/// 누르면 대기 화면이 펼쳐진다.
struct SummaryBar: View {
    let status: StatusPayload
    @Binding var expanded: Bool

    @Environment(\.colorScheme) private var scheme
    @State private var hovering = false

    private var urgent: Bool { (status.nextEventMinutes ?? .max) <= 15 }

    private var hasSomething: Bool {
        !status.nextEvent.isEmpty || !status.todos.isEmpty || !status.notes.isEmpty
    }

    var body: some View {
        if hasSomething {
            Button {
                withAnimation(.easeInOut(duration: 0.2)) { expanded.toggle() }
            } label: {
                HStack(spacing: Theme.Space.sm) {
                    Image(systemName: urgent ? "clock.badge.exclamationmark" : "calendar")
                        .font(.system(size: 10))
                        .foregroundStyle(urgent ? Theme.warning : .secondary)

                    Text(headline)
                        .font(Theme.Font.caption)
                        .foregroundStyle(urgent ? Theme.warning : .secondary)
                        .lineLimit(1)

                    if !status.todos.isEmpty {
                        Text("· 할 일 \(status.todos.count)")
                            .font(Theme.Font.caption)
                            .foregroundStyle(.tertiary)
                    }

                    if !status.notes.isEmpty {
                        Image(systemName: "info.circle.fill")
                            .font(.system(size: 9))
                            .foregroundStyle(Theme.accent)
                    }

                    Spacer(minLength: 0)

                    Image(systemName: "chevron.down")
                        .font(.system(size: 8, weight: .bold))
                        .foregroundStyle(.tertiary)
                        .rotationEffect(.degrees(expanded ? 180 : 0))
                }
                .padding(.horizontal, Theme.Space.md)
                .padding(.vertical, 6)
                .background(
                    hovering ? Theme.hoverFill(scheme) : Theme.cardFill(scheme),
                    in: RoundedRectangle(cornerRadius: 7)
                )
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .onHover { hovering = $0 }
            .help(expanded ? "접기" : "오늘 상황 보기")
        }
    }

    private var headline: String {
        guard let countdown = status.countdown else { return "남은 일정 없음" }
        let title = status.eventTitle
        return title.isEmpty ? countdown : "\(countdown) · \(title)"
    }
}
