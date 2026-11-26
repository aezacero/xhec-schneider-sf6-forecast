# EDA findings

What the exploratory analysis found in `data/raw/`: data problems, units, where each series ends,
what is safe to use at forecast time, how the prices behave, the naive baseline to beat, and how
BOM materials map to price series. Read this before building features or models.

All numbers come from code run on the data snapshot of 12 Nov 2026. Anything not checked in the
data is marked **Assumption**. Supplier names are replaced by `Supplier 1..9`.

## At a glance

| # | Finding | What it means for us |
|---|---|---|
| 1 | Core RM series end **Sep 2026**; steel, FX, power, epoxy **Oct 2026**; CRU stainless **Aug 2026** (304 DE/FR) or **Feb 2026** | The forecast origin and target months must be fixed before comparing models ([section 3](#3-ragged-edge-and-forecast-origin)) |
| 2 | Epichlorohydrin May 2026 = 257 €/t (about 2,500 before and after); the resin price inherits it | Exclude or correct that month for epoxy; ask Schneider |
| 3 | The EU steel PPI (S09) moves about a third as much as real steel prices | Forecast steel from MEPS / CRU prices, not S09 |
| 4 | Every series behaves like a random walk in log levels | Model log changes, not levels |
| 5 | The random walk beats the seasonal naive everywhere; its P10–P90 band holds only 51–75 % of actuals | Baseline = random walk; bands must widen in volatile periods |
| 6 | Drivers lead prices by 1–2 months, rarely further | Little help at +6 / +9; expect the baseline to be hard to beat |
| 7 | On priced raw materials (v1 BOM), AirSeT costs ≈ €75 more than RM6 (€975 vs €900); the gap shrank from +€264 (Apr 2022) to +€73 (Aug 2026) as copper rose | Goal B: the raw-material cost gap is small and narrowing ([section 8](#8-bom-to-price-series)) |
| 8 | RMU prices (file now unlocked): Schneider 2026 P50 €12,233 (+40 %); Eaton, the only SF6-free competitor, +8 % and now 5.5 % cheaper | Goal B: no SF6-free premium to lean on ([section 11](#11-rmu-prices-and-price-vs-cost)) |
| 9 | Priced raw material is only 7–8 % of the unit price (v1 BOM); price does not follow cost one-for-one | Margin and cost base drive the € value of a forecast; supports indexation ([section 11](#11-rmu-prices-and-price-vs-cost)) |
| 10 | € at risk per unit (6 months, v1 BOM): RM6 copper ≈ €154; AirSeT copper ≈ €113, carbon steel ≈ €99, stainless ≈ €94 | Forecasting priority: copper, then stainless and carbon steel ([section 8](#8-bom-to-price-series)) |
| 11 | Steel seasonality has a direction: March up, June–July down, also without 2021–22 | Month terms for MEPS steel only ([section 5](#5-how-prices-behave)) |
| 12 | Steel and plastics have fat, right-skewed tails; volatility clusters in steel and stainless | Bands scale with recent volatility, asymmetric quantiles allowed ([section 5](#5-how-prices-behave)) |
| 13 | Few drivers keep the same sign before 2020 and over the full sample | Only those enter the models ([section 6](#6-relationships-and-leading-indicators)) |
| 14 | Materials move together across types: copper–aluminium 0.67, carbon steel–stainless 0.60 | BOM index from a joint simulation, not independent bands ([section 6](#6-relationships-and-leading-indicators)) |
| 15 | SF6-free premium over the SF6 average: +46 % (2017) → +1 % (2026) | Goal B: SF6-free is no longer the expensive option ([section 11](#11-rmu-prices-and-price-vs-cost)) |

---

## 1. Data quality

No internal gaps in any core RM, energy, MEPS or CRU flat series (only MEPS Belgium misses one
month). No duplicate months. The long and wide CSVs agree, and D01/D02 and ED01–ED06 recompute
exactly from their inputs.

| Source | Issue | How to handle |
|---|---|---|
| Epoxy | Epichlorohydrin May 2026 = 257 €/t vs about 2,500 around it (log change −2.27 then +2.32). Resin drops 27 % that month and rebounds, so the resin price is **computed from its inputs** | Treat May 2026 epichlorohydrin and resin as errors; never impute silently |
| Epoxy | `other_costs` correlates 0.71 with what is left of the resin price after the three chemical inputs | Do not use `other_costs` as a feature for resin (leakage) |
| Epoxy | Observation day moves from the 1st to the 2nd–5th of the month from Dec 2023 | Map to calendar month; may be point readings, not monthly averages (**Assumption**) |
| Steel workbook | MEPS stainless 430 *high* = *low* + 50 in all 37 months; CRU France EG coil = HDG + 25 in 55 of 59 months | Constant-spread copies: keep one of each pair |
| Steel workbook | Change sheets (`F▲`, `L▲`, `SS▲`) hold **0** for future months; the CRU "Germany" change column is actually France | Never read the change sheets; recompute changes from levels |
| Steel workbook | MEPS prices unchanged in 23–29 % of months, runs up to 5–7 months; steps of 5–10 €/t | Expect many zero changes in metrics and models |
| Steel workbook | CRU stainless BASE can be negative (min −350) | Transaction price = BASE + Alloy (**Assumption**) |
| Supplier files | Debt to equity is 0 in every file | Treat as not reported; use *Total Debt to Equity*, which is filled |
| BOM | Three versions disagree on every mass: `csv/bom_materials.csv` (12 Nov), `RM_Prices_XHEC_Challenge.xlsx` (19 Nov) and `RM_Prices_XHEC_Challenge_v1.xlsx` (20 Nov), e.g. AirSeT total 629 / 547 / 547 kg | Use the 20 Nov v1, as Schneider asked; earlier versions only for sensitivity ([section 8](#8-bom-to-price-series)) |

Large monthly moves are real market events, not errors: the 2021 steel surge, the Mar 2022 spike
and Jun 2022 crash (MEPS CR DE +17 % then −19 %), the Mar 2022 nickel squeeze, Brent in Mar 2020.
A robust z-score scan (|z| > 4) also flags the WTI crash (Apr 2020), the Japan power spike
(Jan 2021) and EU imports of Russian crude (Aug 2025): all real, keep them.

Cross-checks that pass: the LME Westmetall file matches D01 within 0.2 %; CRU flat coil averages
sit about 2 % above MEPS for the same product and country and track it closely, so either can
serve as the L01 / L03 proxy.

## 2. Units and comparability

| Unit | Series | To get €/t |
|---|---|---|
| EUR/t | MEPS, CRU (except UK, Turkey), D01, D02, epoxy | Ready |
| USD/t | S01–S05, MEPS Turkey | Divide by S06 of the same month |
| GBP/t, SEK/t | UK steel, MEPS Sweden | Not possible: no GBP or SEK rate in the data |
| Index | S07–S13 (bases 2021, 1982, Dec 1980), E13–E19 (2021, 1982, 2020), E22 (2016) | Percentage changes only; a € level needs an anchor price |

- **An index is not a price.** S09 vs MEPS CR coil DE: monthly-change correlation 0.58, monthly
  std 0.021 vs 0.057. Rebased to 2021 = 100, MEPS ranges 38–133 and S09 66–146. Using S09 for steel
  understates risk by about 2.7×. The copper PPI follows LME copper more closely (0.93).
- **FX matters, but less than the metal.** Jan 2021 → Sep 2026: copper +60 % in USD, +65 % in EUR;
  the euro's fall explains about 9 % of the EUR move.
- **Everything is nominal.** No deflator is in the data.

## 3. Ragged edge and forecast origin

| Last month | Series |
|---|---|
| Nov 2026 (partial) | LME Westmetall (month-to-date to 11 Nov), CRU spot FR / ES / UK |
| Oct 2026 | MEPS, CRU flat averages, S06 / E23 FX, power E09–E12, epoxy file |
| Sep 2026 | S01–S13, D01, D02, IMF energy, energy PPIs |
| Aug 2026 | CRU stainless 304 Germany and France |
| Jul 2026 | EU crude imports E20, E21 |
| Feb 2026 | All other CRU stainless series (304 IT/ES/UK, 430, 316) |

Options we considered for the forecast origin and targets (we chose A):

| Option | Origin | Targets | Note |
|---|---|---|---|
| A | Sep 2026 for all | Dec 2026, Mar 2027, Jun 2027 | Matches the submission format; stainless is then 4 months out at +3 |
| B | Each series' own last month | Last + 3 / 6 / 9 | Uses all data; target months differ by material |
| C | Forecast month Nov 2026 | Feb, May, Aug 2027 | Horizon counted from the quote date |
| D | Quarterly averages | Q1–Q3 2027 | Matches quarterly price reviews; not what the brief asks |

Also open: monthly average vs month end, native unit vs EUR, first release vs revised value.

## 4. What is safe to use at forecast time

Latest month that can honestly be used for a forecast made in month M (lag observed in the
snapshot, cross-checked with provider notes in `csv/README.md`):

| Source | Usable up to | Revisions |
|---|---|---|
| LME Westmetall | M (partial) | None |
| MEPS, CRU flat, ECB FX, Ember power, epoxy | M − 1 | MEPS / CRU unknown; others none or small |
| IMF prices (S01–S05, E01–E08, E22), D01 / D02 | M − 2 (M − 1 late in the month) | Rare |
| Eurostat and BLS PPIs (S07–S13, E13–E18) | M − 2 (M − 1 late in the month) | Yes: last 2–3 months revised |
| CRU stainless 304 DE / FR | M − 3 | Unknown |
| EU crude imports (E20, E21) | M − 4 | Yes |

Traps found in the files:

- Partial months (LME Nov, CRU weekly and spot) are inputs at most, never targets.
- D01 / D02 use same-month FX: FX at the target month is unknown at forecast time.
- The `csv/README.md` lead-lag table is computed on the full sample: re-estimate inside each
  backtest window. Same for any rebasing, scaling or imputation.
- We hold one vintage only, so a backtest on revised PPIs is slightly optimistic.

## 5. How prices behave

- **Unit roots.** ADF and KPSS agree for every target and driver: random walk in log levels,
  stationary in monthly log changes (S07 borderline).
- **Volatility depends on the period.** MEPS CR coil DE annualised volatility: 0.10 before COVID,
  0.37 in 2022, 0.08 in 2026. PPIs are much calmer (S09: 0.02–0.14).
- **Seasonality is weak.** 5 of 20 series test significant at 5 % (1 expected by chance): energy
  PPI, power DE and HU, MEPS CR and HDG Germany.
  The steel pattern is consistent: March up (+1.3 to +3.1 %), June–July down (−1.7 to −3.7 %) for
  MEPS CR France, CR Germany and HDG Germany, and it holds without 2021–22. Copper, aluminium,
  plastics and epoxy show none. **Use:** month terms for MEPS steel only.
- **Breaks.** A stable mean is rejected for S09, CRU SS304 DE and E13. Regimes: steel +50 %/year in
  2021, −36 to −43 % (annualised) in 2022; 2026 so far copper +30 %, steel about +20 %, plastics
  PPI +20 %, TTF gas +134 % (annualised log changes).
- **Persistence differs by type.** Lag-1 autocorrelation of monthly changes: EU / US PPIs 0.6–0.8
  (S09 0.79, S10 0.74, S08 0.71, S11 0.66), MEPS coils ≈ 0.55, stainless 304 DE 0.45, LME metals and
  FX 0.1–0.3 (copper S01 0.26, D01 0.20). PPIs are averages of contract prices, so their changes
  trend: they are where a model is most likely to beat the random walk.
- **Momentum over 3 months.** Past 3-month change vs next 3-month change: epoxy +0.38, plastics
  +0.32, steel and stainless +0.11 to +0.14, copper and aluminium ≈ 0. **Use:** own 1/3/6/12-month
  changes as features; for LME metals the random walk is the realistic benchmark.
- **Fat tails.** Excess kurtosis of 3-month changes: MEPS steel 1.6–2.2, stainless 1.1–1.4,
  plastics 2.7, copper and aluminium 0.1–0.3. Steel and plastics are right-skewed: big moves are
  mostly up. **Use:** empirical quantiles, asymmetric bands allowed.

Annualised volatility of monthly log changes by period, and whether it clusters (Ljung–Box on
squared changes):

| Series | 2017–19 | 2020–21 | 2022 | 2023–24 | 2025–26 | Clusters |
|---|---|---|---|---|---|---|
| MEPS CR coil FR | 6 % | 23 % | 37 % | 17 % | 10 % | Yes |
| MEPS HDG coil DE | 8 % | 23 % | 37 % | 17 % | 9 % | Yes |
| CRU stainless 304 DE | 14 % | 16 % | 32 % | 20 % | 9 % | Yes |
| Copper EUR (D01) | 12 % | 16 % | 19 % | 13 % | 14 % | No |
| Aluminium EUR (D02) | 11 % | 15 % | 25 % | 14 % | 19 % | No |
| Plastics PPI EU (S11) | 3 % | 8 % | 8 % | 4 % | 11 % | Weak |
| Epoxy resin | 7 % | 13 % | 11 % | 7 % | 10 % | No |

**Use:** bands scale with recent (EWMA) volatility, then are calibrated to 80 % coverage. A fixed
band is too wide in calm years and too narrow in shocks.

Spread of h-month log changes over each series' full history (P10 to P90):

| Series | +3 | +6 | +9 |
|---|---|---|---|
| Copper EUR (D01) | −0.08 to +0.13 | −0.09 to +0.21 | −0.08 to +0.29 |
| Aluminium EUR (D02) | −0.10 to +0.13 | −0.13 to +0.22 | −0.14 to +0.30 |
| MEPS CR coil DE | −0.10 to +0.16 | −0.14 to +0.22 | −0.16 to +0.25 |
| CRU stainless 304 DE | −0.12 to +0.15 | −0.18 to +0.21 | −0.25 to +0.28 |
| Steel PPI EU (S09) | −0.05 to +0.10 | −0.08 to +0.19 | −0.12 to +0.28 |
| Plastics PPI EU (S11) | −0.04 to +0.07 | −0.08 to +0.15 | −0.10 to +0.20 |
| Epoxy resin | −0.06 to +0.08 | −0.11 to +0.14 | −0.12 to +0.23 |

Distributions lean upward because the sample contains several rallies.

## 6. Relationships and leading indicators

- **Use changes, not levels.** Epoxy and Hungarian power correlate 0.89 in levels, 0.05 in monthly
  changes.
- **No reliable long-run link.** Of 12 pairs tested for cointegration only one passes at 5 %, about
  what chance gives. Copper / aluminium is borderline.
- **The 8 MEPS coil series (HR, CR, HDG, EG × DE, FR) move as one:** 3-month change correlations
  ≈ 1, so one steel model covers them. Iron ore (S04) tracks EU steel only weakly (≈ 0.3).
- **Materials of different types also move together.** 3-month change correlations since Nov
  2016: carbon steel–stainless 0.60, copper–aluminium 0.67, plastics with the rest 0.28–0.53.
  **Use:** the BOM index resamples whole months of residuals across materials; independent bands
  would be too narrow, because in a shock materials rise together.
- **Leads are short.** Correlation of the target's monthly change with the driver's change k
  months earlier (band for zero: ±0.18; full sample, exploratory):

| Target ← driver | k = 1 | k = 2 | Holds at 3–9 months? |
|---|---|---|---|
| Steel PPI S09 ← MEPS CR coil DE | 0.68 | 0.51 | Yes (0.39–0.43) |
| Plastics PPI S11 ← Brent | 0.58 | 0.46 | No |
| CRU stainless 304 DE ← nickel | 0.53 | 0.33 | No |
| MEPS CR coil DE ← iron ore | 0.39 | 0.37 | No |
| Aluminium PPI S08 ← TTF gas | 0.37 | 0.29 | Yes (0.40–0.49) |
| MEPS HDG coil DE ← zinc | 0.22 | 0.21 | No |

IMF drivers (iron ore, nickel, Brent) arrive one month later than MEPS, so their k = 1 lead is not
usable in practice. The −0.46 between epichlorohydrin and epoxy at k = 1 comes from the May 2026
error (+0.23 without it).

**Drivers we keep.** Correlation of the driver's past 3-month change
(lag 0–3) with the target's next 3-month change, before 2020 (≈ 35 months) and over the full
sample. A driver is kept only if the sign is the same in both and there is an economic story; the
model's L1 penalty then picks among the kept ones at each origin.

| Target | Kept | Dropped |
|---|---|---|
| Steel (MEPS, S09, S10, S12) | Zinc S05, TTF gas ED02 | Iron ore (sign flips), power, US steel, S09 |
| Stainless 304, nickel S03 | EUR/USD S06, nickel S03 | — |
| Copper (D01, S01, S07) | EUR/USD S06 | Brent (no economic story) |
| Aluminium (D02, S02, S08) | EUR/USD S06, Al 3-month–cash spread | — |
| Plastics (S11, S13), epoxy | Brent E01, TTF ED02, energy index E22 | — |
| Iron ore S04, zinc S05 | Own lags only | — |

Expect clear gains for plastics, modest for steel, little for metals. The pre-2020 sample is thin:
candidates, not proof.

## 7. Naive baseline

Rolling-origin backtest, origins Jan 2020 onwards, each series from its own last month (no
publication lag simulated, revised data: slightly flattering). Random walk = last value; bands =
past h-month change quantiles. MAPE = mean absolute percentage error; coverage target 0.80.

| Series | MAPE +3 / +6 / +9 | P10–P90 coverage +3 / +6 / +9 |
|---|---|---|
| Copper EUR (D01) | 7.1 / 10.5 / 12.9 % | 0.71 / 0.71 / 0.60 |
| Aluminium EUR (D02) | 8.9 / 12.6 / 15.3 % | 0.62 / 0.63 / 0.61 |
| MEPS CR coil DE | 12.0 / 16.4 / 18.3 % | 0.61 / 0.64 / 0.62 |
| MEPS HDG coil DE | 11.7 / 15.7 / 17.7 % | 0.62 / 0.66 / 0.63 |
| CRU stainless 304 DE | 10.0 / 16.2 / 21.5 % | 0.74 / 0.68 / 0.58 |
| Steel PPI EU (S09) | 4.7 / 8.7 / 12.1 % | 0.67 / 0.64 / 0.56 |
| Plastics PPI EU (S11) | 4.3 / 7.4 / 9.9 % | 0.55 / 0.51 / 0.57 |
| Epoxy resin | 5.0 / 8.1 / 11.0 % | 0.69 / 0.61 / 0.58 |
| Nickel (S03) | 11.2 / 15.0 / 17.1 % | 0.83 / 0.81 / 0.82 |

- The seasonal naive (value 12 months before) loses to the random walk in all 36 series × horizon
  cells.
- **Bands fail in shocks.** Coverage is 0.22–0.61 for targets in 2020–22 and 0.67–0.91 for
  2023–26.
- **Small effective sample.** Overlapping horizons leave about 26 / 12 / 8 independent errors at
  +3 / +6 / +9, so coverage carries roughly ±0.18 / ±0.27 / ±0.35 (2 standard errors).
- **Selection rule.** A model replaces the random walk for a target × horizon only if its P50
  error is no higher **and** its P10–P90 coverage is within 0.75–0.85; ties go to the simpler
  model.

## 8. BOM to price series

**Exact** = market price for the same material in €/t or convertible; **proxy** = index or related
material, no € level; **missing** = nothing in the data.

Reference: the 20 Nov v1 BOM (`RM_Prices_XHEC_Challenge_v1.xlsx`), per Schneider's instruction to
use the latest version and document the differences (Schneider's guidance).

| Product | BOM line | Share | Best series | BOM proxy | Status |
|---|---|---|---|---|---|
| AirSeT | Carbon steel, CR coil | 62.8 % | MEPS / CRU CR coil Germany (Hungary parts are indexed to Germany) | S09 | Exact |
| AirSeT | Stainless 304L | 13.9 % | CRU 304 CR 2 mm, BASE + Alloy | S09, S03 | Exact (304, not 304L) |
| AirSeT | Copper | 5.2 % | D01 / LME file | S07 | Exact (new in v1) |
| AirSeT | Epoxy resin | 3.0 % | Epoxy resin €/t (`EPX_RESIN`) | S11 | Exact price available; the BOM maps it to S11 (new in v1) |
| AirSeT | PBT, ETP | 1.9 %, 1.5 % | none (L04, L06 empty) | S11, S13 | Proxy |
| AirSeT | PE, PVC, PP | 0.3 %, 0.1 %, 0.1 % | none | S11, S13 | Proxy (new in v1) |
| AirSeT | Aluminium | 0.9 % | D02 / LME file | S08 | Exact |
| AirSeT | Other | 10.3 % | none | none | Missing: not priceable (Schneider) |
| RM6 | Carbon steel, CR coil | 46.6 % | MEPS / CRU CR coil France (plant in France) | S09 | Exact (given in v1) |
| RM6 | Stainless 304L | 18.0 % | CRU 304, BASE + Alloy | S09, S03 | Exact (304) |
| RM6 | Copper | 12.5 % | D01 / LME file | S07 | Exact |
| RM6 | Epoxy resin | 7.2 % | `EPX_RESIN` | S11 | Exact price available; BOM maps to S11 (new in v1) |
| RM6 | HDG Germany | 6.8 % | MEPS / CRU HDG coil Germany | S10 | Exact |
| RM6 | PET, PP, ETP | 1.8 %, 1.4 %, 1.2 % | none | S11, S13 | Proxy |
| RM6 | Aluminium | 1.6 % | D02 | S08 | Exact |
| RM6 | Brass | 1.1 % | none | none | Missing: proxy from copper and zinc (new in v1) |
| RM6 | Unidentified remainder | 1.8 % | none | none | Missing |
| Both (not in BOM) | Electronics, silver, SF6 | teardown only | none | none | Missing |

**Masses across sources:** AirSeT 547 kg (v1), 629 kg (12 Nov); RM6 310 kg (v1), 275 kg
(benchmark), 715 kg (teardown, of which 629 kg steel). We use the v1 BOM.

**Raw-material cost per unit, Sep 2026 prices (stainless Aug 2026)**, v1 BOM: carbon steel on MEPS
CR Germany (AirSeT) and France (RM6), HDG on MEPS Germany, stainless on CRU 304 Germany, Cu / Al on
D01 / D02, every plastic incl. epoxy at an assumed 3 €/kg on S11 (the BOM mapping); brass, Other
and the remainder left out.

| | AirSeT | RM6 |
|---|---|---|
| Priced mass | 490 of 547 kg | 301 of 310 kg |
| Priced RM cost | €975 | €900 |
| Biggest lines | Copper 37 %, carbon steel 29 %, stainless 21 %, plastics 11 % | Copper 54 %, stainless 17 %, carbon steel 13 %, plastics 12 % |

- **AirSeT costs more than RM6 throughout.** AirSeT minus RM6: +€122 (Jan 2021), +€264 peak
  (Apr 2022), +€62 low (Jan 2026), +€73 (Aug 2026). Copper is the larger line in RM6, so the copper rally since 2021 narrows the gap.
- Both costs move together (12-month changes correlate 0.99) because steel and copper drive both.
- Epoxy is now a BOM line in both products: pricing it on `EPX_RESIN` instead of
  the S11 index would change the plastics line.
- **€ at risk per unit** = line cost × width of its 6-month P10–P90 move (simple % changes, Nov
  2016 → Sep 2026):

| Product | Largest lines (€ per unit) | Total priced RM cost |
|---|---|---|
| RM6 | Copper 154 · stainless 70 · carbon steel 39 · plastics 25 | €900 |
| AirSeT | Copper 113 · carbon steel 99 · stainless 94 · plastics 26 | €975 |

## 9. Goal B data

| Question | Answerable from our data? |
|---|---|
| Competitors and technology at 24 kV | Partly: 5 competitors; only Eaton Xiria is SF6-free; **SM AirSeT is not in the benchmark** |
| SM6 vs AirSeT material cost gap | Yes, for raw materials ([section 8](#8-bom-to-price-series)) |
| Competitor cost structure | Directionally: material ≈ 80 % of should-cost; teardowns inferred; SGC broken (€19) |
| Competitor selling prices | Yes, yearly and synthetic: RMU price benchmark, P10 / P50 / P90 for 6 brands 2017–2026 ([section 11](#11-rmu-prices-and-price-vs-cost)); one real price (Siemens 8DJH, €15,530) |
| TCO, customer ESG demand, non-EU regulation, market sizes | No: needs desk research or Schneider input |
| Supplier risk | Partly: 9 suppliers, latest revenue €5.6 m to €313 m, EBITDA margin −8 % to +16 %; no link from supplier to part |

## 10. Gaps

| Need | Why | Substitute |
|---|---|---|
| RMU selling prices by configuration | Margin at risk, quote rule, price premium | Yearly brand prices, no configuration split; ask for configuration and margin |
| AirSeT "Other", RM6 remainder, brass | No composition or price series | Schneider: treat as non-priceable, run a sensitivity if material; brass from a copper–zinc proxy |
| Electronics, silver, SF6 masses | Named in the brief | Teardown estimates (inferred); epoxy and brass are now in the v1 BOM |
| Plastics prices in €/t | Cost bridge | S11 + anchor (**Assumption**) |
| Rotterdam premiums (L07, L08) | Landed EU price | None free |
| GBP and SEK FX | UK and Sweden steel | ECB public series |
| Deflator | Real terms | Eurostat HICP |
| PPI vintages | Revision effects | Eurostat / ALFRED vintages |
| Purchase prices after 2018, quote terms | Index-to-price spread, quote rule | Ask Schneider |
| TCO inputs, non-EU markets, regulation | Goal B | Desk research |

## 11. RMU prices and price vs cost

Source: `RMU_IQI_EU_Price_Benchmark_2017-2026_Synthetic.xlsx`, sheet `ML_Trend` (unlocked copy
received 19 Nov 2026). Yearly P10 / P50 / P90 unit prices, EUR ex-VAT, 6 brands, synthetic
("AI/ML"), no configuration (1F–4F) split.

| Brand | P50 2026 | vs Schneider | Change 2026 | Avg yearly change 2018–25 | P10–P90 width (% of P50) |
|---|---|---|---|---|---|
| SwitchGear Company | €9,154 | −25.2 % | +32.3 % | +3.0 % | 48.5 % |
| Ormazabal | €9,652 | −21.1 % | +35.8 % | +2.8 % | 37.0 % |
| Eaton (SF6-free) | €11,560 | −5.5 % | +8.4 % | +0.9 % | 53.0 % |
| **Schneider Electric** | **€12,233** | — | +40.0 % | +2.4 % | **27.8 %** |
| ABB | €12,273 | +0.3 % | +39.8 % | +2.6 % | 42.6 % |
| Siemens | €13,762 | +12.5 % | +33.4 % | +2.6 % | 45.8 % |

- **2026 is a step change** for every brand except Eaton; before that prices rose 6–8 %/year in
  2021–22 and were flat in 2023–25.
- **Eaton was the most expensive brand until 2025 and is now cheaper than Schneider.** The
  SF6-free alternative is not a premium product in this data.
- **Schneider prices most consistently** (narrowest band).
- **Against the SF6 average** (Schneider, ABB, Siemens, Ormazabal, SGC), Eaton's SF6-free premium
  fell from +46 % in 2017 to +1 % in 2026. The cause is not in the data (the EU SF6 ban from
  January 2026 is the obvious candidate).

**Price vs material cost.** RM6 fixed-weight material cost index (section 8 cost shares, v1 BOM,
prices relative to Sep 2026), yearly average, against Schneider's yearly P50 change:

| Year | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|---|---|---|---|---|---|
| RM6 material cost | +0.6 % | −5.6 % | −3.5 % | +58.2 % | +8.7 % | −16.6 % | +0.2 % | −1.6 % | +20.6 % |
| Schneider price | +0.9 % | +0.3 % | −0.8 % | +6.7 % | +7.3 % | +1.2 % | +3.8 % | +0.1 % | +40.0 % |

\* Jan–Sep 2026.

- Correlation of the price change with the same-year cost change 0.38, with the previous year's
  0.00: any pass-through happens within the year. Only 8 points: directional.
- **2021: cost absorbed** (cost +58 %, price +7 %); **2026: more than passed on** (cost +21 %,
  price +40 %). Without indexation, a 2021-type shock lands on margin.
- Same story as a ratio (12 Nov BOM, not yet recomputed with v1): Schneider P50 price ÷ priced RM
  cost fell from about 17 to about 11 in 2021–22 and recovered by 2024–25. That drop is the margin
  squeeze the quote rule must prevent.

**Material cost vs price.** Priced BOM raw material (v1) is **€900 (RM6) and €975 (AirSeT),
7.4 % and 8.0 % of the 2026 Schneider P50**, against ≈ 80 % material in the competitor should-cost (≈ €2,600 of
€3,307; the real Siemens 8DJH price of €15,530 is ≈ 4.7× that should-cost, so material is ≈ 17 %
of that price). The gap is processing (bought parts vs commodity), unpriced BOM lines and everything
between should-cost and list price (ETO engineering, channel, warranty, margin). A +20 % RM shock
is ≈ 1.5 % of price, but its share of **margin** depends on a margin we do not have: ask
Schneider, and show quote rules as a sensitivity table (margin × cost base) until then.

## 12. Schneider's guidance on data and method
Guidance shared with all teams during the challenge:

| Topic | Answer | Effect on us |
|---|---|---|
| Copper / aluminium reference for offers | Not prescribed: test and justify LME cash vs 3-month | Both are in the pipeline (`LME_{CU,AL}_{CASH,3M}_{USD,EUR}`); the pricing step uses cash |
| External data | Public data allowed (daily LME, FX, longer Eurostat) if documented and known at forecast time | Optional; the backtest's cut-off rules apply to any new series |
| BOM version | Use the latest as the reference; document discrepancies | v1 used here (section 8) |
| "Other" material | Non-priceable; sensitivity if material | Left unpriced (section 10) |
| Cost index weighting | Cost (price × mass), not mass; state a base date | Matches section 8 and the cost index |
| Missing series (brass, L01–L08) | Use the best public proxy and explain it | L01–L03 rebuilt from MEPS / CRU; brass needs a proxy |
| Provisional observations | Exclude or flag | LME month-to-date already dropped |
