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

    # mode="agent" 면 prompt 를 모델에 보낸다. "rule" 이면 rule 이름의
    # 파이썬 함수를 부른다 — 모델 호출이 없으므로 비용이 0이다.
    mode: str = "agent"
    prompt: str = ""
    rule: str = ""

    notify: bool = False           # 알림을 띄울 것인가
    title: str = ""                # 알림 제목

    # 기억에 어떤 분류로 쌓을지. 나중에 "이번 분기 뭐 했지" 가
    # 업무 로그만 골라 읽을 수 있어야 한다.
    kind: str = "briefing"
    enabled: bool = True
    schedule: Schedule = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "schedule", Schedule.parse(self.cron))
        if self.mode == "agent" and not self.prompt:
            raise ValueError(f"{self.name}: agent 잡에는 prompt 가 필요합니다")
        if self.mode == "rule" and not self.rule:
            raise ValueError(f"{self.name}: rule 잡에는 rule 이름이 필요합니다")
        if self.mode not in {"agent", "rule"}:
            raise ValueError(f"{self.name}: 알 수 없는 mode '{self.mode}'")


DEFAULT_JOBS: tuple[Job, ...] = (
    Job(
        name="morning_brief",
        cron="0 8 * * 0-4",  # 평일 08:00 (0=월)
        prompt=(
            "오늘 아침 브리핑을 만들어줘. 오늘 일정, 미완료 리마인더, "
            "구독 피드의 최근 항목을 확인하고, 가장 먼저 신경 써야 할 것 "
            "한 가지를 짚어줘. 7줄을 넘기지 마."
        ),
        notify=True,
        title="아침 브리핑",
    ),
    # 하루 96번 도는 잡이다. 모델을 태우면 비용의 대부분이 여기서 나오고,
    # 애초에 판단이 필요 없는 일이라 규칙으로 돌린다 (ADR-008).
    Job(
        name="upcoming_event",
        cron="*/15 * * * *",
        mode="rule",
        rule="upcoming_event",
        notify=True,
        title="곧 시작하는 일정",
    ),
    # 30분마다. 판단이 전부 코드라 비용이 0이다.
    Job(
        name="detect",
        cron="*/30 * * * *",
        mode="rule",
        rule="detect",
        notify=False,  # 알림 여부는 신호의 severity 가 정한다
    ),
    # 일정 15분 전 창에 걸리도록 5분마다 확인한다. 규칙이라 비용이 0이다.
    Job(
        name="meeting_prep",
        cron="*/5 * * * *",
        mode="rule",
        rule="meeting_prep",
        kind="prep",
        notify=False,  # 쪽지로만. 알림은 upcoming_event 가 이미 한다
    ),
    # 새벽에 한 번. 바뀐 파일만 읽으므로 보통 몇 초다.
    Job(
        name="reindex_docs",
        cron="0 4 * * *",
        mode="rule",
        rule="reindex_docs",
        kind="index",
        notify=False,
    ),
    # 하루를 닫으며 오늘 한 일을 쌓는다. 쌓인 것이 분기 회고의 근거가 된다.
    Job(
        name="work_log",
        cron="30 18 * * 0-4",
        mode="rule",
        rule="work_log",
        kind="worklog",
        notify=False,
    ),
    Job(
        name="weekly_review",
        cron="0 18 * * 4",  # 금요일 18:00
        prompt=(
            "이번 주 회고를 만들어줘. 이번 주 일정, 처리한 리마인더, "
            "레포별 커밋과 아직 커밋하지 않은 변경을 돌아보고, "
            "다음 주로 넘어가는 것들을 정리해줘."
        ),
        notify=False,  # 조용히 기억에 적재. 알림까지 띄우지 않는다
    ),
)
