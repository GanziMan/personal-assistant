"""문서 색인.

SQLite 파일 하나에 청크와 벡터를 담는다. 기억 DB 와 분리한다 —
기억은 사용자와 비서 사이에 있었던 일이고, 이쪽은 디스크에 이미
존재하는 파일의 파생물이다. 언제든 지우고 다시 만들 수 있어야 한다.

변경 감지는 (경로, 크기, mtime) 으로 한다. 내용 해시를 매번 뜨면
수천 개 파일에서 색인이 느려지고, 이 세 값이 같은데 내용만 다른
경우는 실질적으로 없다.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS documents (
    path      TEXT PRIMARY KEY,
    size      INTEGER NOT NULL,
    mtime     REAL    NOT NULL,
    indexed   REAL    NOT NULL,
    chunks    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chunks (
    id      INTEGER PRIMARY KEY,
    path    TEXT NOT NULL REFERENCES documents(path) ON DELETE CASCADE,
    seq     INTEGER NOT NULL,
    text    TEXT NOT NULL,
    vec     BLOB
);

CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text, content='chunks', content_rowid='id', tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;
"""


@dataclass(slots=True)
class Stored:
    id: int
    path: str
    seq: int
    text: str


class DocIndex:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    # ---- 변경 감지 -------------------------------------------------

    def needs_index(self, file: Path) -> bool:
        try:
            stat = file.stat()
        except OSError:
            return False
        row = self.db.execute(
            "SELECT size, mtime FROM documents WHERE path = ?", (str(file),)
        ).fetchone()
        if row is None:
            return True
        return row["size"] != stat.st_size or abs(row["mtime"] - stat.st_mtime) > 1.0

    def forget(self, path: str) -> None:
        self.db.execute("DELETE FROM chunks WHERE path = ?", (path,))
        self.db.execute("DELETE FROM documents WHERE path = ?", (path,))
        self.db.commit()

    def prune_missing(self) -> int:
        """사라진 파일의 색인을 지운다."""
        rows = self.db.execute("SELECT path FROM documents").fetchall()
        gone = [r["path"] for r in rows if not Path(r["path"]).exists()]
        for path in gone:
            self.forget(path)
        return len(gone)

    # ---- 적재 -----------------------------------------------------

    def put(self, file: Path, texts: list[str], vectors: list[bytes | None]) -> None:
        stat = file.stat()
        self.forget(str(file))

        self.db.execute(
            "INSERT INTO documents (path, size, mtime, indexed, chunks)"
            " VALUES (?,?,?,?,?)",
            (str(file), stat.st_size, stat.st_mtime, time.time(), len(texts)),
        )
        self.db.executemany(
            "INSERT INTO chunks (path, seq, text, vec) VALUES (?,?,?,?)",
            [(str(file), i, t, v) for i, (t, v) in enumerate(zip(texts, vectors, strict=True))],
        )
        self.db.commit()

    # ---- 조회 -----------------------------------------------------

    def keyword(self, query: str, *, limit: int = 30) -> list[int]:
        tokens = [t for t in query.replace('"', " ").split() if t]
        if not tokens:
            return []
        match = " OR ".join(f'"{t}"' for t in tokens)
        rows = self.db.execute(
            "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
            (match, limit),
        ).fetchall()
        return [int(r["rowid"]) for r in rows]

    def vectors(self) -> list[tuple[int, bytes]]:
        rows = self.db.execute(
            "SELECT id, vec FROM chunks WHERE vec IS NOT NULL"
        ).fetchall()
        return [(int(r["id"]), r["vec"]) for r in rows]

    def fetch(self, ids: list[int]) -> list[Stored]:
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        rows = self.db.execute(
            f"SELECT id, path, seq, text FROM chunks WHERE id IN ({placeholders})",  # noqa: S608
            tuple(ids),
        ).fetchall()
        return [Stored(int(r["id"]), r["path"], int(r["seq"]), r["text"]) for r in rows]

    def stats(self) -> tuple[int, int, float]:
        row = self.db.execute(
            "SELECT COUNT(*) AS docs, COALESCE(SUM(chunks), 0) AS chunks,"
            " COALESCE(MAX(indexed), 0) AS last FROM documents"
        ).fetchone()
        return int(row["docs"]), int(row["chunks"]), float(row["last"])
