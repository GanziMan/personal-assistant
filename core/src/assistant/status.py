"""대기 화면 요약.

항상 떠 있는 패널이 1분마다 갱신된다. 그때마다 모델을 부르면 하루
1440번이다 — 15분 잡에서 배운 것과 같은 실수를 UI 쪽에서 반복하게
된다 (ADR-008). 그래서 여기서는 도구만 직접 부른다.

도구가 없거나 실패해도 화면은 떠야 한다. 없는 항목은 빈 값으로 둔다.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

log = logging.getLogger(__name__)

CACHE_SECONDS = 45.0
MAX_TODOS = 5

_LEAD_MIN = re.compile(r"^(\d+)\s*분 뒤")
_LEAD_HOUR = re.compile(r"^(\d+)\s*시간 뒤")
_LEAD_DAY = re.compile(r"^(\d+)\s*일 뒤")


def lead_minutes(text: str) -> int | None:
    """도구가 돌려준 문장에서 남은 시간을 분으로 환산한다."""
    if m := _LEAD_MIN.match(text):
        return int(m.group(1))
    if m := _LEAD_HOUR.match(text):
        return int(m.group(1)) * 60
    if m := _LEAD_DAY.match(text):
        return int(m.group(1)) * 60 * 24
    return None


@dataclass(slots=True)
class Status:
    next_event: str = ""
    next_event_minutes: int | None = None
    todos: list[str] = field(default_factory=list)
    brief: str = ""
    brief_at: float = 0.0
    notes: list[str] = field(default_factory=list)
    tools_ready: bool = False
    capabilities: list[dict] = field(default_factory=list)
    health_line: str = ""
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_reminders(text: str, *, limit: int = MAX_TODOS) -> list[str]:
    """리마인더 도구 출력에서 미완료 항목만 골라 짧게 만든다."""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("○"):  # ✓ 는 완료
            continue
        title = line[1:].strip().split("  (")[0].strip()
        if title:
            out.append(title)
        if len(out) >= limit:
            break
    return out


class StatusProvider:
    """도구와 기억에서 대기 화면 내용을 모은다."""

    def __init__(self, agent) -> None:  # noqa: ANN001 - 순환 임포트 회피
        self.agent = agent
        self._cached = Status()

    async def get(self, *, force: bool = False) -> Status:
        if not force and time.time() - self._cached.updated_at < CACHE_SECONDS:
            return self._cached

        status = Status(updated_at=time.time())
        tools = self.agent.tools
        status.tools_ready = bool(tools.schemas())

        status.next_event, status.next_event_minutes = await self._next_event(tools)
        status.todos = await self._todos(tools)
        status.brief, status.brief_at = self._latest_brief()
        status.notes = self._notes()
        status.capabilities, status.health_line = await self._health()

        self._cached = status
        return status

    async def _next_event(self, tools) -> tuple[str, int | None]:  # noqa: ANN001
        try:
            text = (await tools.call("calendar__next_event", {})).strip()
        except Exception as exc:
            log.debug("next_event 실패: %s", exc)
            return "", None
        if not text or "없습니다" in text:
            return "", None
        return text, lead_minutes(text)

    async def _todos(self, tools) -> list[str]:  # noqa: ANN001
        try:
            text = await tools.call("calendar__list_reminders", {"include_completed": False})
        except Exception as exc:
            log.debug("list_reminders 실패: %s", exc)
            return []
        return parse_reminders(text)

    async def _health(self) -> tuple[list[dict], str]:
        """비서가 스스로의 상태를 안다. 모델을 부르지 않는다."""
        from .health import probe_ollama, probe_tools, summarize

        models = self.agent.config.models
        caps = [
            probe_tools(self.agent.tools),
            await probe_ollama(models.local_endpoint, models.local_embed_model),
        ]
        return [c.to_dict() for c in caps], summarize(caps)

    def _notes(self) -> list[str]:
        """감지기가 남긴 쪽지. 오래된 것은 스스로 사라진다."""
        from .detect.notes import NoteBoard

        try:
            return [n.message for n in NoteBoard().load()]
        except Exception as exc:
            log.debug("쪽지 조회 실패: %s", exc)
            return []

    def _latest_brief(self) -> tuple[str, float]:
        """가장 최근 브리핑을 기억에서 꺼낸다. 모델을 부르지 않는다."""
        try:
            row = self.agent.memory.db.execute(
                "SELECT body, ts FROM episodes WHERE kind = 'briefing'"
                " ORDER BY ts DESC LIMIT 1"
            ).fetchone()
        except Exception as exc:
            log.debug("브리핑 조회 실패: %s", exc)
            return "", 0.0
        return ("", 0.0) if row is None else (str(row["body"]), float(row["ts"]))
