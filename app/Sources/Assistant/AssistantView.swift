import SwiftUI

/// 패널 전체. 아바타와 인사, 대기 화면, 대화, 제안 칩, 입력.
struct AssistantView: View {
    @ObservedObject var conversation: ConversationModel
    @ObservedObject var status: StatusModel
    @ObservedObject var panel: PanelController

    @Environment(\.colorScheme) private var scheme
    @FocusState private var inputFocused: Bool

    private var hasConversation: Bool { !conversation.turns.isEmpty }

    private var mood: AvatarMood {
        if conversation.isWorking { return .thinking }
        if let m = status.status.nextEventMinutes, m <= 15 { return .alert }
        return .idle
    }

    var body: some View {
        VStack(spacing: 0) {
            header

            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        if !hasConversation {
                            IdleView(model: status) { todo in
                                conversation.input = "\(todo) 관련해서 도와줘"
                                inputFocused = true
                            }
                            .transition(.opacity.combined(with: .move(edge: .top)))
                        }

                        ForEach(conversation.turns) { turn in
                            TurnRow(
                                turn: turn,
                                streaming: conversation.isWorking
                                    && turn.id == conversation.turns.last?.id
                            )
                            .id(turn.id)
                            .transition(.opacity)
                        }
                    }
                    .padding(.horizontal, 15)
                    .padding(.bottom, 10)
                }
                .onChange(of: conversation.turns.last?.text) { _, _ in
                    guard let last = conversation.turns.last else { return }
                    withAnimation(.easeOut(duration: 0.15)) {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }

            if !hasConversation {
                suggestionRow
            }
            inputBar
        }
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: Theme.panelRadius))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.panelRadius)
                .strokeBorder(Theme.stroke(scheme), lineWidth: 1)
        )
        .task {
            status.start()
            inputFocused = true
        }
    }

    // MARK: - 헤더

    private var header: some View {
        HStack(alignment: .center, spacing: 10) {
            Avatar(mood: mood)

            VStack(alignment: .leading, spacing: 1) {
                Text(conversation.isWorking ? "생각하는 중" : "비서")
                    .font(.system(size: 12, weight: .semibold))
                Text(conversation.isWorking
                     ? " "
                     : Greeting.line(for: status.status))
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer(minLength: 4)

            if hasConversation {
                iconButton("arrow.counterclockwise", help: "대화 비우기") {
                    withAnimation { conversation.clear() }
                }
            }

            iconButton(panel.isPinned ? "pin.fill" : "pin.slash",
                       help: panel.isPinned ? "항상 위 — 끄기" : "항상 위 — 켜기",
                       active: panel.isPinned) {
                panel.isPinned.toggle()
            }
        }
        .padding(.horizontal, 14)
        .padding(.top, 12)
        .padding(.bottom, 10)
    }

    private func iconButton(
        _ symbol: String, help: String, active: Bool = false, action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Image(systemName: symbol)
                .font(.system(size: 11, weight: .medium))
                .frame(width: 22, height: 22)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .foregroundStyle(active ? Color.accentColor : Color.secondary)
        .help(help)
    }

    // MARK: - 제안 칩

    private var suggestionRow: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(Suggestion.current(for: status.status)) { item in
                    Button {
                        conversation.input = item.prompt
                        conversation.submit()
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: item.icon)
                                .font(.system(size: 9))
                            Text(item.label)
                                .font(.system(size: 11, weight: .medium))
                        }
                        .padding(.horizontal, 9)
                        .padding(.vertical, 5)
                        .background(Theme.cardFill(scheme), in: Capsule())
                        .overlay(Capsule().strokeBorder(Theme.stroke(scheme), lineWidth: 1))
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 15)
        }
        .frame(height: 34)
    }

    // MARK: - 입력

    private var inputBar: some View {
        HStack(spacing: 8) {
            TextField("무엇을 할까요?", text: $conversation.input, axis: .vertical)
                .textFieldStyle(.plain)
                .font(.system(size: 13))
                .lineLimit(1...5)
                .focused($inputFocused)
                .onSubmit(conversation.submit)

            if conversation.isWorking {
                Button(action: conversation.cancel) {
                    Image(systemName: "stop.circle.fill")
                        .font(.system(size: 17))
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .help("중단")
            } else {
                let empty = conversation.input.trimmingCharacters(in: .whitespaces).isEmpty
                Button(action: conversation.submit) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 17))
                }
                .buttonStyle(.plain)
                .foregroundStyle(empty ? Color.secondary.opacity(0.4) : Color.accentColor)
                .disabled(empty)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 9)
        .cardBackground()
        .padding(.horizontal, 12)
        .padding(.bottom, 12)
        .padding(.top, 4)
    }
}

