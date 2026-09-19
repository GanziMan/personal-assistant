"""구독 백엔드 — Claude Agent SDK.

Claude Code 로그인 자격으로 동작한다. 사용량은 구독 한도에서 빠지고
API 크레딧을 쓰지 않는다 (ADR-007).

격리가 중요하다. SDK 는 기본적으로 사용자의 Claude Code 설정과 전역
MCP 서버를 물려받는다. 비서가 사용자의 모든 커넥터에 손대는 것은
의도가 아니므로 둘 다 끊는다 (ADR-011).
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

APPROVE_PREFIX = "/승인"


class ClaudeCodeMissing(RuntimeError):
    """Claude Code CLI 가 없거나 로그인되어 있지 않다."""


def is_destructive(tool_name: str) -> bool:
    """mcp__calendar__create_event 같은 이름에서 마지막 마디로 판단한다."""
    return tool_name.split("__")[-1].startswith(DESTRUCTIVE_PREFIXES)


class SubscriptionBackend:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._clients: dict[str, Any] = {}
        self._options: Any = None

        # 확인 게이트 상태. 승인은 1회용이다 (ADR-005).
        self._approved: set[str] = set()
        self._pending: dict[str, tuple[str, str]] = {}  # session -> (tool, prompt)

    def _allowed_tools(self, server_names: list[str]) -> list[str]:
        """우리 MCP 서버 + (선택) 내장 웹 도구.

        Read/Write/Bash 같은 내장 도구는 주지 않는다. 그것들은 파일
        서버의 경로 경계를 그대로 우회한다 — 경계를 한 곳에 두려면
        파일 접근은 우리 서버만 통해야 한다.
        """
        tools = [f"mcp__{name}" for name in server_names]
        if self.config.agent.allow_web_tools:
            tools += ["WebSearch", "WebFetch"]
        return tools

    async def _permit(self, tool_name: str, args: dict[str, Any], context: Any) -> Any:
        from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

        if not is_destructive(tool_name):
            return PermissionResultAllow()

        if tool_name in self._approved:
            self._approved.discard(tool_name)  # 한 번 허락한 삭제가 계속 유효하면 안 된다
            return PermissionResultAllow()

        return PermissionResultDeny(
            message=(
                f"'{tool_name}' 은 되돌릴 수 없는 작업이라 승인이 필요합니다. "
                f"사용자가 '{APPROVE_PREFIX}' 라고 답하면 한 번만 실행됩니다. "
                "지금은 실행하지 말고, 무엇을 하려 했는지 한 줄로 설명하세요."
            )
        )

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
            # 우리가 준 서버만 쓴다. 사용자의 전역 MCP 설정을 물려받지 않는다.
            strict_mcp_config=True,
            # CLAUDE.md·프로젝트 설정도 읽지 않는다. 비서의 행동은
            # prompts.py 하나로만 결정되어야 한다.
            setting_sources=[],
            allowed_tools=self._allowed_tools(list(mcp_servers)),
            can_use_tool=self._permit,
            max_turns=self.config.agent.max_iterations,
            effort=self.config.models.effort,
            # 토큰 단위로 받는다. 문장이 통째로 오면 실제보다 훨씬
            # 느리게 느껴진다 — 체감 지연의 대부분이 여기였다.
            include_partial_messages=True,
        )
        log.info(
            "구독 백엔드 준비: MCP 서버 %s (effort=%s)",
            ", ".join(mcp_servers) or "(없음)",
            self.config.models.effort,
        )

    async def prewarm(self, session_id: str = "panel") -> None:
        """클라이언트를 미리 띄워둔다.

        첫 연결에서 SDK 가 claude 프로세스와 MCP 서버들을 모두 기동한다.
        그 비용을 사용자의 첫 질문이 치르게 두지 않는다.
        """
        try:
            await self._client(session_id)
            log.info("구독 백엔드 예열 완료 (%s)", session_id)
        except Exception as exc:
            log.warning("예열 실패 (무시하고 계속): %s", exc)

    async def _client(self, session_id: str) -> Any:
        if session_id not in self._clients:
            from claude_agent_sdk import ClaudeSDKClient

            client = ClaudeSDKClient(options=self._options)
            await client.connect()
            self._clients[session_id] = client
        return self._clients[session_id]

    async def stream(self, session_id: str, prompt: str) -> AsyncIterator[Event]:
        from claude_agent_sdk import (
            AssistantMessage,
            ResultMessage,
            StreamEvent,
            ToolUseBlock,
        )

        # 승인 응답이면 보류된 도구를 한 번 풀고 원래 요청을 다시 보낸다
        if prompt.strip().startswith(APPROVE_PREFIX):
            pending = self._pending.pop(session_id, None)
            if pending is None:
                yield Event(EventType.TEXT, session_id, "승인할 작업이 없습니다.")
                yield Event(EventType.DONE, session_id)
                return
            tool, original = pending
            self._approved.add(tool)
            prompt = original

        try:
            client = await self._client(session_id)
            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, StreamEvent):
                    # 원본 Anthropic 스트림 이벤트. 텍스트 델타만 흘린다.
                    raw = message.event
                    if raw.get("type") == "content_block_delta":
                        delta = raw.get("delta") or {}
                        if delta.get("type") == "text_delta" and (chunk := delta.get("text")):
                            yield Event(EventType.TEXT, session_id, chunk)
                    continue

                if isinstance(message, AssistantMessage):
                    # 텍스트는 이미 델타로 흘려보냈다. 도구 호출만 본다.
                    for block in message.content:
                        if isinstance(block, ToolUseBlock):
                            name = getattr(block, "name", "")
                            yield Event(EventType.TOOL_CALL, session_id, name)
                            if is_destructive(name) and name not in self._approved:
                                self._pending[session_id] = (name, prompt)
                                yield Event(
                                    EventType.CONFIRM,
                                    session_id,
                                    f"{name} 실행을 승인하려면 '{APPROVE_PREFIX}' 라고 보내세요.",
                                    {"tool": name},
                                )
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
