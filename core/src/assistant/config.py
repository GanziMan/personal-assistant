"""설정과 경로.

비서의 런타임 상태는 전부 ~/.assistant 아래 모은다. 레포 디렉터리에는
코드만 두고, 개인 데이터는 한 곳에서 백업·삭제할 수 있게 한다.
"""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

HOME = Path(os.environ.get("ASSISTANT_HOME", Path.home() / ".assistant"))

SOCKET_PATH = HOME / "agent.sock"
DB_PATH = HOME / "memory.db"
AUDIT_PATH = HOME / "audit.jsonl"
LOG_DIR = HOME / "logs"
CONFIG_PATH = HOME / "config.toml"


@dataclass(slots=True)
class ModelConfig:
    """어느 두뇌를 쓸지.

    backend="subscription" 이면 Claude Code 로그인(Pro/Max)에서 사용량이
    빠지고 API 과금이 없다. "api" 는 키체인의 API 키로 토큰 과금된다.
    """

    backend: str = "subscription"

    # 구독 경로에서는 별칭을 쓴다. Claude Code 가 현재 모델로 해석한다.
    subscription_model: str = "sonnet"

    # 추론 강도. 비서가 하는 일은 대부분 조회와 요약이라 high 가 필요
    # 없다. 기본값(high)을 그대로 쓰면 체감 지연이 몇 배로 벌어진다.
    effort: str = "low"

    # 모델 ID 는 platform.claude.com/docs/en/models/overview 기준 (2026-09).
    # 일상 대화·짧은 작업은 sonnet, 계획·코딩은 opus 로 올린다.
    cloud_model: str = "claude-sonnet-5"
    cloud_model_heavy: str = "claude-opus-5"
    local_endpoint: str = "http://127.0.0.1:11434"
    local_chat_model: str = "qwen3:14b"  # M2 Pro 32GB 기준
    local_embed_model: str = "nomic-embed-text"

    # 라우팅을 통째로 클라우드로 고정 (로컬 모델 미설치 시)
    force_cloud: bool = False


@dataclass(slots=True)
class AgentConfig:
    """에이전트 루프의 한계값."""

    max_iterations: int = 25
    max_input_tokens: int = 120_000
    request_timeout_s: float = 120.0

    # 파괴적 도구는 확인 게이트를 통과해야 한다 (ADR-005)
    require_confirmation: bool = True

    # 데몬 기동 시 SDK 클라이언트를 미리 연결해둔다. 첫 질문이
    # MCP 서버 기동 비용을 뒤집어쓰지 않게 한다.
    prewarm: bool = True

    # Claude Code 내장 웹 도구. 검색·페치는 직접 만들 이유가 없다.
    # 파일·셸 내장 도구는 여전히 막는다 — 그건 우리 파일 서버의
    # 경로 경계를 우회하는 통로가 된다.
    allow_web_tools: bool = True


def default_servers() -> list[dict[str, object]]:
    """기본 MCP 서버.

    명령을 절대 경로로 준다. 데몬을 띄우는 launchd 도, SDK 가 띄우는
    자식 프로세스도 PATH 가 우리 venv 를 모른다 — 이름만 주면
    '실행 파일을 찾지 못함' 으로 조용히 실패한다.
    """
    bindir = Path(sys.executable).parent
    return [
        {"name": "calendar", "command": str(bindir / "macos-calendar-mcp"), "args": []},
        {"name": "system", "command": str(bindir / "macos-system-mcp"), "args": []},
        {"name": "files", "command": str(bindir / "macos-files-mcp"), "args": []},
        {"name": "feeds", "command": str(bindir / "feeds-mcp"), "args": []},
        {"name": "dev", "command": str(bindir / "dev-mcp"), "args": []},
    ]


@dataclass(slots=True)
class Config:
    models: ModelConfig = field(default_factory=ModelConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    servers: list[dict[str, object]] = field(default_factory=default_servers)
    timezone: str = "Asia/Seoul"
    locale: str = "ko_KR"

    def system_prompt(self) -> str:
        """시스템 프롬프트를 현재 시각으로 채운다."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from .prompts import SYSTEM

        return SYSTEM.format(
            timezone=self.timezone,
            now=datetime.now(ZoneInfo(self.timezone)).strftime("%Y-%m-%d %H:%M (%A)"),
        )

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        """config.toml 을 읽는다. 없으면 기본값."""
        path = path or CONFIG_PATH
        if not path.exists():
            return cls()

        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        return cls(
            models=ModelConfig(**raw.get("models", {})),
            agent=AgentConfig(**raw.get("agent", {})),
            servers=raw.get("servers", default_servers()),
            timezone=raw.get("timezone", "Asia/Seoul"),
            locale=raw.get("locale", "ko_KR"),
        )


def ensure_dirs() -> None:
    """런타임 디렉터리를 만든다. 소유자만 접근 가능하게."""
    HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    LOG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
