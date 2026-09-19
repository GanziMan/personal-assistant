"""이미지 경로 판별과 붙여넣기 폴더.

패널에서 붙여넣은 스크린샷은 ~/.assistant/pasted 에 떨어진다.
허용 폴더 밖이지만 비서가 스스로 만든 자리이므로 읽기를 허용한다.
오래된 것은 스스로 지운다 — 스크린샷이 쌓이면 그것도 유출 표면이다.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

PASTED_DIR = Path(
    os.environ.get("ASSISTANT_HOME", Path.home() / ".assistant")
) / "pasted"

IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".heic", ".webp"})

TTL_HOURS = 24.0


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def prune(*, now: float | None = None, ttl_hours: float = TTL_HOURS) -> int:
    """오래된 붙여넣기 이미지를 지운다."""
    if not PASTED_DIR.is_dir():
        return 0
    cutoff = (now if now is not None else time.time()) - ttl_hours * 3600
    removed = 0
    for item in PASTED_DIR.iterdir():
        try:
            if item.is_file() and item.stat().st_mtime < cutoff:
                item.unlink()
                removed += 1
        except OSError:
            continue
    return removed
