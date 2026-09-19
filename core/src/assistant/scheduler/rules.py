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


@rule("upcoming_event")
async def upcoming_event(tools) -> str:  # noqa: ANN001
    """30분 안에 시작하는 일정. 없으면 빈 문자열."""
    return (await tools.call("calendar__upcoming", {"within_minutes": 30})).strip()
