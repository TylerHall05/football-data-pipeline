# Football Data Pipeline

An end-to-end data engineering project: extract football match data from
[football-data.co.uk](https://www.football-data.co.uk/), clean and validate it
with Python, load it into PostgreSQL with SQL, and explore it in a dashboard.

> Work in progress. This README grows as the pipeline is built.

## Planned stages

1. **Extract** - download season CSVs, cache raw files
2. **Transform** - clean, type, deduplicate and validate
3. **Load** - idempotent upserts into PostgreSQL
4. **Analyse** - SQL views (league table, form, season summary)
5. **Serve** - Streamlit dashboard
6. **Automate** - tests, CI and scheduled updates
