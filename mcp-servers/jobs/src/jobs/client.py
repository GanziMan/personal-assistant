"""사람인 채용정보 API 클라이언트.

access-key 는 키체인에서 읽는다. 설정 파일에 두지 않는다 — 비서의
다른 비밀들과 같은 자리에 둔다 (ARCHITECTURE §7).
"""

from __future__ import annotations

import subprocess
from functools import lru_cache
from typing import Any

import httpx

ENDPOINT = "https://oapi.saramin.co.kr/job-search"
KEYCHAIN_SERVICE = "assistant-saramin"
TIMEOUT = 20.0

ERRORS = {
    1: "access-key 가 없습니다.",
    2: "access-key 가 유효하지 않습니다.",
    3: "요청 조건이 잘못됐습니다.",
    4: "오늘 요청 한도를 넘었습니다.",
    99: "사람인 서버 오류입니다.",
}


class JobsError(RuntimeError):
    """호출이 실패했다. 사람이 읽을 수 있는 메시지를 담는다."""


@lru_cache(maxsize=1)
def access_key() -> str:
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise JobsError(f"키체인에 접근할 수 없습니다: {exc}") from exc

    if result.returncode != 0:
        raise JobsError(
            "사람인 access-key 가 키체인에 없습니다.\n"
            f'  security add-generic-password -a "$USER" -s {KEYCHAIN_SERVICE} -w'
        )
    return result.stdout.strip()


async def search(params: dict[str, str]) -> list[dict[str, Any]]:
    """공고 목록을 가져온다."""
    query = {**params, "access-key": access_key()}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                ENDPOINT, params=query, headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise JobsError(f"사람인 API 호출 실패: {exc}") from exc
    except ValueError as exc:
        raise JobsError("사람인 응답을 해석할 수 없습니다.") from exc

    return extract(payload)


def extract(payload: Any) -> list[dict[str, Any]]:
    """응답에서 공고 목록만 꺼낸다. 오류면 예외로 바꾼다.

    별도 함수로 둔 이유는 테스트다. 네트워크 없이 응답 형태를
    검증할 수 있어야 한다.
    """
    if not isinstance(payload, dict):
        raise JobsError("사람인 응답 형식이 예상과 다릅니다.")

    if "code" in payload and "jobs" not in payload:
        code = payload.get("code")
        detail = ERRORS.get(code if isinstance(code, int) else -1)
        raise JobsError(detail or str(payload.get("message", "알 수 없는 오류")))

    jobs = payload.get("jobs")
    if not isinstance(jobs, dict):
        return []

    found = jobs.get("job")
    if isinstance(found, dict):   # 결과가 하나면 배열이 아니다
        return [found]
    return [j for j in (found or []) if isinstance(j, dict)]
