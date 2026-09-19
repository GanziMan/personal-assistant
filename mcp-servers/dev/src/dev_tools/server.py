"""개발 보조 MCP 서버. 읽기 전용."""

from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from . import discover
from .git import GitError, run, status

mcp = MCPServer("dev")


def _repo_or_error(name: str) -> Path | str:
    repo = discover.resolve_repo(name)
    if repo is None:
        return f"'{name}' 레포를 찾지 못했습니다. list_repos 로 목록을 보세요."
    return repo


@mcp.tool()
def list_repos() -> str:
    """찾은 git 레포 목록."""
    repos = discover.find_repos()
    if not repos:
        roots = ", ".join(str(r) for r in discover.roots()) or "(없음)"
        return f"git 레포를 찾지 못했습니다.\n탐색한 곳: {roots}"
    return "\n".join(f"- {r.name}  ({r.parent})" for r in repos)


@mcp.tool()
def repo_status(name: str) -> str:
    """레포의 브랜치와 변경 상태."""
    repo = _repo_or_error(name)
    if isinstance(repo, str):
        return repo
    try:
        return f"{repo.name}  {status(repo).describe()}"
    except GitError as exc:
        return f"읽을 수 없습니다: {exc}"


@mcp.tool()
def all_status() -> str:
    """찾은 모든 레포의 상태를 한눈에. 손 놓은 작업을 찾을 때 쓴다."""
    repos = discover.find_repos(limit=30)
    if not repos:
        return "레포를 찾지 못했습니다."

    lines = []
    for repo in repos:
        try:
            state = status(repo)
        except GitError:
            continue
        if state.clean and not state.ahead and not state.behind:
            continue  # 깨끗한 레포는 보고할 게 없다
        lines.append(f"{repo.name:24} {state.describe()}")

    return "\n".join(lines) if lines else "모든 레포가 깨끗합니다."


@mcp.tool()
def recent_commits(name: str, days: int = 7, limit: int = 20) -> str:
    """최근 커밋 목록."""
    repo = _repo_or_error(name)
    if isinstance(repo, str):
        return repo
    try:
        out = run(
            repo, "log", f"--since={days}.days", f"-{limit}",
            "--pretty=format:%h  %ad  %s", "--date=short",
        )
    except GitError as exc:
        return f"읽을 수 없습니다: {exc}"
    return out.strip() or f"최근 {days}일간 커밋이 없습니다."


@mcp.tool()
def changed_files(name: str) -> str:
    """아직 커밋하지 않은 변경 파일 목록."""
    repo = _repo_or_error(name)
    if isinstance(repo, str):
        return repo
    try:
        out = run(repo, "status", "--porcelain=v1")
    except GitError as exc:
        return f"읽을 수 없습니다: {exc}"
    return out.strip() or "변경 사항이 없습니다."


@mcp.tool()
def search_code(query: str, name: str, limit: int = 30) -> str:
    """레포 안에서 코드를 검색한다 (git grep, 추적 중인 파일만)."""
    repo = _repo_or_error(name)
    if isinstance(repo, str):
        return repo
    try:
        out = run(repo, "grep", "-n", "-I", "--max-count=3", "-e", query)
    except GitError:
        return f"'{query}' 를 찾지 못했습니다."

    lines = out.splitlines()[:limit]
    return "\n".join(lines) if lines else f"'{query}' 를 찾지 못했습니다."


def main() -> int:
    if sys.platform != "darwin":
        print("이 서버는 macOS 전용입니다.", file=sys.stderr)
        return 1
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
