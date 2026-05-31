# Automation Project — Master Constitution

This repository has three systems that share the same codebase:

1. **Daily Global Economic Newspaper Briefing** — the core product
2. **Market Tools** — FastAPI backend + React/Vite frontend on Render
3. **Personal Intelligence OS** — Telegram bot + NLP classifier + Obsidian routing

---

## System 1: Daily Global Economic Newspaper Briefing

### Objective
Produce a daily global economic and geopolitical briefing in the style of a leading
international financial newspaper (FT, Bloomberg, WSJ, Handelsblatt, The Economist, Reuters).

Every briefing answers four questions:
- What happened globally today?
- Why does it matter economically?
- Which markets and industries are affected?
- What should be monitored next?

### Editorial Standards
**Style:** Continuous journalistic prose. Analytical, precise, neutral, high information
density. Minimize bullet points — use them only for data tables or short enumerations.

**Depth:** Every story must follow: `Thesis → Economic reasoning → Market/strategic implication`

**Mechanisms:** Always make the economic chain explicit (e.g. rate hike → real yields rise →
gold pressure → USD strengthening → EUR/USD decline → European export margin compression).

**Conflicting views:** If reputable sources disagree, present both interpretations and explain
the underlying reasoning. Do not force a conclusion.

**Tone:** No simplifications, no filler. Write for an informed reader — an investor, analyst,
or senior executive.

### Seven Mandatory Sections (always in this order)
1. **Major Global Story** — Lead with the single most consequential development. Explain what
   happened, why it matters, and expected economic consequences. Priority topics: central bank
   decisions, geopolitical shocks, macro data surprises, financial market disruptions.

2. **Global Markets and Macroeconomy** — Structured macro overview focused on Germany, US,
   and Brazil. Cover: GDP trends, inflation dynamics, labor markets, central bank signals,
   forward expectations. Connect macro to capital markets and investment sentiment.

3. **Commodities and Raw Materials** — Always cover: Gold, Silver, Brent Oil, Natural Gas,
   Copper. Optional if relevant: Iron Ore, Lithium, Wheat, Soybeans. Explain price movements
   through monetary policy, real rates, geopolitical risk, industrial demand, supply
   constraints. Flag divergences.

4. **Currency Markets** — EUR/USD is mandatory. Explain drivers: rate differentials, capital
   flows, inflation expectations, risk sentiment. Connect FX moves to trade competitiveness,
   corporate earnings, and capital allocation.

5. **Industry and Corporate Developments** — Cover Technology, Energy, Finance, Industrials.
   For every company mentioned: state industry, market segment, and economic relevance. Focus
   on M&A, VC trends, regulation, technology shifts, supply chain restructuring.

6. **Geopolitics and Global Trade** — Analyze sanctions, trade negotiations, conflicts,
   energy security, supply chain realignment. Focus on implications for Europe, US, China,
   Russia, and global trade systems.

7. **Additional Developments** — Concise list of relevant stories not covered in depth.

### Geographic Priorities
**Primary (always covered):** Germany · United States · Brazil

**Secondary (when relevant):** European Union · China · Russia · Latin America · Emerging markets

Always explain cross-regional linkages:
- US monetary policy → EUR/USD → European export competitiveness
- China demand → commodity prices → Brazil fiscal/trade balance
- Energy markets → German industrial output and competitiveness

### Data and Source Priorities
**Tier 1 (prioritize):** Financial Times · Bloomberg · Reuters · Wall Street Journal ·
Handelsblatt · The Economist · New York Times (Business)

**Required regional sources:**
- Brazil: https://www.infomoney.com.br/ · https://www.folha.uol.com.br/
- Latin America/Spain: https://elpais.com/
- Europe: https://www.theguardian.com/europe
- Reference/explainer: https://www.investopedia.com/

**Gold and Silver — mandatory tri-unit format:**
```
Gold:   3,340 USD/oz  |  107.38 USD/g  |  107,380 USD/kg
Silver:    36 USD/oz  |    1.16 USD/g  |    1,160 USD/kg
```
Unit conversion is computed programmatically in `scripts/utils.py` (`oz_to_gram`,
`oz_to_kg`). Never approximate or hand-calculate.

