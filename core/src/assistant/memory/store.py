"""기억 저장소.

SQLite 파일 하나. 별도 서버를 띄우지 않는다 (ADR-002).
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterable
from pathlib import Path

from ..config import DB_PATH
from . import vectors
from .fusion import reciprocal_rank_fusion
from .models import Episode, Fact, Hit

_SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")


def _escape_fts(query: str) -> str:
    """FTS5 질의로 안전하게. 사용자 문장이 연산자로 해석되면 안 된다."""
    tokens = [t for t in query.replace('"', " ").split() if t]
    return " OR ".join(f'"{t}"' for t in tokens) if tokens else '""'


class MemoryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DB_PATH
        if self.path != Path(":memory:"):
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(_SCHEMA)
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    # ---- 쓰기 -----------------------------------------------------

    def add_episode(self, ep: Episode) -> int:
        cur = self.db.execute(
            "INSERT INTO episodes (ts, kind, session_id, title, body, source, importance)"
            " VALUES (?,?,?,?,?,?,?)",
            (ep.ts, ep.kind, ep.session_id, ep.title, ep.body, ep.source, ep.importance),
        )
        self.db.commit()
        ep.id = int(cur.lastrowid or 0)
        return ep.id

    def add_fact(self, fact: Fact) -> int:
        cur = self.db.execute(
            "INSERT INTO facts (created_ts, updated_ts, subject, body, confidence, evidence)"
            " VALUES (?,?,?,?,?,?)",
            (
                fact.created_ts,
                fact.updated_ts,
                fact.subject,
                fact.body,
                fact.confidence,
                fact.evidence,
            ),
        )
        self.db.commit()
        fact.id = int(cur.lastrowid or 0)
        return fact.id

    def supersede_fact(self, old_id: int, new: Fact) -> int:
        """사실을 고친다. 지우지 않고 대체 이력을 남긴다."""
        new_id = self.add_fact(new)
        self.db.execute(
            "UPDATE facts SET superseded_by = ?, updated_ts = ? WHERE id = ?",
            (new_id, time.time(), old_id),
        )
        self.db.commit()
        return new_id

    def set_embedding(self, owner_type: str, owner_id: int, model: str, vec: list[float]) -> None:
        normalized = vectors.normalize(vec)
        self.db.execute(
            "INSERT OR REPLACE INTO embeddings (owner_type, owner_id, model, dim, vec)"
            " VALUES (?,?,?,?,?)",
            (owner_type, owner_id, model, len(normalized), vectors.pack(normalized)),
        )
        self.db.commit()

    def touch(self, ids: Iterable[int]) -> None:
        """참조된 기억의 접근 기록을 올린다. 망각 정책의 입력이 된다."""
        now = time.time()
        self.db.executemany(
            "UPDATE episodes SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
            [(now, i) for i in ids],
        )
        self.db.commit()

    # ---- 검색 -----------------------------------------------------

    def keyword_search(self, query: str, *, limit: int = 20) -> list[int]:
        rows = self.db.execute(
            "SELECT rowid FROM episodes_fts WHERE episodes_fts MATCH ?"
            " ORDER BY rank LIMIT ?",
            (_escape_fts(query), limit),
        ).fetchall()
        return [int(r["rowid"]) for r in rows]

    def vector_search(self, vec: list[float], *, limit: int = 20) -> list[int]:
        """전수 계산. 개인 규모에서는 이걸로 충분하다."""
        probe = vectors.normalize(vec)
        rows = self.db.execute(
            "SELECT owner_id, vec FROM embeddings WHERE owner_type = 'episode'"
        ).fetchall()

        scored = [
            (int(r["owner_id"]), vectors.dot(probe, vectors.unpack(r["vec"])))
            for r in rows
            if len(r["vec"]) == len(probe) * 4
        ]
        scored.sort(key=lambda kv: -kv[1])
        return [i for i, _ in scored[:limit]]

    def search(
        self, query: str, *, vec: list[float] | None = None, limit: int = 8
    ) -> list[Hit]:
        """하이브리드 검색. 벡터와 BM25 를 RRF 로 합친다."""
        rankings: list[list[int]] = [self.keyword_search(query, limit=limit * 3)]
        if vec:
            rankings.append(self.vector_search(vec, limit=limit * 3))

        merged = reciprocal_rank_fusion(rankings, limit=limit)
        if not merged:
            return []

        by_id = {i: s for i, s in merged}
        placeholders = ",".join("?" * len(by_id))
        rows = self.db.execute(
            f"SELECT id, title, body, ts FROM episodes"  # noqa: S608 - id 는 정수 바인딩
            f" WHERE id IN ({placeholders}) AND archived = 0",
            tuple(by_id),
        ).fetchall()

        hits = [
            Hit("episode", int(r["id"]), by_id[int(r["id"])], r["title"], r["body"], r["ts"])
            for r in rows
        ]
        hits.sort(key=lambda h: -h.score)
        self.touch(h.id for h in hits)
        return hits

    def live_facts(self, subject: str | None = None) -> list[Fact]:
        """대체되지 않은 현재 사실들."""
        sql = "SELECT * FROM facts WHERE superseded_by IS NULL"
        args: tuple = ()
        if subject:
            sql += " AND subject = ?"
            args = (subject,)
        sql += " ORDER BY confidence DESC, updated_ts DESC"

        return [
            Fact(
                subject=r["subject"],
                body=r["body"],
                confidence=r["confidence"],
                evidence=r["evidence"],
                created_ts=r["created_ts"],
                updated_ts=r["updated_ts"],
                id=int(r["id"]),
            )
            for r in self.db.execute(sql, args).fetchall()
        ]

    def episodes_by_kind(
        self, kind: str, *, since: float | None = None, limit: int = 120
    ) -> list[Hit]:
        """분류로 골라 읽는다. "이번 분기 뭐 했지" 가 여기로 간다.

        검색이 아니라 열람이다. 업무 로그는 질의어로 찾는 게 아니라
        기간으로 훑는 것이 맞다.
        """
        sql = "SELECT id, title, body, ts FROM episodes WHERE kind = ? AND archived = 0"
        args: list = [kind]
        if since is not None:
            sql += " AND ts >= ?"
            args.append(since)
        sql += " ORDER BY ts DESC LIMIT ?"
        args.append(limit)

        return [
            Hit("episode", int(r["id"]), 0.0, r["title"], r["body"], r["ts"])
            for r in self.db.execute(sql, tuple(args)).fetchall()
        ]

    # ---- 망각 -----------------------------------------------------

    def archive_stale(self, *, older_than_days: float = 90) -> int:
        """오래됐고 최근에 참조되지 않은 일화를 접는다.

        누적 접근 횟수가 아니라 '마지막으로 불려나온 시점'으로 판단한다.
        3년 전에 열 번 본 기억은 지금 필요한 기억이 아니고, 어제 한 번
        본 기억은 살아있는 기억이다.

        지우지 않고 archived 표시만 한다. 검색에서 빠지되 복구는 가능하다.
        """
        cutoff = time.time() - older_than_days * 86400
        cur = self.db.execute(
            "UPDATE episodes SET archived = 1"
            " WHERE archived = 0 AND ts < ?"
            "   AND (last_accessed IS NULL OR last_accessed < ?)"
            "   AND importance < 0.8",
            (cutoff, cutoff),
        )
        self.db.commit()
        return cur.rowcount
