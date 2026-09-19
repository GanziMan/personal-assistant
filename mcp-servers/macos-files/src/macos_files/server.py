"""파일 MCP 서버.

조회·검색·요약은 자유롭게, 이동·이름변경은 확인 게이트를 거친다.
삭제 도구는 아예 노출하지 않는다 — 되돌릴 수 없는 것 중에서도
파일 삭제는 실수의 대가가 가장 크고, 정리는 '옮기기' 로 충분하다.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import inspect as ins
from .paths import Boundary, PathDenied, from_env

mcp = FastMCP("macos-files")
_boundary: Boundary | None = None


def boundary() -> Boundary:
    global _boundary
    if _boundary is None:
        _boundary = from_env()
    return _boundary


def _denied(exc: PathDenied) -> str:
    return f"거부됨: {exc}"


@mcp.tool()
def allowed_folders() -> str:
    """비서가 손댈 수 있는 폴더 목록."""
    return boundary().describe()


@mcp.tool()
def list_folder(folder: str, limit: int = 40, sort: str = "recent") -> str:
    """폴더 내용을 본다. sort: recent | size | name"""
    try:
        root = boundary().resolve(folder)
    except PathDenied as exc:
        return _denied(exc)
    if not root.is_dir():
        return f"폴더가 아닙니다: {folder}"

    try:
        items = ins.entries(root.iterdir())
    except PermissionError:
        return f"읽을 수 없습니다 (권한): {folder}"

    key = {
        "recent": lambda e: -e.mtime,
        "size": lambda e: -e.size,
        "name": lambda e: e.path.name.lower(),
    }.get(sort, lambda e: -e.mtime)
    items.sort(key=key)

    if not items:
        return f"{folder}: 비어 있습니다."
    shown = items[:limit]
    lines = "\n".join(e.describe() for e in shown)
    more = f"\n… 외 {len(items) - len(shown)}개" if len(items) > len(shown) else ""
    return f"{root} ({len(items)}개)\n{lines}{more}"


@mcp.tool()
def search_files(query: str, folder: str = "~/Downloads", days: int = 0, limit: int = 30) -> str:
    """파일 이름으로 찾는다. days>0 이면 그 기간 안에 수정된 것만."""
    try:
        root = boundary().resolve(folder)
    except PathDenied as exc:
        return _denied(exc)

    cutoff = time.time() - days * 86400 if days > 0 else 0.0
    q = query.lower()
    hits: list[Path] = []
    for path in ins.walk(root):
        if q not in path.name.lower():
            continue
        try:
            if cutoff and path.stat().st_mtime < cutoff:
                continue
        except OSError:
            continue
        hits.append(path)
        if len(hits) >= limit:
            break

    if not hits:
        window = f" (최근 {days}일)" if days else ""
        return f"'{query}' 와 맞는 파일이 없습니다{window}."
    return "\n".join(e.describe(base=root) for e in ins.entries(hits))


@mcp.tool()
def read_text(path: str, max_chars: int = 8000) -> str:
    """텍스트 파일을 읽는다. 긴 파일은 앞부분만."""
    try:
        target = boundary().resolve(path)
    except PathDenied as exc:
        return _denied(exc)
    if not target.is_file():
        return f"파일이 아닙니다: {path}"
    if not ins.is_probably_text(target):
        return f"텍스트 파일이 아닙니다: {target.suffix or '(확장자 없음)'}"

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"읽을 수 없습니다: {exc}"

    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n… ({len(text) - max_chars}자 더 있음)"


@mcp.tool()
def find_duplicates(folder: str = "~/Downloads") -> str:
    """같은 내용으로 보이는 파일을 묶어서 보여준다. 지우지는 않는다."""
    try:
        root = boundary().resolve(folder)
    except PathDenied as exc:
        return _denied(exc)

    groups = ins.group_duplicates(ins.walk(root, max_entries=1000))
    if not groups:
        return "중복으로 보이는 파일이 없습니다."

    blocks = []
    wasted = 0
    for paths in sorted(groups.values(), key=lambda g: -g[0].stat().st_size)[:15]:
        size = paths[0].stat().st_size
        wasted += size * (len(paths) - 1)
        names = "\n".join(f"  {p.relative_to(root)}" for p in paths)
        blocks.append(f"{ins.human_size(size)} × {len(paths)}개\n{names}")

    return (
        f"중복 후보 {len(groups)}묶음, 약 {ins.human_size(wasted)} 절약 가능\n\n"
        + "\n\n".join(blocks)
        + "\n\n(삭제는 하지 않습니다. 확인 후 직접 지우세요.)"
    )


@mcp.tool()
def suggest_cleanup(folder: str = "~/Downloads", days: int = 90) -> str:
    """오래된 파일을 확장자별로 묶어 정리안을 제안한다. 실행하지 않는다."""
    try:
        root = boundary().resolve(folder)
    except PathDenied as exc:
        return _denied(exc)

    cutoff = time.time() - days * 86400
    buckets: dict[str, list[Path]] = {}
    for path in ins.walk(root, max_entries=1500):
        try:
            if path.stat().st_mtime >= cutoff:
                continue
        except OSError:
            continue
        buckets.setdefault(path.suffix.lower() or "(확장자 없음)", []).append(path)

    if not buckets:
        return f"{days}일 이상 손대지 않은 파일이 없습니다."

    lines = [
        f"{suffix}  {len(paths)}개  "
        f"({ins.human_size(sum(p.stat().st_size for p in paths))})"
        for suffix, paths in sorted(buckets.items(), key=lambda kv: -len(kv[1]))
    ]
    return (
        f"{days}일 이상 손대지 않은 파일\n" + "\n".join(lines[:12]) +
        "\n\n제안: 확장자별 하위 폴더로 옮기기. 진행하려면 말씀하세요."
    )


@mcp.tool()
def move_file(source: str, destination: str) -> str:
    """파일을 옮긴다. 되돌릴 수 없으므로 데몬의 확인 게이트를 거친다."""
    try:
        src = boundary().resolve(source)
        dst = boundary().resolve(destination)
    except PathDenied as exc:
        return _denied(exc)

    if not src.exists():
        return f"없는 파일입니다: {source}"
    if dst.exists():
        return f"이미 있습니다. 덮어쓰지 않습니다: {destination}"

    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    return f"옮겼습니다: {src.name} → {dst}"


def main() -> int:
    if sys.platform != "darwin":
        print("이 서버는 macOS 전용입니다.", file=sys.stderr)
        return 1
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
