import SwiftUI

/// 처음 열었을 때. 빈 화면 대신 무엇을 시킬 수 있는지 보여준다.
///
/// 한 번 대화하면 다시 나오지 않는다. 안내가 계속 자리를 차지하면
/// 그때부터는 소음이다.
struct Onboarding: View {
    let onPick: (String) -> Void

    @AppStorage("onboarding.dismissed") private var dismissed = false

    private static let examples: [(String, String, String)] = [
        ("calendar", "오늘 일정 뭐야", "캘린더를 직접 읽습니다"),
        ("folder", "다운로드에 정리할 거 있어?", "허용된 폴더만 봅니다"),
        ("doc.text.magnifyingglass", "정산 관련 정리한 문서 찾아줘", "내용으로 찾습니다"),
        ("chevron.left.forwardslash.chevron.right", "손 놓은 브랜치 있어?", "모든 레포를 한 번에"),
        ("doc.on.clipboard", "방금 복사한 거 봐줘", "붙여넣지 않아도 됩니다"),
    ]

    var body: some View {
        if !dismissed {
            VStack(alignment: .leading, spacing: 11) {
                HStack {
                    Text("이런 걸 시킬 수 있습니다")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(.tertiary)
                    Spacer()
                    Button {
                        withAnimation { dismissed = true }
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 9, weight: .bold))
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.tertiary)
                    .help("다시 보지 않기")
                }

                VStack(alignment: .leading, spacing: 8) {
                    ForEach(Self.examples, id: \.1) { icon, prompt, note in
                        Button {
                            onPick(prompt)
                        } label: {
                            HStack(alignment: .top, spacing: 8) {
                                Image(systemName: icon)
                                    .font(.system(size: 11))
                                    .foregroundStyle(Color.accentColor)
                                    .frame(width: 15, alignment: .center)
                                    .padding(.top, 1)

                                VStack(alignment: .leading, spacing: 1) {
                                    Text(prompt)
                                        .font(.system(size: 12))
                                    Text(note)
                                        .font(.system(size: 10))
                                        .foregroundStyle(.tertiary)
                                }
                                Spacer(minLength: 0)
                            }
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                }

                Text("⌥Space 로 부르고, ⌘J 로 접습니다. 파일을 끌어다 놓아도 됩니다.")
                    .font(.system(size: 10))
                    .foregroundStyle(.tertiary)
                    .padding(.top, 2)
            }
            .padding(12)
            .cardBackground()
        }
    }
}
