# Pricing: cost index, scenarios, cost bridge and quote rules

Turns the material forecasts into what a pricing team uses: a product cost index, € per unit,
margin at risk and quote rules, for RM6 and RM AirSeT at +3 / +6 / +9 months. Code:
`src/schneider_forecast/pricing.py`.

## Summary
- **Cost index per product** (origin 2026-09 = 100), weighted by **cost** (price × mass), as
  Schneider asked. P10 / P50 / P90 come from a **joint simulation**: materials move together, so
  the index band is not the sum of the material bands.
- **Six CSV rows** (`target_type = bom_index`): 2 products × 3 horizons, stacked into the
  submission file by `submit.py`.
- **Cost bridge:** index change → € per unit → margin at risk, per material, horizon and scenario.
- **Quote rules:** price adjustment, risk buffer, quotation validity and indexation trigger, all
  from the same three numbers (index P50, index P90, exposed cost share).
- **Sensitivity table** (exposed cost share × margin), because Schneider did not share either.
- **Inputs for Goal B:** the AirSeT vs RM6 cost gap with its band, € at risk per material,
  validity and trigger per product.

Section numbers (§) refer to [`eda_findings.md`](eda_findings.md) (v1 BOM, §8 and §11). The
forecast design is in [`methodology.md`](methodology.md); this doc implements its §4 (business
link) on the v1 BOM.

## How to use it
```bash
uv run python -m schneider_forecast.data       # clean data in data/processed/
uv run python -m schneider_forecast.pricing    # about 25 s, writes 14 files (see Results)
```
```python
import pandas as pd
from schneider_forecast.config import DATA_PROCESSED

bom_rows = pd.read_csv(DATA_PROCESSED / "bom_index_rows.csv")  # 6 CSV rows
quotes = pd.read_csv(DATA_PROCESSED / "quote_rules.csv")  # product × horizon × scenario
```

## Inputs

| File | What the pricing step uses |
|---|---|
| `bom_clean.csv` | The v1 BOM: product × line, `plant_country` (AirSeT HU, RM6 FR), share, kg, `price_series` |
| `bom_versions.csv` | 12 Nov CSV, 19 Nov xlsx and v1 stacked: BOM-version sensitivity |
| `prices_wide.csv` | Prices at the origin (cost weights) and past monthly changes of every BOM series (co-movement for the simulation); also `MEPS_FR_CR` (RM6 steel), `LME_CU_{CASH,3M}_EUR`, S05 (zinc, for brass) |
| `series_catalog.csv` | Units, last month, `needs_nowcast` (L02 ends 2026-08) |
| `rmu_prices.csv` | Schneider P50 unit price (the price P in the bridge) |
| `outputs/forecasts/p2_forecasts_202609.csv`, `p3_forecasts_202609.csv` | Material forecasts at origin 2026-09, in the submission columns |
| `outputs/backtest/p2_selected_strict.csv`, `p3_selected_strict.csv` | Strict-run backtest rows of the chosen models, for the index backtest |

- Target months are 2026-12, 2027-03, 2027-06 for every series (origin + h, as in the harness).
- Any series missing from the forecast files gets a **placeholder forecast** (random walk with
  volatility-scaled bands, half-life 3) and a warning. With the final forecasts none is needed.

**v1 BOM lines → series** (from `bom_clean.csv`, EDA §8):

