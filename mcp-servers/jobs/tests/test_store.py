from pathlib import Path

from jobs.config import JobsConfig, Search
from jobs.store import SeenStore


def test_new_job_is_new(tmp_path: Path):
    assert SeenStore(tmp_path / "s.json").is_new("1")


def test_marked_job_is_not_new(tmp_path: Path):
    store = SeenStore(tmp_path / "s.json")
    store.mark(["1"])
    assert not store.is_new("1")


def test_marks_survive_restart(tmp_path: Path):
    path = tmp_path / "s.json"
    SeenStore(path).mark(["1", "2"])
    assert not SeenStore(path).is_new("2")


def test_old_marks_are_pruned(tmp_path: Path):
    store = SeenStore(tmp_path / "s.json")
    store.mark(["old"], now=1000)
    store.prune(now=1000 + 200 * 86400, ttl_days=120)
    assert store.is_new("old")


def test_forget_all(tmp_path: Path):
    store = SeenStore(tmp_path / "s.json")
    store.mark(["1", "2"])
    assert store.forget_all() == 2
    assert store.is_new("1")


def test_corrupt_file_is_ignored(tmp_path: Path):
    path = tmp_path / "s.json"
    path.write_text("{{깨짐")
    assert SeenStore(path).is_new("1")


# ---- 검색 조건 ------------------------------------------------------

def test_params_include_defaults():
    params = Search(name="테스트").to_params()
    assert params["sort"] == "pd"
    assert params["sr"] == "directhire", "기본은 헤드헌팅 제외"


def test_params_omit_empty_filters():
    params = Search(name="테스트").to_params()
    assert "keywords" not in params and "loc_mcd" not in params


def test_params_include_given_filters():
    params = Search(name="t", keywords="백엔드", loc_mcd="101", job_mid_cd="2").to_params()
    assert params["keywords"] == "백엔드"
    assert params["loc_mcd"] == "101"
    assert params["job_mid_cd"] == "2"


def test_agency_filter_can_be_disabled():
    assert "sr" not in Search(name="t", exclude_agency=False).to_params()


def test_config_roundtrip(tmp_path: Path):
    path = tmp_path / "jobs.json"
    config = JobsConfig(searches=[Search(name="백엔드", keywords="Python")])
    config.save(path)
    assert JobsConfig.load(path).find("백엔드").keywords == "Python"


def test_missing_config_is_empty(tmp_path: Path):
    assert JobsConfig.load(tmp_path / "nope.json").searches == []
