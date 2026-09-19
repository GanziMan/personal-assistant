import AppKit
import SwiftUI

/// 비서가 스스로의 상태를 드러내는 줄.
///
/// 꺼진 기능이 있으면 무엇이 나빠지는지와 고치는 명령까지 보여준다.
/// "왜 검색이 시원찮지" 를 사용자가 혼자 추측하게 두지 않는다.
struct HealthBanner: View {
    let capabilities: [Capability]
    @State private var expanded = false

    private var down: [Capability] { capabilities.filter { !$0.ok } }

    var body: some View {
        if !down.isEmpty {
            VStack(alignment: .leading, spacing: 7) {
                Button {
                    withAnimation(.easeInOut(duration: 0.18)) { expanded.toggle() }
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "bolt.slash.fill")
                            .font(.system(size: 10))
                        Text(headline)
                            .font(Theme.Font.label)
                            .lineLimit(1)
                        Spacer(minLength: 2)
                        Image(systemName: expanded ? "chevron.up" : "chevron.down")
                            .font(.system(size: 8, weight: .bold))
                    }
                    .foregroundStyle(.yellow)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)

                if expanded {
                    ForEach(down) { capability in
                        CapabilityRow(capability: capability)
                    }
                }
            }
            .padding(.horizontal, Theme.Space.md)
            .padding(.vertical, Theme.Space.sm)
            .background(.yellow.opacity(0.12), in: RoundedRectangle(cornerRadius: Theme.Radius.card))
        }
    }

    private var headline: String {
        down.count == 1
            ? "\(down[0].label) 꺼짐"
            : "\(down.count)개 기능 꺼짐"
    }
}

private struct CapabilityRow: View {
    let capability: Capability
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            if !capability.degraded.isEmpty {
                Text(capability.degraded)
                    .font(Theme.Font.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if !capability.fix.isEmpty {
                Button {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(capability.fix, forType: .string)
                    copied = true
                    Task {
                        try? await Task.sleep(for: .seconds(1.4))
                        copied = false
                    }
                } label: {
                    HStack(spacing: 5) {
                        Text(capability.fix)
                            .font(Theme.Font.mono)
                        Image(systemName: copied ? "checkmark" : "doc.on.doc")
                            .font(.system(size: 9))
                    }
                    .padding(.horizontal, 7)
                    .padding(.vertical, 4)
                    .background(.quaternary.opacity(0.4), in: RoundedRectangle(cornerRadius: 6))
                }
                .buttonStyle(.plain)
                .foregroundStyle(copied ? Color.green : Color.secondary)
                .help("복사해서 터미널에 붙여넣으세요")
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

/// 헤더에 늘 붙는 작은 점. 모든 기능이 정상이면 보이지 않는다.
struct HealthDot: View {
    let capabilities: [Capability]

    var body: some View {
        if capabilities.contains(where: { !$0.ok }) {
            Circle()
                .fill(.yellow)
                .frame(width: 5, height: 5)
                .help("일부 기능이 꺼져 있습니다")
        }
    }
}
