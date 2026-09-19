import SwiftUI

/// 패널 전체. 위는 대기 화면, 아래는 대화, 맨 아래는 입력.
///
/// 대화를 시작하면 대기 화면이 접힌다. 좁은 패널에서 둘 다 펼쳐두면
/// 어느 쪽도 읽히지 않는다.
struct AssistantView: View {
    @ObservedObject var conversation: ConversationModel
    @ObservedObject var status: StatusModel
    @ObservedObject var panel: PanelController

    @FocusState private var inputFocused: Bool

    private var hasConversation: Bool { !conversation.turns.isEmpty }

    var body: some View {
        VStack(spacing: 0) {
            header

            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        if !hasConversation {
                            IdleView(model: status)
                                .transition(.opacity)
                        }

                        ForEach(conversation.turns) { turn in
                            TurnRow(turn: turn).id(turn.id)
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.bottom, 12)
                }
                .onChange(of: conversation.turns.last?.text) { _, _ in
                    guard let last = conversation.turns.last else { return }
                    withAnimation(.easeOut(duration: 0.15)) {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }

            inputBar
        }
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .task {
            status.start()
            inputFocused = true
        }
    }

    private var header: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(conversation.isWorking ? Color.accentColor : Color.secondary.opacity(0.45))
                .frame(width: 6, height: 6)

            Text(conversation.isWorking ? "생각 중" : "비서")
                .font(.caption)
                .foregroundStyle(.secondary)

            Spacer()

            if hasConversation {
                Button {
                    withAnimation { conversation.clear() }
                } label: {
                    Image(systemName: "arrow.counterclockwise")
                }
                .buttonStyle(.plain)
                .help("대화 비우기")
            }

            Button {
                panel.isPinned.toggle()
            } label: {
                Image(systemName: panel.isPinned ? "pin.fill" : "pin.slash")
            }
            .buttonStyle(.plain)
            .foregroundStyle(panel.isPinned ? Color.accentColor : Color.secondary)
            .help(panel.isPinned ? "항상 위 — 끄기" : "항상 위 — 켜기")
        }
        .font(.system(size: 11))
        .padding(.horizontal, 14)
        .padding(.top, 10)
        .padding(.bottom, 10)
    }

    private var inputBar: some View {
        VStack(spacing: 0) {
            Divider().opacity(0.5)
            HStack(spacing: 8) {
                TextField("무엇을 할까요?", text: $conversation.input, axis: .vertical)
                    .textFieldStyle(.plain)
                    .font(.callout)
                    .lineLimit(1...5)
                    .focused($inputFocused)
                    .onSubmit(conversation.submit)

                if conversation.isWorking {
                    Button(action: conversation.cancel) {
                        Image(systemName: "stop.circle.fill")
                    }
                    .buttonStyle(.plain)
                    .help("중단")
                } else {
                    Button(action: conversation.submit) {
                        Image(systemName: "arrow.up.circle.fill")
                    }
                    .buttonStyle(.plain)
                    .disabled(conversation.input.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 11)
        }
    }
}

struct TurnRow: View {
    let turn: Turn

    var body: some View {
        switch turn.role {
        case .user:
            Text(turn.text)
                .font(.callout)
                .padding(.horizontal, 10)
                .padding(.vertical, 7)
                .background(Color.accentColor.opacity(0.18), in: RoundedRectangle(cornerRadius: 10))
                .frame(maxWidth: .infinity, alignment: .trailing)

        case .assistant:
            Text(turn.text.isEmpty ? "…" : turn.text)
                .font(.callout)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)

        case .tool:
            HStack(spacing: 5) {
                Image(systemName: "wrench.and.screwdriver")
                Text(toolLabel(turn.text))
            }
            .font(.caption2)
            .foregroundStyle(.tertiary)
            .frame(maxWidth: .infinity, alignment: .leading)

        case .error:
            Text(turn.text)
                .font(.caption)
                .foregroundStyle(.red)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    /// "mcp__calendar__list_events" 를 "calendar · list events" 로.
    private func toolLabel(_ raw: String) -> String {
        let parts = raw.split(separator: "_").filter { !$0.isEmpty }
        guard parts.count >= 2 else { return raw }
        let server = parts[parts.count - 2 >= 1 ? 1 : 0]
        let tool = parts.suffix(from: min(2, parts.count - 1)).joined(separator: " ")
        return "\(server) · \(tool)"
    }
}
