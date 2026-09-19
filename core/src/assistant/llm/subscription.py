"""구독 백엔드 — Claude Agent SDK.

Claude Code 로그인 자격으로 동작한다. 사용량은 구독 한도에서 빠지고
API 크레딧을 쓰지 않는다 (ADR-007).

에이전트 루프와 MCP 서버 연결을 SDK 가 맡는다. 우리 ToolRegistry 는
규칙 잡(모델 없이 도구만 부르는 경로)에서 계속 쓰인다.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import AsyncIterator
from typing import Any

from ..config import Config
from ..protocol import Event, EventType
from ..tools.spec import DESTRUCTIVE_PREFIXES

log = logging.getLogger(__name__)


class ClaudeCodeMissing(RuntimeError):
    """Claude Code CLI 가 없거나 로그인되어 있지 않다."""


def _safe_tool_names(server_names: list[str]) -> list[str] | None:
    """읽기 전용 도구만 자동 허용한다.

    SDK 경로에서는 아직 대화형 확인 게이트를 붙이지 못했다. 그때까지는
    되돌릴 수 없는 도구를 모델이 부르지 못하게 막는 쪽을 택한다 —
    못 하는 비서가 잘못 지우는 비서보다 낫다. (P6 에서 can_use_tool 로 교체)
    """
    return None if not server_names else [f"mcp__{name}" for name in server_names]


class SubscriptionBackend:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._clients: dict[str, Any] = {}
        self._options: Any = None

    async def start(self) -> None:
        if shutil.which("claude") is None:
            raise ClaudeCodeMissing(
                "Claude Code CLI 를 찾을 수 없습니다.\n"
                "  npm install -g @anthropic-ai/claude-code\n"
                "  claude login"
            )

        from claude_agent_sdk import ClaudeAgentOptions

        mcp_servers = {
            str(s["name"]): {
                "type": "stdio",
                "command": str(s["command"]),
                "args": list(s.get("args", [])),
            }
            for s in self.config.servers
        }

        self._options = ClaudeAgentOptions(
            system_prompt=self.config.system_prompt(),
            model=self.config.models.subscription_model,
            mcp_servers=mcp_servers,
            # 파일시스템·셸 같은 내장 도구는 주지 않는다. 비서가 쓸 도구는
            # 우리가 붙인 MCP 서버뿐이다.
            allowed_tools=_safe_tool_names(list(mcp_servers)) or [],
            permission_mode="default",
            max_turns=self.config.agent.max_iterations,
        )
        log.info("구독 백엔드 준비: MCP 서버 %d개", len(mcp_servers))

    async def _client(self, session_id: str) -> Any:
        if session_id not in self._clients:
            from claude_agent_sdk import ClaudeSDKClient

            client = ClaudeSDKClient(options=self._options)
            await client.connect()
            self._clients[session_id] = client
        return self._clients[session_id]

    async def stream(self, session_id: str, prompt: str) -> AsyncIterator[Event]:
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

        try:
            client = await self._client(session_id)
            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield Event(EventType.TEXT, session_id, block.text)
                        elif isinstance(block, ToolUseBlock):
                            name = getattr(block, "name", "")
                            yield Event(EventType.TOOL_CALL, session_id, name)
                            if name.split("__")[-1].startswith(DESTRUCTIVE_PREFIXES):
                                log.info("되돌릴 수 없는 도구 호출: %s", name)
                elif isinstance(message, ResultMessage):
                    break

            yield Event(EventType.DONE, session_id)

        except ClaudeCodeMissing as exc:
            yield Event(EventType.ERROR, session_id, str(exc))
        except Exception as exc:
            log.exception("구독 백엔드 실패")
            yield Event(EventType.ERROR, session_id, f"{type(exc).__name__}: {exc}")

    async def aclose(self) -> None:
        for client in self._clients.values():
            try:
                await client.disconnect()
            except Exception:
                pass
        self._clients.clear()
