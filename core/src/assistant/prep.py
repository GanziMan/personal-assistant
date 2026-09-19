"""회의 전 준비.

일정 시작 전에 같은 자리에서 쓸 만한 것을 모아 패널에 올려둔다.
물어보기 전에 준비돼 있는 것이 비서와 대시보드를 가르는 지점이다.

모으는 일은 코드가 한다. 같은 제목의 지난 기록, 제목과 겹치는 파일,
그 시간대에 손대던 레포 — 전부 조회다. 요약이 필요하면 사용자가
패널에서 물을 때 모델이 읽는다 (ADR-027 과 같은 이유).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# 검색어로 쓰기엔 너무 흔해서 걸러내는 말들
STOPWORDS = frozenset({
    "회의", "미팅", "정기", "주간", "월간", "일일", "스탠드업", "리뷰",
    "싱크", "점검", "논의", "공유", "meeting", "sync", "weekly", "daily",
    "standup", "review", "1on1", "1:1",
})

MIN_TERM_LENGTH = 2
MAX_TERMS = 3


def keywords(title: str) -> list[str]:
    """일정 제목에서 검색할 만한 말만 남긴다.

    "주간 회의" 같은 제목은 검색어가 없다. 억지로 "회의" 로 찾으면
    관계없는 것이 잔뜩 나와서 준비가 오히려 방해가 된다.
    """
    tokens = re.split(r"[\s\-_/·,()\[\]]+", title)
    out: list[str] = []
    for token in tokens:
        cleaned = token.strip().strip(".:")
        if len(cleaned) < MIN_TERM_LENGTH:
            continue
        if cleaned.lower() in STOPWORDS:
            continue
        out.append(cleaned)
    return out[:MAX_TERMS]


@dataclass(slots=True)
class Prep:
    event: str
    minutes: int
    past: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    repos: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.past or self.files or self.repos)

    def render(self) -> str:
        lines = [f"{self.minutes}분 뒤 «{self.event}» — 참고할 것"]
        if self.past:
            lines += ["지난 기록"] + [f"  · {p}" for p in self.past[:3]]
        if self.files:
            lines += ["관련 파일"] + [f"  · {f}" for f in self.files[:3]]
        if self.repos:
            lines += ["작업 중인 레포"] + [f"  · {r}" for r in self.repos[:3]]
        return "\n".join(lines)


def trim(text: str, *, limit: int = 3) -> list[str]:
    """도구 출력에서 쓸 만한 줄만 추린다."""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # "없습니다", "찾지 못했습니다" 같은 빈 응답은 버린다
        if "없습니다" in line or "찾지 못했" in line:
            continue
        out.append(line)
        if len(out) >= limit:
            break
    return out
