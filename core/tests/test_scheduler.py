from datetime import datetime

import pytest

from assistant.scheduler.jobs import DEFAULT_JOBS, Job
from assistant.scheduler.runner import Scheduler


def _scheduler(jobs, calls):
    async def run_job(job: Job) -> str:
        calls.append(job.name)
        return "결과"

    async def on_result(job: Job, text: str) -> None:
        calls.append(f"{job.name}:delivered")

    return Scheduler(jobs, run_job=run_job, on_result=on_result)


def test_default_jobs_all_parse():
    assert len(DEFAULT_JOBS) >= 3
    for job in DEFAULT_JOBS:
        assert job.schedule is not None


def test_notifying_jobs_declare_a_title():
    for job in DEFAULT_JOBS:
        if job.notify:
            assert job.title, f"{job.name}: 알림 잡은 제목이 있어야 한다"


def test_most_jobs_are_silent_by_default():
    quiet = [j for j in DEFAULT_JOBS if not j.notify]
    assert quiet, "조용한 적재가 기본이어야 한다"


def test_due_returns_matching_jobs():
    job = Job(name="t", cron="0 8 * * *", prompt="p")
    s = _scheduler([job], [])
    assert s.due(datetime(2026, 9, 21, 8, 0)) == [job]
    assert s.due(datetime(2026, 9, 21, 9, 0)) == []


def test_disabled_jobs_never_run():
    job = Job(name="off", cron="* * * * *", prompt="p", enabled=False)
    assert _scheduler([job], []).due(datetime(2026, 9, 21, 8, 0)) == []


@pytest.mark.asyncio
async def test_tick_does_not_double_fire_in_same_minute():
    calls: list[str] = []
    s = _scheduler([Job(name="t", cron="* * * * *", prompt="p")], calls)
    s.now = lambda: datetime(2026, 9, 21, 8, 0)  # type: ignore[method-assign]

    await s._tick()
    await s._tick()
    assert calls.count("t") == 1, "같은 분에 두 번 돌면 안 된다"


@pytest.mark.asyncio
async def test_empty_result_is_not_delivered():
    calls: list[str] = []

    async def run_job(job: Job) -> str:
        return "없음"

    async def on_result(job: Job, text: str) -> None:
        calls.append("delivered")

    s = Scheduler(
        [Job(name="t", cron="* * * * *", prompt="p")], run_job=run_job, on_result=on_result
    )
    s.now = lambda: datetime(2026, 9, 21, 8, 0)  # type: ignore[method-assign]
    await s._tick()
    assert calls == [], "'없음' 은 사용자를 방해하지 않는다"


@pytest.mark.asyncio
async def test_failing_job_does_not_stop_others():
    calls: list[str] = []

    async def run_job(job: Job) -> str:
        if job.name == "bad":
            raise RuntimeError("터짐")
        calls.append(job.name)
        return "ok"

    async def on_result(job: Job, text: str) -> None:
        pass

    jobs = [Job(name="bad", cron="* * * * *", prompt="p"), Job(name="good", cron="* * * * *", prompt="p")]
    s = Scheduler(jobs, run_job=run_job, on_result=on_result)
    s.now = lambda: datetime(2026, 9, 21, 8, 0)  # type: ignore[method-assign]
    await s._tick()
    assert calls == ["good"]


def test_rule_jobs_need_a_rule_name():
    with pytest.raises(ValueError, match="rule 이름"):
        Job(name="bad", cron="* * * * *", mode="rule")


def test_agent_jobs_need_a_prompt():
    with pytest.raises(ValueError, match="prompt"):
        Job(name="bad", cron="* * * * *", mode="agent")


def test_frequent_jobs_do_not_use_the_model():
    """자주 도는 잡이 모델을 부르면 비용이 터진다 (ADR-008)."""
    from assistant.scheduler.cron import Schedule

    for job in DEFAULT_JOBS:
        # 하루 24번 넘게 도는 잡인가
        runs_per_day = len(Schedule.parse(job.cron).minute) * len(Schedule.parse(job.cron).hour)
        if runs_per_day > 24:
            assert job.mode == "rule", f"{job.name}: 하루 {runs_per_day}회면 규칙이어야 한다"


def test_every_rule_job_points_at_a_registered_rule():
    from assistant.scheduler import rules

    for job in DEFAULT_JOBS:
        if job.mode == "rule":
            assert job.rule in rules.registered(), f"{job.name}: 등록 안 된 규칙 '{job.rule}'"
