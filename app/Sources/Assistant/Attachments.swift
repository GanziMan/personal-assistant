import AppKit
import SwiftUI
import UniformTypeIdentifiers

/// 패널에 들어온 파일과 붙여넣은 이미지를 다룬다.
///
/// 파일 내용을 앱이 직접 읽지 않는다. 경로만 만들어 비서에게 넘기고,
/// 읽기는 도구가 한다 — 그래야 파일 서버의 경로 경계가 한 곳에
/// 유지된다 (ADR-035).
enum Attachments {
    static let pastedDirectory = URL(fileURLWithPath: NSHomeDirectory())
        .appendingPathComponent(".assistant/pasted")

    private static let imageSuffixes: Set<String> = [
        "png", "jpg", "jpeg", "gif", "bmp", "tiff", "heic", "webp",
    ]

    static func isImage(_ url: URL) -> Bool {
        imageSuffixes.contains(url.pathExtension.lowercased())
    }

    /// 떨어진 파일들을 비서에게 건넬 문장으로.
    static func prompt(for urls: [URL]) -> String {
        guard !urls.isEmpty else { return "" }

        let paths = urls.map(\.path)
        if urls.count == 1, let one = urls.first {
            return isImage(one)
                ? "\(one.path) 이미지에서 글자 읽어서 설명해줘"
                : "\(one.path) 내용 보고 정리해줘"
        }
        return "다음 파일들 보고 정리해줘:\n" + paths.map { "- \($0)" }.joined(separator: "\n")
    }

    /// 클립보드의 이미지를 파일로 떨군다. 경로를 돌려준다.
    static func savePastedImage(from pasteboard: NSPasteboard = .general) -> URL? {
        guard let image = NSImage(pasteboard: pasteboard),
              let tiff = image.tiffRepresentation,
              let rep = NSBitmapImageRep(data: tiff),
              let png = rep.representation(using: .png, properties: [:])
        else { return nil }

        do {
            try FileManager.default.createDirectory(
                at: pastedDirectory,
                withIntermediateDirectories: true,
                attributes: [.posixPermissions: 0o700]
            )
        } catch {
            return nil
        }

        let name = "paste-\(Int(Date().timeIntervalSince1970)).png"
        let url = pastedDirectory.appendingPathComponent(name)
        do {
            try png.write(to: url, options: .atomic)
        } catch {
            return nil
        }
        return url
    }

    /// 드롭 제공자에서 파일 URL 을 꺼낸다.
    static func urls(from providers: [NSItemProvider]) async -> [URL] {
        var out: [URL] = []
        for provider in providers {
            guard provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier)
            else { continue }
            if let url = await loadURL(from: provider) {
                out.append(url)
            }
        }
        return out
    }

    private static func loadURL(from provider: NSItemProvider) async -> URL? {
        await withCheckedContinuation { continuation in
            _ = provider.loadObject(ofClass: URL.self) { url, _ in
                continuation.resume(returning: url)
            }
        }
    }
}
