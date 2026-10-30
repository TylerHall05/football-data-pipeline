-- Reference (dimension) tables. All DDL is idempotent so migrations can be re-run safely.

CREATE TABLE IF NOT EXISTS leagues (
    league_code TEXT PRIMARY KEY,            -- football-data.co.uk code, e.g. 'E0'
    name        TEXT NOT NULL,
    country     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE             -- cleaned name; aliases are resolved upstream
);
