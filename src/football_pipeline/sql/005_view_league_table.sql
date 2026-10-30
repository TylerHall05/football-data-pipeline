-- Standings per league and season. Ranked by points, then goal difference, then goals scored.
CREATE OR REPLACE VIEW v_league_table AS
WITH totals AS (
    SELECT league_code, season, team,
           count(*)                         AS played,
           count(*) FILTER (WHERE points = 3) AS won,
           count(*) FILTER (WHERE points = 1) AS drawn,
           count(*) FILTER (WHERE points = 0) AS lost,
           sum(goals_for)                   AS goals_for,
           sum(goals_against)               AS goals_against,
           sum(goals_for - goals_against)   AS goal_difference,
           sum(points)                      AS points
    FROM v_team_matches
    GROUP BY league_code, season, team
)
SELECT rank() OVER (
           PARTITION BY league_code, season
           ORDER BY points DESC, goal_difference DESC, goals_for DESC
       ) AS position,
       totals.*
FROM totals;
