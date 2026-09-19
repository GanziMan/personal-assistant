import time
from pathlib import Path

import pytest

from docsearch.index import DocIndex


@pytest.fixture
def index(tmp_path: Path) -> DocIndex:
    idx = DocIndex(tmp_path / "idx.db")
    yield idx
    idx.close()


def _file(tmp_path: Path, name: str = "a.md", body: str = "내용") -> Path:
    path = tmp_path / name
    path.write_text(body)
    return path


def test_new_file_needs_index(index: DocIndex, tmp_path: Path):
    assert index.needs_index(_file(tmp_path))


def test_unchanged_file_is_skipped(index: DocIndex, tmp_path: Path):
    path = _file(tmp_path)
    index.put(path, ["조각"], [None])
    assert not index.needs_index(path)


def test_changed_size_triggers_reindex(index: DocIndex, tmp_path: Path):
    path = _file(tmp_path)
    index.put(path, ["조각"], [None])
    path.write_text("훨씬 더 긴 내용으로 바뀌었습니다")
    assert index.needs_index(path)


def test_missing_file_is_not_indexed(index: DocIndex, tmp_path: Path):
    assert not index.needs_index(tmp_path / "nope.md")


def test_reindex_replaces_old_chunks(index: DocIndex, tmp_path: Path):
    path = _file(tmp_path)
    index.put(path, ["옛날 조각", "또 하나"], [None, None])
    index.put(path, ["새 조각"], [None])
    _, chunks, _ = index.stats()
    assert chunks == 1


def test_prune_removes_deleted_files(index: DocIndex, tmp_path: Path):
    path = _file(tmp_path)
    index.put(path, ["조각"], [None])
    path.unlink()
    assert index.prune_missing() == 1
    assert index.stats()[0] == 0


def test_keyword_search_finds_chunk(index: DocIndex, tmp_path: Path):
    path = _file(tmp_path)
    index.put(path, ["정산 관련 정리 문서"], [None])
    ids = index.keyword("정산")
    assert ids and index.fetch(ids)[0].text.startswith("정산")


def test_keyword_search_ignores_fts_operators(index: DocIndex, tmp_path: Path):
    index.put(_file(tmp_path), ["평범한 내용"], [None])
    index.keyword('NEAR OR "unclosed')  # 예외가 나면 안 된다


def test_vectors_skips_null(index: DocIndex, tmp_path: Path):
    index.put(_file(tmp_path), ["a", "b"], [None, b"\x00" * 8])
    assert len(index.vectors()) == 1


def test_stats_counts_documents_and_chunks(index: DocIndex, tmp_path: Path):
    index.put(_file(tmp_path, "a.md"), ["1", "2"], [None, None])
    index.put(_file(tmp_path, "b.md"), ["3"], [None])
    docs, chunks, last = index.stats()
    assert (docs, chunks) == (2, 3)
    assert last > time.time() - 60


def test_empty_index_stats(index: DocIndex):
    assert index.stats()[:2] == (0, 0)
