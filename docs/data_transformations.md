# Data transformations

Log every transformation applied between `data/raw/` and `data/processed/`:
frequency alignment, currency conversion, date alignment, imputation, and new external sources.

| Step | Input | Output | What it does | Code |
|---|---|---|---|---|
| 1 | `csv/rm_prices_monthly_wide.csv` | S01–S13, D01, D02 | Drop `year`, `month_num` and the empty licensed series L01–L08 | `data.load_rm_prices` |
| 2 | `csv/energy_prices_monthly_wide.csv` | E01–E24, ED01–ED06 | Read as is | `data.load_energy` |
| 3 | Steel workbook, sheet `MEPS` | L01, L03, `MEPS_{DE,FR}_{HR,CR,HDG,EG}` | Rebuild the multi-row header (country row 0, product row 4); keep Germany and France coil prices (€/t, low values); text to numbers; drop empty future months. Germany CR coil → **L01**, Germany HDG coil → **L03**. The `▲` change sheets are never read | `data.parse_meps` |
| 4 | Steel workbook, sheet `CRU Stainless` | L02 | Grade 304 Germany: **price = BASE + Alloy surcharge**; dates on the 15th → month start | `data.parse_cru_stainless` |
| 5 | `Epoxy for student.xlsx` | `EPX_BENZENE`, `EPX_ACETONE`, `EPX_ECH`, `EPX_OTHER`, `EPX_RESIN` | Observation dates (1st–5th) → month; numbers read strictly. `EPX_OTHER` (resin minus inputs) is kept: same-month use leaks the resin price | `data.load_epoxy` |
| 6 | `LME_Copper_Aluminium_EU_Monthly_2016_2026.xlsx` | `LME_{CU,AL}_{CASH,3M}_{USD,EUR}`, `LME_{CU,AL}_{STOCKS,SPREAD}` | Completed months only (the provisional month-to-date row is dropped); cash and 3-month prices kept for the choice of offer reference | `data.load_lme` |
| 7 | Steps 1–6 | `prices_wide.csv` | Outer join on month (Jan 2008 → Sep 2026); **every month after the origin 2026-09 dropped**; no imputation, no currency conversion, no inflation adjustment | `data.build_prices` |
| 8 | `prices_wide.csv`, catalogs, `config.PUB_LAG` | `series_catalog.csv` | Per series: source, material, region, unit, first / last month, count, `gap_months` (months from the last value to the origin), publication lag, `is_target` (BOM proxy with data, plus `EPX_RESIN` and S06), `needs_nowcast` (target with `gap_months` > 0) | `data.build_catalog` |
| 9 | Known issues | `data_flags.csv` | Epichlorohydrin, resin and `EPX_OTHER` May 2026 (error) and three real market events (WTI Apr 2020, Japan power Jan 2021, Russian crude imports Aug 2025) listed with their treatment; values kept as published | `data.KNOWN_DATA_ISSUES` |
| 10 | `RM_Prices_XHEC_Challenge_v1.xlsx` (sheet `BOM_Materials`, the 20 Nov reference) | `bom_clean.csv` | Mass-total rows and plant name dropped; plant code kept and `plant_country` added (it decides the steel index); `price_series` = first proxy with data (none for Other, brass, unidentified remainder) | `data.clean_bom` |
| 10b | The three BOM versions (12 Nov CSV, 19 Nov xlsx, 20 Nov v1) | `bom_versions.csv` | Each cleaned as in step 10 and stacked with a `version` column; not merged (plastic rows share a price series, so rows cannot be matched one-to-one) | `data.bom_versions` |
| 11 | RMU price benchmark, sheet `ML_Trend` | `rmu_prices.csv` | Brand × year P10 / P50 / P90 unit prices (EUR ex-VAT); year-on-year column dropped | `data.load_rmu` |
| 12 | All outputs | — | Build stops if: a cell cannot be read as a number, months are not unique / sorted, data after the origin, a series lacks a publication lag, or the 19 targets are not all present with no inner gaps and no values ≤ 0 | `data.to_numbers`, `data.run_checks`, `data.build_catalog` |

