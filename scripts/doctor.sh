#!/usr/bin/env bash
# 비서 상태 진단. 뭐가 안 될 때 이것부터 돌린다.
set -uo pipefail

RUNTIME="$HOME/.assistant"
VENV="$RUNTIME/venv"
LABEL="com.assistant.daemon"

hdr() { printf '\n\033[1m── %s ──\033[0m\n' "$1"; }
ok()  { printf '  \033[32m✓\033[0m %s\n' "$1"; }
no()  { printf '  \033[31m✗\033[0m %s\n' "$1"; }

hdr "데몬"
if [[ -S "$RUNTIME/agent.sock" ]]; then ok "소켓 있음"; else no "소켓 없음"; fi
state=$(launchctl print "gui/$UID/$LABEL" 2>/dev/null | awk -F'= ' '/^\tstate/{print $2}')
[[ -n "$state" ]] && ok "서비스 상태: $state" || no "서비스가 등록되지 않음"
# 이름만 보면 macOS 자체 Siri 데몬(assistantd)에 걸린다. 경로로 찾는다.
pid=$(pgrep -f "$VENV/bin/assistantd" | head -1)
[[ -n "$pid" ]] && ok "프로세스 PID $pid" || no "프로세스 없음"

hdr "구독 백엔드"
if command -v claude >/dev/null; then
  ok "claude: $(command -v claude)"
  claude -p "ok" >/dev/null 2>&1 && ok "로그인됨" || no "로그인 안 됨 (claude login)"
else
  no "claude CLI 없음"
fi

hdr "MCP 서버 실행 파일"
for s in macos-calendar-mcp macos-system-mcp macos-files-mcp feeds-mcp dev-mcp memory-mcp docsearch-mcp jobs-mcp; do
  [[ -x "$VENV/bin/$s" ]] && ok "$s" || no "$s (install.sh 재실행 필요)"
done

hdr "로컬 임베딩 (Ollama)"
if curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  ok "Ollama 응답함"
  curl -fsS http://127.0.0.1:11434/api/tags 2>/dev/null | grep -q nomic-embed-text \
    && ok "nomic-embed-text 있음" || no "nomic-embed-text 없음 (ollama pull nomic-embed-text)"
else
  no "Ollama 응답 없음 (brew services start ollama)"
fi

hdr "메뉴바 앱"
app_pid=$(pgrep -f "$HOME/Applications/Assistant.app" | head -1)
if [[ -n "$app_pid" ]]; then
  ok "실행 중 (PID $app_pid)"
  built=$(stat -f "%Sm" -t "%m/%d %H:%M" "$HOME/Applications/Assistant.app/Contents/MacOS/Assistant" 2>/dev/null)
  [[ -n "$built" ]] && echo "    빌드 시각: $built"
else
  no "실행 중 아님 (build-app.sh)"
fi

hdr "보호 폴더 접근 (TCC)"
for d in Downloads Documents Desktop; do
  if "$VENV/bin/python" -c "
import os,sys
try: os.listdir(os.path.expanduser('~/$d')); print('ok')
except Exception as e: print('fail:', e); sys.exit(1)
" >/dev/null 2>&1; then ok "~/$d"; else no "~/$d — 권한 없음"; fi
done

LOG="$RUNTIME/logs/daemon.err.log"

# 마지막 기동 이후만 본다. 로그 전체를 보여주면 이미 고친 오류가
# 계속 따라다녀서, 지금 문제인지 옛날 흔적인지 구분되지 않는다.
since_last_start() {
  [[ -f "$LOG" ]] || return 1
  local start
  start=$(grep -n "listening on" "$LOG" | tail -1 | cut -d: -f1)
  if [[ -n "$start" ]]; then tail -n "+$start" "$LOG"; else cat "$LOG"; fi
}

hdr "이번 기동의 MCP 연결"
if out=$(since_last_start); then
  echo "$out" | grep -E "MCP 서버|구독 백엔드" | tail -8 || echo "  (연결 기록 없음)"
else
  echo "  (로그 파일 없음)"
fi

hdr "이번 기동의 오류"
if out=$(since_last_start); then
  found=$(echo "$out" | grep -iE "error|traceback|failed|실패" | tail -12)
  [[ -n "$found" ]] && echo "$found" || ok "없음"
else
  echo "  (로그 파일 없음)"
fi
echo
