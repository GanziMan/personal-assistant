from pathlib import Path

from feeds.store import FeedStore


def test_add_and_load(tmp_path: Path):
    s = FeedStore(tmp_path / "f.json")
    assert s.add("뉴스", "https://example.com/rss")
    assert [f.name for f in s.load()] == ["뉴스"]


def test_duplicate_url_rejected(tmp_path: Path):
    s = FeedStore(tmp_path / "f.json")
    s.add("뉴스", "https://example.com/rss")
    assert not s.add("다른 이름", "https://example.com/rss")
    assert len(s.load()) == 1


def test_remove_by_name_or_url(tmp_path: Path):
    s = FeedStore(tmp_path / "f.json")
    s.add("뉴스", "https://a.com/rss")
    s.add("블로그", "https://b.com/rss")
    assert s.remove("뉴스")
    assert s.remove("https://b.com/rss")
    assert s.load() == []


def test_corrupt_file_does_not_crash(tmp_path: Path):
    path = tmp_path / "f.json"
    path.write_text("{{ 깨진 json")
    assert FeedStore(path).load() == []


def test_missing_file_is_empty(tmp_path: Path):
    assert FeedStore(tmp_path / "nope.json").load() == []
