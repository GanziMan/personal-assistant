"""업무 로그.

하루 끝에 커밋·일정·완료한 할 일을 모아 한 덩어리로 쌓는다.
쌓인 것이 주간 보고와 분기 회고의 근거가 된다.

모델을 쓰지 않는다. 오늘 무엇을 했는지는 조회와 정리의 문제이지
추론이 아니다 (ADR-008). 요약이 필요하면 나중에 사용자가 물을 때
그때 모델이 읽는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

_COMMIT = re.compile(r"^([0-9a-f]{7,40})\s\s(.+)$")


@dataclass(slots=True)
class RepoWork:
    repo: str
    commits: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DayLog:
    date: str
    repos: list[RepoWork] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    done: list[str] = field(default_factory=list)

    @property
    def commit_count(self) -> int:
        return sum(len(r.commits) for r in self.repos)

    @property
    def empty(self) -> bool:
        return not (self.repos or self.events or self.done)

    def title(self) -> str:
        bits = []
        if self.commit_count:
            bits.append(f"커밋 {self.commit_count}건")
        if self.events:
            bits.append(f"일정 {len(self.events)}건")
        if self.done:
            bits.append(f"완료 {len(self.done)}건")
        return f"{self.date} — " + (", ".join(bits) if bits else "기록 없음")

    def body(self) -> str:
        blocks: list[str] = []
        for repo in self.repos:
            listed = "\n".join(f"  - {c}" for c in repo.commits)
            blocks.append(f"[{repo.repo}]\n{listed}")
        if self.events:
            blocks.append("[일정]\n" + "\n".join(f"  - {e}" for e in self.events))
        if self.done:
            blocks.append("[완료한 일]\n" + "\n".join(f"  - {d}" for d in self.done))
        return "\n\n".join(blocks)


def parse_commits(text: str) -> list[RepoWork]:
    """commits_across_repos 출력을 레포별로 나눈다."""
    repos: list[RepoWork] = []
    current: RepoWork | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            current = RepoWork(line[3:].strip())
            repos.append(current)
            continue
        if current is None:
            continue
        if match := _COMMIT.match(line.strip()):
            current.commits.append(match.group(2).strip())

    return [r for r in repos if r.commits]


def parse_events(text: str) -> list[str]:
    """일정 목록에서 제목만 추린다."""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        # "09/20 14:00–15:00  팀 회의  [업무]"
        parts = [p for p in line.split("  ") if p]
        if len(parts) < 2 or not parts[0][:2].isdigit():
            continue
        out.append(parts[1])
    return out


def parse_done(text: str) -> list[str]:
    """완료 표시된 리마인더만."""
    return [
        line.strip()[1:].strip().split("  (")[0].strip()
        for line in text.splitlines()
        if line.strip().startswith("✓")
    ]


def build(
    *, commits: str, events: str, reminders: str, now: datetime | None = None
) -> DayLog:
    now = now or datetime.now()
    return DayLog(
        date=now.strftime("%Y-%m-%d (%a)"),
        repos=parse_commits(commits),
        events=parse_events(events),
        done=parse_done(reminders),
    )
