#!/usr/bin/env bash
# 비서 설치 — 런타임 구성, 키체인 항목 확인, launchd 등록
#
# 중요: 가상환경을 레포 안이 아니라 ~/.assistant 아래에 만든다.
# ~/Documents, ~/Desktop, ~/Downloads 는 macOS 가 TCC 로 보호하는 폴더라
# launchd 로 뜬 데몬이 그 안의 파일을 읽지 못한다 (자세한 내용은
# docs/DECISIONS.md ADR-006).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="$HOME/.assistant"
VENV="$RUNTIME/venv"
AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST="$AGENT_DIR/com.assistant.daemon.plist"
LABEL="com.assistant.daemon"

CLEAN=0
[[ "${1:-}" == "--clean" ]] && CLEAN=1

say() { printf '\033[1m▸\033[0m %s\n' "$1"; }
die() { printf '\033[31m✗\033[0m %s\n' "$1" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "macOS 전용입니다."
command -v uv >/dev/null || die "uv 가 필요합니다:  brew install uv"

say "기존 데몬 정지"
# venv 를 건드리기 전에 멈춰야 한다. 실행 중인 인터프리터 아래를
# 갈아엎으면 이후 launchctl 동작이 예측 불가능해진다.
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
for _ in $(seq 1 20); do
  launchctl print "gui/$UID/$LABEL" >/dev/null 2>&1 || break
  sleep 0.25
done

say "런타임 디렉터리 준비"
mkdir -p "$RUNTIME/logs"
chmod 700 "$RUNTIME"

if (( CLEAN )); then
  say "가상환경 삭제 후 재생성"
  # 기억 DB·설정·로그는 건드리지 않는다. venv 만 민다.
  rm -rf "$VENV"
else
  say "가상환경 준비 ($VENV)"
fi
uv venv --python 3.12 --allow-existing "$VENV" >/dev/null

say "패키지 설치"
# editable(-e) 로 넣지 않는다. editable 이면 런타임에 레포 경로를 읽어야
# 하고, 그 경로가 보호 폴더면 다시 같은 문제가 난다.
uv pip install --python "$VENV/bin/python" -q \
  "$REPO/core" \
  "$REPO/mcp-servers/macos-calendar" \
  "$REPO/mcp-servers/macos-system" \
  "$REPO/mcp-servers/macos-files" \
  "$REPO/mcp-servers/feeds" \
  "$REPO/mcp-servers/dev"

[[ -x "$VENV/bin/assistantd" ]] || die "assistantd 진입점이 만들어지지 않았습니다."

say "임포트 검증"
"$VENV/bin/python" -c "import assistant.daemon" || die "데몬 임포트 실패 (위 오류 확인)"

say "Claude Code 확인 (구독 백엔드)"
if ! command -v claude >/dev/null; then
  command -v npm >/dev/null || die "node/npm 이 필요합니다:  brew install node"
  echo "  Claude Code CLI 를 설치합니다."
  npm install -g @anthropic-ai/claude-code
fi

if ! claude -p "ok" >/dev/null 2>&1; then
  echo
  echo "  Claude Code 로그인이 필요합니다. 다음을 실행한 뒤 이 스크립트를 다시 돌리세요:"
  echo "    claude login"
  die "로그인되지 않았습니다."
fi
echo "  구독 계정으로 동작합니다. API 키는 필요 없습니다."

say "launchd 등록"
mkdir -p "$AGENT_DIR"
# launchd 는 PATH 가 거의 비어 있다. claude 와 node 경로를 직접 넣어준다.
DAEMON_PATH="$(dirname "$(command -v claude)"):$(dirname "$(command -v node)")"
DAEMON_PATH="$DAEMON_PATH:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

sed -e "s|__VENV__|$VENV|g" -e "s|__HOME__|$HOME|g" -e "s|__PATH__|$DAEMON_PATH|g" \
    "$REPO/scripts/com.assistant.daemon.plist" > "$PLIST"

# 이미 등록돼 있으면 bootstrap 이 "Input/output error (5)" 로 실패한다.
# 실패가 아니라 이미 있는 것이므로 kickstart 로 이어간다.
if ! launchctl bootstrap "gui/$UID" "$PLIST" 2>/dev/null; then
  echo "  (이미 등록돼 있습니다 — 재시작합니다)"
fi
launchctl kickstart -k "gui/$UID/$LABEL" >/dev/null 2>&1 || \
  die "데몬을 시작할 수 없습니다.  launchctl print gui/\$UID/$LABEL"

for _ in $(seq 1 15); do
  [[ -S "$RUNTIME/agent.sock" ]] && break
  sleep 1
done

if [[ -S "$RUNTIME/agent.sock" ]]; then
  say "데몬이 떴습니다."
  echo
  echo "  사용:    $VENV/bin/assistant '오늘 일정 뭐야'"
  echo "  로그:    tail -f ~/.assistant/logs/daemon.err.log"
  echo "  재시작:  launchctl kickstart -k gui/\$UID/$LABEL"
  echo
  echo "  코드를 고친 뒤에는 이 스크립트를 다시 실행하세요 (editable 설치가 아닙니다)."
  echo "  깨끗하게 다시 깔려면:  ./scripts/install.sh --clean"
else
  echo
  echo "--- daemon.err.log (마지막 30줄) ---"
  tail -30 "$RUNTIME/logs/daemon.err.log" 2>/dev/null || echo "(로그 없음)"
  die "소켓이 생기지 않았습니다."
fi
