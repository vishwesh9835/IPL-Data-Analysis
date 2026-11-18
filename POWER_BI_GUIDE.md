# Power BI Guide — IPL Analytics

This guide builds a four-page Power BI report from the **same cleaned data the notebook analysed**, so every number in the report can be checked against the notebook.

> **About the `.pbix` file:** a `.pbix` can only be created and saved by Power BI Desktop (Windows). It cannot be generated from code or edited by an AI tool. This guide, the theme and the notebook export get you there in roughly 45 minutes; save the result as `IPL_Dashboard.pbix`. On Mac, use the Power BI web service (app.powerbi.com) with the same CSV files.

> **Power BI is optional for this project.** `dashboard.html` already gives an interactive view (season range, team and venue-sample filters) built from the same cleaned tables. Build the Power BI report if you want the skill on your portfolio; Power BI Desktop is a free download (Windows) if it needs reinstalling.

---

## 0. What you need

| Item | Where it comes from |
|------|---------------------|
| `powerbi/matches_clean.csv`, `powerbi/team_matches.csv`, `powerbi/deliveries_clean.csv` | Run `ipl_final.ipynb` top to bottom (Section 14) |
| `powerbi_kit/IPL_Theme.json` | This repository |
| Power BI Desktop | Free download from Microsoft |

**Why not clean the raw CSVs inside Power BI?** Two sets of cleaning rules drift apart. The notebook already fixes seasons, team names (in both files), venue names and missing values; the export applies those fixes once and the report reads the result.

What the export changes compared with the notebook's in-memory data:

- `-1` placeholders in `result_margin`, `target_runs`, `target_overs` become real NULLs, so averages are not polluted.
- `team_matches.csv` has one row per team per match, so win % is a plain `SUM / COUNT`.
- `deliveries_clean.csv` carries ready-made flags (`balls_faced`, `legal_delivery`, `bowler_runs`, `bowler_wicket`, `is_four`, `is_six`) that follow the same cricket rules as the notebook: wides are not balls faced, byes and leg-byes are not charged to the bowler, run-outs and retirements are not bowler wickets.

---

## 1. Load the data (Power Query)

1. **Home → Transform data → Manage Parameters → New Parameter**
   - Name: `DataFolder`, Type: Text, Current value: the full path to your `powerbi` folder **ending with a backslash**, e.g. `C:\Projects\IPL\powerbi\`
2. **Home → New Source → Blank Query → Advanced Editor**, one query per table. Paste each block below and rename the query to `matches`, `team_matches`, `deliveries`.

The path comes from the parameter, so the report works on any machine after changing one value.

**`matches`**

```powerquery
let
    Source   = Csv.Document(File.Contents(DataFolder & "matches_clean.csv"),
                 [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                 {"id", Int64.Type}, {"season", Int64.Type}, {"date", type date},
                 {"result_margin", type number}, {"target_runs", type number},
                 {"target_overs", type number}, {"toss_winner_won", Int64.Type}
               }, "en-US")
in
    Typed
```

**`team_matches`**

```powerquery
let
    Source   = Csv.Document(File.Contents(DataFolder & "team_matches.csv"),
                 [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                 {"match_id", Int64.Type}, {"season", Int64.Type}, {"date", type date},
                 {"result_margin", type number}, {"won", Int64.Type}, {"no_result", Int64.Type},
                 {"lost", Int64.Type}, {"toss_won", Int64.Type}
               }, "en-US")
in
    Typed
```

**`deliveries`**

```powerquery
let
    Source   = Csv.Document(File.Contents(DataFolder & "deliveries_clean.csv"),
                 [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                 {"match_id", Int64.Type}, {"inning", Int64.Type}, {"over", Int64.Type}, {"ball", Int64.Type},
                 {"batsman_runs", Int64.Type}, {"extra_runs", Int64.Type}, {"total_runs", Int64.Type},
                 {"is_wicket", Int64.Type}, {"balls_faced", Int64.Type}, {"legal_delivery", Int64.Type},
                 {"bowler_runs", Int64.Type}, {"bowler_wicket", Int64.Type},
                 {"is_four", Int64.Type}, {"is_six", Int64.Type}
               }, "en-US")
