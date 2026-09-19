from assistant.status import Status, lead_minutes, parse_reminders


def test_lead_minutes_from_minutes():
    assert lead_minutes("12분 뒤 — 09/20 14:00 팀 회의") == 12


def test_lead_minutes_from_hours():
    assert lead_minutes("3시간 뒤 — 회의") == 180


def test_lead_minutes_from_days():
    assert lead_minutes("2일 뒤 — 워크숍") == 2880


def test_lead_minutes_unknown_shape():
    assert lead_minutes("곧 시작합니다") is None


def test_parse_reminders_keeps_only_incomplete():
    text = (
        "리마인더 3건\n"
        "○ 보고서 초안  (09/22 18:00)  [할 일]\n"
        "✓ 끝난 일  (기한 없음)  [할 일]\n"
        "○ 장보기  (기한 없음)  [개인]"
    )
    assert parse_reminders(text) == ["보고서 초안", "장보기"]


def test_parse_reminders_strips_metadata():
    assert parse_reminders("○ 제목만 남아야 함  (09/22 18:00)  [목록]") == ["제목만 남아야 함"]


def test_parse_reminders_respects_limit():
    text = "\n".join(f"○ 할 일 {i}" for i in range(10))
    assert len(parse_reminders(text, limit=3)) == 3


def test_parse_reminders_on_empty_input():
    assert parse_reminders("리마인더가 없습니다.") == []


def test_status_serializes_for_the_wire():
    payload = Status(next_event="10분 뒤 회의", next_event_minutes=10).to_dict()
    assert payload["next_event_minutes"] == 10
    assert payload["todos"] == []
