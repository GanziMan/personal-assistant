import SwiftUI

/// 말을 걸지 않을 때 보이는 부분.
///
/// 항상 떠 있는 창은 비어 있으면 거슬려서 닫게 되고, 가득 차면 작업에
/// 방해가 된다. 지금 당장 쓸모 있는 것만, 한눈에 읽히게 둔다.
struct IdleView: View {
    @ObservedObject var model: StatusModel
    var onTodoTap: (String) -> Void = { _ in }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if !model.daemonReachable {
                DaemonBanner()
            }

            NextEventCard(status: model.status)

            if !model.status.todos.isEmpty {
                SectionCard(icon: "checklist", title: "남은 할 일") {
                    VStack(alignment: .leading, spacing: 9) {
                        ForEach(model.status.todos, id: \.self) { item in
                            TodoRow(text: item) { onTodoTap(item) }
                        }
                    }
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

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            if let countdown = status.countdown {
                HStack(alignment: .firstTextBaseline, spacing: 7) {
                    Image(systemName: urgent ? "clock.badge.exclamationmark" : "clock")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(urgent ? Color.orange : Color.secondary)

                    Text(countdown)
                        .font(.system(size: 27, weight: .semibold, design: .rounded))
                        .foregroundStyle(urgent ? Color.orange : Color.primary)
                        .contentTransition(.numericText())
                        .animation(.snappy, value: minutes)
                }

                Text(status.eventTitle)
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)

                if urgent {
                    ProgressView(value: Double(max(0, 15 - minutes)), total: 15)
                        .tint(.orange)
                        .scaleEffect(y: 0.6, anchor: .center)
                        .padding(.top, 2)
                }
            } else {
                HStack(spacing: 7) {
                    Image(systemName: "checkmark.circle")
                        .foregroundStyle(.tertiary)
                    Text("남은 일정 없음")
                        .font(.system(size: 15, weight: .medium, design: .rounded))
                        .foregroundStyle(.secondary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 2)
    }
}

// MARK: - 공통 카드

struct SectionCard<Content: View>: View {
    let icon: String
    let title: String
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack(spacing: 5) {
                Image(systemName: icon)
                    .font(.system(size: 10, weight: .semibold))
                Text(title)
                    .font(.system(size: 11, weight: .medium))
                Spacer()
            }
            .foregroundStyle(.tertiary)

            content
        }
        .padding(12)
        .cardBackground()
    }
}

private struct TodoRow: View {
    let text: String
    let action: () -> Void

    @State private var hovering = false

    var body: some View {
        Button(action: action) {
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: hovering ? "circle.inset.filled" : "circle")
                    .font(.system(size: 11))
                    .foregroundStyle(hovering ? Color.accentColor : Color.secondary)
                    .padding(.top, 1)

                Text(text)
                    .font(.system(size: 13))
                    .foregroundStyle(.primary)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)

                Spacer(minLength: 0)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hovering = $0 }
        .help("눌러서 비서에게 넘기기")
    }
}

private struct BriefCard: View {
    let text: String
    @Binding var expanded: Bool

    private var firstLine: String {
        text.split(separator: "\n", maxSplits: 1).first.map(String.init) ?? text
    }

    var body: some View {
        SectionCard(icon: "sun.horizon", title: "오늘 브리핑") {
            VStack(alignment: .leading, spacing: 7) {
                Text(expanded ? text : firstLine)
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .lineLimit(expanded ? nil : 2)
                    .textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)

                Button {
                    withAnimation(.easeInOut(duration: 0.2)) { expanded.toggle() }
                } label: {
                    HStack(spacing: 3) {
                        Text(expanded ? "접기" : "더 보기")
                        Image(systemName: expanded ? "chevron.up" : "chevron.down")
                            .font(.system(size: 8, weight: .bold))
                    }
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
                }
                .buttonStyle(.plain)
            }
        }
    }
}

struct DaemonBanner: View {
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "exclamationmark.triangle.fill")
            Text("데몬이 실행 중이 아닙니다")
            Spacer()
        }
        .font(.system(size: 11))
        .foregroundStyle(.orange)
        .padding(.horizontal, 10)
        .padding(.vertical, 7)
        .background(.orange.opacity(0.14), in: RoundedRectangle(cornerRadius: 8))
    }
}
