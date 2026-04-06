# Daily Global Economic Newspaper Briefing — Project Instructions

## 1. Project Objective

Produce a daily global economic and geopolitical briefing in the style of a leading international financial newspaper (FT, Bloomberg, WSJ, Handelsblatt, The Economist, Reuters).

The briefing must answer four questions:
- What happened globally today?
- Why does it matter economically?
- Which markets and industries are affected?
- What should be monitored next?

---

## 2. Editorial Standards

**Style:** Continuous journalistic prose. Analytical, precise, neutral, high information density. Minimize bullet points — use them only for data tables or short enumerations.

**Depth:** Every story must follow: `Thesis → Economic reasoning → Market/strategic implication`

**Mechanisms:** Always make the economic chain explicit (e.g. rate hike → real yields rise → gold pressure → USD strengthening → EUR/USD decline → European export margin compression).

**Conflicting views:** If reputable sources disagree, present both interpretations and explain the underlying reasoning. Do not force a conclusion.

**Tone:** No simplifications, no filler. Write for an informed reader — an investor, analyst, or senior executive.

---

## 3. Mandatory Sections

Generate every briefing with the following seven sections, in order:

1. **Major Global Story** — Lead with the single most consequential development. Explain what happened, why it matters, and expected economic consequences. Priority topics: central bank decisions, geopolitical shocks, macro data surprises, financial market disruptions.

2. **Global Markets and Macroeconomy** — Structured macro overview focused on Germany, US, and Brazil. Cover: GDP trends, inflation dynamics, labor markets, central bank signals, forward expectations. Connect macro to capital markets and investment sentiment.

3. **Commodities and Raw Materials** — Always cover: Gold, Silver, Brent Oil, Natural Gas, Copper. Optional if relevant: Iron Ore, Lithium, Wheat, Soybeans. Explain price movements through monetary policy, real rates, geopolitical risk, industrial demand, supply constraints. Flag divergences.

4. **Currency Markets** — EUR/USD is mandatory. Explain drivers: rate differentials, capital flows, inflation expectations, risk sentiment. Connect FX moves to trade competitiveness, corporate earnings, and capital allocation.

5. **Industry and Corporate Developments** — Cover Technology, Energy, Finance, Industrials. For every company mentioned: state industry, market segment, and economic relevance. Focus on M&A, VC trends, regulation, technology shifts, supply chain restructuring. Include strategic and valuation implications.

6. **Geopolitics and Global Trade** — Analyze sanctions, trade negotiations, conflicts, energy security, supply chain realignment. Focus on implications for Europe, US, China, Russia, and global trade systems.

7. **Additional Developments** — Concise list of relevant stories not covered in depth (central bank shifts, tech trends, banking sector, regional risks).

---

## 4. Geographic Priorities

**Primary (always covered):** Germany · United States · Brazil

**Secondary (when relevant):** European Union · China · Russia · Latin America · Emerging markets

Always explain cross-regional linkages. Key chains to model:
- US monetary policy → EUR/USD → European export competitiveness
- China demand → commodity prices → Brazil fiscal/trade balance
- Energy markets → German industrial output and competitiveness

---

## 5. Data and Source Priorities

**Tier 1 (prioritize):** Financial Times, Bloomberg, Reuters, Wall Street Journal, Handelsblatt, The Economist, New York Times (Business)

**Required regional sources:**
- Brazil: https://www.infomoney.com.br/, https://www.folha.uol.com.br/
- Latin America/Spain: https://elpais.com/
- Europe: https://www.theguardian.com/europe
- Reference/explainer: https://www.investopedia.com/

**Gold and Silver pricing — mandatory format (all three units):**

```
Gold:   3,340 USD/oz  |  107.00 USD/g  |  107,000 USD/kg
Silver:    36 USD/oz  |    1.16 USD/g  |    1,160 USD/kg
```

All other commodities: report in market-standard units with daily change (% and absolute).

---

## 6. Output Requirements

- **Target reading time:** 5–10 minutes
- **Format:** Markdown with clear `##` section headers
- **Prose:** Narrative newspaper feel — not a bullet dump
- **Length:** Dense but not padded. Cut anything that doesn't add analytical value
- **No:** vague hedges, redundant transitions, surface-level summaries

---

## 7. Engineering Principles

- Fetch live data for commodities and FX before generating the briefing
- Scrape or summarize from Tier 1 sources; fall back to secondary sources if Tier 1 is unavailable
- Gold/Silver unit conversion must be computed programmatically — never approximated
- If a data source is unavailable, note it explicitly in the relevant section rather than omitting it silently
- Separate data ingestion logic from content generation logic
- All output must be deterministic given the same input date and data snapshot

---

## 8. Delivery Roadmap

| Phase | Scope |
|-------|-------|
| 1 | Manual generation: prompt-driven, no automation |
| 2 | Semi-automated: data fetching scripts + templated generation |
| 3 | Fully automated: scheduled daily run, structured data pipeline, output to file/email/API |

Track current phase in `config/phase.txt`.

---

## 9. File Structure Expectations

```
automation/
├── CLAUDE.md                  # This file — project instructions
├── config/
│   ├── phase.txt              # Current delivery phase
│   └── sources.yaml           # Source URLs and priorities
├── data/
│   └── YYYY-MM-DD/            # Raw fetched data per run date
├── output/
│   └── YYYY-MM-DD-briefing.md # Generated briefings
├── scripts/
│   ├── fetch_data.py          # Data ingestion
│   ├── generate_briefing.py   # Content generation
│   └── utils.py               # Shared helpers
└── tests/
    └── test_prices.py         # Unit tests for price conversion, formatting
```

---

## 10. Rules for Future Updates

1. **Do not change the seven mandatory sections** without explicit user instruction.
2. **Do not remove geographic priorities** — Germany, US, Brazil are always primary.
3. **Always preserve the Gold/Silver tri-unit format** — it is a hard requirement.
4. **Prose style is non-negotiable** — reject any refactor that converts sections to bullet lists.
5. **Source list is additive** — add sources freely, but never remove Tier 1 sources.
6. **Cross-regional linkages must always be explained** — never report a US rate decision without noting EUR/USD and European implications.
7. **When in doubt, go deeper** — this project trades length for analytical depth, not brevity.
8. **Update `config/phase.txt`** when advancing the delivery roadmap phase.
