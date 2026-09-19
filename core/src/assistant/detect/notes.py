"""대기 화면에 띄울 알림 쪽지.

ALERT 는 시스템 알림으로 바로 나가고, QUIET 는 기억에만 쌓인다.
그 사이에 있는 NOTE 를 담아두는 곳이다 — 지금 당장 방해할 일은
아니지만 패널을 볼 때는 보여야 하는 것들.

오래된 쪽지는 스스로 사라진다. 사용자가 치우지 않아도 쌓이지 않아야
한다.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from ..config import HOME

DEFAULT_PATH = HOME / "notes.json"
TTL_HOURS = 24.0
MAX_NOTES = 4


@dataclass(slots=True)
class Note:
    key: str
    message: str
    ts: float


class NoteBoard:
    def __init__(self, path: Path | None = None, *, ttl_hours: float = TTL_HOURS) -> None:
        self.path = path or DEFAULT_PATH
        self.ttl_hours = ttl_hours

    def load(self, *, now: float | None = None) -> list[Note]:
        now = now if now is not None else time.time()
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        cutoff = now - self.ttl_hours * 3600
        notes = [
            Note(str(n["key"]), str(n["message"]), float(n["ts"]))
            for n in raw
            if isinstance(n, dict) and {"key", "message", "ts"} <= n.keys()
        ]
        fresh = [n for n in notes if n.ts >= cutoff]
        return sorted(fresh, key=lambda n: -n.ts)[:MAX_NOTES]

    def put(self, key: str, message: str, *, now: float | None = None) -> None:
        """같은 키는 덮어쓴다. 같은 얘기가 여러 줄 쌓이지 않게."""
        now = now if now is not None else time.time()
        notes = [n for n in self.load(now=now) if n.key != key]
        notes.insert(0, Note(key, message, now))
        self._write(notes[:MAX_NOTES])

    def dismiss(self, key: str) -> None:
        self._write([n for n in self.load() if n.key != key])

    def _write(self, notes: list[Note]) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            self.path.write_text(
                json.dumps([asdict(n) for n in notes], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
