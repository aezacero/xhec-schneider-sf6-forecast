# Goal B research: questions and answers (Ali)

Research of 23/11/2026 for my own B1–B5 proposal. Facts link to sources; **vendor** = a
manufacturer's claim; **inference** = my reasoning; **assumption** = a number to check. Questions
8–11 list the options the evidence supports, not a choice. Our data covers RM6 / RM AirSeT; the
slides ask about SM6 / SM AirSeT: same technology change, numbers may differ (Q12).

## Bottom line
1. **Cost is not the obstacle.** AirSeT's raw material costs +€75 more (≈ 0.6% of price), down
   from +€264 in 2022; our forecast keeps it at €58–118 over 9 months. Buyers say they'd pay
   16–20% more for SF6-free (Q1, Q6, Q8).
2. **TCO is the same or a bit lower, never higher**, as long as the premium stays small. Every cost
   that differs favours AirSeT (no gas handling, recovery or servicing-gas risk; ~€430 of carbon
   where it is priced). The amounts per unit are small and no independent study confirms it (Q2).
3. **So switching is a no-regret choice:** a tiny premium buys protection against costs that only
   go one way (regulation, end-of-life recovery, Scope 3 disclosure). The real barriers are habit
   (SF6 is the default spec) and trust in a newer technology (Q9, Q19).
4. **Data centres are the best first target:** +25.7%/yr, 90%+ pre-leased, hyperscalers jointly ask
   suppliers for Scope 3 data and EPDs, and delay costs ~$150–240K per MW-month. Utilities switch
   only when forced; industry and buildings are price-led and slower (Q3, Q15, Q18).
5. **Switchgear is a bottleneck, not the worst one.** Grid connection (4–8+ years) and transformers
   (~128 weeks) are tighter; MV switchgear is now 52–104 weeks vs ~24 before 2020 (Q15).
6. **Sales angles, strongest first:** near-parity cost + Scope 3 fit (today); one SF6-free design
   valid everywhere for 30–40 years (today); faster ordering and commissioning with RM AirSeT 38
   Software Defined (vendor estimate, deliveries from 2028) (Q18).
7. **Where:** the US first (≈ 90% of Americas build-out; SF6 rules in CA, NY, MA), the UK next;
   SE Asia and the Gulf through the same customers' new sites; China later (Q3).
8. **Competition:** Siemens, ABB and Eaton sell the same story; Eaton is cheaper and has the longest
   record. "SF6-free" alone doesn't win; Schneider's edge is range (38 kV), capacity and price
   discipline (Q7).
9. **Risks:** the real AirSeT premium is unknown (one Schneider price in the benchmark); copper and
   nickel come from concentrated, policy-exposed countries, which argues for indexation rather than
   for either product (Q13, Q17).

## Emission scopes (GHG Protocol)
| Scope | Covers | Data-centre example | SF6 / AirSeT |
|---|---|---|---|
| 1 · Direct | What the company burns or leaks | Generators, refrigerants, **SF6 from its own switchgear** | AirSeT removes the SF6 leak |
| 2 · Purchased energy | Electricity, heat, cooling bought | Grid power for servers (largest item) | No effect |
| 3 · Value chain | Suppliers' and end-of-life emissions | Embodied carbon of building, servers, switchgear | Switchgear's manufacturing footprint and end-of-life SF6 |

Scope 1 is usually < 10% of a data centre's emissions, Scope 3 is 38–69% (Q4): AirSeT's stronger
case is in Scope 3.

## Terms
| Term | Meaning |
|---|---|
| MV, kV | Medium voltage (≈ 1–52 kV, the local distribution grid); kV = 1,000 volts |
| RMU / modular switchgear | Compact sealed unit (RM6, RM AirSeT) / cubicles combined per site (SM6, SM AirSeT) |
| GIS, sealed for life | Gas-insulated switchgear; tank filled at the factory, never refilled |
| SF6 / SF6-free | Insulating gas, most potent greenhouse gas the IPCC assesses / air insulation + vacuum switching |
| GWP, CO₂e | Warming vs the same mass of CO₂ over 100 years (SF6 ≈ 23,500–24,300); emission × GWP |
| F-gas Regulation, CARB, Subpart DD | EU SF6 restrictions; California's regulator; US SF6 reporting rule |
| EU ETS, CBAM | EU carbon market (≈ €90/t, Nov 2026); EU carbon charge on imports such as steel (from 2027) |
| ESG, net zero, embodied emissions | Sustainability reporting; target of zero net emissions; emissions from making a product |
| EPD / PEP | Product lifecycle-emissions declaration; Schneider's version |
| TCO | Total cost of ownership: purchase + installation + maintenance + handling + end of life |
| Should-cost, BOM, teardown | Estimated cost to make; list of materials; taking a product apart to estimate both |
| ETO, quote validity, indexation, risk buffer | Engineered to order; how long a price holds; price linked to an index; margin for adverse cost moves |
| Hyperscaler, colocation, pre-leased | Largest cloud operators; data centres renting space to many tenants; rented before built |
| LME, MEPS / CRU | Metals exchange; steel price agencies |
| P10 / P50 / P90, random walk | Forecast range (10% below / middle / 10% above); "price stays as today" baseline |

---

