"""도구와 서버 명세."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 이 접두사로 시작하는 도구는 되돌릴 수 없다고 본다 (ADR-005).
# 서버가 스스로 안전하다고 주장해도 데몬이 판단한다.
DESTRUCTIVE_PREFIXES: tuple[str, ...] = (
    "delete_",
    "remove_",
    "move_",
    "overwrite_",
    "write_",
    "send_",
    "create_event",
    "update_event",
)


@dataclass(slots=True, frozen=True)
class ServerSpec:
    """MCP 서버 하나를 띄우는 방법."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    # 이 서버가 손댈 수 있는 경로. 데몬이 강제한다 (ARCHITECTURE §7).
    allowed_paths: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass(slots=True, frozen=True)
class ToolSpec:
    """서버가 노출한 도구 하나."""

    server: str
    name: str
    description: str
    schema: dict[str, Any]

    @property
    def qualified(self) -> str:
        """모델에 보여줄 이름. 서버가 달라도 충돌하지 않게 한다."""
        return f"{self.server}__{self.name}"

    @property
    def destructive(self) -> bool:
        return self.name.startswith(DESTRUCTIVE_PREFIXES)

    def to_anthropic(self) -> dict[str, Any]:
        return {
            "name": self.qualified,
            "description": self.description,
            "input_schema": self.schema,
        }
