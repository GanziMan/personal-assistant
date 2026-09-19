import time
from pathlib import Path

import pytest

from assistant.memory.models import Episode, Fact
from assistant.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    s = MemoryStore(tmp_path / "m.db")
    yield s
    s.close()


def test_episode_roundtrip(store: MemoryStore):
    ep = Episode(title="포트 충돌 해결", body="5432 를 쓰는 프로세스를 죽였다", kind="note")
    assert store.add_episode(ep) > 0
    assert store.search("포트 충돌")[0].title == "포트 충돌 해결"


def test_keyword_search_finds_body_terms(store: MemoryStore):
    store.add_episode(Episode(title="회의", body="사내 인증 서버 마이그레이션 논의"))
    assert store.search("마이그레이션"), "본문도 색인돼야 한다"


def test_search_ignores_fts_operators(store: MemoryStore):
    store.add_episode(Episode(title="NEAR 테스트", body="본문"))
    # 사용자 문장이 FTS 연산자로 해석되면 예외가 난다
    store.search('NEAR OR "unclosed')


def test_archived_episodes_drop_out(store: MemoryStore):
    store.add_episode(Episode(title="옛날 일", ts=time.time() - 200 * 86400, importance=0.1))
    assert store.archive_stale(older_than_days=90) == 1
    assert not store.search("옛날")


def test_recently_recalled_memory_survives(store: MemoryStore):
    """오래됐어도 최근에 불려나온 기억은 살아있는 기억이다."""
    store.add_episode(Episode(title="옛날이지만 쓰는 것", ts=time.time() - 200 * 86400))
    store.search("옛날이지만")  # 방금 참조됨
    assert store.archive_stale(older_than_days=90) == 0


def test_important_episodes_survive_archiving(store: MemoryStore):
    store.add_episode(
        Episode(title="중요한 결정", ts=time.time() - 200 * 86400, importance=0.9)
    )
    assert store.archive_stale(older_than_days=90) == 0
    assert store.search("중요한")


def test_search_marks_access(store: MemoryStore):
    store.add_episode(Episode(title="추적 대상"))
    store.search("추적")
    row = store.db.execute("SELECT access_count FROM episodes").fetchone()
    assert row["access_count"] == 1


def test_fact_supersede_keeps_history(store: MemoryStore):
    old = Fact(subject="선호 에디터", body="VS Code", confidence=0.5)
    old_id = store.add_fact(old)
    new_id = store.supersede_fact(old_id, Fact(subject="선호 에디터", body="Neovim", confidence=0.8))

    live = store.live_facts("선호 에디터")
    assert [f.body for f in live] == ["Neovim"]
    assert new_id != old_id
    assert store.db.execute(
        "SELECT superseded_by FROM facts WHERE id = ?", (old_id,)
    ).fetchone()["superseded_by"] == new_id


def test_vector_search_ranks_by_similarity(store: MemoryStore):
    a = store.add_episode(Episode(title="고양이"))
    b = store.add_episode(Episode(title="자동차"))
    store.set_embedding("episode", a, "m", [1.0, 0.0])
    store.set_embedding("episode", b, "m", [0.0, 1.0])
    assert store.vector_search([0.9, 0.1])[0] == a


def test_vector_search_skips_dimension_mismatch(store: MemoryStore):
    a = store.add_episode(Episode(title="차원 다름"))
    store.set_embedding("episode", a, "m", [1.0, 0.0, 0.0])
    assert store.vector_search([1.0, 0.0]) == []
