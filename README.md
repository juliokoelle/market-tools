# Julio's Personal AI Dashboard

A personal market intelligence dashboard: daily economic briefings (FT/Bloomberg/Handelsblatt style), portfolio tracker, stock screener, and stock analyzer. Deployed on Render.com at `https://market-tools.onrender.com`.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design, [ROADMAP.md](ROADMAP.md) for the 4-week plan, and [PROJECT_STATUS.md](PROJECT_STATUS.md) for the current audit.

## Current Phase: 2 — Live Data + API-Driven Generation

All market data is fetched live (Twelve Data, yfinance, NewsAPI + 8 RSS feeds). Briefings are generated via Anthropic (Claude Sonnet 4.6, "Premium") or OpenAI (GPT-5.4-mini, "Quick") with a button click. Cost tracking is built in with a $15/month budget counter.

## Local Development

```bash
# 1. Clone and install
git clone <repo>
cd automation
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. On macOS, install weasyprint system libs (for PDF export)
brew install pango gdk-pixbuf

# 3. Configure secrets
cp .env.example .env
# Fill in: TWELVE_DATA_API_KEY, NEWS_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY

# 4. Start the API
uvicorn scripts.api:app --reload --port 8000

# 5. Open the frontend
open frontend/index.html
```

## Generating a Briefing

Click **Generate Premium** (Claude Sonnet 4.6, ~$0.05/briefing) or **Generate Quick** (GPT-5.4-mini, ~$0.01/briefing) in the Daily Briefing tab. The cost counter below the buttons shows monthly spend vs. the $15.00 budget.

The briefing pipeline:
1. Fetches live commodity and FX prices (Twelve Data + yfinance)
2. Fetches economic headlines (NewsAPI + 8 RSS feeds — cached 30 min)
3. Builds a structured prompt with market interpretation signals
4. Calls the selected LLM with the `config/briefing_prompt.md` system prompt
5. Saves to `outputs/YYYY-MM-DD-briefing.md` and `outputs/latest-briefing.md`
6. Syncs to `~/projects/julio-brain/10_Daily/YYYY-MM-DD.md` (local git commit)
7. Tracks cost in `data/cost_log.json`

Or via CLI:
```bash
python -m scripts.generate_briefing --provider anthropic
python -m scripts.generate_briefing --provider openai
python -m scripts.generate_briefing --prompt-only   # preview prompt, no LLM call
```

## PDF Export

```bash
python -m scripts.render_pdf 2026-04-25
# → outputs/pdf/2026-04-25-briefing.pdf
```

Or via API: `GET /briefing/2026-04-25/pdf` (auto-generates if not yet rendered).

## Key API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/briefing/generate?provider=anthropic\|openai` | Generate new briefing |
| GET | `/briefing/list` | List last 30 briefings with PDF status |
| GET | `/briefing/{date}` | Get briefing as markdown + HTML |
| GET | `/briefing/{date}/pdf` | Serve PDF (generates on demand) |
| GET | `/briefing/cost-summary` | Monthly cost vs. budget |
| GET | `/portfolio/holdings` | Load saved portfolio |
| POST | `/portfolio/holdings` | Save portfolio holdings |

## Project Structure

```
automation/
├── config/
│   ├── briefing_prompt.md    # LLM system prompt (journalist persona + editorial rules)
│   ├── models.yaml           # Model IDs and pricing per provider
│   ├── phase.txt             # Current delivery phase (2)
│   └── sources.yaml          # Source URLs and priorities
├── data/
│   ├── cache/                # RSS feed cache (30-min TTL)
│   ├── cost_log.json         # Per-briefing cost tracking
│   ├── portfolio.json        # Persistent portfolio holdings
│   └── raw/YYYY-MM-DD/       # Fetched market data per run
├── frontend/
│   └── index.html            # Single-page dashboard (Vanilla JS)
├── outputs/
│   ├── pdf/                  # Generated PDFs
│   ├── latest-briefing.md    # Most recent briefing (frontend default)
│   └── YYYY-MM-DD-briefing.md
├── scripts/
│   ├── api.py                # FastAPI backend (all endpoints)
│   ├── fetch_data.py         # Market data ingestion (Twelve Data, yfinance, NewsAPI)
│   ├── generate_briefing.py  # Prompt assembly + multi-provider LLM pipeline
│   ├── news_sources.py       # RSS feed aggregation (8 feeds, 30-min cache)
│   ├── portfolio.py          # Portfolio risk analysis
│   ├── render_pdf.py         # Markdown → PDF export (weasyprint)
│   ├── stock_analyzer.py     # Single-stock analysis
│   ├── sync_to_brain.py      # julio-brain Obsidian vault sync
│   ├── universe.py           # Stock screening universe
│   └── utils.py              # Shared helpers (price conversion, paths)
└── tests/
    ├── test_news_sources.py
    ├── test_prices.py        # Includes generate_briefing helpers
    └── test_render_pdf.py
```

## Running Tests

```bash
pytest tests/ -v
```

## Deployment (Render.com)

The `Dockerfile` handles weasyprint system dependencies. Set these environment variables in the Render dashboard:
- `TWELVE_DATA_API_KEY`
- `NEWS_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GIT_PUSH_ENABLED` — set to `true` once you add a GitHub remote to julio-brain (see below)

## julio-brain Sync

Briefings are automatically committed to `~/projects/julio-brain/10_Daily/` after each generation. To enable remote push once you add a GitHub remote:

```bash
cd ~/projects/julio-brain
git remote add origin git@github.com:juliokoelle/julio-brain-private.git
git push -u origin main
```

Then set `GIT_PUSH_ENABLED=true` in `.env`. The sync script checks for a configured remote before pushing — no code change needed.

## Model Configuration

Edit `config/models.yaml` to change models or pricing without touching code:

```yaml
anthropic:
  default_model: claude-sonnet-4-6
  cost_input_per_million: 3.00
  cost_output_per_million: 15.00

openai:
  default_model: gpt-5.4-mini
  cost_input_per_million: 0.75
  cost_output_per_million: 4.50
```

## Cost Reference

| Provider | Model | Est. cost/briefing |
|---|---|---|
| Anthropic | claude-sonnet-4-6 | ~$0.03–0.08 |
| OpenAI | gpt-5.4-mini | ~$0.01–0.03 |

Monthly budget: $15.00 (displayed in the frontend cost counter).
