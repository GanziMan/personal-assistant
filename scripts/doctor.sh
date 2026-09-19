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
pid=$(pgrep -f assistantd | head -1)
[[ -n "$pid" ]] && ok "프로세스 PID $pid" || no "프로세스 없음"

hdr "구독 백엔드"
if command -v claude >/dev/null; then
  ok "claude: $(command -v claude)"
  claude -p "ok" >/dev/null 2>&1 && ok "로그인됨" || no "로그인 안 됨 (claude login)"
else
  no "claude CLI 없음"
fi

hdr "MCP 서버 실행 파일"
for s in macos-calendar-mcp macos-system-mcp macos-files-mcp feeds-mcp; do
  [[ -x "$VENV/bin/$s" ]] && ok "$s" || no "$s (install.sh 재실행 필요)"
done

hdr "메뉴바 앱"
pgrep -f "Assistant" >/dev/null && ok "실행 중" || no "실행 중 아님 (build-app.sh)"

hdr "보호 폴더 접근 (TCC)"
for d in Downloads Documents Desktop; do
  if "$VENV/bin/python" -c "
import os,sys
try: os.listdir(os.path.expanduser('~/$d')); print('ok')
except Exception as e: print('fail:', e); sys.exit(1)
" >/dev/null 2>&1; then ok "~/$d"; else no "~/$d — 권한 없음"; fi
done

hdr "최근 오류 (daemon.err.log)"
if [[ -f "$RUNTIME/logs/daemon.err.log" ]]; then
  grep -iE "error|traceback|failed|실패" "$RUNTIME/logs/daemon.err.log" | tail -12 || echo "  (오류 없음)"
else
  echo "  (로그 파일 없음)"
fi

hdr "MCP 연결 로그"
grep -E "MCP 서버|구독 백엔드" "$RUNTIME/logs/daemon.err.log" 2>/dev/null | tail -6 || echo "  (없음)"
echo
