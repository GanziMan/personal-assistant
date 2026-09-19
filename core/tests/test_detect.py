import time
from pathlib import Path

import pytest

from assistant.detect.probes import folder_pileup, stale_changes
from assistant.detect.signals import Severity, Signal
from assistant.detect.store import SignalStore


@pytest.fixture
def store(tmp_path: Path) -> SignalStore:
    return SignalStore(tmp_path / "signals.json")


def _signal(**kw) -> Signal:
    return Signal(key=kw.pop("key", "k"), message="m", **kw)


# ---- 반복 억제 ------------------------------------------------------

def test_first_time_is_always_said(store: SignalStore):
    assert store.should_say(_signal())


def test_same_signal_is_silenced_within_cooldown(store: SignalStore):
    s = _signal(cooldown_hours=24)
    store.mark_said(s, now=1000)
    assert not store.should_say(s, now=1000 + 3600)


def test_cooldown_expires(store: SignalStore):
    s = _signal(cooldown_hours=1)
    store.mark_said(s, now=1000)
    assert store.should_say(s, now=1000 + 3700)


def test_changed_state_breaks_cooldown(store: SignalStore):
    """디스크 95% → 97% 는 새 소식이다."""
    store.mark_said(_signal(fingerprint="95"), now=1000)
    assert store.should_say(_signal(fingerprint="97"), now=1000 + 60)


def test_unchanged_state_stays_silent(store: SignalStore):
    store.mark_said(_signal(fingerprint="95"), now=1000)
    assert not store.should_say(_signal(fingerprint="95"), now=1000 + 60)


def test_forget_allows_immediate_resay(store: SignalStore):
    s = _signal()
    store.mark_said(s, now=1000)
    store.forget(s.key)
    assert store.should_say(s, now=1000 + 60)


def test_filter_marks_and_returns_only_new(store: SignalStore):
    a, b = _signal(key="a"), _signal(key="b")
    assert {s.key for s in store.filter([a, b], now=1000)} == {"a", "b"}
    assert store.filter([a, b], now=1000 + 60) == []


def test_records_survive_restart(tmp_path: Path):
    path = tmp_path / "signals.json"
    SignalStore(path).mark_said(_signal(), now=1000)
    assert not SignalStore(path).should_say(_signal(), now=1000 + 60)


def test_corrupt_file_does_not_crash(tmp_path: Path):
    path = tmp_path / "signals.json"
    path.write_text("{{ 깨진")
    assert SignalStore(path).should_say(_signal())


# ---- 감지기 ---------------------------------------------------------

def test_pileup_below_threshold_is_silent(tmp_path: Path):
    for i in range(5):
        (tmp_path / f"f{i}.txt").write_text("x")
    assert folder_pileup(str(tmp_path), threshold=40) is None


def test_pileup_above_threshold_fires(tmp_path: Path):
    for i in range(12):
        (tmp_path / f"f{i}.txt").write_text("x")
    signal = folder_pileup(str(tmp_path), threshold=10)
    assert signal is not None
    assert "12개" in signal.message


def test_pileup_fingerprint_is_bucketed(tmp_path: Path):
    """41개 → 42개마다 다시 말하면 안 된다."""
    for i in range(41):
        (tmp_path / f"f{i}.txt").write_text("x")
    first = folder_pileup(str(tmp_path), threshold=10)
    (tmp_path / "extra.txt").write_text("x")
    second = folder_pileup(str(tmp_path), threshold=10)
    assert first.fingerprint == second.fingerprint


def test_pileup_ignores_hidden_files(tmp_path: Path):
    for i in range(20):
        (tmp_path / f".hidden{i}").write_text("x")
    assert folder_pileup(str(tmp_path), threshold=10) is None


def test_pileup_on_missing_folder(tmp_path: Path):
    assert folder_pileup(str(tmp_path / "nope")) is None


def test_stale_changes_needs_both_dirty_and_old(tmp_path: Path):
    now = time.time()
    fresh_dirty = [("a", True, now)]
    old_clean = [("b", False, now - 999 * 86400)]
    assert stale_changes(fresh_dirty) is None
    assert stale_changes(old_clean) is None


def test_stale_changes_fires_and_lists_repos():
    old = time.time() - 30 * 86400
    signal = stale_changes([("api", True, old), ("web", True, old)])
    assert signal is not None
    assert "api" in signal.message and "web" in signal.message
    assert signal.severity is Severity.QUIET, "알림까지 띄울 일은 아니다"


def test_stale_changes_summarises_many():
    old = time.time() - 30 * 86400
    signal = stale_changes([(f"r{i}", True, old) for i in range(6)])
    assert "외 3개" in signal.message


# ---- 쪽지판 ---------------------------------------------------------

def test_notes_expire(tmp_path: Path):
    from assistant.detect.notes import NoteBoard

    board = NoteBoard(tmp_path / "notes.json", ttl_hours=1)
    board.put("k", "오래된 쪽지", now=1000)
    assert board.load(now=1000 + 60) != []
    assert board.load(now=1000 + 7200) == []


def test_same_key_overwrites(tmp_path: Path):
    from assistant.detect.notes import NoteBoard

    board = NoteBoard(tmp_path / "notes.json")
    board.put("disk", "90% 찼습니다")
    board.put("disk", "95% 찼습니다")
    messages = [n.message for n in board.load()]
    assert messages == ["95% 찼습니다"], "같은 얘기가 여러 줄 쌓이면 안 된다"


def test_notes_are_capped(tmp_path: Path):
    from assistant.detect.notes import MAX_NOTES, NoteBoard

    board = NoteBoard(tmp_path / "notes.json")
    for i in range(10):
        board.put(f"k{i}", f"쪽지 {i}")
    assert len(board.load()) == MAX_NOTES


def test_dismiss_removes_one(tmp_path: Path):
    from assistant.detect.notes import NoteBoard

    board = NoteBoard(tmp_path / "notes.json")
    board.put("a", "A")
    board.put("b", "B")
    board.dismiss("a")
    assert [n.key for n in board.load()] == ["b"]


def test_corrupt_notes_file_is_ignored(tmp_path: Path):
    from assistant.detect.notes import NoteBoard

    path = tmp_path / "notes.json"
    path.write_text("[[[")
    assert NoteBoard(path).load() == []
