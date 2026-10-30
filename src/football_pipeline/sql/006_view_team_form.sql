-- Recent form: each team's last five matches per league and season,
-- with a W/D/L string ordered oldest -> newest (e.g. 'WWDLW').
CREATE OR REPLACE VIEW v_team_form AS
WITH ranked AS (
    SELECT *,
           row_number() OVER (
               PARTITION BY league_code, season, team
               ORDER BY match_date DESC, match_id DESC
           ) AS games_ago
    FROM v_team_matches
)
SELECT league_code, season, team,
       count(*)                AS games,
       sum(points)             AS points_last_5,
       string_agg(CASE points WHEN 3 THEN 'W' WHEN 1 THEN 'D' ELSE 'L' END, ''
                  ORDER BY match_date, match_id) AS form,
       sum(goals_for)          AS goals_for,
       sum(goals_against)      AS goals_against
FROM ranked
WHERE games_ago <= 5
GROUP BY league_code, season, team;
