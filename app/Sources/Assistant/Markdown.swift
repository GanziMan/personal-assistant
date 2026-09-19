import AppKit
import SwiftUI

/// 답변 본문 렌더링.
///
/// 모델은 마크다운으로 답한다. 민무늬 텍스트로 그리면 `**굵게**` 와
/// `- 항목` 이 그대로 보인다. 라이브러리를 끌어오지 않고 필요한 만큼만
/// 직접 나눈다 — 문단, 목록, 코드 블록 셋이면 비서 답변의 거의 전부다.
struct MarkdownText: View {
    let raw: String

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            ForEach(Array(MarkdownBlock.parse(raw).enumerated()), id: \.offset) { _, block in
                switch block {
                case .paragraph(let text):
                    if let path = FilePath.only(in: text) {
                        PathLine(text: text, path: path, attributed: inline(text))
                    } else {
                        Text(inline(text))
                            .font(.system(size: 13))
                            .textSelection(.enabled)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                case .bullet(let items):
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(Array(items.enumerated()), id: \.offset) { _, item in
                            HStack(alignment: .firstTextBaseline, spacing: 7) {
                                Text("•")
                                    .font(.system(size: 13))
                                    .foregroundStyle(.secondary)
                                Text(inline(item))
                                    .font(.system(size: 13))
                                    .textSelection(.enabled)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }

                case .code(let code, let language):
                    CodeBlock(code: code, language: language)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    /// 굵게·기울임·인라인 코드·링크는 AttributedString 이 처리한다.
    private func inline(_ text: String) -> AttributedString {
        (try? AttributedString(
            markdown: text,
            options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        )) ?? AttributedString(text)
    }
}

enum MarkdownBlock {
    case paragraph(String)
    case bullet([String])
    case code(String, String)

    static func parse(_ raw: String) -> [MarkdownBlock] {
        var blocks: [MarkdownBlock] = []
        var paragraph: [String] = []
        var bullets: [String] = []
        var code: [String] = []
        var codeLanguage = ""
        var inCode = false

        func flushParagraph() {
            if !paragraph.isEmpty {
                blocks.append(.paragraph(paragraph.joined(separator: "\n")))
                paragraph = []
            }
        }
        func flushBullets() {
            if !bullets.isEmpty {
                blocks.append(.bullet(bullets))
                bullets = []
            }
        }

        for line in raw.components(separatedBy: "\n") {
            let trimmed = line.trimmingCharacters(in: .whitespaces)

            if trimmed.hasPrefix("```") {
                if inCode {
                    blocks.append(.code(code.joined(separator: "\n"), codeLanguage))
                    code = []
                    codeLanguage = ""
                    inCode = false
                } else {
                    flushParagraph()
                    flushBullets()
                    codeLanguage = String(trimmed.dropFirst(3)).trimmingCharacters(in: .whitespaces)
                    inCode = true
                }
                continue
            }

            if inCode {
                code.append(line)
                continue
            }

            if trimmed.isEmpty {
                flushParagraph()
                flushBullets()
                continue
            }

            // "- 항목", "* 항목", "1. 항목"
            if let item = bulletBody(trimmed) {
                flushParagraph()
                bullets.append(item)
                continue
            }

            flushBullets()
            paragraph.append(line)
        }

        if inCode, !code.isEmpty {
            blocks.append(.code(code.joined(separator: "\n"), codeLanguage))
        }
        flushParagraph()
        flushBullets()
        return blocks
    }

    private static func bulletBody(_ line: String) -> String? {
        for marker in ["- ", "* ", "• "] where line.hasPrefix(marker) {
            return String(line.dropFirst(marker.count))
        }
        // "1. 항목"
        guard let dot = line.firstIndex(of: "."),
              line.distance(from: line.startIndex, to: dot) <= 2,
              line[line.startIndex..<dot].allSatisfy(\.isNumber),
              line.index(after: dot) < line.endIndex,
              line[line.index(after: dot)] == " "
        else { return nil }
        return String(line[line.index(dot, offsetBy: 2)...])
    }
}

private struct CodeBlock: View {
    let code: String
    let language: String

    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                if !language.isEmpty {
                    Text(language)
                        .font(.system(size: 9, weight: .medium))
                        .foregroundStyle(.tertiary)
                }
                Spacer()
                Button {
                    copy()
                } label: {
                    Image(systemName: copied ? "checkmark" : "doc.on.doc")
                        .font(.system(size: 9))
                }
                .buttonStyle(.plain)
                .foregroundStyle(copied ? Color.green : Color.secondary)
                .help("복사")
            }
            .padding(.horizontal, 9)
            .padding(.top, 6)
            .padding(.bottom, 3)

            ScrollView(.horizontal, showsIndicators: false) {
                Text(code)
                    .font(.system(size: 11.5, design: .monospaced))
                    .textSelection(.enabled)
                    .padding(.horizontal, 9)
                    .padding(.bottom, 8)
            }
        }
        .background(Color.primary.opacity(0.06), in: RoundedRectangle(cornerRadius: 8))
    }

    private func copy() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(code, forType: .string)
        copied = true
        Task {
            try? await Task.sleep(for: .seconds(1.4))
            copied = false
        }
    }
}



/// 답변에 나온 파일 경로.
///
/// 비서는 경로를 자주 말한다. 지금까지는 복사해서 Finder 에 붙여야
/// 했다. 줄에 경로가 하나뿐일 때만 버튼을 붙인다 — 여러 개면 어느
/// 것을 여는지 모호해진다.
enum FilePath {
    static func only(in line: String) -> String? {
        let found = matches(in: line)
        return found.count == 1 ? found[0] : nil
    }

    static func matches(in line: String) -> [String] {
        let pattern = #"(?:~|/Users/[^\s]+?)(?:/[^\s,;:()\[\]"']+)+"#
        guard let regex = try? NSRegularExpression(pattern: pattern) else { return [] }

        let range = NSRange(line.startIndex..., in: line)
        return regex.matches(in: line, range: range).compactMap { match in
            guard let r = Range(match.range, in: line) else { return nil }
            let raw = String(line[r]).trimmingCharacters(in: CharacterSet(charactersIn: ".,"))
            return exists(raw) ? raw : nil
        }
    }

    static func exists(_ raw: String) -> Bool {
        FileManager.default.fileExists(atPath: expand(raw))
    }

    static func expand(_ raw: String) -> String {
        raw.hasPrefix("~") ? NSHomeDirectory() + String(raw.dropFirst()) : raw
    }

    static func reveal(_ raw: String) {
        NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: expand(raw))])
    }
}

private struct PathLine: View {
    let text: String
    let path: String
    let attributed: AttributedString

    @State private var hovering = false

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(attributed)
                .font(.system(size: 13))
                .textSelection(.enabled)
                .fixedSize(horizontal: false, vertical: true)

            Button {
                FilePath.reveal(path)
            } label: {
                HStack(spacing: 4) {
                    Image(systemName: "folder")
                        .font(.system(size: 9))
                    Text("Finder 에서 열기")
                        .font(.system(size: 10))
                }
                .padding(.horizontal, 7)
                .padding(.vertical, 3)
                .background(.quaternary.opacity(hovering ? 0.6 : 0.3), in: Capsule())
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
            .onHover { hovering = $0 }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
