import pytest

from assistant.config import Config
from assistant.llm.subscription import APPROVE_PREFIX, SubscriptionBackend, is_destructive


def test_read_only_tools_are_not_gated():
    for name in ("mcp__calendar__list_events", "mcp__calendar__upcoming", "mcp__system__read_clipboard"):
        assert not is_destructive(name), name


def test_mutating_tools_are_gated():
    for name in ("mcp__calendar__create_event", "mcp__system__write_clipboard", "mcp__files__delete_file"):
        assert is_destructive(name), name


def test_server_prefix_does_not_confuse_the_check():
    # 서버 이름에 send 가 들어가도 도구 이름으로만 판단해야 한다
    assert not is_destructive("mcp__send_server__list_events")


@pytest.mark.asyncio
async def test_destructive_tool_is_denied_without_approval():
    b = SubscriptionBackend(Config())
    result = await b._permit("mcp__calendar__create_event", {}, None)
    assert result.behavior == "deny"
    assert APPROVE_PREFIX in result.message


@pytest.mark.asyncio
async def test_approval_is_single_use():
    b = SubscriptionBackend(Config())
    b._approved.add("mcp__calendar__create_event")

    first = await b._permit("mcp__calendar__create_event", {}, None)
    assert first.behavior == "allow"

    second = await b._permit("mcp__calendar__create_event", {}, None)
    assert second.behavior == "deny", "한 번 허락한 작업이 계속 유효하면 안 된다"


@pytest.mark.asyncio
async def test_approval_does_not_leak_to_other_tools():
    b = SubscriptionBackend(Config())
    b._approved.add("mcp__calendar__create_event")
    other = await b._permit("mcp__system__write_clipboard", {}, None)
    assert other.behavior == "deny"


@pytest.mark.asyncio
async def test_read_only_allowed_even_with_no_approvals():
    b = SubscriptionBackend(Config())
    assert (await b._permit("mcp__calendar__list_events", {}, None)).behavior == "allow"


def test_servers_use_absolute_paths():
    """SDK 가 띄우는 자식 프로세스는 우리 venv 를 PATH 에서 못 찾는다."""
    for server in Config().servers:
        assert str(server["command"]).startswith("/"), server
