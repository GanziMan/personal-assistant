"""검색 결과 융합.

벡터 검색과 BM25 는 점수 체계가 달라 그대로 섞을 수 없다. RRF 는
점수 대신 순위만 쓰므로 스케일을 맞출 필요가 없다.

    score(d) = Σ 1 / (k + rank_i(d))
"""

from __future__ import annotations

from collections.abc import Sequence

RRF_K = 60  # 원 논문 권장값. 상위권 가중을 완만하게 만든다.


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[int]], *, k: int = RRF_K, limit: int | None = None
) -> list[tuple[int, float]]:
    """여러 순위 목록을 하나로 합친다. (id, 점수) 를 점수 내림차순으로."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

    merged = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return merged[:limit] if limit else merged
