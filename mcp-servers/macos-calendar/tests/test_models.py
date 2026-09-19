from datetime import datetime

from macos_calendar.models import Event, Reminder


def test_same_day_event_shows_range_once():
    e = Event("회의", datetime(2026, 9, 21, 14), datetime(2026, 9, 21, 15), "업무")
    assert e.describe() == "09/21 14:00–15:00  회의  [업무]"


def test_all_day_event():
    e = Event("휴가", datetime(2026, 9, 21), datetime(2026, 9, 22), "개인", all_day=True)
    assert "종일" in e.describe()


def test_multi_day_event_shows_both_dates():
    e = Event("출장", datetime(2026, 9, 21, 9), datetime(2026, 9, 23, 18), "업무")
    assert "09/21" in e.describe() and "09/23" in e.describe()


def test_location_included_when_present():
    e = Event("회의", datetime(2026, 9, 21, 14), datetime(2026, 9, 21, 15), "업무", location="3층")
    assert "@3층" in e.describe()


def test_reminder_without_due():
    assert "기한 없음" in Reminder("언젠가 할 일", None, False, "할 일").describe()


def test_completed_reminder_marked():
    assert Reminder("끝난 일", None, True, "할 일").describe().startswith("✓")
