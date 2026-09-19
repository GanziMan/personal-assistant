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
