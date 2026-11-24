-- Службова база даних журналу SQL Driver (6 сутностей, див. ПР 1.4).

CREATE TABLE IF NOT EXISTS database_files (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    file_path   TEXT    NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS connections (
    id           INTEGER PRIMARY KEY,
    database_id  INTEGER NOT NULL REFERENCES database_files(id) ON DELETE RESTRICT,
    opened_at    TEXT    NOT NULL,
    closed_at    TEXT,
    status       TEXT    NOT NULL CHECK (status IN ('OPEN', 'CLOSED'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id             INTEGER PRIMARY KEY,
    connection_id  INTEGER NOT NULL REFERENCES connections(id) ON DELETE RESTRICT,
    started_at     TEXT    NOT NULL,
    ended_at       TEXT,
    outcome        TEXT    NOT NULL CHECK (outcome IN ('OPEN', 'COMMIT', 'ROLLBACK'))
);

CREATE TABLE IF NOT EXISTS queries (
    id              INTEGER PRIMARY KEY,
    connection_id   INTEGER NOT NULL REFERENCES connections(id) ON DELETE RESTRICT,
    transaction_id  INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
    sql_text        TEXT    NOT NULL,
    query_type      TEXT    NOT NULL
                    CHECK (query_type IN ('SELECT', 'DML', 'DDL', 'TCL', 'OTHER')),
    executed_at     TEXT    NOT NULL,
    duration_ms     REAL    NOT NULL CHECK (duration_ms >= 0),
    rows_affected   INTEGER,
    status          TEXT    NOT NULL CHECK (status IN ('SUCCESS', 'ERROR'))
);

CREATE TABLE IF NOT EXISTS query_parameters (
    id          INTEGER PRIMARY KEY,
    query_id    INTEGER NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
    position    TEXT    NOT NULL,
    value_text  TEXT,
    value_type  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS error_records (
    id           INTEGER PRIMARY KEY,
    query_id     INTEGER NOT NULL UNIQUE REFERENCES queries(id) ON DELETE CASCADE,
    error_type   TEXT    NOT NULL,
    message      TEXT    NOT NULL,
    occurred_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_queries_executed_at ON queries(executed_at);
