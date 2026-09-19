from macos_system.clipboard import ClipboardHistory, looks_secret


# ---- 비밀 판별 ------------------------------------------------------

def test_github_token_is_secret():
    assert looks_secret("ghp_abcdefghijklmnopqrstuvwxyz1234567890")


def test_fine_grained_pat_is_secret():
    assert looks_secret("github_pat_11ABCDEFG_abcdefghijklmnopqrstuvwxyz0123456789")


def test_openai_style_key_is_secret():
    assert looks_secret("sk-abcdefghijklmnopqrstuvwxyz123456")


def test_aws_key_is_secret():
    assert looks_secret("AKIAIOSFODNN7EXAMPLE")


def test_private_key_is_secret():
    assert looks_secret("-----BEGIN RSA PRIVATE KEY-----\nMIIE...")


def test_jwt_is_secret():
    assert looks_secret("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc")


def test_labelled_password_is_secret():
    assert looks_secret("password: hunter2")
    assert looks_secret("API_KEY=abcdef")


def test_ordinary_text_is_not_secret():
    assert not looks_secret("TypeError: cannot read property 'map' of undefined")


def test_code_snippet_is_not_secret():
    assert not looks_secret("const user = await db.users.findOne({ id })")


def test_korean_text_is_not_secret():
    assert not looks_secret("결제 모듈 리팩터링하면서 발생한 에러입니다")


# ---- 이력 -----------------------------------------------------------

def test_capture_and_latest():
    h = ClipboardHistory()
    assert h.capture("에러 로그")
    assert h.latest().text == "에러 로그"


def test_secret_is_not_captured():
    h = ClipboardHistory()
    assert not h.capture("ghp_abcdefghijklmnopqrstuvwxyz1234567890")
    assert len(h) == 0


def test_blank_is_not_captured():
    h = ClipboardHistory()
    assert not h.capture("   \n  ")


def test_oversized_is_not_captured():
    h = ClipboardHistory()
    assert not h.capture("x" * 5000)


def test_consecutive_duplicates_are_skipped():
    h = ClipboardHistory()
    h.capture("같은 것")
    assert not h.capture("같은 것")
    assert len(h) == 1


def test_history_is_bounded():
    h = ClipboardHistory(max_items=3)
    for i in range(10):
        h.capture(f"항목 {i}")
    assert len(h) == 3


def test_recent_is_newest_first():
    h = ClipboardHistory()
    for i in range(3):
        h.capture(f"항목 {i}")
    assert h.recent()[0].text == "항목 2"


def test_find_matches_case_insensitively():
    h = ClipboardHistory()
    h.capture("TypeError 발생")
    assert h.find("typeerror")


def test_find_returns_nothing_when_absent():
    h = ClipboardHistory()
    h.capture("아무것도")
    assert h.find("없는말") == []


def test_clear_empties():
    h = ClipboardHistory()
    h.capture("뭔가")
    h.clear()
    assert len(h) == 0


def test_preview_is_truncated():
    h = ClipboardHistory()
    h.capture("긴 내용 " * 50)
    assert h.latest().preview().endswith("…")