## 1. Is AirSeT more expensive upfront, in cost and in price? Is the gap growing or shrinking?
**Answer:** slightly dearer in raw materials and less so over time; the price premium is unknown
and the benchmark suggests SF6-free prices have converged.

| Raw material (v1 BOM, Sep 2026; team EDA §8, P4) | RM AirSeT | RM6 |
|---|---|---|
| Cost per unit | €975 | €900 |
| Largest lines | Cu 37 %, carbon steel 29 %, stainless 21 % | Cu 54 %, stainless 17 %, carbon steel 13 % |
| Share of unit price (€12,233) | 8.0 % | 7.4 % |

- **Gap +€75 (≈ 0.6% of price), shrinking:** +€122 (Jan 2021) → **+€264 peak (Apr 2022)** → +€62
  (Jan 2026) → +€73 (Aug 2026). RM6 holds more copper (38.8 vs 28.5 kg), so copper's rally narrows
  it; AirSeT is steel-heavy (344 kg carbon, 75 kg stainless).
- **Next 9 months (P4):** gap €58 / €75 / €118 (P10 / P50 / P90); AirSeT stays dearer 9 times in 10.
- **Price:** no public premium. UK government: SF6-free has higher upfront capital cost
  ([DESNZ](https://assets.publishing.service.gov.uk/media/6ad75df7e2ddccf405a7bf3c/pathways-to-sf6-free-networks.pdf)).
  Benchmark (synthetic): **Eaton, the only SF6-free brand, is 5.5% below Schneider**; its premium
  over SF6 brands fell from +46% (2017) to +1% (2026). No separate AirSeT price (Q13).
- **Inference:** the premise is weak on materials; any premium is a manufacturing or pricing choice.

## 2. Is TCO higher or lower than SM6's? Which costs differ, by how much, over what lifetime?
**Answer:** no study proves it, but every differing cost favours SF6-free; the outcome depends on
the price premium (unknown) and whether the customer prices carbon.

- **Lifetime: 30 years base, 40 sensitivity** (assumption). Sources: 30–40+ years
  ([Fraunhofer IEE](https://www.iee.fraunhofer.de/content/dam/iee/energiesystemtechnik/de/Dokumente/Projekte/f-gas-free/SF6_study-public_report-Fraunhofer_IEE-final2.pdf));
  Schneider benchmark: ≈ 30 (Ormazabal), 35 probably 40–50 (Siemens); vendors: up to 40.

| Cost item | SM6 (SF6) | SM AirSeT | Source |
|---|---|---|---|
| Purchase | Lower (assumed) | Unknown premium | Q1 |
| Gas handling, monitoring, trained staff | Needed | None | [UK gov](https://www.gov.uk/how-to-operate-or-service-high-voltage-switchgear-containing-sf6) |
| Leaks in service | < 0.1 %/yr (sealed MV) | None | [UK gov](https://www.gov.uk/how-to-operate-or-service-high-voltage-switchgear-containing-sf6), [EPA](https://www.epa.gov/sites/production/files/2016-02/documents/leakrates_circuitbreakers.pdf) |
| End-of-life recovery | Mandatory (UK, EU); ≈ 10 % of gas lost | None | [Fraunhofer IEE](https://www.iee.fraunhofer.de/content/dam/iee/energiesystemtechnik/de/Dokumente/Projekte/f-gas-free/SF6_study-public_report-Fraunhofer_IEE-final2.pdf) |
| Servicing gas | EU bans virgin SF6 for servicing from 2035; US duties 25–29 % | None | [ABB](https://www.abb.com/global/en/areas/electrification/services/sf6-services-program), [EPA](https://www.epa.gov/system/files/documents/2023-08/3_SF6%20Supply%20Chain.pdf) |
| Carbon cost | Where carbon is priced or reported | None | Below |
| Regulatory risk | Rising (Q5) | None | Q5 |

- **Carbon value of one RM6:** SF6 charge **1.5 kg** (Schneider benchmark teardown; Ormazabal 1.2,
  Siemens 2.5, ABB 3.24). Emitted over 30 years = 1.5 × (0.1%/yr × 30 + 10% at end of life) ≈
  0.2 kg → × GWP 24,300 ≈ **4.7 tCO₂e → ≈ €430 at €90/t, ≈ 3.5% of price**
  ([EU ETS price](https://gmk.center/en/news/european-carbon-prices-exceeded-e90-t-in-november/)).
  End of life is ≈ 75% of it. Outside the EU it counts only with an internal carbon price.
- **Not quantified:** recovery service cost (no reliable figure); gas ≈ $15–20/kg virgin, $8–12
  recycled ([Marketintelo](https://marketintelo.com/report/sf6-recycling-market), unverified);
  vendors claim lower TCO ([Eaton](https://eaton.com/gb/en-gb/markets/utilities/tomorrowsgrid/air-insulated-switchgear-sf6-free-eaton/download-whitepapers-about-sf6-free-solutions/download-total-cost-of-ownership-tco-whitepapers.html)).
- **Inference:** with a small premium, SF6-free TCO is lower; with a large one, it wins only where
  carbon is priced.

## 3. Which markets, segments and customers prioritise ESG most? Measured how?
**Answer:** hyperscale and colocation data centres and corporate buyers with public targets; not
utilities. Measured by public targets, supplier-emissions requests, SF6 regulation and build-out.

| Segment | ESG pull | Evidence |
|---|---|---|
| Data centres (hyperscale, colocation) | Strong | 2030 targets (Microsoft, Amazon, Google, Digital Realty, Equinix: [Uptime](https://journal.uptimeinstitute.com/unravelling-net-zero/)); joint supplier request for EPDs and Scope 3 data ([DCD](https://datacenterdynamics.com/en/news/aws-digital-realty-google-meta-microsoft-and-schneider-electric-call-for-greater-supplier-transparency-on-scope-3-emissions)) |
| Utilities | Weak, with exceptions | Indian private utilities switched voluntarily (Tata Power, BSES Rajdhani; GoalB_India.md); elsewhere 83 % switch only if forced (ABB survey, vendor, [The Conversation](https://theconversation.com/toward-the-end-of-sf-the-most-powerful-greenhouse-gas-147888)) |
| Industry | Weak to medium | Purchase price is the main barrier for MV buyers ([Fraunhofer](https://www.iee.fraunhofer.de/content/dam/iee/energiesystemtechnik/de/Dokumente/Projekte/f-gas-free/sf6_report_gem_final2.pdf)); no industry-specific survey found |
| Commercial buildings | Weak to medium | MV commercial market grows 2–5%/yr ([GMI](https://www.gminsights.com/industry-analysis/commercial-medium-voltage-distribution-panel-market), [Credence](https://www.credenceresearch.com/report/medium-voltage-commercial-switchgear-market)) vs data centres +25.7%/yr |
| Infrastructure | Not researched | Gap |

- Schneider's orders 2025: buildings 29%, data centres 30%, industry 27%, infrastructure 14%
  (slide 7). The brief centres on data centres: $584B market in 2026, +25.7%/yr, **90%+ of new
  capacity pre-leased**, prices locked 3–9 months (slides 13–14).

| Market | Build-out | SF6 rules | ESG pull (inference) |
|---|---|---|---|
| US | ≈ 90 % of Americas capacity ([JLL](https://www.jll.com/en-us/insights/market-outlook/global-data-centers)) | California (< 38 kV from 2025), New York, Massachusetts ([CARB](https://ww2.arb.ca.gov/our-work/programs/elec-tandd/about), [NY DEC](https://dec.ny.gov/sites/default/files/2024-12/part495expresstermspub.pdf)) | High |
| UK | Not researched | Phase-out planned, no binding MV date ([DESNZ](https://assets.publishing.service.gov.uk/media/6ad75df7e2ddccf405a7bf3c/pathways-to-sf6-free-networks.pdf)) | High ("likely next", Q&A) |
| SE Asia | Half of APAC under construction; Malaysia 1,039 MW, Thailand 859 MW ([C&W](https://www.cushmanwakefield.com/en/australia/news/2026/08/asia-pacifics-data-centre-development-pipeline)) | None found | Medium |
| Gulf | Live small (Saudi ≈ 467 MW); announced large (HUMAIN 6.6 GW by 2034, Stargate UAE 5 GW) ([Khaleej Times](https://www.khaleejtimes.com/business/uae-saudi-arabia-to-add-up-to-3gw-of-data-centre-power-by-2030), [Semafor](https://www.semafor.com/article/08/11/2026/saudi-data-center-capacity-projected-to-boom-but-financing-a-challenge)) | None found | Medium |
| China | Not quantified | Grid SF6 unregulated; ≈ 57 % of world SF6 emissions ([MIT](https://eaps.mit.edu/?p=7258)) | Low now |

## 4. What are their goals, and how does AirSeT help?
**Answer:** emissions targets and supplier emissions data; AirSeT helps most through Scope 3 and
future-proofing.

- **Goals:** Equinix −50% Scope 1+2 by 2030, net zero by 2040
  ([Equinix](https://sustainability.equinix.com/environment/greenhouse-gas-emissions/)); Microsoft's
  emissions +25% in FY2025, driven by construction
  ([S&P Global](https://www.spglobal.com/energy/en/news-research/latest-news/electric-power/092326-path-to-net-zero-ai-build-out-tests-tech-sectors-emissions-trajectory));
  hyperscalers want supplier EPDs, and an equipment disclosure taxonomy exists
  ([OCP](https://www.opencompute.org/blog/open-compute-project-foundation-and-imasons-develop-taxonomy-for-carbon-disclosure)).

| Goal | How AirSeT helps | Strength |
|---|---|---|
| Cut Scope 1 | No SF6 to leak | Small: Scope 1 < 10 %, mostly generators ([Gartner](https://www.gartner.com/technology/media-products/newsletters/Vertiv/1-29AUDSFG/gartner.html)) |
| Cut Scope 3 | Lower lifecycle footprint with a PEP (vendor, [Schneider](https://blog.se.com/datacenter/2024/07/19/data-center-product-decarbonization-at-schneider-electric-a-proactive-approach/)) | Strong: what hyperscalers ask for |
| Simpler reporting | No SF6 inventory ([EPA Subpart DD](https://epa.gov/ghgreporting/subpart-dd-use-electric-transmission-and-distribution-equipment)) | Medium |
| Future-proofing | No SF6-ban or retrofit risk | Medium–strong over 30–40 years |
| Build speed | RM AirSeT 38 Software Defined: up to 3× faster to order and build, 2× faster to commission, vs engineered-to-order gear (vendor estimate; orders 2027, deliveries 2028, Equinix pilot; see Q18) | Strong later, unproven now |

- No operator discloses SF6 specifically: the Scope 1 link is logical but unconfirmed.
- The GHG Protocol corporate standard covers seven gases, SF6 included, so companies reporting
  under it must count SF6 leaks in Scope 1 wherever they operate, with or without local rules
  ([GHG Protocol](https://ghgprotocol.org/corporate-standard)).

## 5. What are SM6's SF6 lifecycle risks? How likely, how costly, where?
**Answer:** leaks are minor for sealed MV gear; end of life, spreading regulation and servicing gas
are the real risks over 30–40 years.

| Risk | Likelihood | Impact | Exposed markets |
|---|---|---|---|
| Leaks in service | Low (< 0.1 %/yr) | Small | All |
| End-of-life loss and recovery | Certain; ≈ 10 % lost | Most lifetime emissions; specialist service | All; mandatory in UK / EU |
| Regulation spreading | Already EU, CA, NY, MA; UK planned | New gear banned; retrofit or reporting duties | US states, UK |
| Servicing gas | High in EU after 2035; tight US market | Higher servicing cost | EU, US |
| Reporting, reputation | Certain for large ESG reporters | Admin cost; visible emissions ([ICN](https://insideclimatenews.org/news/24102026/sf6-climate-super-pollutant-surges-in-beijing/)) | Hyperscalers, US, EU |

| Rule | Dates |
|---|---|
| EU F-gas 2024/573 | No new SF6 MV gear ≤ 24 kV from 2026, 24–52 kV from 2030; virgin servicing gas banned 2035 ([Syke](https://www.syke.fi/en/about-us/news/transition-sf6-free-electrical-switchgear-will-begin-2026), [UBA](https://www.umweltbundesamt.de/system/files/document/2026-09_Factsheet_Schaltanlagen.pdf)) |
| California (CARB) | < 38 kV above ground from 2025, 38 kV from 2028 ([§95352](https://regulations.justia.com/states/california/title-17/division-3/chapter-1/subchapter-10/article-4/subarticle-3-1/section-95352)) |
| New York | Part 495 (2024), phase-outs by application |
| UK | Pathway to phase-out, no binding MV date |
| China | None for the grid; only ≈ 30 % of SF6 recovered in 2020 ([ICN](https://insideclimatenews.org/?p=113867)) |

## 6. What is the raw-material outlook, and what does it mean for the gap?
**Answer:** our forecasts: roughly flat to slightly up; external risks: copper up (US tariff) and an
EU steel floor, pulling the gap in opposite directions.

| Cost index (Sep 2026 = 100), P10 / P50 / P90 | +3 | +6 | +9 |
|---|---|---|---|
| RM AirSeT | 95.0 / 100.0 / 109.0 | 93.7 / 101.9 / 118.5 | 91.9 / 100.7 / 126.3 |
| RM6 | 93.5 / 99.7 / 108.0 | 91.3 / 101.0 / 116.5 | 91.7 / 100.3 / 124.5 |

| Material | External outlook | Effect on AirSeT − RM6 gap (inference) |
|---|---|---|
| Copper | 2027 split surplus / deficit; proposed **US tariff 15 % (2027), 30 % (2028)**, to verify ([Argus](https://www.argusmedia.com/news-and-insights/latest-market-news/2771940-viewpoint-us-copper-faces-uncertain-2026-outlook), [Mining.com](https://www.mining.com/copper-price-bmi-hikes-forecasts-structural-deficits-to-bring-17000-next-decade/)) | Narrows (RM6 more copper) |
| EU steel | Price floor from quotas and CBAM; Q1 2027 offers ≈ €790/t ([S&P](https://www.spglobal.com/energy/en/news-research/latest-news/metals/010726-europes-steel-industry-faces-its-2026-reckoning-with-cbam)) | Widens (AirSeT steel-heavy, made in Hungary) |
| Nickel | 2027 surplus; Indonesian quotas an upside risk ([INSG](https://www.kitco.com/news/off-the-wire/2026-10-13/global-nickel-market-set-surplus-year-and-next-insg-says)) | Slightly narrows |

## 7. Who competes in SF6-free, at what price? Where does Schneider win or lose?
**Answer:** Siemens, ABB and Eaton sell equivalent air + vacuum units with the same footprint; no
public prices; Eaton is cheaper in the benchmark and cheapest to build in the teardown.

| Competitor | SF6-free product (vendor claims) | Track record |
|---|---|---|
| Siemens | 8DJH 12/24 blue GIS: clean air + vacuum, same dimensions, 40-year life ([Siemens](https://www.siemens.com/en-us/content/medium-voltage-blue-gis/)) | Since 2019–20 |
| ABB | SafeRing / SafePlus Air: dry air + vacuum, same footprint ([ABB](https://www.abb.com/global/en/areas/electrification/medium-voltage/switchgear/gas-insulated/safering-safeplus)) | 24 kV still phasing in |
| Eaton | Xiria: air + vacuum to 24 kV ([Eaton](https://www.eaton.com/sg/en-us/catalog/medium-voltage-power-distribution-control-systems/eaton-xiria.html)) | Since 2001, > 2,500 units |
| Schneider | SM / RM AirSeT: pure air + shunt vacuum ([se.com](https://www.se.com/ww/en/work/products/product-launch/sf6free-mv-technology)); 38 kV version orders 2027 | — |

| Schneider teardown (specs only; should-costs not used: file provisional, not reconciled) | Insulation | Made in | SF6 (kg) | Price found |
|---|---|---|---|---|
| Schneider RM6 | SF6 | France | 1.5 | — |
| Ormazabal CGMCOSMOS | SF6 | Spain | 1.2 | — |
| ABB SafePlus | SF6 | — | 3.24 | — |
| Siemens 8DJH | SF6 | Germany | 2.5 | **€15,530** (only real price) |
| **Eaton Xiria** | **Air + vacuum** | Netherlands | **0** | None |

- **Wins:** broad range incl. 38 kV for data centres; most consistent pricing (narrowest band).
- **Loses:** not unique; Eaton cheaper and longest in market; rivals already sell the emissions
  story (ABB claims −99.5%, [ABB](https://electrification.us.abb.com/sites/default/files/2024-10/ABB-Sustainability-Article_FINAL.pdf)).
- Slides call RM AirSeT "solid insulation"; Schneider's site says pure air: clarify before quoting.

## 8. How to price and package AirSeT, profitably? How do P4's outputs help?
**Answer:** the cost case allows near parity, buyers signal +16–20% tolerance, and P4's validity and
indexation can be sold as risk protection.

- **Inputs:** cost gap ≈ 0.6% of price; stated willingness to pay **+16% (no leaks), +20% (low
  warming)** ([Fraunhofer](https://www.iee.fraunhofer.de/content/dam/iee/energiesystemtechnik/de/Dokumente/Projekte/f-gas-free/F-gas-free-study-summary-final.pdf));
  Eaton 5.5% below Schneider; margin at risk +9 P90 ≈ 9–10% of margin; validity AirSeT 6, RM6 9
  months; 2021 replay: buffers fail in shocks, indexation works (P4).

| Pricing option | Supported by | Depends on |
|---|---|---|
| Parity or small premium | Tiny cost gap; cheaper rival | Real manufacturing cost and margin |
| TCO-based premium | +16–20 % tolerance; avoided recovery and carbon | Customer values carbon or handling |
| Raise SF6 prices over time | Spreading regulation; EU servicing-gas ban 2035 | Competitor reaction |

- **Packaging:** index clauses on the indices Schneider buys on (back-to-back, P4); validity as a
  selling point; bundles (monitoring, service, take-back of old SF6 units); procurement levers from
  supplier strength (2 strong, 4 watch, 3 fragile; P4).

## 9. What stops each customer type from switching?
| Customer | Main barrier | Source |
|---|---|---|
| Utilities | No mandate (83 % switch only if forced) | ABB survey (vendor) |
| MV buyers (Europe) | Purchase price | [Fraunhofer](https://www.iee.fraunhofer.de/content/dam/iee/energiesystemtechnik/de/Dokumente/Projekte/f-gas-free/F-gas-free-study-summary-final.pdf) |
| HV grid operators | Cost, availability, complexity, training | [CIGRE](https://cse.cigre.org/cse-n040/the-impacts-of-the-f-gas-regulation-eu-2024/573-on-high-voltage-gas-insulated-switchgear-operators-within-the-power-transmission-industry) |
| Data centres (inference) | Speed to power: grid waits already 4+ years ([JLL](https://www.jll.com/en-us/insights/market-outlook/global-data-centers)) | Inference |
| Industry, buildings | Purchase price; slower growth (MV commercial 2–5%/yr) | Fraunhofer; Q18 (no segment survey found) |

Footprint is not a barrier up to 24 kV ([EC](https://climate.ec.europa.eu/system/files/2020-04/2020_03_25_sf6_and_alternatives_en.pdf)).

## 10. Which levers remove those barriers cheaply? Which can Goal A power?
| Barrier | Lever | Cost | Goal A? |
|---|---|---|---|
| Price | TCO-based quote (avoided recovery, carbon) | Low | Partly |
| Price | Parity where the gap is small | Medium | **Yes** (gap band) |
| Price risk to delivery | Index-linked pricing so AirSeT can match SM6's validity (P4 gives AirSeT 6 months, RM6 9) | Low | **Yes** (P4 rules) |
| No mandate | Target ESG buyers; follow state rules | Low | No |
| Reporting effort | PEP / EPD with avoided SF6 | Low | No |
| Speed to power | Lead-time commitments | Medium | No |
| New-tech risk | Pilots, references, warranty | Medium | No |
| Old SF6 fleet | Take-back with new orders | Medium | No |

Subsidies and bans were rated the most useful policies (Fraunhofer): outside Schneider's control.

## 11. Rollout order, KPIs and failure conditions?
**Answer:** start where ESG pull or rules already exist, build references, then scale.

| Phase | Where the evidence points | Example KPIs |
|---|---|---|
| Pilot | ESG-committed buyers in CA, NY or the UK | Pilot accounts, SF6-free share of their orders, win rate |
| References | Same buyers' new sites (SE Asia, Gulf) | Reference sites, repeat orders, CO₂e avoided |
| Scale | Industry, buildings; utilities as rules arrive | SF6-free share by region, margin vs SM6, lead time |

**Fails if:** premium far above 16–20%; rivals undercut (Eaton already cheaper); regulation stalls
outside the EU; data-centre pipelines aren't built (82% of APAC still planned); AirSeT lead times
exceed SF6 gear; copper falls sharply (gap widens).

## 12–14. For Schneider (Q&A 23/11)
| # | Question | Why |
|---|---|---|
| 12 | SM, RM or both? Can the SM cost gap be shared? | Our data is RM; slides mix both (slide 13 RM, 14–15 SM) |
| 13 | AirSeT list price or premium over SM6 / RM6? | Q1, Q2, Q8 |
| 14 | Margin and share of price exposed to raw materials? | P4's quote rules |
| + | Confirm RM6 / SM6 SF6 charge (benchmark estimate 1.5 kg) | Q2 |

---

## 15. Is switchgear really the data-centre bottleneck? Would they pay for speed?
**Answer:** partly. Grid connection and large transformers are the tightest constraints;
medium-voltage (MV) switchgear is the next tier. Any late item stops energisation, and a month of
delay costs ~$200K per MW, so paying a premium for guaranteed delivery is plausible but unproven.

| Constraint | Lead time / wait | Source |
|---|---|---|
| Grid interconnection (US) | 4 years average (JLL); 8+ years in some PJM cases | [Quartz](https://qz.com/us-power-grid-ai-data-center-demand-constraints-051326), [Data Center Frontier](https://www.datacenterfrontier.com/energy/article/55365067/project-stalled-grid-bottlenecks-threaten-the-fifth-industrial-revolution) |
| Large power transformers | ~128 weeks; generator step-up 144 weeks | [Quartz](https://qz.com/us-power-grid-ai-data-center-demand-constraints-051326) |
| High-voltage breakers | ~125 weeks | [Quartz](https://qz.com/us-power-grid-ai-data-center-demand-constraints-051326) |
| MV switchgear 15 kV / 38 kV | 52–80 / 78–104 weeks (≈24 before 2020); survey average 44 weeks | [Industrial Sage](https://www.industrialsage.com/switchgear-lead-times-2026/), [T&D World](https://tdworld.com/distributed-energy-resources/article/55091365/medium-voltage-switchgear-supply-and-demand) |
| MV transformers | ~82 weeks | [Giga Energy](https://www.gigaenergy.com/blog/lead-time-delays-for-data-centers) |

- Switchgear is "spoken for through 2028" at some suppliers; utilities now order grid equipment
  up to five years ahead ([The Next Web](https://thenextweb.com/news/us-power-companies-scramble-data-centre-equipment), [Cybernews](https://cybernews.com/tech/data-center-power-utilities-grid-equipment/)).
- Up to half of planned US builds have slipped or been cancelled, mostly on power and equipment
  ([Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/half-of-planned-us-data-center-builds-have-been-delayed-or-canceled-growth-limited-by-shortages-of-power-infrastructure-and-parts-from-china-the-ai-build-out-flips-the-breakers), secondary reporting; [Utility Dive](https://www.utilitydive.com/news/the-data-center-boom-continues-apace-but-projects-face-mounting-obstacles/830496/)).

| Cost of one month's delay | Per MW-month | Source |
|---|---|---|
| $14.2M for a 60 MW site (lost revenue, overruns, penalties) | ≈ $237K | [STL Partners](https://stlpartners.com/press/delays-in-data-centre-construction/) |
| $235M a year for 100 MW of colocation leases | ≈ $196K | [Accenture](https://www.accenture.com/content/dam/accenture/final/accenture-com/document-fy26/q4/Accenture-Data-Centre-PoV-2026-v5.pdf) |
| $150M per GW-month of contracted revenue | ≈ $150K | [Occam Edge](https://occamedge.substack.com/p/confronting-the-datacenter-delay) |
| "$3M per MW-month" | not verified, 10× the others | [Latitude Media](https://www.latitudemedia.com/news/the-data-center-flexibility-debate/) |

- **No public data on premiums actually paid for faster switchgear.** The figures above are
  consultant or vendor estimates.
- Inference: a ring main unit (RMU) at ~€12K is tiny next to $150–240K per MW per month of delay, so
  a delivery guarantee is worth more to the buyer than a few % on price.
- Caveat: lead time is a Schneider-vs-rivals argument, not an AirSeT-vs-RM6 one, unless AirSeT
  ships faster. The only claim found is for the 38 kV software-defined version, not yet on sale
  (Q18). Lead times for the current RM range are not public: ask Schneider.

## 16. Do global standard designs favour AirSeT?
**Answer:** likely (inference). Most hyperscalers reuse one standard, prefabricated design and adapt
it locally ([Vertiv](https://www.vertiv.com/498240/globalassets/documents/white-papers/vertiv-colocationmarket2023-br-en-us_380504_0.pdf), [DCD](https://www.datacenterdynamics.com/en/opinions/in-the-era-of-ai-data-center-standardization-is-the-name-of-the-game-heres-why/)).
EU sites must be SF6-free under F-gas 2024/573, so a single global spec is simplest if it is
SF6-free everywhere. Schneider says SF6 removal is becoming a standard supply-chain ESG requirement
([Schneider blog](https://blog.se.com/datacenter/2026/05/29/how-to-build-a-data-centre-that-uses-40-less-energy/), vendor). No source names a hyperscaler that has done this: gap.

## 17. Where do the key metals come from, and how risky is that?
**Answer:** copper and nickel are concentrated in a few countries with policy or political risk,
and refining is concentrated in China and Indonesia. RM6 is more exposed through copper, AirSeT
through nickel (stainless) and EU steel policy.

| Material | Mining | Refining / processing | Main risks | Source |
|---|---|---|---|---|
| Copper | Chile 23–25%, DRC ~14%, Peru ~12% | China ~48% | Chilean royalties and water, DRC instability, Peru protests, proposed US tariff | [USGS MCS 2026](https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-copper.pdf), [NAI 500](https://nai500.com/blog/2026/03/top-5-copper-producers-of-2025-the-race-for-critical-mineral-dominance/) |
| Nickel | Indonesia ~67%, Philippines 10%, Russia 5% | Indonesia 43%, China 31% | Indonesian export bans and quotas, Russia sanctions | [OECD](https://www.oecd.org/en/publications/enhancing-resilience-through-traceability_a898687d-en/full-report/nickel_a87df29d.html) |
| Aluminium | — | China largest smelter; Indonesia growing | Chinese capacity cap, export policy | [S&P Global](https://www.spglobal.com/energy/en/news-research/latest-news/metals/082526-infographic-indonesia-expands-influence-in-global-aluminum-market) |

- Our P10 / P90 bands already price in past volatility, but they were too narrow in 2020–22
  shocks (40–70% coverage), so country shocks are tail risks beyond them.
- Inference: this argues for indexation and back-to-back supply contracts more than for AirSeT
  itself, since both products carry concentrated-sourcing risk.

## 18. Chosen focus: data centres first. Why, and why not the others?
**Answer:** data centres combine the fastest growth, the strongest voluntary ESG pull and the
highest cost of delay. The other segments are sequenced later, not dropped.

| Segment (share of Schneider orders 2025, slide 7) | Why it comes later | Evidence |
|---|---|---|
| Data centres (30%) | **Chosen.** +25.7%/yr, 90%+ pre-leased, joint supplier request for Scope 3 data and EPDs, ~$200K per MW-month of delay | Slides 13–14; Q3, Q15 |
| Utilities | Switch only when mandated (83%); order up to 5 years ahead, so a voluntary offer changes little today | Q3, Q9; [Cybernews](https://cybernews.com/tech/data-center-power-utilities-grid-equipment/) |
| Industry (27%) | Price is the main barrier for MV buyers; no public ESG commitment on switchgear found | [Fraunhofer](https://www.iee.fraunhofer.de/content/dam/iee/energiesystemtechnik/de/Dokumente/Projekte/f-gas-free/sf6_report_gem_final2.pdf) |
| Buildings (29%) | Slower market (MV commercial 2–5%/yr); many small, price-led buyers | [GMI](https://www.gminsights.com/industry-analysis/commercial-medium-voltage-distribution-panel-market), [Credence](https://www.credenceresearch.com/report/medium-voltage-commercial-switchgear-market) |
| Infrastructure (14%) | Smallest share; mostly public tenders | Slide 7; not researched further |

- Defence in one line: a voluntary switch needs a buyer who wants it without a law. Data centres
  are the only segment with published supplier demands, the money to pay, and a reason (delay) to
  value something other than price.
- Weak spots to expect from the jury: industry and buildings were not surveyed directly (no
  segment-level data found); data-centre pipelines can stall (Q11: 82% of APAC still planned);
  growth figures come from paid market reports that disagree.
- Sequencing (links to Q11): data centres build references, then industrial campuses and large
  buildings follow once the price gap closes; utilities as rules arrive.

**Three angles to sell AirSeT to data centres**

| Angle | Evidence | Strength | Caveat |
|---|---|---|---|
| **One standard design worldwide, at scale** | Hyperscalers reuse one prefab design and adapt locally ([Vertiv](https://www.vertiv.com/498240/globalassets/documents/white-papers/vertiv-colocationmarket2023-br-en-us_380504_0.pdf), [DCD](https://www.datacenterdynamics.com/en/opinions/in-the-era-of-ai-data-center-standardization-is-the-name-of-the-game-heres-why/)); EU sites must be SF6-free since Jan 2026 ([ABB](https://new.abb.com/news/detail/131007/preparing-for-the-2026-sf6-transition-building-resilient-grids)), so AirSeT is already the EU volume line (inference); Schneider is adding capacity in Hungary, the US ($700M) and Saudi Arabia ([Business Wire](https://www.businesswire.com/news/home/20250311546988/en), [MMH](https://www.mmh.com/article/schneider-electric-commits-700-million-boost-domestic-manufacturing/Automation), [Zawya](https://www.zawya.com/en/press-release/companies-news/schneider-electric-commits-to-nearly-tripling-saudi-manufacturing-capacity-as-kingdom-marks-ten-years-of-vision-2030-gdlqgel4)) | Strong | No source names a hyperscaler with an SF6-free global spec; scale lowering AirSeT's cost is inference |
| **Ships faster** | RM AirSeT 38 Software Defined: up to 3× faster to order and build, 2× faster to commission, vs engineered-to-order gear ([TechTarget](https://www.techtarget.com/it-infrastructure/news/366651545/Schneider-software-defined-switchgear-targets-AI-data-center-delays), [StorageReview](https://www.storagereview.com/news/schneider-electric-software-defined-medium-voltage-switchgear-yotta-2026-equinix-pilot)); Uptime analyst: faster validation can speed commissioning | Medium now, strong from 2028 | Vendor estimate from its own white paper; orders 2027, deliveries 2028, pilot with Equinix; speed comes from the software-defined, standard design, not from being SF6-free; no lead-time data for today's RM AirSeT |
| **Future-proofing** | 30–40-year life vs spreading rules (EU 2026, CA, NY, MA, UK planned; EU servicing-gas ban 2035); no SF6 inventory or end-of-life recovery | Strong | Outside regulated places, the risk is a probability, not a certainty |

- How they fit together (inference): standard design gives scale, scale and a configurable design
  give speed, and SF6-free keeps the same design valid everywhere for its whole life.
- Ask Schneider: current RM AirSeT vs RM6 lead times; whether 24 kV RM AirSeT gets the same
  software-defined speed-up before 2028.

## 19. If TCO is near parity, why aren't data centres switching already?
**Answer:** the cost case is settled enough; what's left is habit and trust (inference from Q2,
Q9, Q10).

| Choice over 30–40 years | AirSeT | SM6 / RM6 |
|---|---|---|
| Upfront | +€75 raw material (~0.6%), shrinking | — |
| Scope 3 / EPD requests | Meets them | Disclosure gap hyperscalers already ask about |
| Regulation | Already compliant | Ban, retrofit or 2035 EU servicing-gas risk |
| End of life | Nothing to recover | Mandatory SF6 recovery; ~€430 of carbon if priced |
| Global design | One spec everywhere, EU included | Two specs (SF6-free in the EU only) |
| From 2028 | Faster to order and commission (38 kV, vendor) | — |

- **Why the switch doesn't happen on its own:**
  - Outside the EU nothing requires it, so the SF6 spec stays the default in designs and tenders.
  - Quotes compare unit prices, so lifetime costs stay invisible; price is the main stated
    barrier ([Fraunhofer](https://www.iee.fraunhofer.de/content/dam/iee/energiesystemtechnik/de/Dokumente/Projekte/f-gas-free/sf6_report_gem_final2.pdf)).
  - New-technology risk: SF6 gear has decades of field record, AirSeT a few years; an outage costs
    a data centre far more than the switchgear.
  - "SF6-free" doesn't stand out: rivals make the same claim (Q7).
- **Implication:** the strategy is about making AirSeT the easy default and lowering the trust
  barrier (Q10 levers), not about proving it is better.

---

## Outside the questions
1. Speed to power may outweigh price for data centres (4+ year grid waits; Q15, Q18).
2. Utilities won't switch voluntarily; private ESG buyers might (inference).
3. US states (CA, NY, MA) are a possible beachhead without a federal ban.
4. "SF6-free" alone isn't a differentiator: rivals sell the same story.
5. Announced ≠ built: 82% of APAC's pipeline is planned; Gulf gigawatts are targets.
6. Where it's made matters: US copper tariffs hit RM6 / SM6; EU steel policy hits AirSeT (Hungary).
7. China: largest SF6 emitter, unregulated: long-term potential, no near-term pull.
8. Schneider's teardown should-costs are provisional and not reconciled: use its specs, not its costs.

## Checked against Schneider's files
All claims from the slides (end markets, data-centre framing, price locks, unregulated markets),
the RMU benchmark (prices, changes, premiums, bands), the v1 BOM (masses), the competitor benchmark
(Eaton only SF6-free, Siemens €15,530, material ≈ 80%), the data README (plants) and the Q&A notes
were rechecked ✅. Added from the benchmark: SF6 charges, service lives, Eaton's should-cost,
made-in countries. Flagged: "solid insulation" (slides) vs "pure air" (website); slides mix RM and
SM; benchmark uses GWP 22,800 (older IPCC value).

## Assumptions to check
| Assumption | Check with |
|---|---|
| RM6 holds 1.5 kg SF6 (teardown estimate) | Schneider datasheet |
| 30-year life (40 sensitivity) | Schneider datasheet |
| GWP 24,300 | Official IPCC AR6 table |
| €90/t carbon price | Applies only where carbon is priced |
| RM findings transfer to SM | Schneider (Q12) |
| US state dates, US copper tariff | Legal texts, official announcement |
| One Schneider price (€12,233) for both products | Schneider (Q13) |

## Gaps
SF6-free list prices and premiums · recovery service cost per unit · operators' SF6 disclosures ·
industry and building buyers · competitors beyond Siemens, ABB, Eaton · China and Gulf rules ·
RM6 vs AirSeT lead times · premiums paid for faster delivery · hyperscalers with an SF6-free global spec.