## Model-time transformations (inside the models; `data/processed/` is unchanged)

| Step | Input | Output | What it does | Code |
|---|---|---|---|---|
| M1 | Target series in `prices_wide.csv` + `data.KNOWN_DATA_ISSUES` | Model input | Months flagged `error` (epichlorohydrin, epoxy resin, epoxy other costs, May 2026) become gaps before fitting; gaps are kept so a k-month change is always k calendar months; a target whose last month is an error ends one month earlier | `bands.target_logs` |
| M2 | Gaps from M1 | ETS / Chronos input | Filled by straight-line interpolation in log values (these models need a gap-free series); band quantiles skip changes that span a gap | `p3_models.filled` |
| M3 | Prices | Log prices | Models work on log values / log changes and return P10 / P50 / P90 in the original unit | `p3_models`, `bands` |
| M4 | Gaps from M1 | Pooled-model and steel-model features | Filled by straight-line interpolation in log values between the months before and after (only once the month after is known, so no look-ahead); momentum and moving averages need consecutive months | `features.clean_series` |
| M5 | `bom_clean.csv` (v1) + target prices | Total raw-material cost per product and month | Σ kg × price per kg over priced lines; €/t ÷ 1,000; plastics 3 €/kg at the last month moving with S11 (as in the cost index); lines without a series left out; NaN unless every line is priced that month. Masses fixed, prices of each month (no later prices) | `total_cost.total_cost_history` |

## Pricing transformations (outputs in `data/processed/`)

Run with `uv run python -m schneider_forecast.pricing`. Working assumptions behind each step:
[`pricing.md`](pricing.md).

