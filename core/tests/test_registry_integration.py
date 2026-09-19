"""도구 레지스트리와 실제 MCP 서버를 붙여보는 통합 테스트.

단위 테스트가 다 통과해도 프로토콜 버전이 어긋나면 런타임에
'Connection closed' 하나만 남고 끝난다. 실제로 프로세스를 띄워
도구 목록을 받아오는 것까지 확인한다.
"""

from __future__ import annotations

import sys

import pytest

from assistant.tools import ServerSpec, ToolRegistry

feeds = pytest.importorskip("feeds", reason="feeds 서버가 설치되지 않음")


def _spec(tmp_path) -> ServerSpec:  # noqa: ANN001
    return ServerSpec(
        name="feeds",
        command=sys.executable,
        args=["-m", "feeds.server"],
        env={"ASSISTANT_HOME": str(tmp_path)},
    )


@pytest.mark.asyncio
async def test_registry_connects_and_lists_tools(tmp_path):
    registry = ToolRegistry()
    try:
        await registry.start([_spec(tmp_path)])
        names = {t["name"] for t in registry.schemas()}
        assert names, "도구 목록이 비었다 — 서버가 붙지 않았다"
        assert "feeds__list_feeds" in names
        assert "feeds__add_feed" in names
    finally:
        await registry.aclose()


@pytest.mark.asyncio
async def test_registry_calls_a_tool(tmp_path):
    registry = ToolRegistry()
    try:
        await registry.start([_spec(tmp_path)])
        result = await registry.call("feeds__list_feeds", {})
        assert "구독" in result
    finally:
        await registry.aclose()


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected(tmp_path):
    from assistant.tools.registry import ToolError

    registry = ToolRegistry()
    try:
        await registry.start([_spec(tmp_path)])
        with pytest.raises(ToolError, match="없는 도구"):
            await registry.call("feeds__nope", {})
    finally:
        await registry.aclose()


@pytest.mark.asyncio
async def test_dead_server_does_not_kill_the_registry():
    """서버 하나가 안 떠도 비서는 뜬다."""
    registry = ToolRegistry()
    try:
        await registry.start([ServerSpec(name="ghost", command="/nonexistent/binary")])
        assert registry.schemas() == []
    finally:
        await registry.aclose()
