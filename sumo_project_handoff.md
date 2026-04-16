# Sumo Match Prediction Project Handoff

## Project goal

Build a model to predict **sumo match outcomes** using:
- wrestler physical attributes
- rank and career strength
- recent form
- matchup-specific features
- rolling tournament information known **before** each bout

The immediate work completed focused on the **March 2026 Osaka basho (Haru 2026), Makuuchi division**.

---

## Files already created

### 1) Day 1 results
- `haru_2026_day1_makuuchi_results.csv`

Columns:
- `East wrestler`
- `West wrestler`
- `Winner`

### 2) All 15 days of March 2026 Makuuchi results
- `haru_2026_makuuchi_all_days_results.csv`
- `haru_2026_makuuchi_all_days_results.xlsx`

Columns:
- `Day`
- `East wrestler`
- `West wrestler`
- `Winner`

Notes:
- 298 total Makuuchi bouts were captured across all 15 days.

### 3) Wrestler attribute table
- `haru_2026_makuuchi_wrestler_attributes.xlsx`
- `haru_2026_makuuchi_wrestler_attributes.csv`

Later expanded to:
- `haru_2026_makuuchi_wrestler_attributes_v2.xlsx`
- `haru_2026_makuuchi_wrestler_attributes_v2.csv`

Columns include:
- `Wrestler`
- `Current rank`
- `Height`
- `Weight`
- `Signature maneuver / style`
- `Official JSA career record`
- `March 2026 wins / losses / absences`
- `Estimated pre-tournament overall record`
- `JSA profile URL`

Added later:
- `Makuuchi Records`
- `2026 January Record`
- `Most-Used Winning Technique`

### 4) Model-ready March 2026 training table
- `haru_2026_match_training_database.csv`
- `haru_2026_match_training_database.xlsx`

This is the most important output so far.

It contains:
- one row per March 2026 Makuuchi bout
- East/West wrestler identifiers
- target label `east_wins`
- East and West static wrestler attributes
- difference / matchup features
- rolling March pre-match features

---

## Main data sources used

### Official fact-check source
**Japan Sumo Association (JSA) rikishi profile pages**
Used for:
- rank
- height
- weight
- style / signature maneuver
- career record
- Makuuchi record
- January 2026 record
- most-used winning technique

Example profile pattern:
- `https://www.sumo.or.jp/EnSumoDataRikishi/profile/<id>/`

### Official tournament source
**JSA torikumi / results pages**
Used as the tournament reference for:
- daily match schedule
- daily results

Example:
- `https://www.sumo.or.jp/EnHonbashoMain/torikumi/1/1/`

### Structured source used to assemble day-by-day data
**Sumo API**
Used for:
- day-level torikumi / results extraction
- easier structured access than JSA HTML alone

Reference:
- `https://www.sumo-api.com/`
- API guide:
  - `https://www.sumo-api.com/api-guide`

---

## What was done so far

### Step 1: Match results table
A day-by-day Makuuchi results table for March 2026 was created with:
- day
- east wrestler
- west wrestler
- winner

### Step 2: Wrestler attributes table
A wrestler-level table was built containing:
- physical attributes
- rank
- style
- career strength indicators
- January 2026 performance
- Makuuchi-specific record
- top winning technique

### Step 3: Combined training database
The wrestler-level attributes were merged twice into the match table:
- once for East
- once for West

This produced a **match-level supervised learning table**.

### Step 4: Model framing
The recommended target setup is:

- one row per bout
- target = `east_wins`
  - `1` if East won
  - `0` if West won

This was chosen instead of winner-loser formatting because East/West is known **before** the match.

---

## Recommended modeling structure

## Why East vs West is the right setup

Use **East-West**, not **winner-loser**, for the model.

Why:
- East and West are known before the bout
- winner/loser is only known after the bout
- East/West makes it easy to create a clean binary target:
  - `east_wins = 1` or `0`

---

## Feature engineering guidance

The best setup is to keep a mix of:

1. **Absolute features**
2. **Relative / difference features**
3. **Interaction / matchup features**

### Absolute features to preserve
These should usually be kept in original form for both wrestlers:
- `east_weight`, `west_weight`
- `east_height`, `west_height`
- `east_rank_num`, `west_rank_num`
- `east_career_bouts`, `west_career_bouts`
- `east_career_winpct`, `west_career_winpct`
- `east_makuuchi_bouts`, `west_makuuchi_bouts`
- `east_makuuchi_winpct`, `west_makuuchi_winpct`
- `east_jan_wins`, `west_jan_wins`
- `east_jan_losses`, `west_jan_losses`
- `east_style`, `west_style`
- `east_top_technique`, `west_top_technique`

