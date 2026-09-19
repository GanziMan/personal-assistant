#!/usr/bin/env bash
# 비서 설치 — 의존성 설치, 키체인 항목 확인, launchd 등록
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST="$AGENT_DIR/com.assistant.daemon.plist"
LABEL="com.assistant.daemon"

say() { printf '\033[1m▸\033[0m %s\n' "$1"; }
die() { printf '\033[31m✗\033[0m %s\n' "$1" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "macOS 전용입니다."
command -v uv >/dev/null || die "uv 가 필요합니다:  brew install uv"

say "코어 의존성 설치"
cd "$REPO/core"
uv sync --all-extras
VENV="$REPO/core/.venv"
[[ -x "$VENV/bin/assistantd" ]] || die "assistantd 진입점이 만들어지지 않았습니다."

say "런타임 디렉터리 준비"
mkdir -p "$HOME/.assistant/logs"
chmod 700 "$HOME/.assistant"

say "API 키 확인"
if ! security find-generic-password -s assistant-anthropic -w >/dev/null 2>&1; then
  echo "  키체인에 Claude API 키가 없습니다. 지금 저장합니다."
  security add-generic-password -a "$USER" -s assistant-anthropic -w
fi

say "launchd 등록"
mkdir -p "$AGENT_DIR"
sed -e "s|__VENV__|$VENV|g" -e "s|__HOME__|$HOME|g" \
    "$REPO/scripts/com.assistant.daemon.plist" > "$PLIST"

launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST"
launchctl kickstart -k "gui/$UID/$LABEL"

sleep 1
if [[ -S "$HOME/.assistant/agent.sock" ]]; then
  say "데몬이 떴습니다."
  echo
  echo "  사용:    $VENV/bin/assistant '오늘 뭐 해야 하지'"
  echo "  로그:    tail -f ~/.assistant/logs/daemon.err.log"
  echo "  재시작:  launchctl kickstart -k gui/\$UID/$LABEL"
else
  die "소켓이 생기지 않았습니다. 로그를 보세요: ~/.assistant/logs/daemon.err.log"
fi