### Briefing Pipeline
```
fetch_data.py         — Twelve Data (XAU, XAG, EUR/USD) + yfinance (Brent, NG, Copper) + NewsAPI
generate_briefing.py  — builds prompt → calls Anthropic (claude-sonnet-4-6) or OpenAI
run_daily.py          — full pipeline, designed for Render Cron Job
sync_to_brain.py      — PUT to GitHub API → 10_Daily/YYYY-MM-DD.md in julio-brain vault
```

### Delivery Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Manual generation: prompt-driven, no automation | ✅ Done |
| 2 | Semi-automated: data fetching scripts + templated generation via Render Cron | ✅ Current |
| 3 | Fully automated: scheduled daily run, structured data pipeline, output to file/email/API | 🔜 Next |

**Current phase:** 2 (tracked in `config/phase.txt`)

### Output Format
- Target reading time: 5–10 minutes
- Markdown with `##` section headers
- Continuous narrative prose — no bullet dumps
- Dense but not padded — cut anything without analytical value
- Outputs saved to: `outputs/latest-briefing.md` + `outputs/YYYY-MM-DD-briefing.md`

### Briefing Rules (non-negotiable)
1. Do not change the seven mandatory sections without explicit instruction
2. Do not remove Germany, US, Brazil as primary geographies
3. Always preserve the Gold/Silver tri-unit format — computed, never approximated
4. Prose style is mandatory — reject any refactor that converts to bullet lists
5. Source list is additive — never remove Tier 1 sources
6. Always explain cross-regional linkages — never report a US rate decision without EUR/USD
7. When in doubt, go deeper — analytical depth over brevity
8. Update `config/phase.txt` when advancing the delivery roadmap phase

---

## System 2: Market Tools (FastAPI + React/Vite on Render)

### Identity
- **Live URL:** https://market-tools-frontend.onrender.com
- **Backend:** https://market-tools-backend-my0v.onrender.com
- **Stack:** Python/FastAPI (backend) + React/Vite/Tailwind (frontend)
- **Deploy:** Push to `main` → Render auto-deploys both services in ~3 minutes

### Deploy Pipeline
```bash
git add <specific files>
git commit -m "feat/fix/chore(market-tools): <description>"
git push origin main
# Wait ~3min, verify: curl https://market-tools-frontend.onrender.com
```

**VITE_API_URL is build-time only** — most common failure point.
- Set in Render Dashboard → frontend service → Environment Variables
- Must match backend URL exactly (no trailing slash)
- A code change cannot fix a misconfigured env var — check Render Dashboard first

### After Every Change
```bash
cd frontend && npx tsc --noEmit    # zero TypeScript errors required
cd backend  && pytest              # Python tests must pass
git add <specific files> && git commit -m "..." && git push origin main
```

### Key Files
| Path | Purpose |
|------|---------|
| `frontend/src/` | React components and pages |
| `frontend/src/index.css` | CSS variables, Tailwind base, responsive layout |
| `scripts/api.py` | FastAPI app — market data, stock watchlist, briefing preview |
| `scripts/scoring.py` | Bull score (momentum + sentiment + valuation + analyst) |
| `config/watchlist.yaml` | 7-category curated watchlist (26 tickers) |
| `config/models.yaml` | LLM model config and cost tracking |
| `render.yaml` | Render service config (web: backend + static: frontend) |
| `data/stock_watchlist.json` | Personal stock picks from Telegram bot |

### Mobile Layout Rules
- `overflow-x: hidden` on html/body — never remove
- Responsive grids via CSS classes (`.grid-main-sidebar`, `.grid-2`, etc.) — never inline `gridTemplateColumns` with fixed px values on a parent element
- Tables that may overflow: wrap in `.table-scroll` (overflow-x: auto)
- Hamburger nav on mobile at `top: calc(34px + .4rem)` to clear the TickerBanner

### Stop Conditions — Give Julio Instructions Instead
Never autonomously: force-push · secret/token rotation · Render Dashboard changes ·
production rollback. Explain exactly what Julio needs to do, then stop.

