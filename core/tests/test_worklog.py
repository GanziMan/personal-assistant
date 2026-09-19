from datetime import datetime

from assistant.worklog import build, parse_commits, parse_done, parse_events

COMMITS = """## api
a1b2c3d  인증 토큰 갱신 로직 수정
e4f5a6b  테스트 추가

## web
9c8d7e6  로그인 폼 접근성 개선"""

EVENTS = """오늘 일정 2건
09/20 10:00–10:30  스탠드업  [업무]
09/20 14:00–15:00  설계 리뷰  @회의실 A  [업무]"""

REMINDERS = """리마인더 3건
✓ 배포 노트 작성  (09/20 12:00)  [할 일]
○ 보고서 초안  (09/22 18:00)  [할 일]
✓ 코드 리뷰  (기한 없음)  [할 일]"""


def test_commits_grouped_by_repo():
    repos = parse_commits(COMMITS)
    assert [r.repo for r in repos] == ["api", "web"]
    assert len(repos[0].commits) == 2
    assert repos[0].commits[0] == "인증 토큰 갱신 로직 수정"


def test_commits_drop_hash():
    assert not any(
        c.startswith("a1b2c3d") for r in parse_commits(COMMITS) for c in r.commits
    )


def test_empty_repos_are_omitted():
    assert parse_commits("## empty\n\n## api\nabc1234  뭔가") == parse_commits("## api\nabc1234  뭔가")


def test_no_commits_at_all():
    assert parse_commits("최근 1일간 커밋이 없습니다.") == []


def test_events_keep_titles_only():
    assert parse_events(EVENTS) == ["스탠드업", "설계 리뷰"]


def test_event_header_line_is_skipped():
    assert "오늘 일정 2건" not in parse_events(EVENTS)


def test_done_only_takes_completed():
    assert parse_done(REMINDERS) == ["배포 노트 작성", "코드 리뷰"]


def test_done_strips_due_and_list():
    assert all("(" not in d and "[" not in d for d in parse_done(REMINDERS))


def test_build_counts_everything():
    day = build(
        commits=COMMITS, events=EVENTS, reminders=REMINDERS,
        now=datetime(2026, 9, 20),
    )
    assert day.commit_count == 3
    assert "커밋 3건" in day.title()
    assert "일정 2건" in day.title()
    assert "완료 2건" in day.title()


def test_build_body_includes_sections():
    body = build(commits=COMMITS, events=EVENTS, reminders=REMINDERS).body()
    assert "[api]" in body and "[일정]" in body and "[완료한 일]" in body


def test_empty_day_is_detected():
    day = build(commits="", events="", reminders="")
    assert day.empty, "기록이 없으면 쌓지 않는다"


def test_partial_day_is_not_empty():
    day = build(commits=COMMITS, events="", reminders="")
    assert not day.empty
    assert "일정" not in day.title()
