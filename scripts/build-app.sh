#!/usr/bin/env bash
# 메뉴바 앱 빌드 — SwiftPM 으로 컴파일하고 .app 번들을 조립한다.
#
# Xcode 프로젝트를 두지 않는 이유: Command Line Tools 만 있어도 빌드되고,
# .xcodeproj 는 diff 가 읽히지 않아 레포에 두면 리뷰가 불가능해진다.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Assistant"
DEST="${1:-$HOME/Applications}"
BUNDLE="$DEST/$APP_NAME.app"
LABEL="com.assistant.menubar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

say() { printf '\033[1m▸\033[0m %s\n' "$1"; }
die() { printf '\033[31m✗\033[0m %s\n' "$1" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "macOS 전용입니다."
# swift 는 Command Line Tools 에 들어 있지만 PATH 에 없는 경우가 많다.
# xcrun 으로 부르면 CLT 든 전체 Xcode 든 알아서 찾는다.
xcrun --find swift >/dev/null 2>&1 || die "Swift 툴체인이 없습니다:  xcode-select --install"
SWIFT=(xcrun swift)

say "빌드"
cd "$REPO/app"
"${SWIFT[@]}" build -c release

BINARY="$("${SWIFT[@]}" build -c release --show-bin-path)/$APP_NAME"
[[ -x "$BINARY" ]] || die "실행 파일이 만들어지지 않았습니다: $BINARY"

say "번들 조립 ($BUNDLE)"
rm -rf "$BUNDLE"
mkdir -p "$BUNDLE/Contents/MacOS" "$BUNDLE/Contents/Resources"
cp "$BINARY" "$BUNDLE/Contents/MacOS/$APP_NAME"
cp "$REPO/app/Resources/Info.plist" "$BUNDLE/Contents/Info.plist"

# 서명하지 않으면 실행할 때마다 Gatekeeper 가 막는다. 로컬 임시 서명으로 충분하다.
codesign --force --deep --sign - "$BUNDLE" 2>/dev/null || \
  echo "  (코드 서명 생략 — 처음 실행 때 우클릭 → 열기 가 필요할 수 있습니다)"

say "로그인 시 자동 실행 등록"
mkdir -p "$(dirname "$PLIST")"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$BUNDLE/Contents/MacOS/$APP_NAME</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
PLISTEOF

launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST"

say "실행"
open "$BUNDLE"
echo
echo "  메뉴바에 ✦ 아이콘이 보이면 성공입니다."
echo "  ⌥Space 로 부를 수 있습니다."
echo "  중지:  launchctl bootout gui/\$UID/$LABEL && pkill -f $APP_NAME"
