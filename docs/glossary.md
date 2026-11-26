# Glossary

The words the quote tool (`app/`) uses. Each idea has one word, and the app, the exported CSV
and the docs use the same one.

| Term | Meaning |
|---|---|
| Quote price | Price per unit we put on the quote: list price + price adjustment + buffer. |
| List price | Price per unit before raw materials are taken into account. Defaults to Schneider's 2026 benchmark price. |
| Material cost | € of priced raw material in one unit: kg of each material × its price. |
| Exposed share | Material cost ÷ list price: the part of the price that moves with raw materials. |
| Price adjustment | Expected (P50) material cost move by the purchase month, added to the price. |
| Buffer | Extra cover above the expected move, set by the scenario: up to P90 for Downside, none for Baseline, down to P10 for Upside. |
| Margin at risk | Margin lost per unit at list price if material costs reach P90. Shown in € and as % of margin. |
| Safe validity | Longest quote validity whose buffer stays under 10 % of the margin. |
| Reprice trigger | Move in one material's price that costs 10 % of the margin. Past it, reprice or index. |
| Scenario | Cost outcome the quote covers: Downside (P90), Baseline (P50) or Upside (P10). |
| Cost shock | A chosen copper or steel price move, with all other materials held flat. |
| Indexation | The price follows the cost index, so the customer carries the cost move. |
| Fixed price | The list price held for the whole quote, with materials ignored. |
| P10 / P50 / P90 | Forecast range: 1 time in 10 below P10, half the time below P50, 1 time in 10 above P90. |
| Cost index | A product's material cost relative to today (100 = Sep 2026). |
| Material cost at risk | € per unit one material adds if it alone reaches its P90. |
| Cost gap | AirSeT material cost minus RM6 material cost, € per unit. |
| Skill | 1 − our forecast error ÷ the naive forecast's error, since 2020. Above zero beats naive. |
| Naive forecast | No change: the last known value (random walk for a material, 100 for a cost index). |
| Coverage | Share of past outcomes that landed inside P10 to P90. 80 % is the target. |
| Horizon | Months from Sep 2026 to the forecast month: 3, 6 or 9. |
| Range | P10 to P90. Written "range €824 to €1,118 (P10 to P90)". |
| Track record | Skill and coverage of a forecast, every month since 2020. |
| Model | The forecast method the team chose for a series and horizon, shown by its readable name (e.g. "MEPS pooled (3-month P50 held)"). |

Formulas are in [`pricing.md`](pricing.md).
