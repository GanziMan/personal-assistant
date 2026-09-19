import SwiftUI

/// 비서의 시각적 존재.
///
/// 캐릭터 그림을 넣지 않는다. 맥에 상주하는 도구가 귀여운 얼굴을
/// 하고 있으면 하루 이틀은 즐겁고 그다음부터 거슬린다. 대신 추상적인
/// 빛덩어리가 상태에 따라 달라지게 한다 — 존재감은 주되 성격은 주지
/// 않는 선이다.
struct Avatar: View {
    enum State {
        case idle       // 천천히 숨 쉰다
        case thinking   // 빠르게 맥동하며 회전한다
        case alert      // 주의를 끈다

        var tint: Color {
            switch self {
            case .idle: return .accentColor
            case .thinking: return .accentColor
            case .alert: return .orange
            }
        }

        var period: Double {
            switch self {
            case .idle: return 3.6
            case .thinking: return 0.9
            case .alert: return 1.8
            }
        }
    }

    let state: State
    var size: CGFloat = 26

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var pulse = false
    @State private var spin = false

    var body: some View {
        ZStack {
            // 바깥 번짐 — 숨 쉬는 느낌을 만드는 층
            Circle()
                .fill(state.tint.opacity(0.18))
                .frame(width: size * 1.7, height: size * 1.7)
                .scaleEffect(pulse ? 1.0 : 0.72)
                .opacity(pulse ? 0.45 : 0.9)

            // 회전하는 그라데이션 고리 — 생각 중일 때만 눈에 띈다
            Circle()
                .strokeBorder(
                    AngularGradient(
                        colors: [state.tint.opacity(0.0), state.tint.opacity(0.85), state.tint.opacity(0.0)],
                        center: .center
                    ),
                    lineWidth: 2
                )
                .frame(width: size * 1.25, height: size * 1.25)
                .rotationEffect(.degrees(spin ? 360 : 0))
                .opacity(state == .thinking ? 1 : 0)

            // 코어
            Circle()
                .fill(
                    RadialGradient(
                        colors: [.white.opacity(0.9), state.tint],
                        center: .init(x: 0.35, y: 0.3),
                        startRadius: 0,
                        endRadius: size * 0.7
                    )
                )
                .frame(width: size * 0.62, height: size * 0.62)
                .shadow(color: state.tint.opacity(0.6), radius: pulse ? 6 : 3)
        }
        .frame(width: size * 1.7, height: size * 1.7)
        .onAppear { animate() }
        .onChange(of: state.period) { _, _ in animate() }
    }

    private func animate() {
        guard !reduceMotion else { return }
        pulse = false
        withAnimation(.easeInOut(duration: state.period).repeatForever(autoreverses: true)) {
            pulse = true
        }
        if state == .thinking {
            spin = false
            withAnimation(.linear(duration: 1.6).repeatForever(autoreverses: false)) {
                spin = true
            }
        }
    }
}

extension Avatar.State: Equatable {}
