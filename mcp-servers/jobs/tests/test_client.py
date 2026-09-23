import pytest

from jobs.client import JobsError, extract


def test_single_result_is_wrapped_in_list():
    """결과가 하나면 사람인은 배열이 아니라 객체를 준다."""
    payload = {"jobs": {"count": 1, "job": {"id": "1"}}}
    assert extract(payload) == [{"id": "1"}]


def test_multiple_results():
    payload = {"jobs": {"job": [{"id": "1"}, {"id": "2"}]}}
    assert len(extract(payload)) == 2


def test_empty_result():
    assert extract({"jobs": {"count": 0, "job": []}}) == []


def test_missing_jobs_key():
    assert extract({}) == []


@pytest.mark.parametrize(
    "code,fragment",
    [(1, "access-key"), (2, "유효하지"), (3, "조건"), (4, "한도"), (99, "서버")],
)
def test_error_codes_become_readable(code, fragment):
    with pytest.raises(JobsError, match=fragment):
        extract({"code": code, "message": "whatever"})


def test_unknown_error_code_uses_message():
    with pytest.raises(JobsError, match="이상한 오류"):
        extract({"code": 77, "message": "이상한 오류"})


def test_non_dict_payload():
    with pytest.raises(JobsError):
        extract(["배열이 옴"])
