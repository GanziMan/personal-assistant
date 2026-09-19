from pathlib import Path

from macos_system.images import IMAGE_SUFFIXES, is_image, prune


def test_common_image_types():
    for name in ("a.png", "b.JPG", "c.heic", "d.webp"):
        assert is_image(Path(name)), name


def test_non_images():
    for name in ("a.txt", "b.pdf", "c", "d.md"):
        assert not is_image(Path(name)), name


def test_suffixes_are_lowercase():
    assert all(s == s.lower() for s in IMAGE_SUFFIXES)


def test_prune_on_missing_dir_is_safe(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("macos_system.images.PASTED_DIR", tmp_path / "nope")
    assert prune() == 0


def test_prune_removes_only_old(monkeypatch, tmp_path: Path):
    import os, time

    monkeypatch.setattr("macos_system.images.PASTED_DIR", tmp_path)
    old = tmp_path / "old.png"
    new = tmp_path / "new.png"
    old.write_bytes(b"x")
    new.write_bytes(b"x")
    past = time.time() - 100 * 3600
    os.utime(old, (past, past))

    assert prune(ttl_hours=24) == 1
    assert not old.exists() and new.exists()
