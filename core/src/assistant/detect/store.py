"""신호 기록.

무엇을 언제 말했는지 남긴다. 이게 없으면 비서는 같은 말을 영원히
반복한다.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from ..config import HOME
from .signals import Signal

DEFAULT_PATH = HOME / "signals.json"


@dataclass(slots=True)
class Record:
    last_said: float
    fingerprint: str


class SignalStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_PATH
        self._records: dict[str, Record] = self._load()

    def _load(self) -> dict[str, Record]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return {
            key: Record(float(v.get("last_said", 0)), str(v.get("fingerprint", "")))
            for key, v in raw.items()
            if isinstance(v, dict)
        }

    def _save(self) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        payload = {
            key: {"last_said": r.last_said, "fingerprint": r.fingerprint}
            for key, r in self._records.items()
        }
        try:
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass  # 기록 실패가 비서를 멈추면 안 된다

    def should_say(self, signal: Signal, *, now: float | None = None) -> bool:
        """이 신호를 지금 말해도 되는가."""
        now = now if now is not None else time.time()
        record = self._records.get(signal.key)

        if record is None:
            return True

        # 상태가 실제로 달라졌으면 쿨다운을 무시한다.
        # "디스크 95% → 97%" 는 새 소식이다.
        if signal.fingerprint and signal.fingerprint != record.fingerprint:
            return True

        return now - record.last_said >= signal.cooldown_hours * 3600

    def mark_said(self, signal: Signal, *, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        self._records[signal.key] = Record(now, signal.fingerprint)
        self._save()

    def forget(self, key: str) -> None:
        """상태가 해소됐다. 다음에 다시 생기면 즉시 말할 수 있게 한다."""
        if self._records.pop(key, None) is not None:
            self._save()

    def filter(self, signals: list[Signal], *, now: float | None = None) -> list[Signal]:
        """말해도 되는 것만 남기고 기록한다."""
        out = []
        for signal in signals:
            if self.should_say(signal, now=now):
                self.mark_said(signal, now=now)
                out.append(signal)
        return out
