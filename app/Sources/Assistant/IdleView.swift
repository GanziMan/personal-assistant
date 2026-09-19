import SwiftUI

/// 말을 걸지 않을 때 보이는 부분.
///
/// 위계를 셋으로 나눈다. 다음 일정은 강조 카드, 할 일과 쪽지는
/// 보통 카드, 브리핑은 접힌 카드. 전부 같은 회색 상자면 무엇이
/// 중요한지 눈이 구분하지 못한다 (ADR-037).
struct IdleView: View {
    @ObservedObject var model: StatusModel
    var onTodoTap: (String) -> Void = { _ in }

    private var isQuiet: Bool {
        model.status.nextEvent.isEmpty
            && model.status.todos.isEmpty
            && model.status.notes.isEmpty
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.md) {
            if isQuiet {
                QuietState()
            } else {
                NextEventCard(status: model.status)

                ForEach(model.status.notes, id: \.self) { note in
                    NoteRow(text: note)
                }

                if !model.status.todos.isEmpty {
                    TodoCard(items: model.status.todos, onTap: onTodoTap)
                }
            }

            if !model.status.brief.isEmpty {
                BriefCard(text: model.status.brief, expanded: $model.briefExpanded)
            }
        }
    }
}

// MARK: - 다음 일정

private struct NextEventCard: View {
    let status: StatusPayload

    private var minutes: Int { status.nextEventMinutes ?? .max }
    private var urgent: Bool { minutes <= 15 }

    /// 남은 시간을 한 시간 기준으로 환산한 비율. 링 게이지에 쓴다.
    private var progress: Double {
        guard minutes < 60 else { return 0 }
        return max(0, min(1, Double(60 - minutes) / 60))
    }

    var body: some View {
        if let countdown = status.countdown {
            HStack(alignment: .center, spacing: Theme.Space.md) {
                Ring(progress: progress, urgent: urgent)

                VStack(alignment: .leading, spacing: 2) {
                    Text(countdown)
                        .font(Theme.Font.display)
                        .foregroundStyle(urgent ? Theme.warning : .primary)
                        .contentTransition(.numericText())
                        .animation(.snappy, value: minutes)

                    Text(status.eventTitle)
                        .font(Theme.Font.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer(minLength: 0)
            }
            .padding(Theme.Space.md)
            .cardBackground(emphasized: urgent)
        } else {
            HStack(spacing: Theme.Space.sm) {
                Image(systemName: "checkmark.circle")
                    .foregroundStyle(.tertiary)
                Text("남은 일정 없음")
                    .font(Theme.Font.body)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, Theme.Space.xs)
        }
    }
}

/// 남은 시간을 도는 링. 숫자만 있을 때보다 한눈에 들어온다.
private struct Ring: View {
    let progress: Double
    let urgent: Bool

    private let size: CGFloat = 34

    var body: some View {
        ZStack {
            Circle()
                .stroke(.quaternary, lineWidth: 3)
            Circle()
                .trim(from: 0, to: progress)
                .stroke(
                    urgent ? Theme.warning : Theme.accent,
                    style: StrokeStyle(lineWidth: 3, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))
                .animation(.easeInOut(duration: 0.4), value: progress)

            Image(systemName: urgent ? "exclamationmark" : "calendar")
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(urgent ? Theme.warning : .secondary)
        }
        .frame(width: size, height: size)
    }
}

// MARK: - 할 일

private struct TodoCard: View {
    let items: [String]
    let onTap: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.sm) {
            HStack(spacing: Theme.Space.xs) {
                Image(systemName: "checklist")
                    .font(.system(size: 10, weight: .semibold))
                Text("남은 할 일")
                Spacer()
                Text("\(items.count)")
            }
            .sectionLabel()

            VStack(alignment: .leading, spacing: Theme.Space.sm) {
                ForEach(items, id: \.self) { item in
                    TodoRow(text: item) { onTap(item) }
                }
            }
        }
        .padding(Theme.Space.md)
        .cardBackground()
    }
}

private struct TodoRow: View {
    let text: String
    let action: () -> Void

    @Environment(\.colorScheme) private var scheme
    @State private var hovering = false

    var body: some View {
        Button(action: action) {
            HStack(alignment: .top, spacing: Theme.Space.sm) {
                Image(systemName: hovering ? "circle.inset.filled" : "circle")
                    .font(.system(size: 11))
                    .foregroundStyle(hovering ? Theme.accent : .secondary)
                    .padding(.top, 1)

                Text(text)
                    .font(Theme.Font.body)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)

                Spacer(minLength: 0)
            }
            .padding(.horizontal, Theme.Space.xs)
            .padding(.vertical, 2)
            .background(
                hovering ? Theme.hoverFill(scheme) : .clear,
                in: RoundedRectangle(cornerRadius: 6)
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hovering = $0 }
        .help("눌러서 비서에게 넘기기")
    }
}

// MARK: - 쪽지와 브리핑

private struct NoteRow: View {
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: Theme.Space.sm) {
            Image(systemName: "info.circle")
                .font(.system(size: 11))
                .foregroundStyle(Theme.accent)
                .padding(.top, 1)
            Text(text)
                .font(Theme.Font.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(Theme.Space.md)
        .cardBackground()
    }
}

private struct BriefCard: View {
    let text: String
    @Binding var expanded: Bool

    private var firstLine: String {
        text.split(separator: "\n", maxSplits: 1).first.map(String.init) ?? text
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.sm) {
            Button {
                withAnimation(.easeInOut(duration: 0.2)) { expanded.toggle() }
            } label: {
                HStack(spacing: Theme.Space.xs) {
                    Image(systemName: "sun.horizon")
                        .font(.system(size: 10, weight: .semibold))
                    Text("오늘 브리핑")
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.system(size: 9, weight: .bold))
                        .rotationEffect(.degrees(expanded ? 90 : 0))
                }
                .sectionLabel()
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            Text(expanded ? text : firstLine)
                .font(Theme.Font.caption)
                .foregroundStyle(.secondary)
                .lineLimit(expanded ? nil : 2)
                .textSelection(.enabled)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(Theme.Space.md)
        .cardBackground()
    }
}

/// 아무 일도 없을 때. "남은 일정 없음" 한 줄만 덩그러니 두지 않는다.
private struct QuietState: View {
    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.xs) {
            Image(systemName: "cup.and.saucer")
                .font(.system(size: 20, weight: .light))
                .foregroundStyle(.tertiary)
                .padding(.bottom, Theme.Space.xs)

            Text("조용한 시간입니다")
                .font(Theme.Font.title)
                .foregroundStyle(.secondary)

            Text("남은 일정도 할 일도 없습니다.")
                .font(Theme.Font.caption)
                .foregroundStyle(.tertiary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, Theme.Space.lg)
    }
}

struct DaemonBanner: View {
    var body: some View {
        HStack(spacing: Theme.Space.sm) {
            Image(systemName: "exclamationmark.triangle.fill")
            Text("데몬이 실행 중이 아닙니다")
            Spacer()
        }
        .font(Theme.Font.caption)
        .foregroundStyle(Theme.warning)
        .padding(.horizontal, Theme.Space.md)
        .padding(.vertical, Theme.Space.sm)
        .background(Theme.warning.opacity(0.12), in: RoundedRectangle(cornerRadius: Theme.Radius.card))
    }
}
