"""선제 작업 정의.

원칙: 알림은 비싸다 (ARCHITECTURE §6). 기본은 조용한 적재이고,
실제로 알림을 띄우는 잡은 notify=True 로 명시해야 한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cron import Schedule


@dataclass(slots=True, frozen=True)
class Job:
    name: str
    cron: str
    prompt: str
    notify: bool = False           # 알림을 띄울 것인가
    title: str = ""                # 알림 제목
    enabled: bool = True
    schedule: Schedule = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "schedule", Schedule.parse(self.cron))


DEFAULT_JOBS: tuple[Job, ...] = (
    Job(
        name="morning_brief",
        cron="0 8 * * 0-4",  # 평일 08:00 (0=월)
        prompt=(
            "오늘 아침 브리핑을 만들어줘. 오늘 일정과 미완료 리마인더를 확인하고, "
            "가장 먼저 신경 써야 할 것 한 가지를 짚어줘. 5줄을 넘기지 마."
        ),
        notify=True,
        title="아침 브리핑",
    ),
    Job(
        name="upcoming_event",
        cron="*/15 * * * *",
        prompt=(
            "30분 안에 시작하는 일정이 있으면 한 줄로 알려줘. "
            "없으면 '없음'만 답해."
        ),
        notify=True,
        title="곧 시작하는 일정",
    ),
    Job(
        name="weekly_review",
        cron="0 18 * * 4",  # 금요일 18:00
        prompt=(
            "이번 주 회고를 만들어줘. 이번 주에 있었던 일정과 처리한 리마인더를 "
            "돌아보고, 다음 주로 넘어가는 것들을 정리해줘."
        ),
        notify=False,  # 조용히 기억에 적재. 알림까지 띄우지 않는다
    ),
)
