"""기억 열람 서버.

쓰기는 노출하지 않는다. 기억을 쌓는 것은 스케줄러와 에이전트 루프의
일이고, 모델이 직접 기억을 고쳐 쓰기 시작하면 무엇이 사실인지
추적할 수 없게 된다.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("memory")

PERIODS = {
    "오늘": 1, "어제": 2, "이번 주": 7, "지난주": 14,
    "이번 달": 31, "이번 분기": 92, "올해": 366,
}


def _store():  # noqa: ANN202
    from assistant.memory.store import MemoryStore

    return MemoryStore()


@mcp.tool()
def work_log(period: str = "이번 주") -> str:
    """업무 로그를 기간으로 읽는다.

    period: 오늘 | 어제 | 이번 주 | 지난주 | 이번 달 | 이번 분기 | 올해
    또는 일 수(예: "30")
    """
    days = PERIODS.get(period.strip())
    if days is None:
        try:
            days = int(period.strip())
        except ValueError:
            return f"기간을 읽을 수 없습니다: {period}. {' | '.join(PERIODS)} 중 하나를 쓰세요."

    since = time.time() - days * 86400
    entries = _store().episodes_by_kind("worklog", since=since)
    if not entries:
        return f"{period} 업무 기록이 없습니다."

    blocks = [f"{e.title}\n{e.body}" for e in entries]
    return f"{period} 업무 로그 {len(entries)}일치\n\n" + "\n\n".join(blocks)


@mcp.tool()
def recall(query: str, limit: int = 8) -> str:
    """기억에서 찾는다. 키워드와 의미를 함께 쓴다."""
    hits = _store().search(query, limit=limit)
    if not hits:
        return f"'{query}' 와 맞는 기억이 없습니다."
    return "\n\n".join(h.describe() for h in hits)


@mcp.tool()
def briefings(days: int = 7) -> str:
    """지난 브리핑들."""
    entries = _store().episodes_by_kind("briefing", since=time.time() - days * 86400)
    if not entries:
        return f"최근 {days}일간 브리핑이 없습니다."
    return "\n\n".join(
        f"[{datetime.fromtimestamp(e.ts):%m/%d %H:%M}] {e.body}" for e in entries
    )


def main() -> int:
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
