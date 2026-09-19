from assistant.protocol import Event, EventType


def test_roundtrip_preserves_korean():
    original = Event(EventType.TEXT, "sess1", "오늘 일정 알려줘", {"n": 1})
    decoded = Event.decode(original.encode())
    assert decoded == original
    assert "오늘" in original.encode().decode()  # 이스케이프되지 않았다


def test_encoding_is_newline_delimited():
    payload = Event(EventType.PROMPT, text="a\nb").encode()
    assert payload.endswith(b"\n")
    assert payload.count(b"\n") == 1, "본문 개행이 프레이밍을 깨면 안 된다"