| Product | Line | Share | Price at origin | Moves with (forecast) | Status |
|---|---|---|---|---|---|
| AirSeT | Carbon steel CR coil | 62.8 % | L01 (MEPS CR Germany; HU plant) | L01 | Exact |
| AirSeT | Stainless 304L | 13.9 % | L02 (CRU 304 Germany) | L02 | Exact (304) |
| AirSeT | Copper | 5.2 % | D01 | D01 | Exact (new in v1) |
| AirSeT | Epoxy resin | 3.0 % | 3 €/kg (EDA §8) | S11 | Proxy; `EPX_RESIN` as sensitivity |
| AirSeT | PBT, ETP, PE, PVC, PP | 3.9 % | 3 €/kg (EDA §8) | S11 | Proxy |
| AirSeT | Aluminium | 0.9 % | D02 | D02 | Exact |
| AirSeT | Other | 10.3 % | none | — | Left out (not priceable, Schneider) |
| RM6 | Carbon steel CR coil | 46.6 % | `MEPS_FR_CR` (FR plant) | L01 | Exact level; change from L01 |
| RM6 | Stainless 304L | 18.0 % | L02 | L02 | Exact (304) |
| RM6 | Copper | 12.5 % | D01 | D01 | Exact |
| RM6 | Epoxy resin | 7.2 % | 3 €/kg (EDA §8) | S11 | Proxy; `EPX_RESIN` as sensitivity |
| RM6 | HDG coil | 6.8 % | L03 (MEPS HDG Germany, as labelled) | L03 | Exact |
| RM6 | PET, PP, ETP | 4.4 % | 3 €/kg (EDA §8) | S11 | Proxy |
| RM6 | Aluminium | 1.6 % | D02 | D02 | Exact |
| RM6 | Brass | 1.1 % | none | — | Left out; copper–zinc proxy as sensitivity |
| RM6 | Unidentified remainder | 1.8 % | none | — | Left out |

