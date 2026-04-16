# Sumo Data Foundation

This project builds the data foundation for pre-bout Makuuchi match prediction.
The first production ingestion stage is intentionally limited to 2025 plus
available 2026 basho so the data can be validated before pulling 2010-2024.

## Storage Layout

The pipeline uses three layers:

- `data/raw/`: exact cached source responses from Sumo API and optional JSA
  profile pages. These files make runs auditable and reproducible.
- `data/sumo.db`: canonical SQLite database with raw and normalized tables.
  SQLite is the source of truth for joins and validation.
- `data/exports/`: generated CSV and Markdown validation outputs for review.

CSV files are intentionally exports rather than the canonical store, because
multi-year sumo data has relational structure: matches, wrestlers, banzuke rows,
profiles, and validation checks all need stable joins.

## First Validation Run

Run the 2025 plus available 2026 validation stage:

```powershell
python -m sumo_data run-validation --start-year 2025 --end-year 2026
```

To also cache raw JSA profile HTML for wrestlers with an `nskId`:

```powershell
python -m sumo_data run-validation --start-year 2025 --end-year 2026 --fetch-jsa-profiles
```

The broader historical backfill should wait until the validation exports look
acceptable:

```powershell
python -m sumo_data download --start-year 2010 --end-year 2024
python -m sumo_data validate
```

## Useful Outputs

- `data/exports/matches_master.csv`
- `data/exports/wrestlers_master.csv`
- `data/exports/banzuke_master.csv`
- `data/exports/validation_report.md`
- `data/exports/validation_basho_summary.csv`
- `data/exports/validation_bout_counts_by_basho_day.csv`
- `data/exports/validation_fixture_overlap_haru_2026.csv`

## Tests

```powershell
python -m unittest discover -s tests
```
