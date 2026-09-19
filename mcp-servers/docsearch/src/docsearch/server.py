"""로컬 문서 의미 검색 서버.

파일 서버와 같은 경로 경계를 쓴다 (ADR-013). 색인도 검색도 허용
폴더 밖으로 나가지 않는다.

임베딩은 Ollama 로컬 모델이다. 문서를 통째로 밖에 보내는 일은
하지 않는다 — 이 기능의 존재 이유 자체가 거기에 있다.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer

from assistant.memory import vectors as vec
from assistant.memory.fusion import reciprocal_rank_fusion
from macos_files import inspect as ins
from macos_files.paths import Boundary, PathDenied, from_env

from .chunk import split
from .index import DocIndex

mcp = MCPServer("docsearch")

INDEX_PATH = Path.home() / ".assistant" / "docindex.db"
OLLAMA = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
BATCH = 32
MAX_FILE_BYTES = 2_000_000

_index: DocIndex | None = None
_boundary: Boundary | None = None


def index() -> DocIndex:
    global _index
    if _index is None:
        _index = DocIndex(INDEX_PATH)
    return _index


def boundary() -> Boundary:
    global _boundary
    if _boundary is None:
        _boundary = from_env()
    return _boundary


async def embed(texts: list[str]) -> list[bytes | None]:
    """임베딩을 만든다. Ollama 가 없으면 None 으로 채운다 — 색인은
    계속되고 검색은 키워드만 쓴다."""
    out: list[bytes | None] = []
    async with httpx.AsyncClient(base_url=OLLAMA, timeout=120) as client:
        for start in range(0, len(texts), BATCH):
            batch = texts[start : start + BATCH]
            try:
                r = await client.post(
                    "/api/embed", json={"model": EMBED_MODEL, "input": batch}
                )
                r.raise_for_status()
                out += [vec.pack(vec.normalize(e)) for e in r.json()["embeddings"]]
            except Exception:
                out += [None] * len(batch)
    return out


async def embed_one(text: str) -> list[float] | None:
    result = await embed([text])
    return vec.unpack(result[0]) if result and result[0] else None


@mcp.tool()
async def reindex(folder: str = "", max_files: int = 400) -> str:
    """허용 폴더의 텍스트 문서를 색인한다. 바뀐 파일만 다시 읽는다."""
    roots = [boundary().resolve(folder)] if folder else boundary().roots
    if not roots:
        return "허용된 폴더가 없습니다."

    store = index()
    removed = store.prune_missing()
    scanned = updated = failed = 0

    for root in roots:
        for path in ins.walk(root, max_entries=max_files * 3):
            if not ins.is_probably_text(path):
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue

            scanned += 1
            if scanned > max_files:
                break
            if not store.needs_index(path):
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                failed += 1
                continue

            chunks = split(text)
            if not chunks:
                continue

            bodies = [c.text for c in chunks]
            store.put(path, bodies, await embed(bodies))
            updated += 1

    docs, total, _ = store.stats()
    lines = [
        f"색인 완료 — 새로 읽은 문서 {updated}개, 전체 {docs}개 문서 / {total}개 조각"
    ]
    if removed:
        lines.append(f"사라진 문서 {removed}개 정리")
    if failed:
        lines.append(f"읽지 못한 문서 {failed}개")
    return "\n".join(lines)


@mcp.tool()
async def search_docs(query: str, limit: int = 6) -> str:
    """내용으로 문서를 찾는다. 파일명이 기억나지 않을 때 쓴다."""
    store = index()
    docs, total, _ = store.stats()
    if total == 0:
        return "아직 색인된 문서가 없습니다. reindex 를 먼저 실행하세요."

    rankings = [store.keyword(query, limit=limit * 4)]

    if (probe := await embed_one(query)) is not None:
        scored = [
            (cid, vec.dot(probe, vec.unpack(blob)))
            for cid, blob in store.vectors()
            if len(blob) == len(probe) * 4
        ]
        scored.sort(key=lambda kv: -kv[1])
        rankings.append([cid for cid, _ in scored[: limit * 4]])

    merged = reciprocal_rank_fusion(rankings, limit=limit)
    if not merged:
        return f"'{query}' 와 맞는 문서가 없습니다."

    order = {cid: rank for rank, (cid, _) in enumerate(merged)}
    found = sorted(store.fetch([cid for cid, _ in merged]), key=lambda s: order[s.id])

    blocks = []
    for item in found:
        name = Path(item.path).name
        blocks.append(f"[{name}]  {item.path}\n{item.text[:500]}")
    return "\n\n".join(blocks)


@mcp.tool()
def index_status() -> str:
    """색인 상태."""
    docs, chunks, last = index().stats()
    if docs == 0:
        return "색인된 문서가 없습니다."
    when = time.strftime("%m/%d %H:%M", time.localtime(last)) if last else "?"
    return f"문서 {docs}개 / 조각 {chunks}개 · 마지막 색인 {when}"


def main() -> int:
    if sys.platform != "darwin":
        print("이 서버는 macOS 전용입니다.", file=sys.stderr)
        return 1
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
