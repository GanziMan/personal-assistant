"""EventKit 얇은 래퍼.

AppleScript 로 Calendar.app 을 조종하는 방식을 쓰지 않는다. 앱이 떠
있어야 하고, 느리고, 사용자가 창을 만지면 깨진다. EventKit 은 앱과
무관하게 저장소를 직접 읽는다.

대신 TCC 권한이 필요하다. 데몬 프로세스가 처음 접근할 때 macOS 가
사용자에게 묻고, 거부되면 복구할 방법이 없으니 안내 문구를 명확히 둔다.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

if sys.platform != "darwin":  # pragma: no cover - macOS 전용
    raise ImportError("EventKit 은 macOS 에서만 씁니다")

from EventKit import (  # type: ignore[import-not-found]
    EKAuthorizationStatusFullAccess,
    EKEntityTypeEvent,
    EKEntityTypeReminder,
    EKEventStore,
)
from Foundation import NSDate  # type: ignore[import-not-found]


from .models import Event, Reminder  # noqa: E402


class PermissionDenied(RuntimeError):
    """캘린더 접근이 거부됐다."""


def _to_datetime(nsdate) -> datetime:  # noqa: ANN001
    return datetime.fromtimestamp(nsdate.timeIntervalSince1970())


class CalendarStore:
    def __init__(self) -> None:
        self._store = EKEventStore.alloc().init()

    def ensure_access(self, entity: int = EKEntityTypeEvent) -> None:
        status = EKEventStore.authorizationStatusForEntityType_(entity)
        if status == EKAuthorizationStatusFullAccess:
            return

        done: dict[str, object] = {}

        def handler(granted, error):  # noqa: ANN001
            done["granted"] = bool(granted)

        if entity == EKEntityTypeReminder:
            self._store.requestFullAccessToRemindersWithCompletion_(handler)
        else:
            self._store.requestFullAccessToEventsWithCompletion_(handler)

        # 콜백이 즉시 돌아오지 않을 수 있다. 권한 다이얼로그는 사용자가
        # 답해야 끝나므로, 여기서는 상태를 다시 읽는 것으로 갈음한다.
        if EKEventStore.authorizationStatusForEntityType_(entity) != EKAuthorizationStatusFullAccess:
            raise PermissionDenied(
                "캘린더 접근 권한이 없습니다. "
                "시스템 설정 → 개인정보 보호 및 보안 → 캘린더 에서 허용해 주세요."
            )

    def events_between(self, start: datetime, end: datetime) -> list[Event]:
        self.ensure_access(EKEntityTypeEvent)
        predicate = self._store.predicateForEventsWithStartDate_endDate_calendars_(
            NSDate.dateWithTimeIntervalSince1970_(start.timestamp()),
            NSDate.dateWithTimeIntervalSince1970_(end.timestamp()),
            None,
        )
        found = self._store.eventsMatchingPredicate_(predicate) or []
        events = [
            Event(
                title=str(e.title() or "(제목 없음)"),
                start=_to_datetime(e.startDate()),
                end=_to_datetime(e.endDate()),
                calendar=str(e.calendar().title()),
                location=str(e.location() or ""),
                all_day=bool(e.isAllDay()),
                notes=str(e.notes() or ""),
            )
            for e in found
        ]
        return sorted(events, key=lambda e: e.start)

    def events_for_day(self, day: datetime) -> list[Event]:
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        return self.events_between(start, start + timedelta(days=1))

    def reminders(self, *, include_completed: bool = False) -> list[Reminder]:
        """미완료 리마인더를 가져온다.

        EventKit 리마인더 조회는 콜백 기반이라 동기 코드에서 다루기
        까다롭다. 런루프를 짧게 돌려 결과를 회수한다.
        """
        from Foundation import NSRunLoop  # type: ignore[import-not-found]

        self.ensure_access(EKEntityTypeReminder)
        predicate = (
            self._store.predicateForRemindersInCalendars_(None)
            if include_completed
            else self._store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(
                None, None, None
            )
        )

        box: list = []
        done = {"ok": False}

        def handler(items):  # noqa: ANN001
            box.extend(items or [])
            done["ok"] = True

        self._store.fetchRemindersMatchingPredicate_completion_(predicate, handler)

        loop = NSRunLoop.currentRunLoop()
        deadline = datetime.now() + timedelta(seconds=5)
        while not done["ok"] and datetime.now() < deadline:
            loop.runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.05))

        out: list[Reminder] = []
        for r in box:
            due = r.dueDateComponents()
            due_dt = None
            if due is not None and due.date() is not None:
                due_dt = _to_datetime(due.date())
            out.append(
                Reminder(
                    title=str(r.title() or "(제목 없음)"),
                    due=due_dt,
                    completed=bool(r.isCompleted()),
                    list_name=str(r.calendar().title()),
                    notes=str(r.notes() or ""),
                )
            )
        return sorted(out, key=lambda x: (x.due is None, x.due or datetime.max))
