"""구독 목록. ~/.assistant/feeds.json 하나에 담는다."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_PATH = Path(
    os.environ.get("ASSISTANT_HOME", Path.home() / ".assistant")
) / "feeds.json"


@dataclass(slots=True)
class Feed:
    name: str
    url: str


class FeedStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_PATH

    def load(self) -> list[Feed]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return [Feed(**f) for f in raw if isinstance(f, dict) and "url" in f]

    def save(self, feeds: list[Feed]) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([asdict(f) for f in feeds], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, name: str, url: str) -> bool:
        """이미 있으면 False. 같은 피드를 두 번 받지 않는다."""
        feeds = self.load()
        if any(f.url == url for f in feeds):
            return False
        feeds.append(Feed(name=name or url, url=url))
        self.save(feeds)
        return True

    def remove(self, name_or_url: str) -> bool:
        feeds = self.load()
        kept = [f for f in feeds if f.name != name_or_url and f.url != name_or_url]
        if len(kept) == len(feeds):
            return False
        self.save(kept)
        return True
