"""MCP 서버들의 수명주기와 도구 디스패치.

서버는 각각 독립 프로세스다. 하나가 죽어도 비서 전체는 살아있어야
하므로, 연결 실패는 그 서버의 도구만 목록에서 빠지는 것으로 처리한다
(ARCHITECTURE §3.2).
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..audit import AuditLog
from .spec import ServerSpec, ToolSpec

log = logging.getLogger(__name__)


class ToolError(RuntimeError):
    """도구 실행이 실패했다. 모델에 돌려줘서 스스로 복구하게 한다."""


class ConfirmationRequired(Exception):
    """파괴적 도구다. 사용자 확인 전에는 실행하지 않는다 (ADR-005)."""

    def __init__(self, tool: ToolSpec, args: dict[str, Any]) -> None:
        super().__init__(f"{tool.qualified} 는 확인이 필요합니다")
        self.tool = tool
        self.args = args


class ToolRegistry:
    def __init__(self, *, audit: AuditLog | None = None, require_confirmation: bool = True) -> None:
        self.audit = audit or AuditLog()
        self.require_confirmation = require_confirmation

        self._stack = AsyncExitStack()
        self._sessions: dict[str, ClientSession] = {}
        self._tools: dict[str, ToolSpec] = {}
        self._approved: set[str] = set()

    # ---- 수명주기 -------------------------------------------------

    async def start(self, specs: list[ServerSpec]) -> None:
        for spec in specs:
            if not spec.enabled:
                continue
            try:
                await self._connect(spec)
            except Exception as exc:
                # 서버 하나가 죽어도 비서는 뜬다
                log.warning("MCP 서버 '%s' 연결 실패: %s", spec.name, exc)
                self.audit.record("server_start_failed", server=spec.name, error=repr(exc))

    async def _connect(self, spec: ServerSpec) -> None:
        params = StdioServerParameters(command=spec.command, args=spec.args, env=spec.env or None)
        read, write = await self._stack.enter_async_context(stdio_client(params))
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        self._sessions[spec.name] = session
        listed = await session.list_tools()
        for tool in listed.tools:
            ts = ToolSpec(
                server=spec.name,
                name=tool.name,
                description=tool.description or "",
                schema=tool.input_schema or {"type": "object", "properties": {}},
            )
            self._tools[ts.qualified] = ts

        log.info("MCP 서버 '%s': 도구 %d개", spec.name, len(listed.tools))

    async def aclose(self) -> None:
        await self._stack.aclose()
        self._sessions.clear()
        self._tools.clear()

    # ---- 조회 -----------------------------------------------------

    def schemas(self) -> list[dict[str, Any]]:
        """모델에 넘길 도구 정의."""
        return [t.to_anthropic() for t in self._tools.values()]

    def get(self, qualified: str) -> ToolSpec:
        if qualified not in self._tools:
            raise ToolError(f"없는 도구입니다: {qualified}")
        return self._tools[qualified]

    # ---- 확인 게이트 ----------------------------------------------

    def approve(self, qualified: str) -> None:
        """사용자가 이번 실행을 승인했다."""
        self._approved.add(qualified)

    # ---- 실행 -----------------------------------------------------

    async def call(self, qualified: str, args: dict[str, Any]) -> str:
        tool = self.get(qualified)

        if tool.destructive and self.require_confirmation:
            if qualified in self._approved:
                self._approved.discard(qualified)  # 1회용
            else:
                raise ConfirmationRequired(tool, args)

        session = self._sessions.get(tool.server)
        if session is None:
            raise ToolError(f"서버 '{tool.server}' 가 떠 있지 않습니다")

        try:
            result = await session.call_tool(tool.name, args)
        except Exception as exc:
            self.audit.tool_call(name=qualified, args=args, ok=False, error=repr(exc))
            raise ToolError(f"{qualified} 실행 실패: {exc}") from exc

        text = "\n".join(
            block.text for block in result.content if getattr(block, "type", "") == "text"
        )
        self.audit.tool_call(name=qualified, args=args, ok=not result.is_error)

        if result.is_error:
            raise ToolError(text or f"{qualified} 가 오류를 반환했습니다")
        return text
