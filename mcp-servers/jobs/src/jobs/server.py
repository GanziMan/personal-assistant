"""채용공고 MCP 서버.

사람인 공식 API 만 쓴다. 크롤링하지 않는다 (ADR-039).
"""

from __future__ import annotations

import sys

from mcp.server.mcpserver import MCPServer

from . import ats
from .client import JobsError, search
from .config import CompanyEntry, JobsConfig, Search
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


# ---- 관심 회사 (ATS 직접 조회) --------------------------------------


@mcp.tool()
async def check_company(slug: str) -> str:
    """회사가 어느 채용 시스템을 쓰는지 찾는다.

    slug 는 회사 채용 페이지 URL 에 들어가는 이름이다.
    예: boards.greenhouse.io/toss 면 slug 는 toss.
    """
    found = await ats.detect(slug)
    if not found:
        return (
            f"'{slug}' 로는 Greenhouse·Lever·Ashby 어디에서도 공고를 찾지 못했습니다.\n"
            "회사 채용 페이지 주소를 확인해 보세요 — URL 마지막 부분이 slug 입니다."
        )
    listed = ", ".join(found)
    return f"'{slug}' 을(를) {listed} 에서 찾았습니다. add_company 로 등록하세요."


@mcp.tool()
async def add_company(slug: str, label: str = "", keywords: str = "") -> str:
    """관심 회사를 등록한다. ATS 는 자동으로 찾는다.

    keywords 를 주면 그 말이 들어간 공고만 본다 (쉼표로 구분).
    """
    config = JobsConfig.load()
    if config.find_company(slug):
        return f"'{slug}' 은 이미 등록돼 있습니다."

    found = await ats.detect(slug)
    if not found:
        return f"'{slug}' 에서 공고를 찾지 못했습니다. check_company 로 먼저 확인하세요."

    config.companies.append(
        CompanyEntry(
            slug=slug,
            ats=found[0],
            label=label,
            keywords=[k.strip() for k in keywords.split(",") if k.strip()],
        )
    )
    config.save()
    return f"'{label or slug}' 을(를) {found[0]} 로 등록했습니다."


@mcp.tool()
def list_companies() -> str:
    """등록한 관심 회사들."""
    config = JobsConfig.load()
    if not config.companies:
        return "등록된 회사가 없습니다. check_company 로 확인한 뒤 add_company 로 추가하세요."
    return "\n".join(
        f"- {c.label or c.slug} ({c.ats})"
        + (f" · 키워드 {', '.join(c.keywords)}" if c.keywords else "")
        for c in config.companies
    )


@mcp.tool()
def remove_company(slug: str) -> str:
    """관심 회사를 지운다."""
    config = JobsConfig.load()
    before = len(config.companies)
    key = slug.strip().lower()
    config.companies = [
        c for c in config.companies if c.slug.lower() != key and c.label.lower() != key
    ]
    if len(config.companies) == before:
        return f"'{slug}' 을 찾지 못했습니다."
    config.save()
    return f"'{slug}' 을 지웠습니다."


@mcp.tool()
async def company_jobs(only_new: bool = False, limit: int = 30) -> str:
    """등록한 회사들의 공고를 가져온다. 사람인 승인 없이도 된다."""
    config = JobsConfig.load()
    if not config.companies:
        return "등록된 회사가 없습니다."

    store = SeenStore()
    blocks: list[str] = []
    fresh: list[str] = []

    for entry in config.companies:
        company = ats.Company(slug=entry.slug, ats=entry.ats, label=entry.label)
        jobs = [j for j in await ats.fetch(company) if ats.matches(j, entry.keywords)]
        if only_new:
            jobs = [j for j in jobs if store.is_new(j.id)]
        if not jobs:
            continue

        fresh += [j.id for j in jobs]
        shown = jobs[:limit]
        listed = "\n\n".join(j.describe() for j in shown)
        more = f"\n\n… 외 {len(jobs) - len(shown)}건" if len(jobs) > len(shown) else ""
        blocks.append(f"■ {company.name} ({len(jobs)}건)\n\n{listed}{more}")

    if not blocks:
        return "새 공고가 없습니다." if only_new else "공고가 없습니다."

    if only_new:
        store.mark(fresh)
    return "\n\n".join(blocks)


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
