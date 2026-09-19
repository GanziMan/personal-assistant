import SwiftUI

/// 말을 걸지 않을 때 보이는 부분.
///
/// 항상 떠 있는 창은 비어 있으면 거슬려서 닫게 된다. 그렇다고 가득
/// 채우면 작업에 방해가 된다. 지금 당장 쓸모 있는 것만 둔다 —
/// 다음 일정, 남은 할 일, 접어둔 아침 브리핑.
struct IdleView: View {
    @ObservedObject var model: StatusModel

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            if !model.daemonReachable {
                DaemonBanner()
            }

            NextEventCard(status: model.status)

            if !model.status.todos.isEmpty {
                TodoList(items: model.status.todos)
            }

            if !model.status.brief.isEmpty {
                BriefCard(text: model.status.brief, expanded: $model.briefExpanded)
            }
        }
    }
}

private struct NextEventCard: View {
    let status: StatusPayload

    private var urgent: Bool { (status.nextEventMinutes ?? .max) <= 15 }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let countdown = status.countdown {
                Text(countdown)
                    .font(.system(size: 26, weight: .semibold, design: .rounded))
                    .foregroundStyle(urgent ? Color.orange : Color.primary)
                    .contentTransition(.numericText())

                Text(status.eventTitle)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            } else {
                Text("남은 일정 없음")
                    .font(.system(size: 20, weight: .medium, design: .rounded))
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct TodoList: View {
    let items: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("남은 할 일")
                .font(.caption)
                .foregroundStyle(.tertiary)

            ForEach(items, id: \.self) { item in
                HStack(alignment: .top, spacing: 7) {
                    Circle()
                        .strokeBorder(.secondary, lineWidth: 1.2)
                        .frame(width: 7, height: 7)
                        .padding(.top, 5)
                    Text(item)
                        .font(.callout)
                        .lineLimit(2)
                }
            }
        }
    }
}

private struct BriefCard: View {
    let text: String
    @Binding var expanded: Bool

    private var firstLine: String {
        text.split(separator: "\n", maxSplits: 1).first.map(String.init) ?? text
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Button {
                withAnimation(.easeInOut(duration: 0.18)) { expanded.toggle() }
            } label: {
                HStack(spacing: 5) {
                    Text("오늘 브리핑")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                    Image(systemName: expanded ? "chevron.down" : "chevron.right")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(.tertiary)
                    Spacer()
                }
            }
            .buttonStyle(.plain)

            Text(expanded ? text : firstLine)
                .font(.callout)
                .foregroundStyle(.secondary)
                .lineLimit(expanded ? nil : 2)
                .textSelection(.enabled)
        }
        .padding(10)
        .background(.quaternary.opacity(0.4), in: RoundedRectangle(cornerRadius: 9))
    }
}

struct DaemonBanner: View {
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "exclamationmark.triangle.fill")
            Text("데몬이 실행 중이 아닙니다")
            Spacer()
        }
        .font(.caption)
        .padding(.horizontal, 9)
        .padding(.vertical, 6)
        .background(.orange.opacity(0.22), in: RoundedRectangle(cornerRadius: 7))
    }
}
