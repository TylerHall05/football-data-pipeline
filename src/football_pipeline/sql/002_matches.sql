-- Fact table: one row per played match.
-- Constraints mirror the Python validation rules so bad data cannot enter even if the
-- application layer is bypassed.

CREATE TABLE IF NOT EXISTS matches (
    match_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    league_code  TEXT     NOT NULL REFERENCES leagues (league_code),
    season       CHAR(4)  NOT NULL CHECK (season ~ '^[0-9]{4}$'),
    match_date   DATE     NOT NULL,
    kickoff_time TIME,
    home_team_id INTEGER  NOT NULL REFERENCES teams (team_id),
    away_team_id INTEGER  NOT NULL REFERENCES teams (team_id),
    home_goals   SMALLINT NOT NULL CHECK (home_goals BETWEEN 0 AND 20),
    away_goals   SMALLINT NOT NULL CHECK (away_goals BETWEEN 0 AND 20),
    result       CHAR(1)  NOT NULL CHECK (result IN ('H', 'D', 'A')),
    ht_home_goals SMALLINT CHECK (ht_home_goals >= 0),
    ht_away_goals SMALLINT CHECK (ht_away_goals >= 0),
    ht_result    CHAR(1)  CHECK (ht_result IN ('H', 'D', 'A')),
    referee      TEXT,
    home_shots            SMALLINT CHECK (home_shots >= 0),
    away_shots            SMALLINT CHECK (away_shots >= 0),
    home_shots_on_target  SMALLINT CHECK (home_shots_on_target >= 0),
    away_shots_on_target  SMALLINT CHECK (away_shots_on_target >= 0),
    home_fouls            SMALLINT CHECK (home_fouls >= 0),
    away_fouls            SMALLINT CHECK (away_fouls >= 0),
    home_corners          SMALLINT CHECK (home_corners >= 0),
    away_corners          SMALLINT CHECK (away_corners >= 0),
    home_yellows          SMALLINT CHECK (home_yellows >= 0),
    away_yellows          SMALLINT CHECK (away_yellows >= 0),
    home_reds             SMALLINT CHECK (home_reds >= 0),
    away_reds             SMALLINT CHECK (away_reds >= 0),
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Natural key: the target of the loader's ON CONFLICT upsert.
    CONSTRAINT uq_match_fixture UNIQUE (league_code, season, match_date, home_team_id, away_team_id),
    CONSTRAINT ck_different_teams CHECK (home_team_id <> away_team_id),
    CONSTRAINT ck_result_matches_score CHECK (
        result = CASE
            WHEN home_goals > away_goals THEN 'H'
            WHEN home_goals < away_goals THEN 'A'
            ELSE 'D'
        END
    )
);

CREATE INDEX IF NOT EXISTS ix_matches_league_season ON matches (league_code, season);
CREATE INDEX IF NOT EXISTS ix_matches_home_team ON matches (home_team_id);
CREATE INDEX IF NOT EXISTS ix_matches_away_team ON matches (away_team_id);
