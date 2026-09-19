from datetime import datetime

import pytest

from macos_calendar.dates import DateParseError, resolve_range

# 2026-09-19 는 토요일
NOW = datetime(2026, 9, 19, 14, 30)


def test_today_is_one_full_day():
    start, end = resolve_range("오늘", now=NOW)
    assert start == datetime(2026, 9, 19)
    assert end == datetime(2026, 9, 20)


def test_tomorrow():
    start, _ = resolve_range("내일", now=NOW)
    assert start == datetime(2026, 9, 20)


def test_this_week_starts_monday():
    start, end = resolve_range("이번 주", now=NOW)
    assert start == datetime(2026, 9, 14), "월요일 시작"
    assert end == datetime(2026, 9, 21)


def test_next_week_follows_this_week():
    _, this_end = resolve_range("이번 주", now=NOW)
    next_start, _ = resolve_range("다음 주", now=NOW)
    assert next_start == this_end


def test_weekday_resolves_forward():
    start, _ = resolve_range("월요일", now=NOW)
    assert start == datetime(2026, 9, 21)


def test_weekday_today_resolves_to_today():
    start, _ = resolve_range("토", now=NOW)
    assert start == datetime(2026, 9, 19)


def test_this_month_spans_to_next_month():
    start, end = resolve_range("이번 달", now=NOW)
    assert (start, end) == (datetime(2026, 9, 1), datetime(2026, 10, 1))


def test_iso_date():
    start, end = resolve_range("2026-12-25", now=NOW)
    assert (start, end) == (datetime(2026, 12, 25), datetime(2026, 12, 26))


def test_unknown_phrase_explains_itself():
    with pytest.raises(DateParseError, match="오늘"):
        resolve_range("언젠가", now=NOW)
