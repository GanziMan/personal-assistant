"""알림 발송.

osascript 의 `display notification` 은 알림을 띄우지만 클릭 액션도
소리 제어도 없고, 보내는 앱이 '스크립트 편집기'로 뜬다. terminal-notifier
가 있으면 그걸 쓰고, 없으면 osascript 로 떨어진다.

알림은 비싸다 (ARCHITECTURE §6). 여기서는 보낼 수 있게만 하고, 언제
보낼지는 스케줄러의 화이트리스트가 정한다.
"""

from __future__ import annotations

import shutil
import subprocess


def _escape_applescript(text: str) -> str:
    """AppleScript 문자열 리터럴로 안전하게 만든다.

    사용자 데이터(일정 제목 등)가 그대로 들어오므로, 따옴표 하나로
    스크립트가 깨지거나 의도치 않은 구문이 실행되면 안 된다.
    """
    return text.replace("\\", "\\\\").replace('"', '\\"')


def send(title: str, message: str, *, subtitle: str = "", sound: bool = False) -> str:
    if binary := shutil.which("terminal-notifier"):
        cmd = [binary, "-title", title, "-message", message]
        if subtitle:
            cmd += ["-subtitle", subtitle]
        if sound:
            cmd += ["-sound", "default"]
        subprocess.run(cmd, check=False, capture_output=True, timeout=10)
        return "알림을 보냈습니다."

    script = (
        f'display notification "{_escape_applescript(message)}" '
        f'with title "{_escape_applescript(title)}"'
    )
    if subtitle:
        script += f' subtitle "{_escape_applescript(subtitle)}"'
    if sound:
        script += ' sound name "default"'

    result = subprocess.run(
        ["osascript", "-e", script], check=False, capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return f"알림 실패: {result.stderr.strip()}"
    return "알림을 보냈습니다. (terminal-notifier 를 설치하면 더 낫습니다)"
