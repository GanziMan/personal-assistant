"""RSS/Atom 파싱.

feedparser 를 쓰지 않는다. 필요한 것은 제목·링크·시각 세 개뿐이고,
표준 라이브러리로 충분하다. 의존성 하나를 줄이는 것보다, 파싱 실패를
우리가 제어할 수 있다는 점이 크다 — 피드는 깨진 XML 이 흔하다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

_NS = re.compile(r"\{[^}]+\}")


@dataclass(slots=True)
class Item:
    title: str
    link: str
    published: datetime | None
    summary: str = ""

    def describe(self) -> str:
        when = f"{self.published:%m/%d %H:%M}" if self.published else "시각 미상"
        return f"[{when}] {self.title}\n  {self.link}"


def _tag(element) -> str:  # noqa: ANN001
    """네임스페이스를 떼어낸 태그 이름."""
    return _NS.sub("", element.tag).lower()


def _text(element, *names: str) -> str:  # noqa: ANN001
    for child in element:
        if _tag(child) in names:
            return (child.text or "").strip()
    return ""


def _link(element) -> str:  # noqa: ANN001
    for child in element:
        if _tag(child) != "link":
            continue
        # Atom 은 href 속성, RSS 는 텍스트
        if href := child.attrib.get("href"):
            if child.attrib.get("rel", "alternate") == "alternate":
                return href
        elif child.text:
            return child.text.strip()
    return ""


def _when(element) -> datetime | None:  # noqa: ANN001
    raw = _text(element, "pubdate", "published", "updated", "date")
    if not raw:
        return None

    try:  # RFC 822 (RSS)
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        pass

    try:  # ISO 8601 (Atom)
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse(xml: str | bytes) -> list[Item]:
    """RSS 와 Atom 을 한 함수로 처리한다. 깨진 피드는 빈 목록."""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return []

    items: list[Item] = []
    for element in root.iter():
        if _tag(element) not in {"item", "entry"}:
            continue
        title = _text(element, "title")
        if not title:
            continue
        items.append(
            Item(
                title=title,
                link=_link(element),
                published=_when(element),
                summary=_text(element, "description", "summary")[:300],
            )
        )
    return items


def recent(items: list[Item], *, hours: int) -> list[Item]:
    """최근 N시간 안의 항목. 시각을 모르는 항목은 남긴다.

    버리지 않는 이유: 시각이 없는 피드가 생각보다 많고, 조용히
    사라지는 것보다 한 번 더 보이는 쪽이 낫다.
    """
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    out = []
    for item in items:
        if item.published is None:
            out.append(item)
            continue
        when = item.published
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when.timestamp() >= cutoff:
            out.append(item)
    return sorted(out, key=lambda i: (i.published is None, -(i.published.timestamp() if i.published else 0)))