in
    Typed
```

Click **Close & Apply**.

> Do **not** add team-name replacements here. The export is already cleaned (Royal Challengers **Bangalore**, Punjab Kings, Delhi Capitals, Rising Pune Supergiant). Re-mapping in Power Query would make the report disagree with the notebook.

---

## 2. Data model

Open **Model view** and create two relationships (both many-to-one, single direction):

```text
matches[id]  1 ───────►  * team_matches[match_id]
matches[id]  1 ───────►  * deliveries[match_id]
```

- `matches` acts as the shared dimension: a **season** or **venue** slicer built on `matches` filters both fact tables.
- A **team** slicer should use `team_matches[team]` and drives the team pages only. Do not relate teams to `deliveries` as well: that would create two filter paths and ambiguous results.
- No separate date or player tables are needed. `batter` and `bowler` are used directly from `deliveries`.

---

## 3. DAX measures

Create an empty table to hold them: **Home → Enter Data**, name it `_Measures`, load, then **New measure** for each item below.

```dax
-- Overview
Total Matches = COUNTROWS ( matches )
Seasons       = DISTINCTCOUNT ( matches[season] )
Venues        = DISTINCTCOUNT ( matches[venue] )

-- Teams (team_matches has one row per team per match)
Matches Played = COUNTROWS ( team_matches )
Wins           = SUM ( team_matches[won] )
Win %          = DIVIDE ( [Wins], [Matches Played] )
Seasons Played = DISTINCTCOUNT ( team_matches[season] )
Finals Played  = CALCULATE ( COUNTROWS ( team_matches ), team_matches[match_type] = "Final" )
Titles         = CALCULATE ( SUM ( team_matches[won] ), team_matches[match_type] = "Final" )
Finals per Season % = DIVIDE ( [Finals Played], [Seasons Played] )

-- Toss (toss_winner_won is blank for no-result matches, so they drop out automatically)
Matches With a Result = COUNT ( matches[toss_winner_won] )
Toss Winner Win %     = DIVIDE ( SUM ( matches[toss_winner_won] ), COUNT ( matches[toss_winner_won] ) )

-- Batting
Total Runs      = SUM ( deliveries[batsman_runs] )
Balls Faced     = SUM ( deliveries[balls_faced] )
Strike Rate     = DIVIDE ( [Total Runs], [Balls Faced] ) * 100
Sixes           = SUM ( deliveries[is_six] )
Fours           = SUM ( deliveries[is_four] )
Boundary Run %  = DIVIDE ( [Fours] * 4 + [Sixes] * 6, [Total Runs] )
Sixes per Match = DIVIDE ( [Sixes], [Total Matches] )
Highest Score   = MAXX ( SUMMARIZE ( deliveries, deliveries[match_id], deliveries[batter] ), [Total Runs] )