- **RM6 steel:** priced at the French level (Schneider's part-to-index mapping follows the plant),
  but moved with the L01 forecast. The eight MEPS coils move as one (EDA §6), so nobody needs to
  forecast France separately.
- Electronics, silver and SF6 are not BOM lines: out of the index, stated as a data limit.

## Outputs

| What | File |
|---|---|
| 6 `bom_index` rows: `target_id` = `RM6_NE_IQI_433520` / `RMAirSeT IIQ 24kV IEC`, `region` = `EU`, `unit` = `index (origin=100)`, P10 / P50 / P90, `model_name` = `bom_joint_sim_v1` | `data/processed/bom_index_rows.csv` |
| € per unit by material, margin at risk, quote rules per horizon × scenario, validity, triggers | `pricing_cost_bridge.csv`, `quote_rules.csv`, `quote_validity.csv`, `index_triggers.csv` |
| Sensitivity tables and BOM-version checks | `sensitivity_table.csv`, `pricing_sensitivities.csv` |
| AirSeT vs RM6 cost gap (€, P10 / P50 / P90 per horizon) | `cost_gap.csv` |
| 2021 replay and the index backtest | `replay_2021*.csv`, `index_backtest*.csv` |

## Step 1 · Cost weights at the origin

For each product and each priced BOM line m (base date = the origin, 2026-09; L02 2026-08):

```
c_m = kg_m × p_m          (€ per unit; p_m = price at the origin in €/kg)
C_0 = Σ c_m               (priced raw-material cost per unit)
w_m = c_m / C_0           (cost weight; sums to 1)
```

- p_m: €/t series ÷ 1,000. Plastics and epoxy: 3 €/kg at the origin (EDA §8), later moves
  follow S11.
- Weights are **cost** shares, not mass shares, as Schneider asked: a kilo of copper weighs
  about 15 times a kilo of steel in the index.
- **v1 BOM, Sep 2026 prices (EDA §8):**

| | AirSeT | RM6 |
|---|---|---|
| Priced mass | 490 of 547 kg | 301 of 310 kg |
| C_0, priced RM cost | **€974** | **€898** |
| Cost weights | Copper 37 %, carbon steel 29 %, stainless 21 %, plastics 11 % | Copper 54 %, stainless 17 %, carbon steel 13 %, plastics 12 % |

Copper leads both products in €, although it is only 5 % (AirSeT) and 12.5 % (RM6) of the mass.

## Step 2 · BOM cost index

For horizon h (3, 6, 9) and r_m,h = price at origin + h ÷ price at the origin:

```
I_h = 100 × Σ_m w_m × r_m,h
```

- The index only needs the weights, not the absolute kg: if all masses are off by the same factor,
  the index does not change, only the € figures do. That is why the BOM version matters more for
  the € bridge than for the CSV rows.
- A line kept flat (e.g. AirSeT "Other" in the sensitivity) has r = 1 and damps the index.

## Step 3 · Scenarios from the P10 / P50 / P90 bands

**The quantile of a sum is not the sum of quantiles** (methodology §4.1). Adding the P90s assumes
every material hits its bad case in the same month; adding nothing assumes they never do. The two
products' costs correlate 0.99 over 12 months (EDA §8), and copper–aluminium 0.67, carbon
steel–stainless 0.60 (EDA §6). So the index is simulated:

1. **Each material's range from its forecast.** Turn its P10 / P50 / P90 into a full distribution
   of the h-month log change: straight lines between the three points, tails extended with the
   same slope.
2. **Co-movement from history.** Take the h-month log changes of all BOM series on the same past
   dates (overlapping windows, 2016 → 2026), and turn each one into its rank (0 to 1) within its own
   history.
3. **Draw.** Pick a past date at random (10,000 draws), read the rank of every material on that
   date, and read each material's change at that rank from step 1. A month that was bad for copper
   and aluminium stays bad for both, but the size of the move comes from the forecast.
4. **Index per draw** with step 2, then read P10 / P50 / P90 of the index off the 10,000 draws.

```
Scenarios per product and horizon:
  downside = I_h(P10)    baseline = I_h(P50)    upside = I_h(P90)
```

Checks: P10 ≤ P50 ≤ P90; the index P90 lies between the weighted average of the material P50s and
the weighted sum of the material P90s; with all bands at zero the index is 100.

This is methodology §4.1's "resample whole months of past changes", with the band sizes taken
from the forecasts instead of from history.

## Step 4 · Cost bridge: € per unit and margin at risk

```
ΔC_h(q)   = C_0 × (I_h(q) / 100 − 1)          € per unit, q ∈ {P10, P50, P90}
ΔC_m,h(q) = c_m × (r_m,h(q) − 1)               € per unit for one material (explanation only:
                                               the lines do not add up to ΔC_h, see step 3)
```

**Order of magnitude** before the forecasts (EDA §8, width of the historical 6-month P10–P90
move, € per unit):

| Product | Largest lines | Priced RM cost |
|---|---|---|
| RM6 | Copper 154 · stainless 70 · carbon steel 39 · plastics 25 | €898 |
| AirSeT | Copper 113 · carbon steel 99 · stainless 94 · plastics 26 | €974 |

To get from cost to price and margin, two numbers Schneider has not given us:

| Symbol | Meaning | Working value |
|---|---|---|
| P | Unit selling price | Schneider P50 2026 = **€12,233** (`rmu_prices.csv`, synthetic; same P for both products) |
| α | Exposed cost share: the share of the price whose cost moves with the index | Base: **α_0 = C_0 / P**: AirSeT ≈ **8.0 %**, RM6 ≈ **7.3 %** |
| m | Margin, as a share of price | Unknown: **20 %** central, 10 % and 30 % in the sensitivity |

```
Margin at risk, share of price :  MaR_h = α × (I_h(P90) / 100 − 1)
Margin at risk, € per unit     :  MaR_h × P
Margin at risk, share of margin:  MaR_h / m
```

α can be larger than α_0: bought parts (castings, busbars, enclosures) carry metal too, and
unpriced BOM lines ("Other", brass, remainder) are left out. That is what the sensitivity table
covers.

## Step 5 · Quote rules per horizon

From methodology §4.3, with the thresholds made concrete. h = months from the quote to when the
material is bought: quotation validity + 1 month lead time (the steel part mapping uses M − 1).

| Lever | Formula | Plain words |
|---|---|---|
| Price adjustment | P_quote = P_list × (1 + α × (I_h(P50) / 100 − 1)) | Pass on the expected cost move, only on the exposed share |
| Risk buffer | B_h = P_list × α × (I_h(P90) − I_h(P50)) / 100 | Covers the upside scenario: 9 times out of 10, cost ends below it |
| Quotation validity | V = longest h in {3, 6, 9} with α × (I_h(P90) − I_h(P50)) / 100 ≤ τ | Keep the quote open as long as the buffer stays within the tolerance |
| Indexation trigger | Revise when the named index m moves more than X_m = τ / (α × w_m); revision = P_list × α × w_m × index change | Beyond the validity, or in long contracts, the price follows LME copper (both products, largest weight), MEPS CR coil and CRU 304 |
| Scenarios | Quote at I_h(P10), I_h(P50), I_h(P90) | Downside / baseline / upside price for the tender team |

- **Tolerance τ** (working): the quote may lose at most 10 % of the margin before it must be
  revised, τ = 0.10 × m = 2 % of price at m = 20 %.
- **Example** (shape only, before forecasts): RM6, copper weight w ≈ 0.54, τ = 2 % of price. With
  α = α_0 = 7.3 %, the trigger is X = 0.02 / (0.073 × 0.54) ≈ ±50 %: a raw-material-only cost base
  barely needs indexation. With α = 17 %, X ≈ ±22 %. The trigger depends far more on α than on
  the forecast, so α is the first number to get from Schneider.
- **Crisis buffer: tested and dropped.** The shared bands still cover only 43–62 % in 2020–22
  ([`forecasting_other.md`](forecasting_other.md) §4), so we tried scaling the buffer by recent ÷
  median volatility (never down). The 2021 replay (Results) shows it counts volatility twice (the
  bands already widen with it) and overprices by about a quarter of the margin after a shock, while
  cutting the worst loss only a little. The live quote rules use the band buffer alone; the
  replay keeps the crisis option as evidence. Shocks are handled by indexation instead.
- **Copper reference:** the index uses D01 (LME cash in EUR, the forecast target). For the
  indexation clause, cash and 3-month are both kept (`LME_CU_CASH_EUR` vs `LME_CU_3M_EUR`), as
  Schneider asked teams to justify the choice.
- **FX:** D01 and D02 are already in EUR, so their bands include EUR/USD risk. No separate FX
  add-on, or FX would be counted twice; the FX part is shown only as an explanation (S06 band ×
  USD-priced share). This refines the FX line of methodology §4.4.
- **Supplier risk:** no buffer add-on (no link from supplier to part, EDA §9). Handled instead
  as a procurement lever: see "Procurement levers" below.
- **Check on history (2021 replay):** the rules replayed month by month over 2020–23 with only the
  data known each month, compared with what costs really did (RM6 cost +58 %, price +7 % in 2021,
  EDA §11). Results below.

## Step 6 · Sensitivity table

Margin lost, as a share of the margin, for a given cost shock. Shown here for a +20 % shock (EDA
§11: "≈ 1.5 % of price"); the final tables use each product's I_h(P90) per horizon.

| α (exposed share of price) | Where the value comes from | m = 10 % | m = 20 % | m = 30 % |
|---|---|---|---|---|
| 7.3 % | RM6 α_0, priced raw material only | 15 % | 7 % | 5 % |
| 8.0 % | AirSeT α_0, priced raw material only | 16 % | 8 % | 5 % |
| 10 % | Priced RM plus the unpriced lines (**assumption**) | 20 % | 10 % | 7 % |
| 17 % | Material share of the one real competitor price (Siemens 8DJH, EDA §11) | 34 % | 17 % | 11 % |
| 25 % | Bought parts with metal content (**assumption**, upper case) | 50 % | 25 % | 17 % |

Cell = α × 20 % ÷ m. Read: if 17 % of the price is exposed and the margin is 20 %, a 20 % cost
rise eats 17 % of the margin. The same grid gives the validity and trigger per cell.

## Goal B input: AirSeT vs RM6 cost gap
On priced raw material AirSeT costs more than RM6 throughout: +€122 (Jan 2021), +€264 peak
(Apr 2022), +€73 (Aug 2026) (EDA §8). RM6 has more copper, so the copper rally
narrows the gap. Its P10 / P50 / P90 come at +3 / +6 / +9 from the same simulation (both
products in one draw), under each BOM sensitivity.

## Results

All numbers below use the final Sep 2026 forecasts: steel from the pooled MEPS model and
Chronos-2 (stainless), copper and aluminium from the random walk, plastics from the blend. No
placeholder is needed. Margin shares assume m = 20 % and α = α_0 (raw
material only), until Schneider answers.

**Files written to `data/processed/`:** `bom_index_rows.csv` (6 CSV rows), `pricing_cost_weights.csv`,
`pricing_forecasts_used.csv`, `pricing_cost_bridge.csv`, `quote_rules.csv`, `quote_validity.csv`,
`index_triggers.csv`, `sensitivity_table.csv`, `cost_gap.csv`, `pricing_sensitivities.csv`,
`replay_2021.csv`, `replay_2021_summary.csv`, `index_backtest.csv`, `index_backtest_scores.csv`.

**Cost weights** match the EDA: €974 AirSeT (EDA rounds to €975), €898 RM6 (EDA €900); copper 37 % and
54 % of the cost.

**Cost index, the 6 CSV rows** (P10 / P50 / P90, 100 = Sep 2026):

| Product | +3 | +6 | +9 |
|---|---|---|---|
| AirSeT | 95.0 / 100.0 / 109.0 | 93.7 / 101.9 / 118.5 | 91.9 / 100.7 / 126.3 |
| RM6 | 93.5 / 99.7 / 108.0 | 91.3 / 101.0 / 116.5 | 91.7 / 100.3 / 124.5 |

The middle case rises up to 2 % at +6 months because the steel model expects steel up about 4–5 %;
copper (a random walk) stays flat.

**€ per unit and quotes** (price €12,233):

| Product | Margin at risk at P90, +3 / +6 / +9 | Risk buffer (share of price) | Quote with buffer | Validity |
|---|---|---|---|---|
| AirSeT | €88 / €180 / €256 (4 / 7 / 10 % of margin) | 0.7 / 1.3 / 2.0 % | €12,321 / €12,413 / €12,489 | 6 months |
| RM6 | €72 / €148 / €220 (3 / 6 / 9 % of margin) | 0.6 / 1.1 / 1.8 % | €12,305 / €12,381 / €12,453 | 9 months |

- **Indexation triggers** at α_0: copper ±68 % (AirSeT) and ±50 % (RM6), steel and stainless beyond
  ±85 %. With raw material at about 8 % of the price, indexation only matters if the exposed
  share is larger: the sensitivity table shows when it does.
- **Goal B cost gap** (AirSeT − RM6): +€75 today; +6 months P10 / P50 / P90 = €67 / €86 / €111,
  +9 months €58 / €75 / €118. AirSeT stays dearer on raw material in 9 draws out of 10.

**BOM and price sensitivities** (+6 months): the index barely moves (P90 115–122 in every case), the
€ cost moves a lot, so the CSV rows are robust and the € figures need their assumption stated.

| Case | AirSeT cost | RM6 cost | Index P90, AirSeT / RM6 |
|---|---|---|---|
| Base (v1 BOM) | €974 | €898 | 118 / 116 |
| Epoxy at resin price | €1,004 | €940 | 117 / 115 |
| Plastics at benchmark rates | €1,020 | €909 | 119 / 116 |
| "Other" kept flat at 4 €/kg | €1,198 | €898 | 115 / 116 |
| Brass as copper + zinc | €974 | €930 | 118 / 116 |
| 12 Nov BOM | €639 | €804 | 121 / 116 |
| 19 Nov BOM | €558 | €771 | 122 / 116 |

The 12 Nov case reproduces the team's earlier EDA figures (€641 / €805): a check on the code.

**2021 replay** (quote every month 2020–23, buy 6 months later; margin lost as a share of the
margin, negative = price ended above cost; grouped by purchase month). The replay refits the
team's random walk with volatility bands each month on the **strict data cut** (only prices
already published at the quote month, as in model selection), since the chosen models have no
forecast at every past month here; it uses the shared band code with its 2× volatility cap.