// MARK: - 대화 한 줄

struct TurnRow: View {
    let turn: Turn
    var streaming: Bool = false

    var body: some View {
        switch turn.role {
        case .user:
            Text(turn.text)
                .font(.system(size: 13))
                .padding(.horizontal, 11)
                .padding(.vertical, 7)
                .background(Color.accentColor.opacity(0.9), in: RoundedRectangle(cornerRadius: 12))
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity, alignment: .trailing)

        case .assistant:
            HStack(alignment: .bottom, spacing: 3) {
                if turn.text.isEmpty {
                    ThinkingDots()
                } else {
                    MarkdownText(raw: turn.text)
                }
                if streaming && !turn.text.isEmpty {
                    TypingCaret()
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

        case .tool:
            ToolChip(name: turn.text, running: turn.running)
                .frame(maxWidth: .infinity, alignment: .leading)

        case .error:
            HStack(alignment: .top, spacing: 6) {
                Image(systemName: "exclamationmark.circle")
                    .font(.system(size: 10))
                Text(turn.text)
                    .font(.system(size: 11))
                    .textSelection(.enabled)
            }
            .foregroundStyle(.orange)
            .padding(9)
            .background(.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 9))
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

/// 도구 호출 하나. 도는 동안 스피너, 끝나면 체크.
private struct ToolChip: View {
    let name: String
    let running: Bool

    var body: some View {
        HStack(spacing: 5) {
            if running {
                ProgressView()
                    .controlSize(.mini)
                    .scaleEffect(0.6)
                    .frame(width: 9, height: 9)
            } else {
                Image(systemName: "checkmark")
                    .font(.system(size: 8, weight: .bold))
                    .foregroundStyle(.green)
            }
            Text(label)
                .font(.system(size: 10))
        }
        .foregroundStyle(.tertiary)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(.quaternary.opacity(0.3), in: Capsule())
        .animation(.easeInOut(duration: 0.2), value: running)
    }

    /// "mcp__calendar__list_events" 를 "calendar · list events" 로.
    private var label: String {
        let parts = name.components(separatedBy: "__").filter { !$0.isEmpty }
        guard parts.count >= 2 else { return name }
        return "\(parts[parts.count - 2]) · "
            + parts[parts.count - 1].replacingOccurrences(of: "_", with: " ")
    }
}

/// 스트리밍 중 글자 끝에서 깜빡이는 커서.
private struct TypingCaret: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var on = true

    var body: some View {
        RoundedRectangle(cornerRadius: 1)
            .fill(Color.accentColor)
            .frame(width: 2, height: 14)
            .opacity(on ? 1 : 0.15)
            .onAppear {
                guard !reduceMotion else { return }
                withAnimation(.easeInOut(duration: 0.55).repeatForever()) { on = false }
            }
    }
}

/// 첫 글자가 오기 전. 빈 줄만 있으면 멈춘 것처럼 보인다.
private struct ThinkingDots: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var phase = 0.0

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3, id: \.self) { index in
                Circle()
                    .fill(.secondary)
                    .frame(width: 5, height: 5)
                    .opacity(opacity(index))
            }
        }
        .padding(.vertical, 4)
        .onAppear {
            guard !reduceMotion else { return }
            withAnimation(.linear(duration: 1.2).repeatForever(autoreverses: false)) {
                phase = 3
            }
        }
    }

    private func opacity(_ index: Int) -> Double {
        reduceMotion ? 0.5 : (Int(phase) % 3 == index ? 1.0 : 0.3)
    }
}
