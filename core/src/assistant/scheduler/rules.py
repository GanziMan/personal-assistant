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


@rule("new_jobs")
async def new_jobs(tools) -> str:  # noqa: ANN001
    """새로 올라온 채용공고를 확인한다.

    사람인 API 는 하루 요청 한도가 있다. 하루 두 번이면 충분하고,
    자주 부를 이유도 없다 — 공고는 분 단위로 바뀌지 않는다.
    """
    from ..detect.notes import NoteBoard

    try:
        result = (await tools.call("jobs__find_jobs", {"only_new": True})).strip()
    except Exception as exc:
        log.debug("공고 조회 실패: %s", exc)
        return ""

    if not result or "없습니다" in result.splitlines()[0]:
        return ""

    # 몇 건인지만 쪽지로. 목록은 물어보면 기억에서 꺼낸다.
    count = result.count("■")
    headline = f"새 채용공고가 올라왔습니다 ({count}개 검색 조건)"
    NoteBoard().put("new_jobs", headline)
    return result


@rule("reindex_docs")
async def reindex_docs(tools) -> str:  # noqa: ANN001
    """문서 색인을 갱신한다. 바뀐 파일만 다시 읽으므로 대개 금방 끝난다."""
    try:
        result = await tools.call("docsearch__reindex", {})
    except Exception as exc:
        log.debug("색인 실패: %s", exc)
        return ""
    # 새로 읽은 게 없으면 조용히 넘어간다
    return "" if "새로 읽은 문서 0개" in result else result


@rule("meeting_prep")
async def meeting_prep(tools) -> str:  # noqa: ANN001
    """일정 시작 전에 참고할 것을 모아 패널 쪽지로 올린다.

    모으는 일은 전부 조회다. 요약은 사용자가 물을 때 모델이 한다
    (ADR-028).
    """
    from ..detect.notes import NoteBoard
    from ..prep import Prep, keywords, trim
    from ..status import lead_minutes

    raw = (await tools.call("calendar__upcoming", {"within_minutes": 15})).strip()
    board = NoteBoard()
    if not raw:
        board.dismiss("meeting_prep")
        return ""

    # "12분 뒤 설계 리뷰 @회의실" 에서 제목만
    minutes = lead_minutes(raw) or 0
    title = raw.split("분 뒤", 1)[-1].split("@", 1)[0].strip()

    terms = keywords(title)
    prep = Prep(event=title, minutes=minutes)

    async def safe(name: str, args: dict) -> str:
        try:
            return await tools.call(name, args)
        except Exception as exc:
            log.debug("%s 실패: %s", name, exc)
            return ""

    if terms:
        query = " ".join(terms)
        prep.past = trim(await safe("memory__recall", {"query": query, "limit": 3}))
        prep.files = trim(await safe("files__search_files", {"query": terms[0], "days": 60}))

    prep.repos = trim(await safe("dev__all_status", {}), limit=2)

    if prep.empty:
        return ""

    board.put("meeting_prep", prep.render())
    return prep.render()


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
        # 알림은 앱이 띄운다. 데몬이 osascript 로 띄우면 눌러도 아무
        # 일이 일어나지 않는다 (ADR-036). 쪽지에 올려두면 앱이 가져간다.

    return "\n".join(lines)


@rule("upcoming_event")
async def upcoming_event(tools) -> str:  # noqa: ANN001
    """30분 안에 시작하는 일정. 없으면 빈 문자열."""
    return (await tools.call("calendar__upcoming", {"within_minutes": 30})).strip()
