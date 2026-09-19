import SwiftUI

/// 디자인 토큰.
///
/// 크기와 여백을 그때그때 숫자로 적으면 위계가 흐려진다. 10, 11, 12,
/// 13 이 섞여 있으면 어느 것이 더 중요한지 눈이 구분하지 못한다.
/// 단계를 미리 정하고 그중에서만 고른다 (ADR-037).
enum Theme {

    // MARK: - 타이포

    /// macOS 시스템 텍스트 스타일에 맞춘 다섯 단계.
    /// 본문(13pt)은 AppKit 의 기본 크기다 — 시스템 앱과 같은 리듬이 난다.
    enum Font {
        /// 카운트다운처럼 한눈에 읽혀야 하는 값
        static let display = SwiftUI.Font.system(size: 28, weight: .medium, design: .rounded)
        /// 카드 제목, 강조된 한 줄
        static let title = SwiftUI.Font.system(size: 13, weight: .semibold)
        /// 본문. 대화와 목록
        static let body = SwiftUI.Font.system(size: 13)
        /// 보조 설명
        static let caption = SwiftUI.Font.system(size: 11)
        /// 라벨, 상태
        static let label = SwiftUI.Font.system(size: 11, weight: .medium)
        /// 코드
        static let mono = SwiftUI.Font.system(size: 12, design: .monospaced)
    }

    // MARK: - 여백

    /// 4의 배수. 그 사이 값은 쓰지 않는다.
    enum Space {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 24
    }

    enum Radius {
        static let card: CGFloat = 10
        static let panel: CGFloat = 12
        static let pill: CGFloat = 999
    }

    // MARK: - 색

    /// 색을 직접 쓰지 않고 여기를 거친다. 라이트에서 흰 선을 긋는
    /// 실수를 구조적으로 막는다.
    static func stroke(_ scheme: ColorScheme) -> Color {
        scheme == .dark ? .white.opacity(0.10) : .black.opacity(0.09)
    }

    static func cardFill(_ scheme: ColorScheme) -> Color {
        scheme == .dark ? .white.opacity(0.055) : .black.opacity(0.035)
    }

    /// 눌린 상태, 호버
    static func hoverFill(_ scheme: ColorScheme) -> Color {
        scheme == .dark ? .white.opacity(0.10) : .black.opacity(0.06)
    }

    /// 강조색은 시스템을 따른다. 사용자가 시스템 설정에서 고른 색이
    /// 곧 취향이고, 앱이 자기 색을 고집할 이유가 없다.
    static let accent = Color.accentColor

    /// 주의를 끌어야 할 때만. 임박한 일정, 꺼진 기능.
    static let warning = Color.orange
}

/// 카드 한 장.
struct CardBackground: ViewModifier {
    @Environment(\.colorScheme) private var scheme
    var radius: CGFloat = Theme.Radius.card
    var emphasized = false

    func body(content: Content) -> some View {
        content
            .background(
                emphasized ? Theme.accent.opacity(0.08) : Theme.cardFill(scheme),
                in: RoundedRectangle(cornerRadius: radius)
            )
            .overlay(
                RoundedRectangle(cornerRadius: radius)
                    .strokeBorder(
                        emphasized ? Theme.accent.opacity(0.25) : Theme.stroke(scheme),
                        lineWidth: 1
                    )
            )
    }
}

extension View {
    func cardBackground(radius: CGFloat = Theme.Radius.card, emphasized: Bool = false) -> some View {
        modifier(CardBackground(radius: radius, emphasized: emphasized))
    }

    /// 섹션 라벨. 대문자화하지 않는다 — 한글에서는 의미가 없고
    /// 영문만 튀어 보인다.
    func sectionLabel() -> some View {
        font(Theme.Font.label).foregroundStyle(.tertiary)
    }
}
