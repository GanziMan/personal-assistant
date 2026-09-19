"""감지기.

각 함수는 상태를 보고 Signal 을 내거나 None 을 낸다. 판단은 전부
코드로 한다 — 모델은 여기 끼지 않는다 (ADR-008).

해소되면 forget 할 수 있도록, 조건이 풀린 경우도 키를 알려준다.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from .signals import Severity, Signal

# ---- 디스크 --------------------------------------------------------

DISK_KEY = "disk_pressure"
DISK_WARN = 0.90
DISK_ALERT = 0.95


def disk_pressure(path: str = "/") -> Signal | None:
    """디스크가 차고 있다. 물어보지 않으면 영영 모르는 종류의 일."""
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return None

    ratio = (usage.total - usage.free) / usage.total if usage.total else 0.0
    if ratio < DISK_WARN:
        return None

    percent = int(ratio * 100)
    free_gb = usage.free / 1024**3
    severity = Severity.ALERT if ratio >= DISK_ALERT else Severity.NOTE

    return Signal(
        key=DISK_KEY,
        message=f"디스크가 {percent}% 찼습니다. 남은 공간 {free_gb:.1f}GB.",
        severity=severity,
        cooldown_hours=12,
        # 1%p 단위로 지문을 만든다. 95→96 은 새 소식, 95→95 는 아니다
        fingerprint=str(percent),
    )


# ---- 폴더 적체 ------------------------------------------------------

PILEUP_KEY = "downloads_pileup"
PILEUP_THRESHOLD = 40


def folder_pileup(
    folder: str = "~/Downloads", *, threshold: int = PILEUP_THRESHOLD
) -> Signal | None:
    """폴더에 파일이 쌓였다."""
    root = Path(folder).expanduser()
    if not root.is_dir():
        return None

    try:
        files = [p for p in root.iterdir() if p.is_file() and not p.name.startswith(".")]
    except (PermissionError, OSError):
        return None

    if len(files) < threshold:
        return None

    total = sum(_size(p) for p in files)
    # 10개 단위로 뭉뚱그린다. 41개→42개마다 다시 말하지 않기 위해서다
    bucket = len(files) // 10 * 10

    return Signal(
        key=PILEUP_KEY,
        message=(
            f"{root.name} 폴더에 파일 {len(files)}개 "
            f"({total / 1024**3:.1f}GB)가 쌓였습니다."
        ),
        severity=Severity.NOTE,
        cooldown_hours=72,
        fingerprint=str(bucket),
    )


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


# ---- 오래된 미커밋 변경 ---------------------------------------------

STALE_REPO_KEY = "stale_repo"
STALE_DAYS = 5


def stale_changes(
    repo_states: list[tuple[str, bool, float]], *, days: int = STALE_DAYS
) -> Signal | None:
    """커밋하지 않은 변경이 오래 방치됐다.

    repo_states: (이름, 더러운가, 마지막 수정 시각) 목록.
    git 호출은 부르는 쪽에서 한다 — 여기는 판단만 한다.
    """
    cutoff = time.time() - days * 86400
    stale = sorted(
        name for name, dirty, mtime in repo_states if dirty and mtime < cutoff
    )
    if not stale:
        return None

    listed = ", ".join(stale[:3])
    more = f" 외 {len(stale) - 3}개" if len(stale) > 3 else ""

    return Signal(
        key=STALE_REPO_KEY,
        message=f"{days}일 넘게 커밋하지 않은 변경이 있습니다 — {listed}{more}.",
        severity=Severity.QUIET,  # 알림까지 띄울 일은 아니다
        cooldown_hours=24 * 7,
        fingerprint="|".join(stale),
    )


ALL_KEYS = (DISK_KEY, PILEUP_KEY, STALE_REPO_KEY)
