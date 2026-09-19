from datetime import datetime

import pytest

from assistant.scheduler.cron import CronError, Schedule

# 2026-09-19 는 토요일(weekday=5)
SAT = datetime(2026, 9, 19, 14, 30)


def test_every_minute_matches_always():
    assert Schedule.parse("* * * * *").matches(SAT)


def test_specific_time():
    s = Schedule.parse("30 14 * * *")
    assert s.matches(SAT)
    assert not s.matches(SAT.replace(minute=31))


def test_weekday_range_excludes_weekend():
    weekdays = Schedule.parse("0 8 * * 0-4")  # 0=월 … 4=금
    assert not weekdays.matches(datetime(2026, 9, 19, 8, 0)), "토요일은 제외"
    assert weekdays.matches(datetime(2026, 9, 21, 8, 0)), "월요일은 포함"


def test_step_values():
    s = Schedule.parse("*/15 * * * *")
    assert s.matches(SAT.replace(minute=0))
    assert s.matches(SAT.replace(minute=45))
    assert not s.matches(SAT.replace(minute=7))


def test_list_values():
    s = Schedule.parse("0 9,13,18 * * *")
    for hour in (9, 13, 18):
        assert s.matches(SAT.replace(hour=hour, minute=0))
    assert not s.matches(SAT.replace(hour=10, minute=0))


def test_next_after_skips_current_minute():
    s = Schedule.parse("30 14 * * *")
    nxt = s.next_after(SAT)
    assert nxt == datetime(2026, 9, 20, 14, 30), "지금 맞아도 다음 것을 준다"


def test_next_after_finds_next_weekday():
    s = Schedule.parse("0 8 * * 0-4")
    assert s.next_after(datetime(2026, 9, 19, 9, 0)) == datetime(2026, 9, 21, 8, 0)


def test_next_after_crosses_month():
    s = Schedule.parse("0 0 1 * *")
    assert s.next_after(datetime(2026, 9, 19)) == datetime(2026, 10, 1, 0, 0)


def test_next_after_returns_none_when_impossible():
    # 2월 30일은 오지 않는다
    assert Schedule.parse("0 0 30 2 *").next_after(SAT) is None


@pytest.mark.parametrize(
    "expr",
    ["* * * *", "60 * * * *", "* 24 * * *", "* * * * 7", "5-1 * * * *", "*/0 * * * *", ", * * * *"],
)
def test_invalid_expressions_are_rejected(expr: str):
    with pytest.raises(CronError):
        Schedule.parse(expr)


def test_error_message_names_the_field():
    with pytest.raises(CronError, match="hour"):
        Schedule.parse("0 99 * * *")
