-- Cumulative points after each of a team's matches: the data behind a "title race" chart.
CREATE OR REPLACE VIEW v_points_progression AS
SELECT league_code, season, team, match_date,
       row_number() OVER w AS matchweek,
       sum(points) OVER w  AS cumulative_points,
       sum(goals_for - goals_against) OVER w AS cumulative_goal_difference
FROM v_team_matches
WINDOW w AS (PARTITION BY league_code, season, team ORDER BY match_date, match_id);
