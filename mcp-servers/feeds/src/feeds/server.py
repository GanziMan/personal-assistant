"""피드 MCP 서버."""

from __future__ import annotations

import asyncio
import sys

import httpx
from mcp.server.mcpserver import MCPServer

from .parse import parse, recent
from .store import FeedStore

mcp = MCPServer("feeds")
_store = FeedStore()

TIMEOUT = 15.0
HEADERS = {"User-Agent": "personal-assistant/0.1 (+rss reader)"}


@mcp.tool()
def list_feeds() -> str:
    """구독 중인 피드 목록."""
    feeds = _store.load()
    if not feeds:
        return "구독 중인 피드가 없습니다. add_feed 로 추가하세요."
    return "\n".join(f"- {f.name}  {f.url}" for f in feeds)


@mcp.tool()
def add_feed(url: str, name: str = "") -> str:
    """RSS/Atom 피드를 구독한다."""
    if not url.startswith(("http://", "https://")):
        return "http(s) URL 이어야 합니다."
    if _store.add(name, url):
        return f"추가했습니다: {name or url}"
    return "이미 구독 중입니다."


@mcp.tool()
def remove_feed(name_or_url: str) -> str:
    """구독을 해지한다."""
    return "해지했습니다." if _store.remove(name_or_url) else "찾을 수 없습니다."


async def _fetch(client: httpx.AsyncClient, feed) -> tuple[str, list]:  # noqa: ANN001
    try:
        response = await client.get(feed.url, headers=HEADERS, follow_redirects=True)
        response.raise_for_status()
        return feed.name, parse(response.content)
    except Exception:
        # 피드 하나가 죽어도 나머지는 보여준다
        return feed.name, []


@mcp.tool()
async def fetch_recent(hours: int = 24, per_feed: int = 5) -> str:
    """구독 피드에서 최근 항목을 모은다."""
    feeds = _store.load()
    if not feeds:
        return "구독 중인 피드가 없습니다."

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        results = list(await asyncio.gather(*(_fetch(client, f) for f in feeds)))

    blocks = []
    failed = []
    for name, items in results:
        fresh = recent(items, hours=hours)[:per_feed]
        if not items:
            failed.append(name)
            continue
        if not fresh:
            continue
        body = "\n".join(i.describe() for i in fresh)
        blocks.append(f"## {name}\n{body}")

    if not blocks:
        note = f" (실패: {', '.join(failed)})" if failed else ""
        return f"최근 {hours}시간 안에 새 항목이 없습니다{note}."

    tail = f"\n\n(불러오지 못함: {', '.join(failed)})" if failed else ""
    return "\n\n".join(blocks) + tail


def main() -> int:
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
