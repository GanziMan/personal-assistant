"""데몬. 유닉스 소켓 서버.

launchd 로 로그인 시 상주한다. 포트를 열지 않으므로 같은 맥의 다른
프로세스가 우연히 말을 걸 수 없다 (ADR-003).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import signal
import sys

from .agent import Agent
from .config import LOG_DIR, SOCKET_PATH, Config, ensure_dirs
from .protocol import Event, EventType
from .scheduler import DEFAULT_JOBS, Scheduler
from .scheduler import rules
from .scheduler.delivery import Delivery

log = logging.getLogger("assistantd")


class Daemon:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.agent = Agent(config)
        self._server: asyncio.Server | None = None
        self._scheduler: Scheduler | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    async def handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = id(writer)
        log.debug("client connected: %s", peer)
        try:
            while line := await reader.readline():
                try:
                    event = Event.decode(line)
                except (json.JSONDecodeError, KeyError, ValueError) as exc:
                    writer.write(Event(EventType.ERROR, text=f"잘못된 요청: {exc}").encode())
                    await writer.drain()
                    continue

                await self._dispatch(event, writer)
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            log.debug("client disconnected: %s", peer)
            with contextlib.suppress(Exception):
                writer.close()
                await writer.wait_closed()

    async def _dispatch(self, event: Event, writer: asyncio.StreamWriter) -> None:
        match event.type:
            case EventType.PING:
                writer.write(Event(EventType.PONG).encode())
                await writer.drain()

            case EventType.PROMPT:
                async for out in self.agent.run(event.session_id or "default", event.text):
                    writer.write(out.encode())
                    await writer.drain()

            case _:
                writer.write(
                    Event(EventType.ERROR, text=f"처리할 수 없는 이벤트: {event.type}").encode()
                )
                await writer.drain()

    async def _run_job(self, job) -> str:  # noqa: ANN001
        """규칙 잡은 도구만, 에이전트 잡은 모델까지."""
        if job.mode == "rule":
            return await rules.get(job.rule)(self.agent.tools)
        return await self.agent.run_silent(job.prompt, session_id=f"job:{job.name}")

    async def serve(self) -> None:
        ensure_dirs()

        # 이전 인스턴스가 남긴 소켓 파일 정리
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()

        # 소켓을 먼저 연다. 도구층이 느리거나 깨져도 클라이언트는 붙을 수
        # 있어야 한다 — 연결조차 안 되면 사용자는 원인을 알 방법이 없다.
        self._server = await asyncio.start_unix_server(self.handle, path=str(SOCKET_PATH))
        os.chmod(SOCKET_PATH, 0o600)  # 소유자만
        log.info("listening on %s", SOCKET_PATH)

        await self.agent.start()

        # 알림 잡은 도구가 있어야 의미가 있다. 도구층이 뜬 뒤에 시작한다.
        self._scheduler = Scheduler(
            list(DEFAULT_JOBS),
            run_job=self._run_job,
            on_result=Delivery(self.agent),
            timezone=self.config.timezone,
        )
        self._scheduler.start()

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)

        async with self._server:
            await stop.wait()

        log.info("shutting down")
        if self._scheduler is not None:
            await self._scheduler.stop()
        await self.agent.aclose()
        with contextlib.suppress(FileNotFoundError):
            SOCKET_PATH.unlink()


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("ASSISTANT_LOG", "INFO"),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    ensure_dirs()
    log.info("logs: %s", LOG_DIR)
    try:
        asyncio.run(Daemon(Config.load()).serve())
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
