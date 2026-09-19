"""로컬 모델 클라이언트 (Ollama).

임베딩·분류·짧은 요약 전용. 여기에 에이전트 루프를 태우지 않는다.
"""

from __future__ import annotations

import httpx


class LocalUnavailable(RuntimeError):
    """Ollama 가 떠 있지 않다."""


class LocalLLM:
    def __init__(self, endpoint: str, *, timeout_s: float = 60.0) -> None:
        self.endpoint = endpoint.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.endpoint, timeout=timeout_s)

    async def available(self) -> bool:
        try:
            r = await self._client.get("/api/tags")
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        r = await self._client.post("/api/embed", json={"model": model, "input": texts})
        r.raise_for_status()
        return r.json()["embeddings"]

    async def complete(self, model: str, prompt: str, *, system: str = "") -> str:
        payload = {"model": model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        r = await self._client.post("/api/generate", json=payload)
        r.raise_for_status()
        return r.json()["response"]

    async def aclose(self) -> None:
        await self._client.aclose()
