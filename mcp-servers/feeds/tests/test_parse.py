from datetime import datetime, timezone

from feeds.parse import parse, recent

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>테스트 피드</title>
  <item>
    <title>첫 글</title>
    <link>https://example.com/1</link>
    <pubDate>Sat, 19 Sep 2026 10:00:00 +0000</pubDate>
    <description>요약입니다</description>
  </item>
  <item>
    <title>둘째 글</title>
    <link>https://example.com/2</link>
    <pubDate>Mon, 01 Jan 2024 10:00:00 +0000</pubDate>
  </item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>아톰 피드</title>
  <entry>
    <title>아톰 글</title>
    <link rel="alternate" href="https://example.com/a"/>
    <updated>2026-09-19T10:00:00Z</updated>
    <summary>아톰 요약</summary>
  </entry>
</feed>"""


def test_rss_parsed():
    items = parse(RSS)
    assert [i.title for i in items] == ["첫 글", "둘째 글"]
    assert items[0].link == "https://example.com/1"
    assert items[0].published.year == 2026


def test_atom_parsed_with_namespace():
    items = parse(ATOM)
    assert len(items) == 1
    assert items[0].link == "https://example.com/a", "Atom 은 href 속성에 링크가 있다"
    assert items[0].published.year == 2026


def test_broken_xml_returns_empty():
    assert parse("<rss><item><title>안 닫힘") == []


def test_empty_input_returns_empty():
    assert parse("") == []


def test_recent_filters_old_items():
    items = parse(RSS)
    now = datetime(2026, 9, 19, 12, tzinfo=timezone.utc)
    # 2024년 항목은 걸러져야 한다
    fresh = [i for i in recent(items, hours=24) if i.published and i.published.year == 2024]
    assert fresh == []


def test_items_without_date_are_kept():
    """시각 없는 피드가 조용히 사라지면 안 된다."""
    xml = "<rss><channel><item><title>시각 없음</title></item></channel></rss>"
    assert len(recent(parse(xml), hours=1)) == 1


def test_items_without_title_are_skipped():
    xml = "<rss><channel><item><link>https://x</link></item></channel></rss>"
    assert parse(xml) == []
