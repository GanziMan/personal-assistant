"""터미널 클라이언트.

SwiftUI 앱이 붙기 전(P5)까지의 프런트엔드이자, 이후로도 디버깅 창구다.
"""

from __future__ import annotations

import asyncio
import sys
import uuid

from .config import SOCKET_PATH
from .protocol import Event, EventType


async def one_shot(prompt: str, session_id: str) -> int:
    try:
        reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))
    except (FileNotFoundError, ConnectionRefusedError):
        print(
            f"데몬에 연결할 수 없습니다 ({SOCKET_PATH}).\n"
            "  launchctl kickstart -k gui/$UID/com.assistant.daemon",
            file=sys.stderr,
        )
        return 1

    writer.write(Event(EventType.PROMPT, session_id, prompt).encode())
    await writer.drain()

    code = 0
    while line := await reader.readline():
        event = Event.decode(line)
        if event.type is EventType.TEXT:
            print(event.text, end="", flush=True)
        elif event.type is EventType.THINKING:
            print(f"\033[2m… {event.text}\033[0m", file=sys.stderr)
        elif event.type is EventType.ERROR:
            print(f"\n오류: {event.text}", file=sys.stderr)
            code = 1
            break
        elif event.type is EventType.DONE:
            print()
            break

    writer.close()
    await writer.wait_closed()
    return code


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("사용법: assistant <말할 내용>", file=sys.stderr)
        return 2
    return asyncio.run(one_shot(" ".join(args), uuid.uuid4().hex[:12]))


if __name__ == "__main__":
    raise SystemExit(main())
