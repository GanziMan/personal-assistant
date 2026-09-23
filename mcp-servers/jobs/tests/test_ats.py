from jobs.ats import Company, PARSERS, matches
from jobs.model import Job

GREENHOUSE = {
    "jobs": [
        {
            "id": 111,
            "title": "Backend Engineer",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/111",
            "location": {"name": "Seoul, Korea"},
        },
        {"id": 112, "title": "", "absolute_url": "x"},  # 제목 없음
    ]
}

LEVER = [
    {
        "id": "abc",
        "text": "백엔드 개발자",
        "hostedUrl": "https://jobs.lever.co/acme/abc",
        "categories": {"location": "서울", "commitment": "정규직"},
    },
    {"id": "def"},  # text 없음
]

ASHBY = {
    "jobs": [
        {
            "id": "z1",
            "title": "Platform Engineer",
            "jobUrl": "https://jobs.ashbyhq.com/acme/z1",
            "location": "Remote",
            "employmentType": "FullTime",
        }
    ]
}


def test_greenhouse_parses_and_skips_untitled():
    jobs = PARSERS["greenhouse"]("acme", GREENHOUSE)
    assert len(jobs) == 1
    assert jobs[0].title == "Backend Engineer"
    assert jobs[0].location == "Seoul, Korea"


def test_lever_parses_and_skips_untitled():
    jobs = PARSERS["lever"]("acme", LEVER)
    assert len(jobs) == 1
    assert jobs[0].title == "백엔드 개발자"
    assert jobs[0].job_type == "정규직"


def test_ashby_parses():
    jobs = PARSERS["ashby"]("acme", ASHBY)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"


def test_ids_are_namespaced_by_ats_and_company():
    """사람인 id 와 섞여도 충돌하지 않아야 한다."""
    gh = PARSERS["greenhouse"]("acme", GREENHOUSE)[0].id
    lv = PARSERS["lever"]("acme", LEVER)[0].id
    assert gh.startswith("gh:acme:") and lv.startswith("lv:acme:")
    assert gh != lv


def test_bad_payload_shapes_return_empty():
    assert PARSERS["greenhouse"]("a", None) == []
    assert PARSERS["greenhouse"]("a", {"jobs": None}) == []
    assert PARSERS["lever"]("a", {"not": "a list"}) == []
    assert PARSERS["ashby"]("a", []) == []


def test_company_name_falls_back_to_slug():
    assert Company(slug="acme", ats="lever").name == "acme"
    assert Company(slug="acme", ats="lever", label="에이스").name == "에이스"


# ---- 키워드 필터 ----------------------------------------------------

def _job(title: str, location: str = "") -> Job:
    return Job(id="1", url="", company="c", title=title, location=location)


def test_empty_keywords_pass_everything():
    assert matches(_job("Designer"), [])


def test_keyword_matches_title_case_insensitively():
    assert matches(_job("Backend Engineer"), ["backend"])


def test_keyword_matches_location():
    assert matches(_job("Engineer", "서울"), ["서울"])


def test_any_keyword_is_enough():
    assert matches(_job("Backend Engineer"), ["frontend", "backend"])


def test_no_match_is_filtered():
    assert not matches(_job("Designer"), ["backend"])