| Bought in 2021–22 | AirSeT avg / worst lost | AirSeT overpriced | RM6 avg / worst lost | RM6 overpriced |
|---|---|---|---|---|
| Fixed price | 9 % / **28 %** | 2 % | 7 % % | 1 % |
| Band buffer (live rule) | −4 % % | 10 % | −3 % % | 8 % |
| Band buffer × crisis factor | −25 % % | **29 %** | −15 % % | 18 % |

- The shock hit quotes made in late 2020: RM6 material cost rose 36–59 % within six months of
  quotes made between Aug 2020 and Jan 2021, and cost ended above the P90 in 42 % of 2021–22
  purchases. Bands widen only after prices have jumped.
- After the peak the buffers overprice (in calm 2023–24 too: 21 % of margin for AirSeT with the
  band buffer, 47 % with the crisis factor). A buffer cannot absorb a 2021-type shock without
  losing tenders: **indexation is the tool for shocks**, the buffer for normal months.

**Index backtest** (every month since 2020-01 on the strict-run backtest rows of the chosen models, harness metrics;
ours vs a naive index: P50 = 100, fixed bands from the basket's own past moves; both on the same
strict data cut):

| | Coverage (target 0.80), ours vs naive | P50 skill vs naive | Band skill vs naive |
|---|---|---|---|
| AirSeT +3 / +6 / +9 | 0.64 / 0.74 / 0.72 vs 0.62 / 0.57 / 0.49 | +4 % / +6 % / +6 % | +24 % / +24 % / +31 % |
| RM6 +3 / +6 / +9 | 0.68 / 0.70 / 0.69 vs 0.61 / 0.58 / 0.49 | +5 % / +7 % / +7 % | +19 % / +21 % / +28 % |