-- Bowling
Wickets             = SUM ( deliveries[bowler_wicket] )
Legal Balls Bowled  = SUM ( deliveries[legal_delivery] )
Runs Conceded       = SUM ( deliveries[bowler_runs] )
Economy             = DIVIDE ( [Runs Conceded], [Legal Balls Bowled] / 6 )
Bowling Average     = DIVIDE ( [Runs Conceded], [Wickets] )
Bowling Strike Rate = DIVIDE ( [Legal Balls Bowled], [Wickets] )
```

Format `Win %`, `Toss Winner Win %`, `Finals per Season %`, `Boundary Run %` as percentages; `Strike Rate`, `Economy`, `Sixes per Match` with 1–2 decimals.

Why these differ from a naive version:

- **Win %** divides by matches *played* (including no-result), matching the notebook. A measure that counts wins using the same filtered table as the team slicer would return 100%.
- **Toss winner win %** excludes no-result matches from the denominator; dividing by all 1,095 matches would give 50.6% instead of 50.8%.
- **Economy** does not charge byes or leg-byes to the bowler; adding `total_runs` would overstate it.

---

## 4. Report pages

Import the theme first: **View → Themes → Browse for themes → `powerbi_kit/IPL_Theme.json`**. (If Power BI rejects the file, open it, delete the `visualStyles` block and import again; the colours still apply.) Use a 16:9 canvas.

| Page | Visuals | Fields | Slicers |
|------|---------|--------|---------|
| **1. Overview** | 4 KPI cards; bar chart of Win % by team; column chart of matches per season | Cards: `Total Matches`, `Seasons`, `Total Runs`, `Wickets`. Bars: `team_matches[team]` / `Win %`. Seasons: `matches[season]` / `Total Matches` | Season |
| **2. Toss & Tactics** | Card: `Toss Winner Win %`; clustered column of win % by decision; table of venue × decision | Column chart axis `matches[toss_decision]`, value `Toss Winner Win %`. Table: `matches[venue]`, `Matches With a Result`, `Toss Winner Win %` | Season, Venue |
| **3. Batting** | Top 10 bar of `Total Runs` by `batter`; scatter of `Strike Rate` vs `Total Runs`; card `Highest Score` | Top N filter on `batter` by `Total Runs` (10). Scatter: details `batter`, filter **`Balls Faced` ≥ 1000** | Season, Batter |
| **4. Bowling & Venues** | Top 10 bar of `Wickets` by `bowler`; table with `Economy`, `Bowling Average`, `Bowling Strike Rate`; bar of `Sixes per Match` by venue; bar of `Total Matches` by venue | Sixes bar: axis `matches[venue]`, filter **`Total Matches` > 20** | Season, Bowler, Venue |

Design tips: keep one accent colour per metric (blue wins, gold toss, red batting, green bowling), sort bars descending, label values directly, and give every visual a descriptive title and alt text.

---

## 5. Check your numbers

With **no slicers applied**, the report must reproduce the notebook:

| Check | Expected |
|-------|----------|
| Total Matches / Seasons | 1,095 / 17 |
| Mumbai Indians — Wins, Win % | 144, 55.2% |
| Chennai Super Kings — Wins, Win % | 138, 58.0% |
| Gujarat Titans — Win % | 62.2% (45 matches) |
| Toss Winner Win % | 50.8% |
| Toss Winner Win % — bat / field | 45.4% / 53.9% |
| V Kohli — Total Runs | 8,014 |
| AD Russell — Strike Rate (Balls Faced ≥ 1000) | about 174.8 |
| YS Chahal — Wickets | 205 |
| M Chinnaswamy Stadium — Sixes per Match | about 14.9 |
| Wankhede Stadium — Total Matches | 118 |

If a number is off, fix it before building more visuals. The usual culprits are a wrong `DataFolder` path, a missing relationship, or a column imported with the wrong type.

---

## 6. Finish and publish

- Save as `IPL_Dashboard.pbix`. It embeds the data, so expect tens of MB; keep it out of git or use Git LFS / a GitHub release.
- Take a page screenshot (**File → Export → PDF**, or a screen capture) into `docs/` and link it from the README.
- Sharing a link through the Power BI service needs a licence; do not use "Publish to web" for anything you do not want public.

---

## 7. Asking an AI assistant for help

An assistant cannot open or edit a `.pbix`, but it can write DAX and M if you give it the model. Paste this and add your task:

```text
I am building an IPL (2008-2024) Power BI report from three cleaned CSV tables.

matches(id, season, city, date, match_type, venue, team1, team2, toss_winner, toss_decision, winner,
        result, result_margin, target_runs, target_overs, method, toss_winner_won)
team_matches(match_id, season, date, match_type, venue, team, opponent, won, lost, no_result, toss_won, ...)
deliveries(match_id, inning, over, ball, batter, bowler, batsman_runs, extra_runs, total_runs, extras_type,
           is_wicket, dismissal_kind, balls_faced, legal_delivery, bowler_runs, bowler_wicket, is_four, is_six)
Relationships: matches[id] -> team_matches[match_id], matches[id] -> deliveries[match_id] (single direction).
Rules: winner = "No Result" for abandoned matches; wides are not balls faced; byes/leg-byes are not charged to the bowler.

Task: <describe the measure or visual you want>
Return DAX with comments, use DIVIDE, and say which table each field comes from.
```
