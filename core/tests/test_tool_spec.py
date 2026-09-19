from assistant.tools.spec import ServerSpec, ToolSpec


def _tool(name: str) -> ToolSpec:
    return ToolSpec(server="calendar", name=name, description="", schema={"type": "object"})


def test_qualified_name_avoids_collision():
    assert _tool("list_events").qualified == "calendar__list_events"


def test_read_only_tools_are_not_destructive():
    for name in ("list_events", "search_events", "next_event", "read_clipboard"):
        assert not _tool(name).destructive, name


def test_mutating_tools_are_destructive():
    for name in ("delete_file", "move_file", "write_clipboard", "create_event", "send_alert"):
        assert _tool(name).destructive, name


def test_server_spec_defaults_are_isolated():
    a, b = ServerSpec("a", "cmd"), ServerSpec("b", "cmd")
    assert a.args is not b.args, "기본 리스트가 인스턴스 간에 공유되면 안 된다"


def test_anthropic_schema_shape():
    payload = _tool("list_events").to_anthropic()
    assert set(payload) == {"name", "description", "input_schema"}
