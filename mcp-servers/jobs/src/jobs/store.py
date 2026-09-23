"""본 공고 기록.

같은 공고를 매번 새 것처럼 보여주면 이 기능은 금방 쓸모없어진다.
감지 신호에서 배운 것과 같다 — 모으는 것보다 이미 본 것을 걸러내는
쪽이 어렵다 (ADR-025).

공고 본문은 저장하지 않는다. id 와 본 시각만 남긴다. 내용은 사이트에
있고, 우리가 사본을 들고 있을 이유가 없다.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .config import HOME

DEFAULT_PATH = HOME / "jobs-seen.json"

# 마감이 지난 공고까지 영원히 들고 있을 이유가 없다
TTL_DAYS = 120


class SeenStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_PATH
        self._seen: dict[str, float] = self._load()

    def _load(self) -> dict[str, float]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return {str(k): float(v) for k, v in raw.items() if isinstance(v, (int, float))}

    def _save(self) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            self.path.write_text(
                json.dumps(self._seen, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass

    def is_new(self, job_id: str) -> bool:
        return job_id not in self._seen

    def mark(self, job_ids: list[str], *, now: float | None = None) -> None:
        stamp = now if now is not None else time.time()
        for job_id in job_ids:
            self._seen[job_id] = stamp
        self.prune(now=stamp)
        self._save()

    def prune(self, *, now: float | None = None, ttl_days: int = TTL_DAYS) -> int:
        cutoff = (now if now is not None else time.time()) - ttl_days * 86400
        stale = [k for k, v in self._seen.items() if v < cutoff]
        for key in stale:
            del self._seen[key]
        return len(stale)

    def forget_all(self) -> int:
        count = len(self._seen)
        self._seen.clear()
        self._save()
        return count

    def __len__(self) -> int:
        return len(self._seen)