### Relative features to create
These are often the most predictive:
- `weight_diff = east_weight - west_weight`
- `height_diff = east_height - west_height`
- `rank_diff`
- `career_winpct_diff`
- `makuuchi_winpct_diff`
- `jan_winpct_diff`
- `current_basho_winpct_diff`
- `prior_day_win_diff`
- `streak_diff`
- `h2h_winpct_east`

### Matchup / interaction features
Useful examples:
- `same_style`
- `style_matchup = east_style + "_vs_" + west_style`
- `technique_matchup = east_top_technique + "_vs_" + west_top_technique`

---

## Ranking conversion

Ranks should be converted to numeric values.

A reasonable approach:
- Yokozuna = 1
- Ozeki = 2
- Sekiwake = 3
- Komusubi = 4
- Maegashira 1 = 5
- Maegashira 2 = 6
- etc.

Then create:
- `east_rank_num`
- `west_rank_num`
- `rank_diff = west_rank_num - east_rank_num`

This makes positive `rank_diff` mean East is higher ranked.

Codex should implement rank parsing carefully because rank strings can contain:
- side marker (East/West)
- rank tier
- rank number

---

## Important leakage rule

Every feature for a match must use only information available **before that match**.

For example:
- predicting Day 13 can use data from Days 1–12
- predicting Day 14 can use data from Days 1–13
- predicting Day 15 can use data from Days 1–14

Do **not** use:
- final tournament records
- future results
- any end-of-basho summaries when building pre-match features

This is critical.

---

## Recommended evaluation strategy

Because this is a rolling tournament forecasting problem, do **not** just make one static random split.

### Good tournament-day split for March 2026
Recommended approach:
- **Train** on Days 2–10
- **Validate / tune** on Days 11–12
- **Test** on Day 13
- **Additional holdout evaluation** on Days 14 and 15

Even better once more data is available:
- train on older tournaments
- validate on a later tournament
- test on March 2026

### Metrics to report
Do not rely only on accuracy.

Use:
- **Accuracy**
- **Log loss**
- **Brier score**
- optionally **AUC**

Best reporting:
- Day 13 accuracy / log loss / Brier
- Day 14 accuracy / log loss / Brier
- Day 15 accuracy / log loss / Brier
- combined Days 13–15 summary

### Baselines to compare against
At minimum, compare the model to:
1. Higher-ranked wrestler always wins
2. Better current March record entering the day wins
3. Better January 2026 record wins

If the model does not beat these baselines, it is not adding much value.

---

## What the final model could look like

### Simple interpretable model
**Logistic Regression**

Good starting features:
- `rank_diff`
- `weight_diff`
- `height_diff`
- `jan_winpct_diff`
- `current_basho_winpct_diff`
- `prior_day_win_diff`
- `career_winpct_diff`

This is useful for explainability.

### Stronger tabular model
**XGBoost** or **LightGBM**

Use:
- East raw features
- West raw features
- difference features
- categorical matchup variables

This will likely outperform logistic regression on tabular data.

### Output
The model should produce:
- `P(East wins)`

And then:
- predicted winner = East if probability > 0.5, else West

---

## What Codex should do next

The next step is to turn this from a one-tournament prototype into a real training pipeline across many tournaments and years.

### Priority 1: Expand to more historical data
Codex should pull:
- multiple years of basho results
- preferably all Makuuchi tournaments available
- eventually Juryo too only if desired later

For each tournament/day/match:
- basho id
- year
- month
- day
- division
- east wrestler
- west wrestler
- winner
- kimarite if available
- absences / fusen info if available

### Priority 2: Build historical wrestler snapshots
For each match, Codex should create a **pre-match snapshot** containing:
- career record entering the bout
- Makuuchi record entering the bout
- current basho record entering the bout
- previous tournament record(s)
- January/previous basho form
- height / weight / rank / style / top technique
- days since last bout if relevant
- prior-day result
- streak entering the bout

### Priority 3: Add head-to-head features
Very important additions:
- lifetime East-vs-West head-to-head before the match
- head-to-head match count
- recent head-to-head form
- maybe kimarite-specific matchup history if available

