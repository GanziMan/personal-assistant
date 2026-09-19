import SwiftUI

/// 라이트/다크 양쪽에서 성립하는 값들.
///
/// 테두리를 `.white.opacity(0.07)` 로 주면 다크에서는 은은한 경계가
/// 되지만 라이트에서는 흰 배경에 흰 선이라 아무것도 안 보인다.
/// 색을 직접 쓰지 않고 여기를 거친다.
enum Theme {
    /// 카드·입력창 테두리. 라이트에서는 어둡게, 다크에서는 밝게.
    static func stroke(_ scheme: ColorScheme) -> Color {
        scheme == .dark ? .white.opacity(0.08) : .black.opacity(0.10)
    }

    /// 카드 배경. 패널이 반투명이라 너무 진하면 뒤가 안 비친다.
    static func cardFill(_ scheme: ColorScheme) -> Color {
        scheme == .dark ? .white.opacity(0.06) : .black.opacity(0.045)
    }

    static let cardRadius: CGFloat = 11
    static let panelRadius: CGFloat = 15
}

/// 카드 한 장의 배경과 테두리를 한 번에.
struct CardBackground: ViewModifier {
    @Environment(\.colorScheme) private var scheme
    var radius: CGFloat = Theme.cardRadius

    func body(content: Content) -> some View {
        content
            .background(Theme.cardFill(scheme), in: RoundedRectangle(cornerRadius: radius))
            .overlay(
                RoundedRectangle(cornerRadius: radius)
                    .strokeBorder(Theme.stroke(scheme), lineWidth: 1)
            )
    }
}

extension View {
    func cardBackground(radius: CGFloat = Theme.cardRadius) -> some View {
        modifier(CardBackground(radius: radius))
    }
}