---

## System 3: Personal Intelligence OS (Telegram Bot)

### What It Does
Every unstructured input (text, voice, photo) is:
1. Classified by Claude Haiku into a typed item (`classifier.py`)
2. Shown to Julio via Telegram inline buttons (✅ Save / ✏️ Retype / ❌ Discard)
3. Routed on confirmation to the correct integration (`capture_router.py`)

### Item Types and Routing
| Type | Routing Target |
|------|---------------|
| `wishlist` | `10_Daily/` → `## Shopping List` + MyWardrobe API |
| `stock_pick` | `10_Daily/` → `## Notes` + Market Tools `/stock-watchlist` |
| `gift_idea` | `50_People/{person}.md` → `## Geschenkideen` |
| `reminder` | `10_Daily/` → `## Follow-ups` |
| `task` | `10_Daily/` → `## Tasks` |
| `question` | `40_Knowledge/open-questions.md` |
| `idea` | `10_Daily/` → `## Notes` with 💡 prefix |
| `note` | `10_Daily/` → `## Notes` |

### Obsidian Vault
- **Location:** `~/projects/julio-brain` (symlink → iCloud)
- **Write method:** GitHub Contents API via `sync_to_brain.py:github_read_modify_write`
- **Daily note path:** `10_Daily/YYYY-MM-DD.md`
- **Sections in daily note:** `## Tasks` · `## Notes` · `## Shopping List` · `## Focus` · `## Log` · `## Open Questions` · `## People` · `## Follow-ups`
- **People files:** `50_People/{firstname-lastname}.md` — Umlauts preserved in filename
- **Knowledge base:** `40_Knowledge/open-questions.md`

### Key Scripts
| Script | Role |
|--------|------|
| `scripts/telegram_bot.py` | Bot entry point, handlers, confirmation flow, 23:55 flush job |
| `scripts/classifier.py` | Claude Haiku → `list[CapturedItem]` (8 types) |
| `scripts/capture_router.py` | Dispatches confirmed items to Obsidian + external APIs |
| `scripts/vault_utils.py` | `insert_into_section`, `make_daily_note`, `note_entry` |
| `scripts/sync_to_brain.py` | `github_read_modify_write` — atomic read-modify-PUT to GitHub API |

### Telegram Commands (bypass classifier, save immediately)
- `/task <text>` → Tasks section of today's daily note
- `/note <text>` → Notes section of today's daily note
- `/frage <text>` → `40_Knowledge/open-questions.md`

### Flush Job
At 23:55 Europe/Berlin, any pending item older than 24h is auto-saved as `note`.
Julio receives a Telegram notification. No input is ever lost.

---

## Shared Engineering Principles

- Fetch live data before generating — never approximate commodity prices
- Gold/Silver unit conversion computed in `scripts/utils.py` — never hardcoded
- If a data source is unavailable, note it explicitly — never silently omit
- Stage only specific files — never `git add -A` or `git add .`
- Separate data ingestion from content generation from Obsidian sync
- All outputs must be deterministic given the same input date and data snapshot

## Required Environment Variables
| Variable | Used by |
|----------|---------|
| `ANTHROPIC_API_KEY` | Briefing generation, Telegram classifier |
| `TWELVE_DATA_API_KEY` | Precious metals prices (fetch_data.py) |
| `NEWS_API_KEY` | Global headlines (fetch_data.py) |
| `GITHUB_TOKEN` | Obsidian vault sync (sync_to_brain.py) |
| `JULIO_BRAIN_OWNER` | GitHub repo owner (default: juliokoelle) |
| `JULIO_BRAIN_REPO_NAME` | GitHub repo name (default: julio-brain) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot |
| `TELEGRAM_OWNER_ID` | Authorized user ID for bot |
| `OPENAI_API_KEY` | Voice transcription (Whisper), photo analysis (GPT-4o) |
| `MARKET_TOOLS_BACKEND_URL` | Used by capture_router for /stock-watchlist |
| `VITE_API_URL` | **Build-time only** — Render frontend env var pointing to backend URL |
