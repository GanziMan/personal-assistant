#!/usr/bin/env bash
# 새 맥에 비서를 처음 설치한다.
#
#   git clone https://github.com/GanziMan/personal-assistant.git
#   cd personal-assistant && ./scripts/bootstrap.sh
#
# 기억과 색인은 맥마다 따로 쌓인다 (ADR-033). 설정만 옮기려면
# scripts/profile.sh 를 쓴다.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

say()  { printf '\n\033[1m▸ %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
die()  { printf '\033[31m✗\033[0m %s\n' "$1" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "macOS 전용입니다."

say "Homebrew"
if command -v brew >/dev/null; then
  ok "$(brew --version | head -1)"
else
  die "Homebrew 가 필요합니다:  https://brew.sh"
fi

say "의존성 설치"
for pkg in uv node ollama; do
  if brew list --formula "$pkg" >/dev/null 2>&1; then
    ok "$pkg"
  else
    echo "  설치 중: $pkg"
    brew install "$pkg"
  fi
done

say "Swift 툴체인"
if xcrun --find swift >/dev/null 2>&1; then
  ok "$(xcrun --find swift)"
else
  echo "  Command Line Tools 를 설치합니다. 창이 뜨면 진행하세요."
  xcode-select --install || true
  die "설치를 마친 뒤 이 스크립트를 다시 실행하세요."
fi

say "Claude Code"
if command -v claude >/dev/null; then
  ok "$(command -v claude)"
else
  npm install -g @anthropic-ai/claude-code
fi

if claude -p "ok" >/dev/null 2>&1; then
  ok "로그인됨"
else
  echo
  echo "  로그인이 필요합니다. 다음을 실행한 뒤 이 스크립트를 다시 돌리세요:"
  echo "    claude login"
  die "로그인되지 않았습니다."
fi

say "Ollama 서비스와 임베딩 모델"
brew services list 2>/dev/null | grep -q "^ollama.*started" || brew services start ollama
for _ in $(seq 1 15); do
  curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
  sleep 1
done
if curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags 2>/dev/null | grep -q nomic-embed-text; then
  ok "nomic-embed-text"
else
  ollama pull nomic-embed-text
fi

say "데몬 설치"
"$REPO/scripts/install.sh"

say "메뉴바 앱 빌드"
"$REPO/scripts/build-app.sh"

say "점검"
"$REPO/scripts/doctor.sh"

cat <<'DONE'

설치가 끝났습니다.

  ⌥Space 로 비서를 부릅니다.

다음 두 가지는 처음 쓸 때 macOS 가 권한을 묻습니다.
  · 캘린더 — 일정을 처음 조회할 때
  · 폴더 접근 — 파일을 처음 찾을 때

다른 맥의 설정을 가져오려면:
  ./scripts/profile.sh import <내보낸파일.json>
DONE
