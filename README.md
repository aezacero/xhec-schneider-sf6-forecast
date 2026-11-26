# Raw-material forecasts and quote rules for RMU switchgear

X-HEC × Schneider Electric data challenge, team 5.

We forecast the raw materials in Schneider's ring main units (steel, stainless, copper,
aluminium, plastics, epoxy, EUR/USD) 3, 6 and 9 months ahead, with P10 / P50 / P90 ranges. The
forecasts feed a cost index for RM6 and RM AirSeT, and the cost index feeds quote rules: what
price to quote, how long the quote can stay open, and when to index it. The same numbers support
the strategy part: AirSeT can be priced close to SM6, so the switch to SF6-free can be won on
trust and lifetime value rather than on a green premium.

## How to run
Everything runs on a laptop CPU with [uv](https://docs.astral.sh/uv/getting-started/installation/).
The challenge data is confidential and not in this repo: without it you can run the tests and the
decision tool on demo data; with it, one command rebuilds the forecast CSV.

### 1. Without the data: tests and demo
```bash
git clone https://github.com/aezacero/xhec-schneider-sf6-forecast.git
cd xhec-schneider-sf6-forecast
uv sync                                          # exact versions from uv.lock
uv run pytest                                    # tests on synthetic data
SCHNEIDER_DEMO=1 uv run streamlit run app/main.py
```

The last command opens the decision tool on generated demo data (see [2. Decision tool](#2-decision-tool)).

### 2. Decision tool
A Streamlit app that turns the forecasts into a quote, for pricers who don't code.

```bash
SCHNEIDER_DEMO=1 uv run streamlit run app/main.py   # generated demo data, no confidential files needed
uv run streamlit run app/main.py                    # real outputs, after the rebuild below
```

It opens at http://localhost:8501. Without the rebuilt outputs (or with `SCHNEIDER_DEMO=1`) it
runs on generated demo data and shows a "Demo data" badge. It only reads `data/processed/` and
`outputs/` on your machine; nothing is sent anywhere.

| Page | Question it answers |
|---|---|
| Guide | How to read the tool in two minutes |
| Quote | What price should go on this quote? Pick a product, validity, list price, margin and cost scenario to get the quote price, risk buffer, margin at risk, safe validity and indexation trigger, plus a copper and steel "what if" and the 2021 replay |
| Cost outlook | How much could material cost move by June 2027, and which material carries the risk? |
| Materials | The forecast and track record (skill, coverage) of each of the 19 series |
| SF6-free | The AirSeT minus RM6 cost gap today and its range to June 2027 |

### 3. With the data: one command to the CSV
Put the challenge data in `data/raw/` (layout below), then:

```bash
uv sync --extra pretrained                      # once: Chronos-2 (not available on Intel Macs)
uv run python -m schneider_forecast.run_all     # data → forecasts → pricing → CSV
```

This writes `outputs/forecasts/team_05_forecast_202609.csv` in about 40–50 seconds on a laptop
CPU, plus the backtests (`outputs/backtest/`) and pricing tables (`data/processed/`). The steps can
also be run one by one: `data`, `p2_selection`, `p3_selection`, `pricing`, `procurement`, `submit`.
If a raw file is missing, the command stops before starting and lists what is missing.

```
data/raw/                       read-only
├── csv/                        contents of data.zip
├── supplier_balance_sheets/    contents of Supplier_balancesheet.zip
└── *.xlsx, *.pdf               the other files
```

### 4. The forecast CSV
One row per target × horizon: 19 materials and 2 product cost indices × 3 horizons = 63 rows.

| Column | Content |
|---|---|
| `team_id` | `team_05` |
| `target_type` | `material` or `bom_index` |
| `target_id` | Series ID (`D01`, `S09`, …) or the product reference (`RM6_NE_IQI_433520`, `RMAirSeT IIQ 24kV IEC`) |
| `region` | `EU` or `WW` |
| `origin_month`, `horizon_m`, `target_month` | `2026-09`; 3, 6, 9; `2026-12`, `2027-03`, `2027-06` |
| `unit` | `EUR/t`, or `index (origin=100)` for every other series, so no USD band is converted with a forecast exchange rate |
| `p10`, `p50`, `p90` | The forecast range |
| `model_name`, `ai_tools` | The model used, and the AI tools involved |

`submit` checks the file before writing it: columns, blanks, duplicates, horizons,
P10 ≤ P50 ≤ P90, positive values, units and the six index rows.

## Structure
### How it works
```
raw files → data pipeline → strict backtest → model choice per material → cost index → quote rules + CSV
```

1. **Data pipeline** ([`docs/data_pipeline.md`](docs/data_pipeline.md)): one monthly table to
   September 2026. The licensed steel series were empty, so they are rebuilt from the MEPS and
   CRU prices in the steel workbook. Nothing is imputed; data errors are flagged and skipped.
2. **Backtest** (same doc): every month since January 2020, each series cut at what had been
   published by then. Every model is compared with the random walk (the last known value).
3. **Models** ([`docs/forecasting_steel.md`](docs/forecasting_steel.md),
   [`docs/forecasting_other.md`](docs/forecasting_other.md)): a pooled MEPS model for steel coils,
   steel indices led by MEPS, Chronos-2 for stainless, a damped-trend and Chronos-2 blend for the
   smooth price indices, the random walk elsewhere. One shared band method for all: past moves
   scaled by today's volatility, capped at twice its usual level.
4. **Pricing** ([`docs/pricing.md`](docs/pricing.md)): materials weighted by their cost in each
   product, simulated moving together, turned into € per unit, margin at risk, a price
   adjustment, a risk buffer, a validity and an indexation trigger.
5. **Strategy** ([`docs/goal_b/`](docs/goal_b/)): a voluntary switch from SM6 to SM AirSeT in
   three markets with no SF6 rule: the US, India and Malaysia–Singapore.

Also: [`docs/methodology.md`](docs/methodology.md) (overall method),
[`docs/eda_findings.md`](docs/eda_findings.md) (what the data showed),
[`docs/data_transformations.md`](docs/data_transformations.md) (every transformation),
[`docs/glossary.md`](docs/glossary.md), and the EDA notebooks in `notebooks/eda/`.

### Repo layout
```
src/schneider_forecast/
  config.py, data.py                  paths, forecast origin, publication delays, data pipeline
  backtest.py, metrics.py, plots.py   backtest harness, scores, coverage and fan charts
  bands.py                            shared P10 / P90 bands
  p2_*.py, pooled.py, features.py, total_cost.py   steel and stainless models
  p3_*.py                             copper, aluminium, plastics, epoxy and FX models
  pricing.py, procurement.py          cost index, quote rules, procurement levers
  decision.py                         calculations behind the app
  submit.py, run_all.py               the CSV, and the one-command rebuild
app/                                  Streamlit decision tool
notebooks/eda/                        exploration notebooks
tests/                                tests on synthetic data (CI has no real data)
docs/                                 method, per-part docs, EDA findings, licences, Goal B
```

## Results
All numbers come from a strict walk-forward backtest: one forecast every month from January 2020
to September 2026, using only data that had been published on each date.

| | +3 months | +6 months | +9 months |
|---|---|---|---|
| **P50 skill vs the random walk**, steel price indices (S09, S10) | +24 to +27 % | +19 to +22 % | +20 % |
| Steel coils (L01, L03) | +11 % | +8 to +9 % | +1 % |
| Stainless (L02) | +9 % | +9 % | +8 % |
| Aluminium and plastics price indices, epoxy | +8 to +23 % | +2 to +11 % | 0 (random walk kept) |
| Copper, aluminium, nickel, iron ore, EUR/USD | 0 (random walk kept) | 0 | 0 |
| **P10–P90 coverage** (target 0.80), steel group | 0.80 | 0.81 | 0.81 |
| Other materials | 0.72 | 0.70 | 0.72 |
| **Cost index P90** (100 = Sep 2026), AirSeT / RM6 | 109.0 / 108.0 | 118.5 / 116.5 | 126.3 / 124.5 |
| **Risk buffer** (share of price), AirSeT / RM6 | 0.7 / 0.6 % | 1.3 / 1.1 % | 2.0 / 1.8 % |

- A model replaces the random walk only if it does at least as well in the 2020–22 shock **and**
  in the calmer 2023–26 years. Where prices trend (steel, price indices), models win; on
  exchange-traded prices nothing beats today's price, and we say so.
- Bands are too narrow in shocks (43–62 % coverage in 2020–22) and a bit wide in calm years
  (86–95 %). Replaying 2021 shows that no buffer absorbs such a shock: a fixed price lost up to
  28 % of the margin and a buffer up to 22 %. So quotes carry a small buffer in normal months and
  an indexation clause for shocks.
- Validity: RM6 quotes can be held 9 months, AirSeT quotes 6, beyond which the price is indexed
  to the steel and copper indices Schneider already buys on.
- The cost index beats a naive index by +4 to +7 % on the P50 and +19 to +31 % on the band score.
- AirSeT needs about €75 more raw material than RM6, 0.6 % of the price.

## Limits and assumptions
- One download of the data (around 12 November 2026). Eurostat and BLS revise their indices after
  release, so the backtest is a little optimistic for those.
- Publication delays are our estimates from that download and the providers' notes, not official
  release calendars. They decide what each backtest month can see.
- L01 to L03 are our rebuild from MEPS and CRU, not the licensed series.
- The three BOM versions disagree on every mass. We use the latest one, as Schneider asked.
  "Other", brass and a small unidentified remainder have no price series.
- Priced raw material is 7.3 % (RM6) and 8.0 % (AirSeT) of the unit price. Schneider's margin and
  the share of the price that really moves with materials are unknown, so the quote rules assume
  a 20 % margin and are also shown for other values.
- Unit prices come from a synthetic benchmark with one Schneider price for both products.
- Prices are nominal. Backtest windows overlap, so there are only about 26, 12 and 8 independent
  errors at +3, +6 and +9 months: small differences between models are not proof.

## Maturity levels
| Level | Status | Evidence |
|---|---|---|
| 1. Reproducible analysis | Met | `uv.lock` pins every package version |
| 2. Naive baseline with bands | Met | Every model is scored against the random walk with bands |
| 3. Pipeline in GitHub Actions | Met, on synthetic data | `.github/workflows/ci.yml`: ruff and pytest on every push and pull request |
| 4. Non-coders can simulate pricing | Met | Streamlit decision tool (`app/`) |
| 5. Runnable by Schneider | Met | One command to the CSV, under a minute on a laptop CPU, plus a demo mode. Chronos-2 does not install on Intel Macs |

## AI tools, compute and licences
We used Claude (Anthropic), mostly Claude Code, to help write the code, tests and docs, and
Granola to take meeting notes. Results were checked with tests and backtests, and the CSV's
`ai_tools` column says which rows used which tool. Chronos-2, the pretrained forecasting model,
runs locally on the CPU, so no data is sent anywhere. A full rebuild emits about 0.004 g of CO₂
(CodeCarbon, French grid factor); no GPU, no cloud. Every model, library, data source and licence
is listed in [`docs/models_and_licenses.md`](docs/models_and_licenses.md).

## Team
| | Goal A | Goal B |
|---|---|---|
| Ali | Data pipeline, backtest harness, EDA | United States |
| Lucca | Steel and stainless models, top-down vs bottom-up comparison | India |
| Jessie | Copper, aluminium, plastics, epoxy and FX models, shared bands, data overview | Malaysia–Singapore |
| Korou | Cost index, quote rules, submission builder, decision tool | |

The code is released under the MIT licence ([`LICENSE`](LICENSE)). The challenge data belongs to
Schneider Electric and is not included.