| Step | Input | Output | What it does | Code |
|---|---|---|---|---|
| R1 | `bom_clean.csv` (v1 BOM), `prices_wide.csv` | `pricing_cost_weights.csv` | € per BOM line at the origin = kg × price per kg (€/t ÷ 1,000); weight = line € ÷ product €. Lines with no price series (Other, brass, unidentified remainder) left out. Plastics and epoxy at a fixed 3 €/kg (S11 is an index). RM6 steel priced at MEPS CR France (French plant), moved with L01. L02 uses its last value (2026-08) | `pricing.cost_weights` |
| R2 | Material P10 / P50 / P90 | `pricing_forecasts_used.csv` | The Sep 2026 material forecasts stacked from `outputs/forecasts/p2_forecasts_202609.csv` and `p3_forecasts_202609.csv` (submission or harness layout); a series they lack gets a placeholder: random walk with volatility-scaled bands, half-life 3 | `pricing.load_forecasts`, `pricing.to_pricing_columns` |
| R3 | R1, R2, past h-month log changes of the BOM series | `bom_index_rows.csv` | Cost index (100 = origin) from 10,000 joint draws: each draw takes one past month's rank of every material's change (materials move together as they did) and reads that rank off the material's own P10 / P50 / P90 line (straight lines through the three points, extended past them). Index = 100 × Σ weight × price ratio. Known data errors skipped (`target_logs`) | `pricing.simulate_index`, `pricing.past_change_ranks` |
| R4 | R3, `rmu_prices.csv` | `pricing_cost_bridge.csv` | € cost per unit per scenario = cost today × index ÷ 100; exposed share = priced RM cost ÷ Schneider P50 2026 (€12,233); margin at risk = exposed share × P90 cost rise, also ÷ an assumed 20 % margin | `pricing.cost_bridge` |
| R5 | R4 | `quote_rules.csv`, `quote_validity.csv`, `index_triggers.csv` | Price adjustment = exposed share × P50 change; risk buffer = exposed share × (P90 − P50); validity = longest horizon with buffer ≤ 10 % of margin; trigger per index = tolerance ÷ (exposed share × cost weight). No crisis factor (see R8) | `pricing.quote_rules`, `pricing.quote_validity`, `pricing.index_triggers` |
| R6 | R4 | `sensitivity_table.csv` | Margin lost at P90 for exposed share {own, 10, 17, 25 %} × margin {10, 20, 30 %} | `pricing.sensitivity_table` |
| R7 | `bom_clean.csv`, `bom_versions.csv` | `pricing_sensitivities.csv`, `cost_gap.csv` | Index and € cost under: epoxy on `EPX_RESIN`, benchmark plastic rates (5.50 / 3.20 €/kg), "Other" flat at 4 €/kg, brass = 63 % copper + 37 % zinc (S05 ÷ S06), and the 12 / 19 Nov BOMs (RM6's unlabelled slice = 45 % of the product mass). AirSeT − RM6 € gap with P10 / P50 / P90 for Goal B | `pricing.run_sensitivities`, `pricing.fill_missing_mass`, `pricing.cost_gap` |
| R8 | `prices_wide.csv` cut at each month 2020-01 → 2023-12 | `replay_2021.csv`, `replay_2021_summary.csv` | 2021 replay: each month, quote 6 months ahead with only the data known then; margin lost (share of margin) under a fixed price, the band buffer and the band buffer × crisis factor (recent ÷ median volatility, never below 1). Grouped by purchase month | `pricing.replay_quotes`, `pricing.replay_summary`, `pricing.crisis_factors` |
| R9 | Strict-run backtest rows of the six BOM series (`outputs/backtest/p2_selected_strict.csv`, `p3_selected_strict.csv`; a missing series gets the baseline run here, also strict), data cut with `available_at(strict=True)` to match | `index_backtest.csv`, `index_backtest_scores.csv` | At each origin since 2020-01 and horizon 3 / 6 / 9: our index (R1 + R3 on that month's data) and a naive index (P50 = 100, P10 / P90 = the basket's own past h-month moves); both scored with P1's `score` / `compare` | `pricing.index_backtest`, `pricing.index_backtest_scores` |
| R10 | `supplier_balance_sheets/` (9 PitchBook exports), sheets `Ratios` and `Income Statement` | `supplier_strength.csv` | Suppliers numbered 1–9 in file order, names dropped. Per supplier, the newest filled year of EBITDA margin, current ratio, quick ratio, total debt to equity (0 read as "not reported") and interest coverage, plus revenue (k€ ÷ 1,000 = € m; one file has no income statement). Group: fragile if EBITDA margin < 0, current ratio < 1 or interest coverage < 1.5; strong if EBITDA margin ≥ 10 %, current ratio ≥ 1.2 and interest coverage ≥ 5 (or no reported debt); watch otherwise. One negotiation lever per group | `procurement.supplier_strength` |
| R11 | Steel workbook, sheet `Reference to Index Mapping` (663 purchased steel parts); `index_triggers.csv` | `back_to_back_indexation.csv` | Parts grouped by the index Schneider buys on (e.g. CR France): count, share, median lead time; CR → L01, HDG → L03 (HR, EZ are not RMU BOM lines); our sell-side trigger per product from R5; copper and aluminium added as LME (D01, D02). Plant and part names dropped; the `UPDATE` sheet (personal names) is never read | `procurement.back_to_back_table`, `procurement.copper_and_aluminium_rows` |

## Submission CSV (`schneider_forecast.submit`)

| Step | Input | Output | What it does | Code |
|---|---|---|---|---|
| S1 | `outputs/forecasts/p2_forecasts_202609.csv`, `p3_forecasts_202609.csv`, `data/processed/bom_index_rows.csv` | `outputs/forecasts/team_05_forecast_202609.csv` | Stacks the rows; EUR/t rows unchanged, every other unit (USD/t, USD/dmt, PPIs, USD per EUR) rebased to `index (origin=100)` = 100 × value ÷ the series' value at 2026-09 (P1 doc A7 default); region from `series_catalog.csv` cut to EU / WW; `team_id` = team_05; `ai_tools` = `chronos-2` when the model uses it, plus `claude-code`. Stops on missing columns, blanks, duplicates, horizons other than 3 / 6 / 9, P10 > P50 or P50 > P90, values ≤ 0, wrong months or units, or fewer than the 6 BOM index rows | `submit.build_submission`, `submit.check_submission` |
