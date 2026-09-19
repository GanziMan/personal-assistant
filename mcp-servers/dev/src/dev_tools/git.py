"""git 조회. 읽기 전용.

git 을 subprocess 로 부르되, 인자는 항상 리스트로 넘기고 셸을 거치지
않는다. 그리고 상태를 바꾸는 명령은 아예 만들지 않는다 (ADR-016).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

TIMEOUT = 15.0


class GitError(RuntimeError):
    pass


def run(repo: Path, *args: str) -> str:
    """repo 안에서 git 명령을 돌린다."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=TIMEOUT, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise GitError(f"git 실행 실패: {exc}") from exc

    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f"git {' '.join(args)} 실패")
    return result.stdout


@dataclass(slots=True)
class Status:
    branch: str
    staged: int
    unstaged: int
    untracked: int
    ahead: int
    behind: int

    @property
    def clean(self) -> bool:
        return not (self.staged or self.unstaged or self.untracked)

    def describe(self) -> str:
        if self.clean:
            body = "깨끗함"
        else:
            parts = []
            if self.staged:
                parts.append(f"staged {self.staged}")
            if self.unstaged:
                parts.append(f"수정 {self.unstaged}")
            if self.untracked:
                parts.append(f"추적 안 됨 {self.untracked}")
            body = ", ".join(parts)

        sync = ""
        if self.ahead or self.behind:
            bits = []
            if self.ahead:
                bits.append(f"↑{self.ahead}")
            if self.behind:
                bits.append(f"↓{self.behind}")
            sync = f"  {' '.join(bits)}"
        return f"[{self.branch}] {body}{sync}"


def parse_status(porcelain: str) -> tuple[str, int, int, int, int, int]:
    """`git status --porcelain=v1 -b` 출력을 센다.

    별도 함수로 둔 이유는 테스트다. git 을 띄우지 않고도 파싱을
    검증할 수 있어야 한다.
    """
    branch = "?"
    ahead = behind = 0
    staged = unstaged = untracked = 0

    for line in porcelain.splitlines():
        if line.startswith("## "):
            head = line[3:]
            branch = head.split("...")[0].strip() or "?"
            if "[" in head:
                marker = head[head.index("[") + 1 : head.rindex("]")]
                for piece in marker.split(","):
                    piece = piece.strip()
                    if piece.startswith("ahead "):
                        ahead = int(piece.split()[1])
                    elif piece.startswith("behind "):
                        behind = int(piece.split()[1])
            continue

        if len(line) < 2:
            continue
        index_state, work_state = line[0], line[1]
        if index_state == "?" and work_state == "?":
            untracked += 1
            continue
        if index_state not in " ?":
            staged += 1
        if work_state not in " ?":
            unstaged += 1

    return branch, staged, unstaged, untracked, ahead, behind


def status(repo: Path) -> Status:
    branch, staged, unstaged, untracked, ahead, behind = parse_status(
        run(repo, "status", "--porcelain=v1", "-b")
    )
    return Status(branch, staged, unstaged, untracked, ahead, behind)
