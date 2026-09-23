"""공고 하나.

사람인 API 응답은 중첩이 깊고 하이픈이 섞인 키를 쓴다. 그대로 들고
다니면 코드 곳곳에서 `job["position"]["experience-level"]["name"]` 을
쓰게 된다. 경계에서 한 번 평평하게 편다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


def _nested(raw: dict[str, Any], *path: str, default: str = "") -> str:
    node: Any = raw
    for key in path:
        if not isinstance(node, dict):
            return default
        node = node.get(key)
    return str(node) if node not in (None, "") else default


@dataclass(slots=True)
class Job:
    id: str
    url: str
    company: str
    title: str
    location: str = ""
    experience: str = ""
    education: str = ""
    job_type: str = ""
    industry: str = ""
    salary: str = ""
    posted_at: float = 0.0
    expires_at: float = 0.0
    keywords: str = ""

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> Job | None:
        job_id = _nested(raw, "id")
        title = _nested(raw, "position", "title")
        if not job_id or not title:
            return None

        return cls(
            id=job_id,
            url=_nested(raw, "url"),
            company=_nested(raw, "company", "detail", "name", default="(회사명 없음)"),
            title=title,
            location=_nested(raw, "position", "location", "name"),
            experience=_nested(raw, "position", "experience-level", "name"),
            education=_nested(raw, "position", "required-education-level", "name"),
            job_type=_nested(raw, "position", "job-type", "name"),
            industry=_nested(raw, "position", "industry", "name"),
            salary=_nested(raw, "salary", "name"),
            posted_at=_timestamp(raw.get("posting-timestamp")),
            expires_at=_timestamp(raw.get("expiration-timestamp")),
            keywords=_nested(raw, "keyword"),
        )

    def describe(self, *, now: float | None = None) -> str:
        head = f"{self.company} — {self.title}"
        bits = [b for b in (self.location, self.experience, self.job_type) if b]
        line = "  ".join(bits)

        tail = ""
        if self.expires_at:
            days = _days_left(self.expires_at, now)
            if days is not None:
                tail = "  · 오늘 마감" if days <= 0 else f"  · D-{days}"

        return f"{head}\n  {line}{tail}\n  {self.url}"


def _timestamp(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _days_left(expires_at: float, now: float | None = None) -> int | None:
    if not expires_at:
        return None
    reference = datetime.fromtimestamp(now) if now else datetime.now()
    return (datetime.fromtimestamp(expires_at).date() - reference.date()).days
