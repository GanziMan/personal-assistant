"""cron 표현식 (분 시 일 월 요일).

라이브러리를 끌어오지 않는다. 필요한 문법은 `*`, 숫자, `a-b`, `a,b`,
`*/n` 뿐이고, 이 정도는 직접 다루는 편이 의존성 하나보다 낫다.
무엇보다 다음 실행 시각 계산은 틀리기 쉬운 곳이라 테스트가 붙어 있어야 한다.

요일은 0=월 … 6=일. cron 관례(0=일)와 다르지만 파이썬 weekday() 와
맞춘다 — 코드 안에서 변환이 한 번 더 일어나는 쪽이 버그를 부른다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

_LIMITS = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day": (1, 31),
    "month": (1, 12),
    "weekday": (0, 6),
}


class CronError(ValueError):
    pass


def _parse_field(spec: str, name: str) -> frozenset[int]:
    low, high = _LIMITS[name]
    allowed: set[int] = set()

    for part in spec.split(","):
        part = part.strip()
        if not part:
            raise CronError(f"{name} 필드가 비었습니다: '{spec}'")

        step = 1
        if "/" in part:
            part, _, step_text = part.partition("/")
            if not step_text.isdigit() or int(step_text) < 1:
                raise CronError(f"{name} 의 간격이 잘못됐습니다: '{step_text}'")
            step = int(step_text)

        if part == "*":
            start, end = low, high
        elif "-" in part:
            a, _, b = part.partition("-")
            start, end = int(a), int(b)
        else:
            start = end = int(part)

        if not (low <= start <= high and low <= end <= high and start <= end):
            raise CronError(f"{name} 범위를 벗어났습니다: '{part}' (허용 {low}-{high})")

        allowed.update(range(start, end + 1, step))

    return frozenset(allowed)


@dataclass(slots=True, frozen=True)
class Schedule:
    minute: frozenset[int]
    hour: frozenset[int]
    day: frozenset[int]
    month: frozenset[int]
    weekday: frozenset[int]

    @classmethod
    def parse(cls, expr: str) -> Schedule:
        fields = expr.split()
        if len(fields) != 5:
            raise CronError(f"5개 필드가 필요합니다 (분 시 일 월 요일): '{expr}'")
        names = ("minute", "hour", "day", "month", "weekday")
        return cls(*(_parse_field(f, n) for f, n in zip(fields, names, strict=True)))

    def matches(self, dt: datetime) -> bool:
        return (
            dt.minute in self.minute
            and dt.hour in self.hour
            and dt.day in self.day
            and dt.month in self.month
            and dt.weekday() in self.weekday
        )

    def next_after(self, now: datetime, *, horizon_days: int = 366) -> datetime | None:
        """now 이후 처음 맞는 시각. 분 단위로 훑는다.

        분 단위 전수 탐색이 낭비로 보이지만, 개인 비서가 다루는 잡은
        기껏해야 수십 개이고 하루에 몇 번 계산한다. 영리한 최적화가
        만들 버그가 더 비싸다.
        """
        cursor = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        limit = now + timedelta(days=horizon_days)
        while cursor <= limit:
            if self.matches(cursor):
                return cursor
            cursor += timedelta(minutes=1)
        return None
