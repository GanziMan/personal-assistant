from dev_tools.git import Status, parse_status


def test_clean_repo():
    branch, staged, unstaged, untracked, ahead, behind = parse_status("## main...origin/main\n")
    assert branch == "main"
    assert (staged, unstaged, untracked, ahead, behind) == (0, 0, 0, 0, 0)


def test_counts_each_category():
    out = "\n".join([
        "## main...origin/main",
        "M  staged.py",      # staged only
        " M unstaged.py",    # unstaged only
        "MM both.py",        # 둘 다
        "?? new.py",
    ])
    _, staged, unstaged, untracked, _, _ = parse_status(out)
    assert (staged, unstaged, untracked) == (2, 2, 1)


def test_ahead_and_behind():
    out = "## main...origin/main [ahead 3, behind 2]\n"
    _, _, _, _, ahead, behind = parse_status(out)
    assert (ahead, behind) == (3, 2)


def test_ahead_only():
    _, _, _, _, ahead, behind = parse_status("## main...origin/main [ahead 1]\n")
    assert (ahead, behind) == (1, 0)


def test_detached_or_local_branch():
    branch, *_ = parse_status("## feature/login\n")
    assert branch == "feature/login"


def test_status_describe_clean():
    assert "깨끗함" in Status("main", 0, 0, 0, 0, 0).describe()


def test_status_describe_shows_sync_markers():
    text = Status("main", 0, 0, 0, 2, 1).describe()
    assert "↑2" in text and "↓1" in text


def test_clean_property():
    assert Status("main", 0, 0, 0, 5, 5).clean, "동기화 상태는 더러움이 아니다"
    assert not Status("main", 1, 0, 0, 0, 0).clean
