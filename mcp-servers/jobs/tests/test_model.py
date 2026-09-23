from datetime import datetime

import pytest

from jobs.model import Job

RAW = {
    "id": "12345",
    "url": "https://www.saramin.co.kr/job/12345",
    "posting-timestamp": "1758300000",
    "expiration-timestamp": "1759000000",
    "company": {"detail": {"name": "토스", "href": "https://..."}},
    "position": {
        "title": "백엔드 개발자",
        "location": {"code": "101", "name": "서울 강남구"},
        "job-type": {"code": "1", "name": "정규직"},
        "experience-level": {"code": 2, "min": 3, "max": 7, "name": "경력 3~7년"},
        "required-education-level": {"code": "8", "name": "대학교졸업(4년)이상"},
        "industry": {"code": "1", "name": "금융"},
    },
    "salary": {"code": "0", "name": "회사내규에 따름"},
    "keyword": "Python,Kotlin",
}


def test_parses_nested_fields():
    job = Job.parse(RAW)
    assert job is not None
    assert job.company == "토스"
    assert job.title == "백엔드 개발자"
    assert job.location == "서울 강남구"
    assert job.experience == "경력 3~7년"


def test_missing_id_is_rejected():
    assert Job.parse({**RAW, "id": ""}) is None


def test_missing_title_is_rejected():
    assert Job.parse({**RAW, "position": {}}) is None


def test_missing_company_gets_placeholder():
    job = Job.parse({**RAW, "company": {}})
    assert job.company == "(회사명 없음)"


def test_broken_nesting_does_not_crash():
    job = Job.parse({**RAW, "position": {"title": "제목", "location": "문자열"}})
    assert job is not None and job.location == ""


def test_bad_timestamp_becomes_zero():
    job = Job.parse({**RAW, "posting-timestamp": "어제"})
    assert job.posted_at == 0.0


def test_describe_includes_company_and_url():
    text = Job.parse(RAW).describe()
    assert "토스" in text and "saramin.co.kr/job/12345" in text


def test_describe_shows_days_left():
    job = Job.parse(RAW)
    now = datetime(2026, 9, 20).timestamp()
    job.expires_at = datetime(2026, 9, 25).timestamp()
    assert "D-5" in job.describe(now=now)


def test_describe_marks_last_day():
    job = Job.parse(RAW)
    now = datetime(2026, 9, 25, 9).timestamp()
    job.expires_at = datetime(2026, 9, 25, 23).timestamp()
    assert "오늘 마감" in job.describe(now=now)


def test_describe_without_expiry():
    job = Job.parse(RAW)
    job.expires_at = 0
    assert "D-" not in job.describe()
