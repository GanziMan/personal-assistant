"""레포 탐색.

사용자에게 "레포 폴더가 어디냐"고 묻지 않는다. 흔한 위치를 훑어
git 레포를 찾고, 없으면 없다고 말한다. 설정을 하나라도 줄이는 쪽이
실제로 쓰이게 만드는 길이다.

ASSISTANT_DEV_ROOTS 로 직접 지정할 수 있다 (콜론 구분).
"""

from __future__ import annotations

import os
from pathlib import Path

CANDIDATE_ROOTS = (
    "~/dev", "~/Dev", "~/workspace", "~/Workspace",
    "~/Projects", "~/projects", "~/src", "~/code", "~/repos",
    "~/Documents", "~/Desktop",
)

# 레포를 찾으러 들어가지 않는 곳
SKIP_DIRS = frozenset({
    "node_modules", ".venv", "venv", "vendor", "Library",
    "__pycache__", ".build", "DerivedData", "target", "dist",
})

MAX_DEPTH = 3


def roots() -> list[Path]:
    raw = os.environ.get("ASSISTANT_DEV_ROOTS", "")
    candidates = [p for p in raw.split(":") if p.strip()] or list(CANDIDATE_ROOTS)

    seen: list[Path] = []
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if not path.is_dir():
            continue
        resolved = path.resolve()
        # ~/dev 와 ~/Dev 가 같은 폴더일 수 있다 (대소문자 무시 파일시스템)
        if resolved not in seen:
            seen.append(resolved)
    return seen


def is_repo(path: Path) -> bool:
    return (path / ".git").exists()


def find_repos(search_roots: list[Path] | None = None, *, limit: int = 60) -> list[Path]:
    """얕은 너비 탐색으로 git 레포를 찾는다.

    레포 안으로는 더 들어가지 않는다 — 서브모듈까지 개별 레포로
    올리면 목록이 쓸모없어진다.
    """
    found: list[Path] = []
    for root in search_roots if search_roots is not None else roots():
        frontier = [(root, 0)]
        while frontier and len(found) < limit:
            current, depth = frontier.pop(0)
            if is_repo(current):
                found.append(current)
                continue  # 레포 내부는 훑지 않는다
            if depth >= MAX_DEPTH:
                continue
            try:
                children = sorted(p for p in current.iterdir() if p.is_dir())
            except (PermissionError, OSError):
                continue
            for child in children:
                if child.name.startswith(".") or child.name in SKIP_DIRS:
                    continue
                frontier.append((child, depth + 1))
    return found


def resolve_repo(name: str) -> Path | None:
    """이름으로 레포를 찾는다. 경로를 통째로 줘도 된다."""
    direct = Path(name).expanduser()
    if direct.is_dir() and is_repo(direct):
        return direct.resolve()

    target = name.strip().lower()
    matches = [r for r in find_repos() if r.name.lower() == target]
    if matches:
        return matches[0]

    partial = [r for r in find_repos() if target in r.name.lower()]
    return partial[0] if len(partial) == 1 else None
