"""일화 → 의미 승격.

같은 이야기가 반복되면 사실로 굳힌다. 자동 승격은 보수적으로 간다 —
잘못 굳은 기억이 제일 고치기 어렵다 (ARCHITECTURE §5).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from .models import Episode, Fact

MIN_OCCURRENCES = 3     # 세 번은 봐야 패턴이다
MIN_CONFIDENCE = 0.4


def confidence_from_evidence(count: int) -> float:
    """증거 수를 신뢰도로. 늘어날수록 완만하게 오르고 1.0 에 닿지 않는다.

    비서가 무언가를 100% 확신하는 상태를 만들지 않는다. 사용자가
    반박했을 때 고칠 여지가 항상 남아야 한다.
    """
    if count <= 0:
        return 0.0
    return min(0.95, 1.0 - 1.0 / (1.0 + count))


def candidates(episodes: Sequence[Episode], *, min_occurrences: int = MIN_OCCURRENCES) -> list[Fact]:
    """반복된 일화 제목을 사실 후보로 올린다."""
    counts = Counter(ep.title.strip() for ep in episodes if ep.title.strip())

    out: list[Fact] = []
    for title, count in counts.items():
        if count < min_occurrences:
            continue
        confidence = confidence_from_evidence(count)
        if confidence < MIN_CONFIDENCE:
            continue
        out.append(
            Fact(subject=title, body=f"{count}회 반복 관찰됨", confidence=confidence, evidence=count)
        )
    return sorted(out, key=lambda f: -f.confidence)


def should_supersede(old: Fact, new: Fact) -> bool:
    """새 사실이 옛 사실을 대체해야 하는가.

    같은 주제이고, 내용이 다르고, 새 쪽 신뢰도가 더 높을 때만.
    """
    return (
        old.subject == new.subject
        and old.body != new.body
        and new.confidence > old.confidence
    )
