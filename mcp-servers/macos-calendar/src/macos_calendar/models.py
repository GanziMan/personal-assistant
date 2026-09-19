"""플랫폼 독립 모델. EventKit 없이도 임포트되고 테스트된다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Event:
    title: str
    start: datetime
    end: datetime
    calendar: str
    location: str = ""
    all_day: bool = False
    notes: str = ""

    def describe(self) -> str:
        """모델이 읽을 한 줄. 사람이 보기에도 자연스럽게."""
        if self.all_day:
            when = f"{self.start:%m/%d} 종일"
        elif self.start.date() == self.end.date():
            when = f"{self.start:%m/%d %H:%M}–{self.end:%H:%M}"
        else:
            when = f"{self.start:%m/%d %H:%M} – {self.end:%m/%d %H:%M}"

        parts = [when, self.title]
        if self.location:
            parts.append(f"@{self.location}")
        parts.append(f"[{self.calendar}]")
        return "  ".join(parts)


@dataclass(slots=True)
class Reminder:
    title: str
    due: datetime | None
    completed: bool
    list_name: str
    notes: str = ""

    def describe(self) -> str:
        mark = "✓" if self.completed else "○"
        when = f"{self.due:%m/%d %H:%M}" if self.due else "기한 없음"
        return f"{mark} {self.title}  ({when})  [{self.list_name}]"
