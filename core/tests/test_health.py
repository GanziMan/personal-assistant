from assistant.health import Capability, summarize


def _cap(ok: bool, label: str = "로컬 임베딩", degraded: str = "검색이 약해집니다.") -> Capability:
    return Capability(key="k", label=label, ok=ok, degraded=degraded)


def test_all_healthy_says_nothing():
    assert summarize([_cap(True), _cap(True, "도구")]) == ""


def test_single_failure_explains_the_cost():
    line = summarize([_cap(False)])
    assert "로컬 임베딩" in line
    assert "검색이 약해집니다." in line, "무엇이 나빠지는지 알려줘야 고칠지 판단한다"


def test_multiple_failures_are_listed_briefly():
    line = summarize([_cap(False), _cap(False, "도구")])
    assert "로컬 임베딩" in line and "도구" in line


def test_empty_input():
    assert summarize([]) == ""


def test_capability_serializes_for_the_wire():
    payload = _cap(False).to_dict()
    assert payload["ok"] is False
    assert set(payload) == {"key", "label", "ok", "detail", "degraded", "fix"}
