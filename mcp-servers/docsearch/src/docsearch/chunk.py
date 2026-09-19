"""문서를 임베딩 단위로 자른다.

문서 하나를 통째로 임베딩하면 긴 문서에서 검색이 무너진다 — 20페이지
분량의 평균 벡터는 무엇과도 어중간하게 닮는다. 그래서 문단 단위로
자르되, 너무 잘면 맥락이 사라지므로 일정 크기까지 붙인다.
"""

from __future__ import annotations

from dataclasses import dataclass

TARGET_CHARS = 900
MAX_CHARS = 1600
MIN_CHARS = 80

# 문단 사이에 겹침을 둔다. 경계에 걸친 문장이 양쪽 어디서도
# 검색되지 않는 일을 막는다.
OVERLAP_CHARS = 120


@dataclass(slots=True)
class Chunk:
    text: str
    index: int

    @property
    def preview(self) -> str:
        flat = " ".join(self.text.split())
        return flat if len(flat) <= 160 else flat[:159] + "…"


def split(text: str) -> list[Chunk]:
    """문단을 모아 적당한 크기의 덩어리로."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    buffer = ""

    for paragraph in paragraphs:
        # 한 문단이 통째로 너무 길면 줄 단위로 쪼갠다
        if len(paragraph) > MAX_CHARS:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.extend(_split_long(paragraph))
            continue

        candidate = f"{buffer}\n\n{paragraph}" if buffer else paragraph
        if len(candidate) > TARGET_CHARS and buffer:
            chunks.append(buffer)
            buffer = _tail(chunks[-1]) + paragraph
        else:
            buffer = candidate

    if buffer.strip():
        chunks.append(buffer)

    return [
        Chunk(c.strip(), i)
        for i, c in enumerate(c for c in chunks if len(c.strip()) >= MIN_CHARS)
    ]


def _tail(previous: str) -> str:
    """앞 덩어리의 꼬리를 겹쳐 붙인다."""
    if len(previous) <= OVERLAP_CHARS:
        return ""
    return previous[-OVERLAP_CHARS:].lstrip() + "\n\n"


def _split_long(paragraph: str) -> list[str]:
    out: list[str] = []
    buffer = ""
    for line in paragraph.splitlines():
        if len(buffer) + len(line) > TARGET_CHARS and buffer:
            out.append(buffer)
            buffer = line
        else:
            buffer = f"{buffer}\n{line}" if buffer else line
    if buffer:
        out.append(buffer)
    return out
