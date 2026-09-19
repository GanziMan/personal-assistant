"""클라우드 모델 클라이언트 (Claude API)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic

from ..keychain import anthropic_api_key


class CloudLLM:
    def __init__(self, *, timeout_s: float = 120.0) -> None:
        self._client = AsyncAnthropic(api_key=anthropic_api_key(), timeout=timeout_s)

    async def stream(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[tuple[str, Any]]:
        """("text", 조각) 또는 ("tool_use", 블록) 을 흘려보낸다.

        시스템 프롬프트에 cache_control 을 붙인다. 비서는 같은 시스템
        프롬프트와 도구 정의를 하루에도 수십 번 반복해서 보내게 되므로,
        캐싱 여부가 비용과 지연에 그대로 나타난다.
        """
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        async with self._client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield "text", event.delta.text

            final = await stream.get_final_message()
            for block in final.content:
                if block.type == "tool_use":
                    yield "tool_use", block
            yield "stop_reason", final.stop_reason
