-- Base analytical views. Everything downstream (league table, form, dashboard) builds on these.

-- Matches with readable team names.
CREATE OR REPLACE VIEW v_match_results AS
SELECT m.match_id, m.league_code, m.season, m.match_date, m.kickoff_time,
       h.name AS home_team, a.name AS away_team,
       m.home_goals, m.away_goals, m.result,
       m.home_shots, m.away_shots, m.home_corners, m.away_corners,
       m.home_yellows, m.away_yellows, m.home_reds, m.away_reds
FROM matches m
JOIN teams h ON h.team_id = m.home_team_id
JOIN teams a ON a.team_id = m.away_team_id;

-- "Long" format: each match appears twice, once from each team's point of view.
-- This makes per-team aggregation (tables, form) a simple GROUP BY.
CREATE OR REPLACE VIEW v_team_matches AS
SELECT match_id, league_code, season, match_date,
       home_team AS team, away_team AS opponent, TRUE AS is_home,
       home_goals AS goals_for, away_goals AS goals_against,
       CASE result WHEN 'H' THEN 3 WHEN 'D' THEN 1 ELSE 0 END AS points
FROM v_match_results
UNION ALL
SELECT match_id, league_code, season, match_date,
       away_team, home_team, FALSE,
       away_goals, home_goals,
       CASE result WHEN 'A' THEN 3 WHEN 'D' THEN 1 ELSE 0 END
FROM v_match_results;
