"""데몬과 클라이언트 사이의 프로토콜.

줄 단위 JSON. 유닉스 도메인 소켓 위에서만 돈다 (ADR-003).
스트리밍이 필요해서 요청/응답 1:1 이 아니라, 하나의 요청에 여러 개의
이벤트가 흘러나오는 형태로 잡는다.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    # 클라이언트 → 데몬
    PROMPT = "prompt"
    CANCEL = "cancel"
    PING = "ping"
    STATUS = "status"            # 대기 화면용 요약 요청

    # 데몬 → 클라이언트
    TEXT = "text"                # 응답 조각 (스트리밍)
    THINKING = "thinking"        # 지금 뭘 하는 중인지
    TOOL_CALL = "tool_call"      # 도구를 부른다
    TOOL_RESULT = "tool_result"
    CONFIRM = "confirm"          # 사용자 확인 요청 (ADR-005)
    DONE = "done"
    ERROR = "error"
    PONG = "pong"
    STATUS_RESULT = "status_result"


@dataclass(slots=True)
class Event:
    type: EventType
    session_id: str = ""
    text: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def encode(self) -> bytes:
        return json.dumps(asdict(self), ensure_ascii=False).encode() + b"\n"

    @classmethod
    def decode(cls, line: bytes) -> Event:
        raw = json.loads(line)
        return cls(
            type=EventType(raw["type"]),
            session_id=raw.get("session_id", ""),
            text=raw.get("text", ""),
            data=raw.get("data", {}),
        )
