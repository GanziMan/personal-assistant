"""잡 러너.

데몬 안에서 도는 asyncio 루프. 별도 cron 등록을 쓰지 않는 이유는,
잡이 에이전트와 기억에 접근해야 하고 그 상태가 데몬 프로세스에 있기
때문이다. launchd 는 데몬 자체를 띄우는 데만 쓴다.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from .jobs import Job

log = logging.getLogger(__name__)

# 잡 실행 결과를 받아 처리하는 콜백 (알림·기억 적재)
Handler = Callable[[Job, str], Awaitable[None]]


class Scheduler:
    def __init__(
        self,
        jobs: list[Job],
        *,
        run_job: Callable[[Job], Awaitable[str]],
        on_result: Handler,
        timezone: str = "Asia/Seoul",
    ) -> None:
        self.jobs = [j for j in jobs if j.enabled]
        self.run_job = run_job
        self.on_result = on_result
        self.tz = ZoneInfo(timezone)
        self._task: asyncio.Task[None] | None = None
        self._last_fired: dict[str, datetime] = {}

    def now(self) -> datetime:
        return datetime.now(self.tz).replace(second=0, microsecond=0)

    def due(self, now: datetime) -> list[Job]:
        """지금 실행해야 하는 잡. 같은 분에 두 번 돌지 않게 막는다."""
        out = []
        for job in self.jobs:
            if not job.schedule.matches(now):
                continue
            if self._last_fired.get(job.name) == now:
                continue
            out.append(job)
        return out

    async def _tick(self) -> None:
        now = self.now()
        for job in self.due(now):
            self._last_fired[job.name] = now
            try:
                result = await self.run_job(job)
            except Exception as exc:
                log.warning("잡 '%s' 실패: %s", job.name, exc)
                continue

            if result.strip() and result.strip() != "없음":
                await self.on_result(job, result.strip())

    async def _loop(self) -> None:
        while True:
            try:
                await self._tick()
            except Exception:  # 루프는 어떤 경우에도 죽지 않는다
                log.exception("스케줄러 tick 실패")

            # 다음 분 경계까지 잔다. 분 단위 스케줄을 놓치지 않으면서
            # 쓸데없이 자주 깨지 않는다.
            now = datetime.now(self.tz)
            await asyncio.sleep(61 - now.second)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())
            log.info("스케줄러 시작: 잡 %d개", len(self.jobs))

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
