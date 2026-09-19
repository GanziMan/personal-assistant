"""경로 경계.

이 모듈이 이 서버의 보안 전부다. 도구를 몇 개 노출하느냐보다,
비서가 어디까지 손댈 수 있느냐가 중요하다.

규칙은 하나다. 모든 경로는 허용 루트 안으로 해석되어야 한다.
해석(resolve) 한 뒤에 검사한다 — `..` 나 심볼릭 링크로 밖을 가리키는
경로는 문자열만 봐서는 걸러지지 않는다.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

# 기본 허용 루트. 사용자가 config 로 좁히거나 넓힐 수 있다.
DEFAULT_ROOTS = ("~/Downloads", "~/Documents", "~/Desktop")

# 허용 루트 안이라도 건드리지 않는 곳
DENIED_NAMES = frozenset({
    ".ssh", ".gnupg", ".aws", ".config", "Library", ".git",
    "Keychains", ".assistant", "node_modules", ".venv",
})


class PathDenied(PermissionError):
    """허용 범위 밖이다."""


class Boundary:
    def __init__(self, roots: Iterable[str] | None = None) -> None:
        self.roots: list[Path] = []
        for raw in roots or DEFAULT_ROOTS:
            path = Path(raw).expanduser()
            # 없는 폴더는 조용히 건너뛴다. Desktop 을 안 쓰는 사람도 있다.
            if path.is_dir():
                self.roots.append(path.resolve())

    def resolve(self, candidate: str | Path) -> Path:
        """경로를 해석하고 경계를 검사한다. 통과하면 절대 경로를 준다."""
        path = Path(candidate).expanduser()

        # strict=False: 아직 없는 파일(쓰기 대상)도 검사할 수 있어야 한다
        resolved = path.resolve(strict=False)

        if not any(self._within(resolved, root) for root in self.roots):
            raise PathDenied(
                f"허용된 폴더 밖입니다: {candidate}\n"
                f"허용: {', '.join(str(r) for r in self.roots) or '(없음)'}"
            )

        for part in resolved.parts:
            if part in DENIED_NAMES:
                raise PathDenied(f"접근하지 않는 위치입니다: {part}")

        return resolved

    @staticmethod
    def _within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True

    def describe(self) -> str:
        if not self.roots:
            return "허용된 폴더가 없습니다."
        return "\n".join(f"- {r}" for r in self.roots)


def from_env() -> Boundary:
    """ASSISTANT_FILE_ROOTS 로 허용 루트를 바꾼다 (콜론 구분)."""
    raw = os.environ.get("ASSISTANT_FILE_ROOTS", "")
    roots = [p for p in raw.split(":") if p.strip()] or None
    return Boundary(roots)
