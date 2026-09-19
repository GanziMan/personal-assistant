"""경로 경계 테스트. 이 서버의 보안이 여기 걸려 있다."""

from pathlib import Path

import pytest

from macos_files.paths import Boundary, PathDenied


@pytest.fixture
def sandbox(tmp_path: Path):
    allowed = tmp_path / "allowed"
    (allowed / "sub").mkdir(parents=True)
    (allowed / "sub" / "note.txt").write_text("안녕")

    secret = tmp_path / "secret"
    secret.mkdir()
    (secret / "keys.txt").write_text("비밀")

    return Boundary([str(allowed)]), allowed, secret


def test_path_inside_root_is_allowed(sandbox):
    boundary, allowed, _ = sandbox
    assert boundary.resolve(str(allowed / "sub" / "note.txt")).exists()


def test_path_outside_root_is_denied(sandbox):
    boundary, _, secret = sandbox
    with pytest.raises(PathDenied):
        boundary.resolve(str(secret / "keys.txt"))


def test_dotdot_escape_is_denied(sandbox):
    """문자열만 보면 허용 루트로 시작하지만 실제로는 밖을 가리킨다."""
    boundary, allowed, _ = sandbox
    with pytest.raises(PathDenied):
        boundary.resolve(str(allowed / ".." / "secret" / "keys.txt"))


def test_symlink_escape_is_denied(sandbox):
    """허용 폴더 안의 심볼릭 링크가 밖을 가리켜도 막아야 한다."""
    boundary, allowed, secret = sandbox
    link = allowed / "escape"
    link.symlink_to(secret)
    with pytest.raises(PathDenied):
        boundary.resolve(str(link / "keys.txt"))


def test_nonexistent_path_inside_root_is_allowed(sandbox):
    """쓰기 대상은 아직 없을 수 있다."""
    boundary, allowed, _ = sandbox
    assert boundary.resolve(str(allowed / "new" / "file.txt"))


def test_denied_names_are_blocked_even_inside_root(sandbox):
    boundary, allowed, _ = sandbox
    (allowed / ".ssh").mkdir()
    with pytest.raises(PathDenied, match="ssh"):
        boundary.resolve(str(allowed / ".ssh" / "id_rsa"))


def test_git_internals_are_blocked(sandbox):
    boundary, allowed, _ = sandbox
    with pytest.raises(PathDenied):
        boundary.resolve(str(allowed / ".git" / "config"))


def test_missing_roots_are_skipped(tmp_path: Path):
    boundary = Boundary([str(tmp_path / "does-not-exist")])
    assert boundary.roots == []
    with pytest.raises(PathDenied):
        boundary.resolve(str(tmp_path))


def test_empty_boundary_denies_everything(tmp_path: Path):
    """허용 루트가 없으면 아무것도 통과하지 않는다 — 기본값이 안전해야 한다."""
    boundary = Boundary([])
    boundary.roots = []
    with pytest.raises(PathDenied):
        boundary.resolve("/etc/passwd")


def test_error_message_lists_allowed_roots(sandbox):
    boundary, allowed, secret = sandbox
    with pytest.raises(PathDenied, match="허용"):
        boundary.resolve(str(secret))
