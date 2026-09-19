#!/usr/bin/env bash
# 비서 제거. 기억 데이터는 남긴다 — 지우려면 ~/.assistant 를 직접 삭제.
set -euo pipefail
LABEL="com.assistant.daemon"
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$HOME/.assistant/venv" "$HOME/.assistant/agent.sock"
echo "제거했습니다. 기억 데이터(memory.db)와 로그는 ~/.assistant 에 남아 있습니다."
