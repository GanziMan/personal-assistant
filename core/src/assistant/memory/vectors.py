"""벡터 직렬화와 유사도.

sqlite-vec 확장이 있으면 그쪽에 맡기고, 없으면 파이썬으로 계산한다.
개인 규모(수만 청크)에서는 전수 계산도 수십 밀리초 안에 끝나므로,
확장 설치를 전제로 깔고 앉지 않는다 (ADR-002).
"""

from __future__ import annotations

import array
import math


def pack(vec: list[float]) -> bytes:
    """float32 리틀엔디언 BLOB 으로."""
    arr = array.array("f", vec)
    if arr.itemsize != 4:  # pragma: no cover
        raise RuntimeError("float32 가 아닌 플랫폼입니다")
    return arr.tobytes()


def unpack(blob: bytes) -> list[float]:
    arr = array.array("f")
    arr.frombytes(blob)
    return list(arr)


def normalize(vec: list[float]) -> list[float]:
    """미리 정규화해 두면 검색 때 내적만으로 코사인이 된다."""
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def cosine(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot(a, b) / (na * nb)
