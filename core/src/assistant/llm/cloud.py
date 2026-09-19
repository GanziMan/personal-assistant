"""클라우드 모델 클라이언트 (Claude API)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic, AuthenticationError

from ..keychain import anthropic_api_key


class CloudAuthError(RuntimeError):
    """키가 틀렸다. 원본 401 대신 고칠 방법을 알려준다."""


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

        try:
            stream_ctx = self._client.messages.stream(**kwargs)
        except AuthenticationError as exc:
            raise CloudAuthError(_AUTH_HELP) from exc

        try:
            async with stream_ctx as stream:
                async for event in stream:
                    if event.type == "content_block_delta" and event.delta.type == "text_delta":
                        yield "text", event.delta.text

                final = await stream.get_final_message()
                for block in final.content:
                    if block.type == "tool_use":
                        yield "tool_use", block
                yield "stop_reason", final.stop_reason
        except AuthenticationError as exc:
            raise CloudAuthError(_AUTH_HELP) from exc


_AUTH_HELP = (
    "Claude API 키가 유효하지 않습니다. 키체인의 값을 확인하세요.\n"
    "  security find-generic-password -s assistant-anthropic -w | cut -c1-12\n"
    "  (sk-ant-api03 으로 시작해야 합니다)\n"
    "다시 넣으려면:\n"
    "  security delete-generic-password -s assistant-anthropic\n"
    '  security add-generic-password -a "$USER" -s assistant-anthropic -w\n'
    "키를 바꾼 뒤에는 데몬을 재시작해야 합니다 (키는 프로세스 안에 캐시됩니다):\n"
    "  launchctl kickstart -k gui/$UID/com.assistant.daemon"
)
