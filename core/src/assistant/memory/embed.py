"""임베딩 생성.

로컬 모델로만 돌린다 (라우팅 정책상 EMBED = LOCAL). 인덱싱은 양이
많아서 클라우드로 보낼 일이 아니고, 개인 문서를 통째로 밖에 보내는
일이기도 하다.

Ollama 가 없으면 임베딩 없이 동작한다. 그 경우 검색은 BM25 만 쓰고,
품질은 떨어지되 비서는 멈추지 않는다.
"""

from __future__ import annotations

import logging

from ..llm.local import LocalLLM
from .models import Episode, Fact
from .store import MemoryStore

log = logging.getLogger(__name__)


class Embedder:
    def __init__(self, local: LocalLLM, model: str) -> None:
        self.local = local
        self.model = model
        self._available: bool | None = None

    async def ready(self) -> bool:
        if self._available is None:
            self._available = await self.local.available()
            if not self._available:
                log.warning("Ollama 가 없습니다. 검색은 키워드만 사용합니다.")
        return self._available

    async def embed(self, texts: list[str]) -> list[list[float]] | None:
        if not texts or not await self.ready():
            return None
        try:
            return await self.local.embed(self.model, texts)
        except Exception as exc:
            log.warning("임베딩 실패: %s", exc)
            self._available = None  # 다음 호출 때 다시 확인
            return None

    async def embed_one(self, text: str) -> list[float] | None:
        result = await self.embed([text])
        return result[0] if result else None

    async def index_episode(self, store: MemoryStore, ep: Episode) -> None:
        if ep.id is None:
            return
        if (vec := await self.embed_one(ep.text())) is not None:
            store.set_embedding("episode", ep.id, self.model, vec)

    async def index_fact(self, store: MemoryStore, fact: Fact) -> None:
        if fact.id is None:
            return
        if (vec := await self.embed_one(fact.text())) is not None:
            store.set_embedding("fact", fact.id, self.model, vec)