### Priority 4: Add rolling form features
Before each bout:
- last 3 matches win %
- last 5 matches win %
- last 10 matches win %
- opponent-adjusted recent strength if possible
- Elo rating before the bout
- Glicko if desired

### Priority 5: Build reusable ETL pipeline
Codex should separate the work into three layers:

#### A. Raw tables
- `raw_matches`
- `raw_wrestlers`
- `raw_banzuke`
- `raw_profiles`
- `raw_kimarite`

#### B. Clean modeling tables
- `wrestlers_master`
- `matches_master`

#### C. Feature tables
- `match_features_prebout`
- `day13_prediction_snapshot`
- `day14_prediction_snapshot`
- `day15_prediction_snapshot`

This should be reproducible from scratch.

---

## Suggested file/database schema

### Wrestlers master
Suggested columns:
- `wrestler_id`
- `shikona_en`
- `heya`
- `height_cm`
- `weight_kg`
- `birth_date`
- `style`
- `top_technique`
- `rank_text`
- `rank_num`
- `career_wins`
- `career_losses`
- `career_absences`
- `makuuchi_wins`
- `makuuchi_losses`
- `makuuchi_absences`

### Matches master
Suggested columns:
- `basho_id`
- `year`
- `month`
- `day`
- `division`
- `east_wrestler`
- `west_wrestler`
- `winner`
- `east_wins`
- `kimarite`
- `fusen_flag`

### Match features pre-bout
Suggested columns:
- identifiers
- East raw features
- West raw features
- difference features
- head-to-head features
- rolling recent-form features
- Elo / rating features
- target label

---

## Example training row structure

A match-level row should look like:

- `basho_id`
- `day`
- `east_wrestler`
- `west_wrestler`
- `east_wins`
- `east_weight`
- `west_weight`
- `weight_diff`
- `east_height`
- `west_height`
- `height_diff`
- `east_rank_num`
- `west_rank_num`
- `rank_diff`
- `east_career_winpct`
- `west_career_winpct`
- `career_winpct_diff`
- `east_makuuchi_winpct`
- `west_makuuchi_winpct`
- `makuuchi_winpct_diff`
- `east_jan_winpct`
- `west_jan_winpct`
- `jan_winpct_diff`
- `east_current_basho_winpct`
- `west_current_basho_winpct`
- `current_basho_winpct_diff`
- `east_prior_day_win`
- `west_prior_day_win`
- `prior_day_win_diff`
- `east_style`
- `west_style`
- `same_style`
- `east_top_technique`
- `west_top_technique`
- `style_matchup`
- `technique_matchup`
- `h2h_east_winpct`
- `h2h_match_count`

---

## Implementation notes for Codex

### 1. Keep scraping and feature generation separate
Do not mix scraping logic directly into modeling notebooks.
Use scripts/modules such as:
- `fetch_profiles.py`
- `fetch_matches.py`
- `build_wrestlers_master.py`
- `build_match_features.py`
- `train_model.py`

### 2. Build id mapping carefully
Names can vary across sources.
Create a stable `wrestler_id` and a mapping layer between:
- API identifiers
- JSA profile ids
- English shikona strings

### 3. Preserve raw data
Always save raw JSON/HTML/API responses so the dataset can be reproduced and audited.

### 4. Version features
Have a clear versioned output:
- `features_v1.csv`
- `features_v2.csv`

### 5. Evaluate chronologically
Never use random cross-validation across time if it mixes future and past.

Use:
- rolling backtests by basho
- train on earlier tournaments, test on later tournaments

### 6. Add calibration
Because this is a probability problem, check calibration plots and possibly use:
- isotonic calibration
- Platt scaling

---

## Suggested modeling roadmap

### Version 1
- one tournament
- static features
- current basho features
- logistic regression
- XGBoost
- accuracy/log loss/Brier

### Version 2
- many tournaments
- head-to-head
- rolling form
- Elo
- stronger time-based evaluation

### Version 3
- kimarite / style matchup details
- division-specific models
- richer ranking and promotion/demotion context
- calibration analysis
- SHAP / feature importance

---

## Short answer for Codex

Build a **historical, pre-bout, match-level dataset** where each row predicts whether the **East wrestler wins**, using only information available before that bout. Expand beyond March 2026 to many tournaments and years, engineer rolling and head-to-head features, and evaluate using time-based holdouts with accuracy, log loss, and Brier score.
