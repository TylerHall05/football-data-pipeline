-- League-level headline stats per season: scoring rate and home advantage.
CREATE OR REPLACE VIEW v_season_summary AS
SELECT league_code, season,
       count(*)                                                          AS matches,
       round(avg(home_goals + away_goals), 2)                            AS goals_per_match,
       round(100.0 * count(*) FILTER (WHERE result = 'H') / count(*), 1) AS home_win_pct,
       round(100.0 * count(*) FILTER (WHERE result = 'D') / count(*), 1) AS draw_pct,
       round(100.0 * count(*) FILTER (WHERE result = 'A') / count(*), 1) AS away_win_pct,
       round(avg(home_yellows + away_yellows), 2)                        AS yellows_per_match,
       round(avg(home_shots + away_shots), 1)                            AS shots_per_match
FROM v_match_results
GROUP BY league_code, season;
