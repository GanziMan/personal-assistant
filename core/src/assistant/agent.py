"""에이전트 루프.

의도 → 계획 → 도구 실행 → 관찰 → 응답. 도구 레지스트리는 P2 에서
붙는다. 지금은 대화만 돈다.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .audit import AuditLog
from .config import Config
from .llm.cloud import CloudLLM
from .llm.router import ModelRouter, TaskKind
from .prompts import SYSTEM
from .protocol import Event, EventType


class Session:
    """하나의 대화. 작업 기억(ARCHITECTURE §5)을 들고 있다."""

    def __init__(self, session_id: str | None = None) -> None:
        self.id = session_id or uuid.uuid4().hex[:12]
        self.messages: list[dict[str, Any]] = []

    def add(self, role: str, content: Any) -> None:
        self.messages.append({"role": role, "content": content})


class Agent:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.router = ModelRouter(config.models)
        self.audit = AuditLog()
        self._cloud: CloudLLM | None = None
        self._sessions: dict[str, Session] = {}

    @property
    def cloud(self) -> CloudLLM:
        # 키체인 접근을 첫 호출까지 미룬다. 키가 없어도 데몬은 뜬다.
        if self._cloud is None:
            self._cloud = CloudLLM(timeout_s=self.config.agent.request_timeout_s)
        return self._cloud

    def session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id)
        return self._sessions[session_id]

    def _system_prompt(self) -> str:
        tz = ZoneInfo(self.config.timezone)
        return SYSTEM.format(
            timezone=self.config.timezone,
            now=datetime.now(tz).strftime("%Y-%m-%d %H:%M (%A)"),
        )

    async def run(self, session_id: str, prompt: str) -> AsyncIterator[Event]:
        """한 턴을 돌린다. 이벤트를 흘려보낸다."""
        session = self.session(session_id)
        session.add("user", prompt)

        route = self.router.route(TaskKind.CHAT)
        self.audit.model_call(
            provider=route.provider, model=route.model, reason=route.reason
        )

        parts: list[str] = []
        try:
            async for kind, payload in self.cloud.stream(
                model=route.model,
                system=self._system_prompt(),
                messages=session.messages,
            ):
                if kind == "text":
                    parts.append(payload)
                    yield Event(EventType.TEXT, session_id, payload)
        except Exception as exc:  # 데몬을 죽이지 않는다
            self.audit.record("error", where="agent.run", error=repr(exc))
            yield Event(EventType.ERROR, session_id, f"{type(exc).__name__}: {exc}")
            return

        session.add("assistant", "".join(parts))
        yield Event(EventType.DONE, session_id)
