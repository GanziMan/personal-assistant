"""기억 레코드."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class Episode:
    """무엇이 있었나. 시간축을 가진 사건."""

    title: str
    body: str = ""
    kind: str = "conversation"
    session_id: str = ""
    source: str = ""
    importance: float = 0.5
    ts: float = field(default_factory=time.time)
    id: int | None = None

    def text(self) -> str:
        """임베딩·검색 대상 문자열."""
        return f"{self.title}\n{self.body}".strip()


@dataclass(slots=True)
class Fact:
    """무엇이 사실인가. 시간축이 없는 선호·결정·관계."""

    subject: str
    body: str
    confidence: float = 0.5
    evidence: int = 1
    created_ts: float = field(default_factory=time.time)
    updated_ts: float = field(default_factory=time.time)
    superseded_by: int | None = None
    id: int | None = None

    def text(self) -> str:
        return f"{self.subject}: {self.body}"


@dataclass(slots=True)
class Hit:
    """검색 결과 한 건."""

    kind: str          # episode | fact
    id: int
    score: float
    title: str
    body: str
    ts: float

    def describe(self) -> str:
        mark = "·" if self.kind == "episode" else "※"
        head = self.title if len(self.title) <= 60 else self.title[:57] + "…"
        return f"{mark} {head}" + (f"\n  {self.body[:200]}" if self.body else "")
