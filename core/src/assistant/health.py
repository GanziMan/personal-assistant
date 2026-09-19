"""비서 자기 상태.

비서가 스스로의 상태를 모르면, 성능이 떨어져도 사용자는 이유를
알 수 없다. Ollama 가 꺼지면 문서 검색이 조용히 나빠지는데 화면에는
아무 표시가 없었다 — 그건 좋은 침묵이 아니다 (ADR-031).

여기서도 모델을 부르지 않는다. 자기 상태는 조회로 알 수 있다.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

import httpx

log = logging.getLogger(__name__)

PROBE_TIMEOUT = 2.0


@dataclass(slots=True)
class Capability:
    """기능 하나의 상태."""

    key: str
    label: str
    ok: bool
    detail: str = ""
    # 꺼졌을 때 무엇이 나빠지는지. 사용자가 고칠지 말지 판단할 근거다.
    degraded: str = ""
    fix: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def probe_ollama(endpoint: str, model: str) -> Capability:
    """로컬 임베딩이 살아 있는가."""
    base = Capability(
        key="embedding",
        label="로컬 임베딩",
        ok=False,
        degraded="문서·기억 검색이 키워드만 씁니다. 내용으로 찾기가 약해집니다.",
        fix="brew services start ollama",
    )

    try:
        async with httpx.AsyncClient(base_url=endpoint, timeout=PROBE_TIMEOUT) as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            names = [m.get("name", "") for m in response.json().get("models", [])]
    except Exception as exc:
        log.debug("Ollama 탐지 실패: %s", exc)
        base.detail = "Ollama 가 응답하지 않습니다."
        return base

    # 태그에 :latest 가 붙는다
    if not any(name.split(":")[0] == model.split(":")[0] for name in names):
        base.detail = f"{model} 모델이 없습니다."
        base.fix = f"ollama pull {model}"
        return base

    return Capability(
        key="embedding", label="로컬 임베딩", ok=True, detail=model
    )


def probe_tools(registry) -> Capability:  # noqa: ANN001
    """도구층이 붙었는가."""
    count = len(registry.schemas())
    if count:
        return Capability(key="tools", label="도구", ok=True, detail=f"{count}개")
    return Capability(
        key="tools",
        label="도구",
        ok=False,
        detail="MCP 서버가 붙지 않았습니다.",
        degraded="일정·파일·레포를 볼 수 없습니다.",
        fix="./scripts/doctor.sh",
    )


def summarize(capabilities: list[Capability]) -> str:
    """꺼진 기능을 한 줄로. 전부 정상이면 빈 문자열."""
    down = [c for c in capabilities if not c.ok]
    if not down:
        return ""
    if len(down) == 1:
        return f"{down[0].label}이(가) 꺼져 있습니다 — {down[0].degraded}"
    labels = ", ".join(c.label for c in down)
    return f"{labels}이(가) 꺼져 있습니다."
