import AppKit
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

            if !panel.isCompact {
                content
            }
        }
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: Theme.panelRadius))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.panelRadius)
                .strokeBorder(Theme.stroke(scheme), lineWidth: 1)
        )
        .background {
            // 보이지 않는 버튼으로 단축키를 건다. 패널에는 메뉴 막대가
            // 없어서 커맨드 등록이 이 방법밖에 없다.
            VStack {
                Button("") { withAnimation { conversation.clear() } }
                    .keyboardShortcut("k", modifiers: .command)
                Button("") { panel.isCompact.toggle() }
                    .keyboardShortcut("j", modifiers: .command)
            }
            .opacity(0)
            .allowsHitTesting(false)
        }
        .onExitCommand { panel.hide() }
        .task {
            status.start()
            inputFocused = true
        }
    }

    private var content: some View {
        VStack(spacing: 0) {
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
    }

    // MARK: - 헤더

    private var header: some View {
        HStack(alignment: .center, spacing: 10) {
            Avatar(mood: mood)

            VStack(alignment: .leading, spacing: 1) {
                HStack(spacing: 5) {
                    Text(headerTitle)
                        .font(.system(size: 12, weight: .semibold))
                        .lineLimit(1)
                    HealthDot(capabilities: status.status.capabilities)
                }
                Text(headerSubtitle)
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

            iconButton(panel.isCompact ? "chevron.down" : "chevron.up",
                       help: panel.isCompact ? "펼치기" : "접기") {
                panel.isCompact.toggle()
            }

            iconButton(panel.isPinned ? "pin.fill" : "pin.slash",
                       help: panel.isPinned ? "항상 위 — 끄기" : "항상 위 — 켜기",
                       active: panel.isPinned) {
                panel.isPinned.toggle()
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, panel.isCompact ? 0 : 11)
        .frame(height: panel.isCompact ? PanelController.compactHeight : nil)
    }

    /// 접었을 때는 다음 일정이 제목 자리로 올라온다.
    private var headerTitle: String {
        if conversation.isWorking { return "생각하는 중" }
        if panel.isCompact, let countdown = status.status.countdown { return countdown }
        return "비서"
    }

    private var headerSubtitle: String {
        if conversation.isWorking { return " " }
        if panel.isCompact {
            return status.status.countdown == nil
                ? "남은 일정 없음"
                : status.status.eventTitle
        }
        return Greeting.line(for: status.status)
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
                .onKeyPress(.upArrow) {
                    // 여러 줄을 편집 중이면 커서 이동이 우선이다
                    guard !conversation.input.contains("\n") else { return .ignored }
                    conversation.recallPrevious()
                    return .handled
                }
                .onKeyPress(.downArrow) {
                    guard !conversation.input.contains("\n") else { return .ignored }
                    conversation.recallNext()
                    return .handled
                }

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
            AssistantTurn(text: turn.text, streaming: streaming)

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

/// 답변 한 덩어리. 호버하면 복사 버튼이 나온다.
private struct AssistantTurn: View {
    let text: String
    let streaming: Bool

    @State private var hovering = false
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .bottom, spacing: 3) {
                if text.isEmpty {
                    ThinkingDots()
                } else {
                    MarkdownText(raw: text)
                }
                if streaming && !text.isEmpty {
                    TypingCaret()
                }
            }

            if hovering && !streaming && !text.isEmpty {
                Button {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(text, forType: .string)
                    copied = true
                    Task {
                        try? await Task.sleep(for: .seconds(1.4))
                        copied = false
                    }
                } label: {
                    HStack(spacing: 3) {
                        Image(systemName: copied ? "checkmark" : "doc.on.doc")
                        Text(copied ? "복사됨" : "복사")
                    }
                    .font(.system(size: 10))
                }
                .buttonStyle(.plain)
                .foregroundStyle(copied ? Color.green : Color.secondary)
                .transition(.opacity)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .onHover { hovering = $0 }
        .animation(.easeInOut(duration: 0.15), value: hovering)
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
