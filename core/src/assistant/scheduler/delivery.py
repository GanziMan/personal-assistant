"""잡 결과 전달.

알림을 띄울지, 조용히 기억에만 넣을지는 잡이 정한다 (jobs.py).
여기서는 그 결정을 실행하기만 한다.
"""

from __future__ import annotations

import logging

from .jobs import Job

log = logging.getLogger(__name__)


class Delivery:
    def __init__(self, agent) -> None:  # noqa: ANN001 - 순환 임포트 회피
        self.agent = agent

    async def __call__(self, job: Job, result: str) -> None:
        # 언제나 기억에 남긴다. 알림을 안 띄워도 나중에 물어보면 답할 수 있어야 한다.
        self.agent.remember(
            title=f"[{job.name}] {result.splitlines()[0][:80]}",
            body=result,
            kind=job.kind,
            importance=0.7 if job.notify else 0.4,
        )

        if not job.notify:
            return

        try:
            await self.agent.tools.call(
                "system__send_alert",
                {"title": job.title or job.name, "message": result[:300]},
            )
        except Exception as exc:
            # 알림 실패는 조용히 넘긴다. 기억에는 이미 들어갔다.
            log.warning("알림 실패 (%s): %s", job.name, exc)
