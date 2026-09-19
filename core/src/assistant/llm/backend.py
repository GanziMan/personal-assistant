"""두뇌 백엔드 인터페이스.

두 가지 경로가 있다.

- subscription: Claude Agent SDK. Claude Code 로그인(Pro/Max 구독)에서
  사용량이 차감된다. 별도 API 과금이 없다.
- api: Messages API 직접 호출. API 키가 필요하고 토큰 단위로 과금된다.

에이전트 루프 위치가 다르다. SDK 백엔드는 루프와 MCP 연결을 SDK 가
직접 돌리고, API 백엔드는 우리 agent.py 가 돌린다. 그래서 인터페이스를
'한 턴을 돌려 이벤트를 흘린다' 수준으로 잡는다 — 그보다 잘게 맞추면
한쪽에 없는 개념을 다른 쪽에 억지로 만들어야 한다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from ..protocol import Event


class Backend(Protocol):
    async def start(self) -> None: ...

    async def aclose(self) -> None: ...

    def stream(self, session_id: str, prompt: str) -> AsyncIterator[Event]:
        """한 턴을 돌린다. TEXT/TOOL_CALL/DONE/ERROR 이벤트를 흘린다."""
        ...
