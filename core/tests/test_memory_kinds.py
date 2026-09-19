import time
from pathlib import Path

import pytest

from assistant.memory.models import Episode
from assistant.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    s = MemoryStore(tmp_path / "m.db")
    yield s
    s.close()


def test_kind_filter_excludes_other_kinds(store: MemoryStore):
    store.add_episode(Episode(title="로그", kind="worklog"))
    store.add_episode(Episode(title="브리핑", kind="briefing"))
    assert [h.title for h in store.episodes_by_kind("worklog")] == ["로그"]


def test_since_filters_old_entries(store: MemoryStore):
    now = time.time()
    store.add_episode(Episode(title="옛날", kind="worklog", ts=now - 100 * 86400))
    store.add_episode(Episode(title="최근", kind="worklog", ts=now - 86400))
    recent = store.episodes_by_kind("worklog", since=now - 7 * 86400)
    assert [h.title for h in recent] == ["최근"]


def test_newest_first(store: MemoryStore):
    now = time.time()
    store.add_episode(Episode(title="어제", kind="worklog", ts=now - 86400))
    store.add_episode(Episode(title="오늘", kind="worklog", ts=now))
    assert [h.title for h in store.episodes_by_kind("worklog")] == ["오늘", "어제"]


def test_archived_entries_are_hidden(store: MemoryStore):
    store.add_episode(Episode(title="옛날", kind="worklog", ts=time.time() - 300 * 86400))
    store.archive_stale(older_than_days=90)
    assert store.episodes_by_kind("worklog") == []


def test_limit_is_respected(store: MemoryStore):
    for i in range(10):
        store.add_episode(Episode(title=f"d{i}", kind="worklog"))
    assert len(store.episodes_by_kind("worklog", limit=3)) == 3


def test_missing_kind_returns_empty(store: MemoryStore):
    assert store.episodes_by_kind("nope") == []
