"""감사 로그.

모든 모델 호출과 도구 실행을 append-only JSONL 로 남긴다.
목적은 디버깅이 아니라 "무엇이 밖으로 나갔는가"에 답하는 것이다
(ARCHITECTURE §4, §7).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .config import AUDIT_PATH


class AuditLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or AUDIT_PATH
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    def record(self, kind: str, **fields: Any) -> None:
        """한 줄 적는다. 실패해도 비서를 멈추지 않는다."""
        entry = {"ts": time.time(), "kind": kind, **fields}
        line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
        try:
            # O_APPEND 로 열어 동시 기록에서도 줄이 섞이지 않게 한다
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                os.write(fd, line.encode("utf-8"))
            finally:
                os.close(fd)
        except OSError:
            pass

    def model_call(self, *, provider: str, model: str, reason: str, tokens_in: int = 0) -> None:
        """어떤 요청이 어느 두뇌로 갔는지. 라우팅 판단 근거까지 남긴다."""
        self.record(
            "model_call", provider=provider, model=model, reason=reason, tokens_in=tokens_in
        )

    def tool_call(self, *, name: str, args: dict[str, Any], ok: bool, error: str = "") -> None:
        self.record("tool_call", name=name, args=args, ok=ok, error=error)
