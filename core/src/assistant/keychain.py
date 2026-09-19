"""macOS 키체인에서 비밀을 읽는다.

API 키를 설정 파일이나 환경변수에 두지 않는다 (ARCHITECTURE §7).
환경변수는 프로세스 목록·크래시 덤프·셸 히스토리로 새고, 설정 파일은
백업과 함께 어딘가로 복사된다. 키체인은 잠금과 접근 제어가 붙는다.

저장:
    security add-generic-password -a "$USER" -s assistant-anthropic -w
"""

from __future__ import annotations

import subprocess
from functools import lru_cache


class SecretNotFound(RuntimeError):
    """키체인에 해당 항목이 없다."""


@lru_cache(maxsize=8)
def get_secret(service: str, account: str | None = None) -> str:
    """키체인의 generic password 를 꺼낸다.

    캐시하는 이유: 에이전트 루프가 돌 때마다 security(1) 를 부르면
    키체인 잠금 해제 프롬프트가 반복될 수 있다.
    """
    cmd = ["security", "find-generic-password", "-s", service, "-w"]
    if account:
        cmd[2:2] = ["-a", account]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
    except FileNotFoundError as exc:  # macOS 가 아님
        raise SecretNotFound(f"security(1) 를 찾을 수 없습니다: {service}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SecretNotFound(f"키체인 접근 시간 초과: {service}") from exc

    if result.returncode != 0:
        raise SecretNotFound(
            f"키체인에 '{service}' 항목이 없습니다.\n"
            f"  security add-generic-password -a \"$USER\" -s {service} -w"
        )
    return result.stdout.strip()


def anthropic_api_key() -> str:
    return get_secret("assistant-anthropic")
