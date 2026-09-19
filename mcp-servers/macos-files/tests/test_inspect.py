from pathlib import Path

from macos_files import inspect as ins


def test_human_size_scales():
    assert ins.human_size(512) == "512B"
    assert ins.human_size(2048).endswith("KB")
    assert ins.human_size(5 * 1024 * 1024).endswith("MB")


def test_walk_skips_hidden_and_heavy_dirs(tmp_path: Path):
    (tmp_path / "keep.txt").write_text("a")
    (tmp_path / ".hidden.txt").write_text("b")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("c")

    names = {p.name for p in ins.walk(tmp_path)}
    assert names == {"keep.txt"}


def test_walk_respects_max_entries(tmp_path: Path):
    for i in range(20):
        (tmp_path / f"f{i}.txt").write_text("x")
    assert len(list(ins.walk(tmp_path, max_entries=5))) == 5


def test_duplicates_are_grouped(tmp_path: Path):
    content = "같은 내용" * 100
    for name in ("a.txt", "b.txt"):
        (tmp_path / name).write_text(content)
    (tmp_path / "c.txt").write_text("다른 내용")

    groups = ins.group_duplicates(ins.walk(tmp_path))
    assert len(groups) == 1
    assert {p.name for p in next(iter(groups.values()))} == {"a.txt", "b.txt"}


def test_empty_files_are_not_duplicates(tmp_path: Path):
    """빈 파일끼리 묶어봐야 사용자에게 줄 정보가 없다."""
    for name in ("a.txt", "b.txt"):
        (tmp_path / name).write_text("")
    assert ins.group_duplicates(ins.walk(tmp_path)) == {}


def test_different_sizes_never_collide(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x" * 100)
    (tmp_path / "b.txt").write_text("x" * 200)
    assert ins.group_duplicates(ins.walk(tmp_path)) == {}


def test_text_detection():
    assert ins.is_probably_text(Path("a.md"))
    assert ins.is_probably_text(Path("a.PY"))
    assert not ins.is_probably_text(Path("a.mp4"))
