"""클립보드 이력.

복사한 것을 비서가 알면 "이 에러 뭐야" 가 붙여넣기 없이 된다.
다만 클립보드는 비밀번호와 토큰이 지나가는 통로이기도 하다. 그래서
기록하지 않는 규칙을 먼저 정한다 (ADR-029).

- 비밀번호 관리자가 표시한 항목은 애초에 읽지 않는다
- 비밀처럼 보이는 문자열은 저장하지 않는다
- 이력은 메모리에만 둔다. 디스크에 남기지 않는다
"""

from __future__ import annotations

import re
import subprocess
import time
from collections import deque
from dataclasses import dataclass

MAX_ITEMS = 12
MAX_CHARS = 4000

# 비밀번호 관리자가 붙이는 표식. 이게 있으면 읽지 않는다.
CONCEALED_TYPES = ("org.nspasteboard.ConcealedType", "com.agilebits.onepassword")

_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|pk|ghp|gho|ghs|github_pat|xox[baprs])[-_][A-Za-z0-9_\-]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                       # AWS 액세스 키
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\."),  # JWT
    re.compile(r"(?i)\b(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S+"),
)


def looks_secret(text: str) -> bool:
    """비밀처럼 보이면 기록하지 않는다.

    완벽한 판별은 불가능하다. 놓치는 쪽보다 과하게 거르는 쪽을 택한다 —
    복사 이력 하나 빠지는 손해는 작고, 토큰이 남는 손해는 크다.
    """
    return any(pattern.search(text) for pattern in _SECRET_PATTERNS)


def is_concealed() -> bool:
    """비밀번호 관리자가 숨김으로 표시했는가."""
    try:
        out = subprocess.run(
            ["osascript", "-e", "clipboard info"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return any(marker in out for marker in CONCEALED_TYPES)


@dataclass(slots=True)
class Clip:
    text: str
    ts: float

    def preview(self, width: int = 70) -> str:
        flat = " ".join(self.text.split())
        return flat if len(flat) <= width else flat[: width - 1] + "…"

    def describe(self) -> str:
        age = time.time() - self.ts
        when = (
            f"{int(age // 3600)}시간 전" if age >= 3600
            else f"{int(age // 60)}분 전" if age >= 60
            else "방금"
        )
        return f"[{when}] {self.preview()}"


class ClipboardHistory:
    """메모리에만 사는 이력. 데몬이 죽으면 함께 사라진다."""

    def __init__(self, *, max_items: int = MAX_ITEMS) -> None:
        self._items: deque[Clip] = deque(maxlen=max_items)

    def capture(self, text: str, *, now: float | None = None) -> bool:
        """한 항목을 담는다. 담지 않았으면 False."""
        if not text or not text.strip():
            return False
        if len(text) > MAX_CHARS:
            return False
        if looks_secret(text):
            return False
        if self._items and self._items[-1].text == text:
            return False  # 같은 내용을 연속으로 쌓지 않는다

        self._items.append(Clip(text, now if now is not None else time.time()))
        return True

    def latest(self) -> Clip | None:
        return self._items[-1] if self._items else None

    def recent(self, limit: int = 5) -> list[Clip]:
        return list(self._items)[-limit:][::-1]

    def find(self, query: str, limit: int = 5) -> list[Clip]:
        q = query.lower()
        return [c for c in reversed(self._items) if q in c.text.lower()][:limit]

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
