"""모델 라우터.

외부로 나가는 유일한 경유지. 어떤 작업을 어느 두뇌로 보낼지 여기서만
결정하고, 결정 근거를 감사 로그에 남긴다 (ARCHITECTURE §4).

판단 기준은 비용이 아니라 '실패했을 때 사용자가 겪는 손해'다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..config import ModelConfig


class TaskKind(StrEnum):
    EMBED = "embed"                # 임베딩 — 양이 많고 품질차 작음
    CLASSIFY = "classify"          # 분류·라우팅 판단 — 짧고 반복적
    SUMMARIZE_SHORT = "summarize_short"
    SUMMARIZE_LONG = "summarize_long"
    PLAN = "plan"                  # 다단계 계획·도구 사용
    CODE = "code"
    CHAT = "chat"


class Provider(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"


@dataclass(slots=True, frozen=True)
class Route:
    provider: Provider
    model: str
    reason: str


# 정책 테이블. 로컬 모델이 좋아지면 이 표만 고친다 (ADR-001 대비책).
_POLICY: dict[TaskKind, tuple[Provider, str]] = {
    TaskKind.EMBED: (Provider.LOCAL, "양이 많고 품질 차이가 작다"),
    TaskKind.CLASSIFY: (Provider.LOCAL, "짧고 반복적, 지연이 중요"),
    TaskKind.SUMMARIZE_SHORT: (Provider.LOCAL, "한 문단 요약은 로컬로 충분하다"),
    TaskKind.SUMMARIZE_LONG: (Provider.CLOUD, "긴 문맥에서 로컬 품질이 무너진다"),
    TaskKind.PLAN: (Provider.CLOUD, "다단계 도구 사용은 로컬이 확실히 무너진다"),
    TaskKind.CODE: (Provider.CLOUD, "품질 차이가 가장 크게 벌어지는 영역"),
    TaskKind.CHAT: (Provider.CLOUD, "대화 품질이 비서의 체감을 좌우한다"),
}

_HEAVY_TASKS = frozenset({TaskKind.CODE, TaskKind.PLAN})


class ModelRouter:
    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    def route(self, kind: TaskKind, *, sensitive: bool = False) -> Route:
        """작업 종류로 두뇌를 고른다.

        sensitive=True 면 정책을 무시하고 로컬로 고정한다. 민감 문서는
        사용자가 예외를 지정하기 전까지 맥을 벗어나지 않는다.
        """
        if sensitive:
            return Route(
                Provider.LOCAL,
                self._local_model(kind),
                "민감 표시된 작업은 로컬로 고정한다",
            )

        provider, reason = _POLICY[kind]

        if provider is Provider.LOCAL and self.config.force_cloud:
            return Route(Provider.CLOUD, self.config.cloud_model, "force_cloud 설정으로 우회")

        if provider is Provider.LOCAL:
            return Route(Provider.LOCAL, self._local_model(kind), reason)

        model = (
            self.config.cloud_model_heavy if kind in _HEAVY_TASKS else self.config.cloud_model
        )
        return Route(Provider.CLOUD, model, reason)

    def _local_model(self, kind: TaskKind) -> str:
        if kind is TaskKind.EMBED:
            return self.config.local_embed_model
        return self.config.local_chat_model
