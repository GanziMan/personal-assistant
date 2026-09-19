"""캘린더·리마인더 MCP 서버.

조회는 자유롭게, 생성·수정은 데몬의 확인 게이트를 거친다. 도구 이름이
create_/update_ 로 시작하면 데몬이 파괴적이라고 판단한다 (tools/spec.py).
"""

from __future__ import annotations

import sys
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from .dates import DateParseError, resolve_range

mcp = FastMCP("macos-calendar")


def _store():  # noqa: ANN202
    """EventKit 접근은 실제 호출 시점까지 미룬다.

    서버가 뜨자마자 권한 다이얼로그를 띄우면, 사용자는 자기가 뭘 허락하는지
    모르는 채로 답하게 된다. 첫 조회 때 묻는 편이 맥락이 분명하다.
    """
    from .eventkit import CalendarStore

    return CalendarStore()


@mcp.tool()
def list_events(when: str = "오늘") -> str:
    """지정한 기간의 일정을 가져온다.

    when: '오늘', '내일', '이번 주', '금요일', '2026-09-21' 등
    """
    try:
        start, end = resolve_range(when, now=datetime.now())
    except DateParseError as exc:
        return str(exc)

    events = _store().events_between(start, end)
    if not events:
        return f"{when}: 일정이 없습니다."
    lines = "\n".join(e.describe() for e in events)
    return f"{when} 일정 {len(events)}건\n{lines}"


@mcp.tool()
def search_events(query: str, days: int = 30) -> str:
    """앞으로 N일 안의 일정을 제목·장소·메모에서 검색한다."""
    from datetime import timedelta

    now = datetime.now()
    events = _store().events_between(now, now + timedelta(days=days))
    q = query.lower()
    hits = [
        e
        for e in events
        if q in e.title.lower() or q in e.location.lower() or q in e.notes.lower()
    ]
    if not hits:
        return f"'{query}' 와 맞는 일정이 앞으로 {days}일 안에 없습니다."
    return "\n".join(e.describe() for e in hits)


@mcp.tool()
def list_reminders(include_completed: bool = False) -> str:
    """리마인더(할 일)를 가져온다. 기본은 미완료만."""
    items = _store().reminders(include_completed=include_completed)
    if not items:
        return "리마인더가 없습니다."
    return f"리마인더 {len(items)}건\n" + "\n".join(r.describe() for r in items)


@mcp.tool()
def next_event() -> str:
    """지금 이후 가장 가까운 일정 하나."""
    from datetime import timedelta

    now = datetime.now()
    events = [e for e in _store().events_between(now, now + timedelta(days=14)) if e.start >= now]
    if not events:
        return "앞으로 2주 안에 일정이 없습니다."

    e = events[0]
    mins = int((e.start - now).total_seconds() // 60)
    if mins < 60:
        lead = f"{mins}분 뒤"
    elif mins < 60 * 24:
        lead = f"{mins // 60}시간 뒤"
    else:
        lead = f"{mins // (60 * 24)}일 뒤"
    return f"{lead} — {e.describe()}"


def main() -> int:
    if sys.platform != "darwin":
        print("이 서버는 macOS 전용입니다.", file=sys.stderr)
        return 1
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