- Calm years (2023–26): coverage 0.77–0.93 and P50 skill +6 to +17 %: the material models add real
  accuracy to the index.
- Shock years (2020–22): bands still cover only 43–47 % (band skill +23 to +35 %), the same limit
  as for single materials.

## Procurement levers (Goal B input, B4)

The supplier balance sheets and Schneider's parts mapping, turned into two negotiation inputs
(`uv run python -m schneider_forecast.procurement`, after `pricing`). Supplier names never leave
the code: suppliers are numbered 1–9.

**1. Supplier strength** (`supplier_strength.csv`): latest year of each supplier's ratios, put in a
group with one lever each.

| Group | Suppliers | Rule | Lever |
|---|---|---|---|
| Strong | 2 | EBITDA margin ≥ 10 %, current ratio ≥ 1.2, interest coverage ≥ 5 (or no debt) | Long contract with prices tied to a public index; ask for index-only price changes |
| Watch | 4 | Neither strong nor fragile (includes one supplier with too little data) | Index-tied contract with a quarterly review; keep a second source qualified |
| Fragile | 3 | EBITDA margin < 0, current ratio < 1 or interest coverage < 1.5 | Do not squeeze on price; dual-source, short commitments, review finances often |

Limits: no file says which supplier delivers which part, so this cannot be tied to RM6 or AirSeT;
the latest year differs by supplier (2020 to 2025); one file has no income statement.

