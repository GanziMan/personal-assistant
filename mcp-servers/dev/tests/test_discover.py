from pathlib import Path

from dev_tools import discover


def _repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").mkdir()
    return path


def test_finds_repos_at_depth(tmp_path: Path):
    _repo(tmp_path / "a")
    _repo(tmp_path / "team" / "b")
    names = {p.name for p in discover.find_repos([tmp_path])}
    assert names == {"a", "b"}


def test_does_not_descend_into_a_repo(tmp_path: Path):
    """서브모듈까지 개별 레포로 올리면 목록이 쓸모없어진다."""
    outer = _repo(tmp_path / "outer")
    _repo(outer / "vendored")
    assert {p.name for p in discover.find_repos([tmp_path])} == {"outer"}


def test_skips_heavy_directories(tmp_path: Path):
    _repo(tmp_path / "node_modules" / "pkg")
    _repo(tmp_path / "real")
    assert {p.name for p in discover.find_repos([tmp_path])} == {"real"}


def test_skips_hidden_directories(tmp_path: Path):
    _repo(tmp_path / ".cache" / "x")
    assert discover.find_repos([tmp_path]) == []


def test_respects_depth_limit(tmp_path: Path):
    deep = tmp_path / "a" / "b" / "c" / "d" / "e"
    _repo(deep)
    assert discover.find_repos([tmp_path]) == []


def test_respects_limit(tmp_path: Path):
    for i in range(10):
        _repo(tmp_path / f"r{i}")
    assert len(discover.find_repos([tmp_path], limit=3)) == 3


def test_roots_skip_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ASSISTANT_DEV_ROOTS", f"{tmp_path}:{tmp_path / 'nope'}")
    assert discover.roots() == [tmp_path.resolve()]


def test_roots_deduplicate(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ASSISTANT_DEV_ROOTS", f"{tmp_path}:{tmp_path}")
    assert len(discover.roots()) == 1
