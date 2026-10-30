-- Operational metadata: one row per league/season load, plus quarantined bad rows.

CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    league_code     TEXT        NOT NULL,
    season          CHAR(4)     NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'succeeded', 'failed', 'skipped')),
    rows_extracted  INTEGER,
    rows_rejected   INTEGER,
    rows_duplicate  INTEGER,
    rows_loaded     INTEGER,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS ix_runs_league_season ON ingestion_runs (league_code, season, started_at DESC);

-- Rows that failed validation are kept (as JSON) with the reason, never silently dropped.
CREATE TABLE IF NOT EXISTS rejected_rows (
    reject_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id        BIGINT NOT NULL REFERENCES ingestion_runs (run_id) ON DELETE CASCADE,
    reject_reason TEXT   NOT NULL,
    row_data      JSONB  NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_rejected_run ON rejected_rows (run_id);
