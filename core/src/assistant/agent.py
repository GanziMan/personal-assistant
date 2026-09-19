"""에이전트 루프.

의도 → 계획 → 도구 실행 → 관찰 → 응답. 도구가 있으면 모델이 부르고,
결과를 다시 모델에 먹여 반복한다. 반복 상한은 config 로 막는다.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .audit import AuditLog
from .config import Config
from .llm.cloud import CloudAuthError, CloudLLM
from .llm.subscription import SubscriptionBackend
from .llm.router import ModelRouter, TaskKind
from .prompts import SYSTEM
from .protocol import Event, EventType
from .memory import Episode, MemoryStore
from .tools import ServerSpec, ToolRegistry
from .tools.registry import ConfirmationRequired, ToolError


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
        self.tools = ToolRegistry(
            audit=self.audit, require_confirmation=config.agent.require_confirmation
        )
        self.memory = MemoryStore()
        self._cloud: CloudLLM | None = None
        self._sessions: dict[str, Session] = {}
        self._backend: SubscriptionBackend | None = None

    @property
    def uses_subscription(self) -> bool:
        return self.config.models.backend == "subscription"

    async def start(self) -> None:
        if self.uses_subscription:
            self._backend = SubscriptionBackend(self.config)
            await self._backend.start()

        # 구독 백엔드는 자기 MCP 연결을 따로 띄운다. 여기 레지스트리를
        # 같은 규모로 또 띄우면 프로세스가 두 배가 되고 기동이 느려진다.
        # 데몬이 직접 부르는 건 대기 화면(calendar)과 알림(system)뿐이다.
        needed = {"calendar", "system", "dev"} if self.uses_subscription else None
        specs = [
            ServerSpec(
                name=str(s["name"]),
                command=str(s["command"]),
                args=list(s.get("args", [])),  # type: ignore[arg-type]
            )
            for s in self.config.servers
            if needed is None or str(s["name"]) in needed
        ]
        await self.tools.start(specs)

        if self._backend is not None and self.config.agent.prewarm:
            await self._backend.prewarm()

    async def aclose(self) -> None:
        if self._backend is not None:
            await self._backend.aclose()
        await self.tools.aclose()
        self.memory.close()

    async def run_silent(self, prompt: str, *, session_id: str = "background") -> str:
        """대화창 없이 한 턴 돌리고 텍스트만 받는다. 스케줄러가 쓴다."""
        parts: list[str] = []
        async for event in self.run(session_id, prompt):
            if event.type is EventType.TEXT:
                parts.append(event.text)
            elif event.type is EventType.ERROR:
                raise RuntimeError(event.text)
        return "".join(parts)

    def remember(self, title: str, body: str = "", *, kind: str = "conversation",
                 session_id: str = "", importance: float = 0.5) -> None:
        """일화를 적재한다. 실패해도 대화를 멈추지 않는다."""
        try:
            self.memory.add_episode(
                Episode(title=title, body=body, kind=kind,
                        session_id=session_id, importance=importance)
            )
        except Exception as exc:
            self.audit.record("memory_write_failed", error=repr(exc))

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
        """한 턴을 돌린다. 도구 호출이 끝날 때까지 반복한다."""
        if self._backend is not None:
            # SDK 가 루프와 도구 호출을 직접 돌린다
            async for event in self._backend.stream(session_id, prompt):
                yield event
            return

        session = self.session(session_id)
        session.add("user", prompt)

        schemas = self.tools.schemas()
        kind = TaskKind.PLAN if schemas else TaskKind.CHAT
        route = self.router.route(kind)
        self.audit.model_call(provider=route.provider, model=route.model, reason=route.reason)

        for _ in range(self.config.agent.max_iterations):
            text_parts: list[str] = []
            tool_uses: list[Any] = []
            stop_reason = ""

            try:
                async for chunk_kind, payload in self.cloud.stream(
                    model=route.model,
                    system=self._system_prompt(),
                    messages=session.messages,
                    tools=schemas or None,
                ):
                    if chunk_kind == "text":
                        text_parts.append(payload)
                        yield Event(EventType.TEXT, session_id, payload)
                    elif chunk_kind == "tool_use":
                        tool_uses.append(payload)
                    elif chunk_kind == "stop_reason":
                        stop_reason = payload or ""
            except CloudAuthError as exc:
                # 이미 사람이 읽을 수 있는 안내다. 타입 이름을 덧붙이지 않는다.
                self.audit.record("error", where="agent.run", error="auth")
                yield Event(EventType.ERROR, session_id, str(exc))
                return
            except Exception as exc:  # 데몬을 죽이지 않는다
                self.audit.record("error", where="agent.run", error=repr(exc))
                yield Event(EventType.ERROR, session_id, f"{type(exc).__name__}: {exc}")
                return

            assistant_content: list[dict[str, Any]] = []
            if text_parts:
                assistant_content.append({"type": "text", "text": "".join(text_parts)})
            for block in tool_uses:
                assistant_content.append(
                    {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
                )
            session.add("assistant", assistant_content or [{"type": "text", "text": ""}])

            if stop_reason != "tool_use" or not tool_uses:
                yield Event(EventType.DONE, session_id)
                return

            results: list[dict[str, Any]] = []
            for block in tool_uses:
                yield Event(
                    EventType.TOOL_CALL, session_id, block.name, {"args": dict(block.input)}
                )
                output, is_error = await self._invoke(block.name, dict(block.input))

                if is_error == "confirm":
                    # 확인이 필요하면 턴을 여기서 끊는다. 사용자가 승인하면
                    # 다음 프롬프트에서 이어간다.
                    yield Event(
                        EventType.CONFIRM,
                        session_id,
                        output,
                        {"tool": block.name, "args": dict(block.input)},
                    )
                    yield Event(EventType.DONE, session_id)
                    return

                yield Event(EventType.TOOL_RESULT, session_id, output[:400], {"tool": block.name})
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                        "is_error": bool(is_error),
                    }
                )

            session.add("user", results)

        yield Event(
            EventType.ERROR, session_id, f"도구 호출이 {self.config.agent.max_iterations}회를 넘었습니다."
        )

    async def _invoke(self, name: str, args: dict[str, Any]) -> tuple[str, str | bool]:
        """도구를 부른다. (출력, 오류표시) 를 돌려준다."""
        try:
            return await self.tools.call(name, args), False
        except ConfirmationRequired as exc:
            return f"'{exc.tool.qualified}' 실행을 승인하시겠습니까? 인자: {exc.args}", "confirm"
        except ToolError as exc:
            # 모델에게 돌려줘서 스스로 고치게 한다
            return str(exc), True
