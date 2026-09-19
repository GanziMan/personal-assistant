"""파일 조회와 요약. 플랫폼 독립이라 테스트가 붙는다."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

TEXT_SUFFIXES = frozenset({
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".log", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".go", ".rs", ".java", ".kt", ".swift", ".sh", ".sql", ".html", ".css",
})

# 해시를 통째로 뜨면 큰 파일에서 느리다. 앞뒤 조각 + 크기로 충분히 가른다.
SAMPLE_BYTES = 65_536


@dataclass(slots=True)
class Entry:
    path: Path
    size: int
    mtime: float
    is_dir: bool

    def describe(self, *, base: Path | None = None) -> str:
        name = str(self.path.relative_to(base)) if base else self.path.name
        if self.is_dir:
            return f"📁 {name}/"
        age = time.time() - self.mtime
        when = (
            f"{int(age // 86400)}일 전" if age >= 86400
            else f"{int(age // 3600)}시간 전" if age >= 3600
            else "방금"
        )
        return f"{name}  ({human_size(self.size)}, {when})"


def human_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024  # type: ignore[assignment]
    return f"{size}B"


def walk(root: Path, *, max_entries: int = 2000) -> Iterator[Path]:
    """숨김 파일과 무거운 디렉터리를 건너뛰며 훑는다."""
    count = 0
    stack = [root]
    while stack and count < max_entries:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except (PermissionError, OSError):
            continue
        for child in children:
            if child.name.startswith("."):
                continue
            if child.is_dir():
                if child.name in {"node_modules", "__pycache__", ".venv", "Library"}:
                    continue
                stack.append(child)
            else:
                count += 1
                yield child
                if count >= max_entries:
                    return


def entries(paths: Iterable[Path], *, base: Path | None = None) -> list[Entry]:
    out: list[Entry] = []
    for p in paths:
        try:
            st = p.stat()
        except OSError:
            continue
        out.append(Entry(p, st.st_size, st.st_mtime, p.is_dir()))
    return out


def is_probably_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def content_key(path: Path) -> str:
    """중복 판정용 키. 크기 + 앞뒤 조각 해시.

    전체 해시를 뜨지 않는 이유는 속도다. 다운로드 폴더에 4GB 영상이
    몇 개 있으면 전수 해시는 분 단위로 걸린다.
    """
    st = path.stat()
    h = hashlib.blake2b(digest_size=16)
    h.update(str(st.st_size).encode())
    with path.open("rb") as f:
        h.update(f.read(SAMPLE_BYTES))
        if st.st_size > SAMPLE_BYTES * 2:
            f.seek(-SAMPLE_BYTES, 2)
            h.update(f.read(SAMPLE_BYTES))
    return h.hexdigest()


def group_duplicates(paths: Iterable[Path]) -> dict[str, list[Path]]:
    """같은 내용으로 보이는 파일들을 묶는다. 2개 이상인 것만."""
    groups: dict[str, list[Path]] = {}
    for p in paths:
        try:
            if p.stat().st_size == 0:
                continue  # 빈 파일끼리 묶어봐야 의미 없다
            groups.setdefault(content_key(p), []).append(p)
        except OSError:
            continue
    return {k: v for k, v in groups.items() if len(v) > 1}
