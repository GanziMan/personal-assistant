"""규칙 잡 — 모델을 쓰지 않는 선제 작업.

"30분 안에 시작하는 일정이 있으면 알려줘"는 판단이 필요 없는 일이다.
캘린더를 읽고 시간을 빼면 끝난다. 이런 걸 에이전트에 태우면 하루 96번
모델을 부르게 되고, 비용의 대부분이 여기서 나온다.

규칙은 도구만 부르고 문자열을 돌려준다. 빈 문자열이면 아무 일도
일어나지 않는다.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

log = logging.getLogger(__name__)

Rule = Callable[["object"], Awaitable[str]]
_REGISTRY: dict[str, Rule] = {}


def rule(name: str) -> Callable[[Rule], Rule]:
    def decorate(fn: Rule) -> Rule:
        _REGISTRY[name] = fn
        return fn

    return decorate


def get(name: str) -> Rule:
    if name not in _REGISTRY:
        raise KeyError(f"규칙 '{name}' 이 없습니다. 등록된 것: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def registered() -> list[str]:
    return sorted(_REGISTRY)


@rule("work_log")
async def work_log(tools) -> str:  # noqa: ANN001
    """오늘 한 일을 모아 한 덩어리로 만든다.

    모델을 쓰지 않는다. 무엇을 했는지는 조회와 정리의 문제다.
    """
    from ..worklog import build

    async def safe(name: str, args: dict) -> str:
        try:
            return await tools.call(name, args)
        except Exception as exc:
            log.debug("%s 실패: %s", name, exc)
            return ""

    day = build(
        commits=await safe("dev__commits_across_repos", {"days": 1}),
        events=await safe("calendar__list_events", {"when": "오늘"}),
        reminders=await safe("calendar__list_reminders", {"include_completed": True}),
    )
    if day.empty:
        return ""
    return f"{day.title()}\n\n{day.body()}"


@rule("detect")
async def detect(tools) -> str:  # noqa: ANN001
    """맥 상태를 살펴 먼저 말할 거리를 찾는다.

    판단은 전부 코드로 한다. 같은 얘기를 반복하지 않는 것이 감지보다
    어렵기 때문에, 신호마다 쿨다운과 상태 지문을 둔다 (ADR-025).
    """
    from ..detect.notes import NoteBoard
    from ..detect.probes import disk_pressure, folder_pileup
    from ..detect.signals import Severity
    from ..detect.store import SignalStore

    found = [probe for probe in (disk_pressure(), folder_pileup()) if probe is not None]
    store = SignalStore()

    # 조건이 풀린 신호는 기록을 지운다. 다시 생기면 즉시 말할 수 있어야 한다.
    live = {s.key for s in found}
    for key in ("disk_pressure", "downloads_pileup"):
        if key not in live:
            store.forget(key)

    fresh = store.filter(found)
    if not fresh:
        return ""

    board = NoteBoard()
    lines = []
    for signal in fresh:
        lines.append(signal.message)
        if signal.severity >= Severity.NOTE:
            board.put(signal.key, signal.message)
        if signal.severity >= Severity.ALERT:
            try:
                await tools.call(
                    "system__send_alert",
                    {"title": "비서", "message": signal.message},
                )
            except Exception as exc:
                log.warning("알림 실패: %s", exc)

    return "\n".join(lines)


@rule("upcoming_event")
async def upcoming_event(tools) -> str:  # noqa: ANN001
    """30분 안에 시작하는 일정. 없으면 빈 문자열."""
    return (await tools.call("calendar__upcoming", {"within_minutes": 30})).strip()
