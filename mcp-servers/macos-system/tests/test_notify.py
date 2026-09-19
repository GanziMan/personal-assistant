from macos_system.notify import _escape_applescript


def test_quotes_are_escaped():
    assert _escape_applescript('제목 "따옴표"') == '제목 \\"따옴표\\"'


def test_backslash_escaped_before_quotes():
    # 역슬래시를 먼저 처리하지 않으면 이스케이프가 깨진다
    assert _escape_applescript('a\\"b') == 'a\\\\\\"b'


def test_injection_attempt_stays_inside_string():
    evil = '" & (do shell script "rm -rf /") & "'
    out = _escape_applescript(evil)
    assert out.count('"') == out.count('\\"'), "따옴표가 모두 이스케이프돼야 한다"
