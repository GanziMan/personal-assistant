import SwiftUI

struct ConversationView: View {
    @ObservedObject var model: ConversationModel
    @FocusState private var inputFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            if model.daemonDown {
                DaemonBanner()
            }

            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 10) {
                        ForEach(model.turns) { turn in
                            TurnRow(turn: turn).id(turn.id)
                        }
                    }
                    .padding(12)
                }
                .onChange(of: model.turns.last?.text) { _, _ in
                    // 스트리밍 중에도 마지막 줄이 보이게 따라간다
                    if let last = model.turns.last {
                        withAnimation(.easeOut(duration: 0.15)) {
                            proxy.scrollTo(last.id, anchor: .bottom)
                        }
                    }
                }
            }
            .frame(maxHeight: .infinity)

            Divider()
            inputBar
        }
        .frame(width: 420, height: 460)
        .onAppear {
            inputFocused = true
            Task { await model.checkDaemon() }
        }
    }

    private var inputBar: some View {
        HStack(spacing: 8) {
            TextField("무엇을 할까요?", text: $model.input, axis: .vertical)
                .textFieldStyle(.plain)
                .lineLimit(1...4)
                .focused($inputFocused)
                .onSubmit(model.submit)

            if model.isWorking {
                Button(action: model.cancel) {
                    Image(systemName: "stop.circle.fill")
                }
                .buttonStyle(.plain)
                .help("중단")
            } else {
                Button(action: model.submit) {
                    Image(systemName: "arrow.up.circle.fill")
                }
                .buttonStyle(.plain)
                .disabled(model.input.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
    }
}

private struct TurnRow: View {
    let turn: Turn

    var body: some View {
        switch turn.role {
        case .user:
            Text(turn.text)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Color.accentColor.opacity(0.15), in: RoundedRectangle(cornerRadius: 8))
                .frame(maxWidth: .infinity, alignment: .trailing)

        case .assistant:
            Text(turn.text.isEmpty ? "…" : turn.text)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)

        case .tool:
            Label(turn.text, systemImage: "wrench.and.screwdriver")
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)

        case .error:
            Text(turn.text)
                .font(.callout)
                .foregroundStyle(.red)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct DaemonBanner: View {
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "exclamationmark.triangle.fill")
            Text("데몬이 실행 중이 아닙니다")
            Spacer()
        }
        .font(.caption)
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(.orange.opacity(0.2))
    }
}
