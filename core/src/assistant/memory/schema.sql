-- 기억 스키마 (ARCHITECTURE §5)
--
-- 일화(episodes): "무엇이 있었나". 시간축을 가진 사건 기록.
-- 의미(facts):    "무엇이 사실인가". 시간축이 없는 선호·결정·관계.
-- 임베딩은 두 계층이 공유하는 별도 테이블에 둔다.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS episodes (
    id            INTEGER PRIMARY KEY,
    ts            REAL    NOT NULL,
    kind          TEXT    NOT NULL,      -- conversation | commit | calendar | file | note
    session_id    TEXT    NOT NULL DEFAULT '',
    title         TEXT    NOT NULL,
    body          TEXT    NOT NULL DEFAULT '',
    source        TEXT    NOT NULL DEFAULT '',

    -- 망각 정책용. 참조되지 않는 기억은 접혀서 아카이브된다.
    importance    REAL    NOT NULL DEFAULT 0.5,
    access_count  INTEGER NOT NULL DEFAULT 0,
    last_accessed REAL,
    archived      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_episodes_ts   ON episodes(ts DESC);
CREATE INDEX IF NOT EXISTS idx_episodes_kind ON episodes(kind, ts DESC);

CREATE TABLE IF NOT EXISTS facts (
    id            INTEGER PRIMARY KEY,
    created_ts    REAL    NOT NULL,
    updated_ts    REAL    NOT NULL,
    subject       TEXT    NOT NULL,      -- 무엇에 대한 사실인가
    body          TEXT    NOT NULL,
    confidence    REAL    NOT NULL DEFAULT 0.5,
    evidence      INTEGER NOT NULL DEFAULT 1,   -- 뒷받침한 일화 수

    -- 사실은 지우지 않고 대체한다. 틀린 기억을 고친 이력이 남아야 한다.
    superseded_by INTEGER REFERENCES facts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_facts_subject ON facts(subject);
CREATE INDEX IF NOT EXISTS idx_facts_live    ON facts(superseded_by) WHERE superseded_by IS NULL;

CREATE TABLE IF NOT EXISTS embeddings (
    owner_type TEXT NOT NULL,            -- episode | fact
    owner_id   INTEGER NOT NULL,
    model      TEXT NOT NULL,
    dim        INTEGER NOT NULL,
    vec        BLOB NOT NULL,            -- float32 리틀엔디언
    PRIMARY KEY (owner_type, owner_id)
);

-- BM25용 전문 검색. 벡터만으로는 파일명·고유명사 질의에서 자주 빗나간다.
CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
    title, body, content='episodes', content_rowid='id', tokenize='unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    subject, body, content='facts', content_rowid='id', tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
    INSERT INTO episodes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
    INSERT INTO episodes_fts(episodes_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
END;

CREATE TRIGGER IF NOT EXISTS episodes_au AFTER UPDATE ON episodes BEGIN
    INSERT INTO episodes_fts(episodes_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
    INSERT INTO episodes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(rowid, subject, body) VALUES (new.id, new.subject, new.body);
END;

CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, subject, body)
    VALUES ('delete', old.id, old.subject, old.body);
END;

CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, subject, body)
    VALUES ('delete', old.id, old.subject, old.body);
    INSERT INTO facts_fts(rowid, subject, body) VALUES (new.id, new.subject, new.body);
END;
