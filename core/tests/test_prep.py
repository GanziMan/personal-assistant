from assistant.prep import Prep, keywords, trim


# ---- 검색어 추출 ----------------------------------------------------

def test_generic_meeting_title_yields_nothing():
    """'주간 회의' 로 검색하면 관계없는 게 잔뜩 나온다."""
    assert keywords("주간 회의") == []
    assert keywords("Daily Standup") == []


def test_specific_terms_survive():
    assert "결제" in keywords("결제 모듈 설계 리뷰")


def test_stopwords_are_dropped():
    assert "리뷰" not in keywords("결제 모듈 설계 리뷰")


def test_separators_are_split():
    terms = keywords("api-gateway / 인증 논의")
    assert "api" in terms and "gateway" in terms


def test_short_tokens_are_dropped():
    assert "a" not in keywords("a 결제 논의")


def test_terms_are_capped():
    assert len(keywords("하나 둘 셋 넷 다섯 여섯")) <= 3


def test_case_insensitive_stopwords():
    assert keywords("WEEKLY SYNC") == []


# ---- 출력 정리 ------------------------------------------------------

def test_trim_drops_empty_responses():
    assert trim("'결제' 와 맞는 파일이 없습니다.") == []


def test_trim_drops_headers():
    assert trim("## api\n실제 줄") == ["실제 줄"]


def test_trim_respects_limit():
    assert len(trim("\n".join(f"줄 {i}" for i in range(10)), limit=2)) == 2


def test_trim_skips_blank_lines():
    assert trim("a\n\n\nb") == ["a", "b"]


# ---- 렌더링 ---------------------------------------------------------

def test_empty_prep_is_detected():
    assert Prep(event="회의", minutes=10).empty


def test_render_includes_event_and_time():
    text = Prep(event="설계 리뷰", minutes=12, past=["지난 결정"]).render()
    assert "12분 뒤" in text and "설계 리뷰" in text


def test_render_omits_missing_sections():
    text = Prep(event="회의", minutes=5, files=["a.md"]).render()
    assert "관련 파일" in text
    assert "지난 기록" not in text


def test_render_caps_each_section():
    text = Prep(event="회의", minutes=5, past=[f"p{i}" for i in range(9)]).render()
    assert text.count("·") == 3
