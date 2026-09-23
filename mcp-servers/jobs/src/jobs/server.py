"""채용공고 MCP 서버.

사람인 공식 API 만 쓴다. 크롤링하지 않는다 (ADR-039).
"""

from __future__ import annotations

import sys

from mcp.server.mcpserver import MCPServer

from .client import JobsError, search
from .config import JobsConfig, Search
from .model import Job
from .store import SeenStore

mcp = MCPServer("jobs")

ATTRIBUTION = "출처: 사람인 (Powered by 취업 사람인)"


@mcp.tool()
def list_searches() -> str:
    """저장해둔 검색 조건들."""
    config = JobsConfig.load()
    if not config.searches:
        return (
            "저장된 검색이 없습니다. add_search 로 추가하세요.\n"
            "예: name='백엔드', keywords='백엔드 Python', loc_mcd='101', job_mid_cd='2'"
        )
    lines = []
    for s in config.searches:
        bits = [b for b in (s.keywords, s.loc_mcd and f"지역 {s.loc_mcd}") if b]
        lines.append(f"- {s.name}: {', '.join(bits) or '조건 없음'}")
    return "\n".join(lines)


@mcp.tool()
def add_search(
    name: str,
    keywords: str = "",
    loc_mcd: str = "",
    job_mid_cd: str = "",
    exclude_agency: bool = True,
) -> str:
    """검색 조건을 저장한다.

    loc_mcd: 지역 대분류 (서울 101, 경기 102, 부산 106 …)
    job_mid_cd: 직무 대분류 (IT개발·데이터 2)
    """
    config = JobsConfig.load()
    if config.find(name):
        return f"'{name}' 은 이미 있습니다. remove_search 후 다시 추가하세요."

    config.searches.append(
        Search(
            name=name, keywords=keywords, loc_mcd=loc_mcd,
            job_mid_cd=job_mid_cd, exclude_agency=exclude_agency,
        )
    )
    config.save()
    return f"'{name}' 검색을 저장했습니다."


@mcp.tool()
def remove_search(name: str) -> str:
    """저장한 검색을 지운다."""
    config = JobsConfig.load()
    before = len(config.searches)
    config.searches = [s for s in config.searches if s.name != name]
    if len(config.searches) == before:
        return f"'{name}' 을 찾지 못했습니다."
    config.save()
    return f"'{name}' 을 지웠습니다."


@mcp.tool()
async def find_jobs(name: str = "", only_new: bool = False, limit: int = 20) -> str:
    """공고를 가져온다.

    name 을 비우면 저장된 모든 검색을 돈다.
    only_new=True 면 아직 안 본 공고만 보여준다.
    """
    config = JobsConfig.load()
    targets = [config.find(name)] if name else config.searches
    targets = [t for t in targets if t is not None]

    if not targets:
        return "검색 조건이 없습니다. add_search 로 먼저 등록하세요."

    store = SeenStore()
    blocks: list[str] = []
    fresh_ids: list[str] = []

    for target in targets:
        try:
            raw = await search(target.to_params())
        except JobsError as exc:
            blocks.append(f"[{target.name}] {exc}")
            continue

        jobs = [j for j in (Job.parse(r) for r in raw) if j is not None]
        if only_new:
            jobs = [j for j in jobs if store.is_new(j.id)]

        if not jobs:
            continue

        fresh_ids += [j.id for j in jobs]
        shown = jobs[:limit]
        listed = "\n\n".join(j.describe() for j in shown)
        more = f"\n\n… 외 {len(jobs) - len(shown)}건" if len(jobs) > len(shown) else ""
        blocks.append(f"■ {target.name} ({len(jobs)}건)\n\n{listed}{more}")

    if not blocks:
        return "새로 올라온 공고가 없습니다." if only_new else "조건에 맞는 공고가 없습니다."

    if only_new:
        store.mark(fresh_ids)

    return "\n\n".join(blocks) + f"\n\n{ATTRIBUTION}"


@mcp.tool()
def forget_seen() -> str:
    """본 공고 기록을 지운다. 다시 처음부터 보고 싶을 때."""
    return f"기록 {SeenStore().forget_all()}건을 지웠습니다."


def main() -> int:
    if sys.platform != "darwin":
        print("이 서버는 macOS 전용입니다 (키체인).", file=sys.stderr)
        return 1
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
