// swift-tools-version: 5.9
import PackageDescription

// Xcode 프로젝트 대신 SwiftPM 을 쓴다. Command Line Tools 만 있어도
// 빌드되고, .app 번들은 scripts/build-app.sh 가 조립한다.
let package = Package(
    name: "Assistant",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(
            name: "Assistant",
            path: "Sources/Assistant"
        )
    ]
)
