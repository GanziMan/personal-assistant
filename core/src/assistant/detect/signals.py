"""감지 신호.

비서가 먼저 말을 걸려면 '지금 뭔가 일어났다'를 알아야 한다. 그런데
감지보다 어려운 건 **같은 얘기를 반복하지 않는 것**이다. 다운로드가
지저분하다는 말을 10분마다 들으면 그 비서는 꺼진다.

그래서 신호마다 키와 쿨다운을 둔다. 같은 키는 쿨다운 안에 다시 말하지
않고, 상태가 실제로 달라졌을 때만 다시 올라온다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Severity(IntEnum):
    QUIET = 0    # 기억에만 쌓는다. 물어보면 답한다
    NOTE = 1     # 대기 화면에 한 줄
    ALERT = 2    # 알림을 띄운다


@dataclass(slots=True, frozen=True)
class Signal:
    key: str                  # 같은 종류를 묶는 이름
    message: str
    severity: Severity = Severity.QUIET

    # 같은 키를 다시 말하기까지 최소 시간
    cooldown_hours: float = 24.0

    # 상태 지문. 달라지면 쿨다운 중이라도 다시 말한다.
    # 예: 디스크 95% → 97% 는 새 소식이지만 95% → 95% 는 아니다
    fingerprint: str = ""
