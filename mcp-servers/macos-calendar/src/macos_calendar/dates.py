"""자연어 날짜 해석.

모델이 "오늘", "내일", "이번 주" 같은 말을 그대로 넘길 수 있게 한다.
모델에게 날짜 계산을 시키면 시간대와 주 시작 요일에서 틀린다.
"""

from __future__ import annotations

from datetime import datetime, timedelta

_RELATIVE_DAYS: dict[str, int] = {
    "그저께": -2,
    "어제": -1,
    "오늘": 0,
    "내일": 1,
    "모레": 2,
    "글피": 3,
    "today": 0,
    "tomorrow": 1,
    "yesterday": -1,
}

_WEEKDAYS: dict[str, int] = {
    "월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6,
}


class DateParseError(ValueError):
    pass


def midnight(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def resolve_range(phrase: str, *, now: datetime) -> tuple[datetime, datetime]:
    """문구를 [시작, 끝) 구간으로 바꾼다. 끝은 배타적이다."""
    text = phrase.strip().lower()
    today = midnight(now)

    if text in _RELATIVE_DAYS:
        start = today + timedelta(days=_RELATIVE_DAYS[text])
        return start, start + timedelta(days=1)

    if text in {"이번 주", "이번주", "this week"}:
        start = today - timedelta(days=today.weekday())  # 월요일 시작
        return start, start + timedelta(days=7)

    if text in {"다음 주", "다음주", "next week"}:
        start = today - timedelta(days=today.weekday()) + timedelta(days=7)
        return start, start + timedelta(days=7)

    if text in {"이번 달", "이번달", "this month"}:
        start = today.replace(day=1)
        nxt = (start + timedelta(days=32)).replace(day=1)
        return start, nxt

    # "금요일", "금" — 오늘 포함 앞으로 가장 가까운 그 요일
    key = text.replace("요일", "")
    if key in _WEEKDAYS:
        delta = (_WEEKDAYS[key] - today.weekday()) % 7
        start = today + timedelta(days=delta)
        return start, start + timedelta(days=1)

    # YYYY-MM-DD
    try:
        start = midnight(datetime.fromisoformat(text))
        return start, start + timedelta(days=1)
    except ValueError:
        pass

    raise DateParseError(
        f"'{phrase}' 를 날짜로 읽을 수 없습니다. "
        "'오늘', '내일', '이번 주', '금요일', '2026-09-21' 같은 형태를 쓰세요."
    )