**2. Back-to-back indexation** (`back_to_back_indexation.csv`): Schneider already buys its steel
parts on public indices, with a 1-month lead time on every filled row. Our quote rules can sell on
the same indices, so a price jump moves cost and price together (the lesson of the 2021 replay).

| Buy-side index | Parts | Our series | What it means |
|---|---|---|---|
| HDG Benelux / Germany / France / UK / Spain | 292 | L03 | Same galvanised-steel index for quote clauses |
| CR France / Spain / Germany / UK | 299 | L01 | Same cold-rolled index for quote clauses |
| HR, EZ (hot-rolled, electro-galvanised) | 72 | — | Not RMU BOM lines: no sell-side clause needed |
| Copper, aluminium | not in the mapping | D01, D02 | Buy and sell on the same LME reference (cash or 3-month, to choose) |

The RM6 plant (France) buys on CR France, HDG France, EZ and HR France; the AirSeT plant (Hungary)
on CR Germany, HDG Germany and HDG France. This matches the steel price levels the cost index uses.

## Assumptions

| # | Question | Working assumption |
|---|---|---|
| 1 | Margin m | Not known: 20 % central, 10–30 % in the sensitivity |
| 2 | Cost base: which share of the price moves with raw materials (α)? | α_0 = priced RM ÷ price (7.3 % RM6, 8.0 % AirSeT); 10–25 % in the sensitivity |
| 3 | Epoxy (3.0 % AirSeT, 7.2 % RM6): S11 index (BOM mapping) or the real epoxy resin price? | S11 at 3 €/kg, as in the EDA; `EPX_RESIN` as a sensitivity |
| 4 | Plastics € level (S11 is an index) | 3 €/kg for every plastic; benchmark rates (5.50 €/kg PBT / ETP, 3.20 €/kg PET) as a sensitivity |
| 5 | AirSeT "Other" (10.3 %) | Left out (Schneider: not priceable). Sensitivity: kept flat at 4 €/kg, which damps the index |
| 6 | RM6 brass (1.1 %) and unidentified remainder (1.8 %) | Left out. Sensitivity: brass = 63 % copper (D01) + 37 % zinc (S05 in EUR) |
| 7 | BOM version | v1 (Schneider: the latest is the reference); 12 Nov and 19 Nov as a sensitivity on € per unit |
| 8 | Steel country | Plant country: AirSeT Germany, RM6 France for the price level; changes from the Germany forecasts (L01, L03) |
| 9 | Copper reference for offers | LME cash (D01) in the index; cash and 3-month both kept for the indexation clause |
| 10 | Which product the benchmark's Schneider price is | The same P (€12,233) for RM6 and AirSeT |
| 11 | Is `bom_index` material cost only? | Yes: priced raw material only |
| 12 | Lead time between order and material purchase | 1 month (steel part mapping) |
| 13 | Tolerance τ for validity and triggers | 10 % of margin |

Every working assumption here is also logged in [`data_transformations.md`](data_transformations.md)
once the code uses it.

## Code
| File | Content |
|---|---|
| `src/schneider_forecast/pricing.py` | 1 `cost_weights` · 2 `index_from_ratios` · 3 `load_forecasts`, `simulate_index`, `index_scenarios` · 4 `cost_bridge` · 5 `quote_rules`, `quote_validity`, `index_triggers` · 6 `sensitivity_table` · 7 `run_sensitivities` · 8 `replay_quotes`, `replay_summary` · 9 `index_backtest`, `index_backtest_scores` · `main` |
| `tests/test_pricing.py` | 26 tests on synthetic data (plus `tests/test_pricing_smoke.py` on the real data, skipped without it): weights sum to 1; flat prices give 100; zero-width bands give 100 in every draw; index band narrower than adding up material P90s; quote, validity, trigger and sensitivity formulas; each sensitivity option; harness file layout; crisis factor; replay; index backtest |
| `docs/data_transformations.md` | Steps R1 to R11 |
| `docs/models_and_licenses.md` | Joint simulation, naive index, placeholder forecasts |
