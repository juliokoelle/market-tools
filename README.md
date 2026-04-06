# Daily Global Economic Newspaper Briefing

A production-oriented system for generating a daily global economic briefing in the style of FT, Bloomberg, and WSJ.

## Current Phase: 1 — Manual Generation

Data is entered manually. Scripts assemble the prompt and scaffold output files.

## Workflow (Phase 1)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Scaffold today's data directory
python scripts/fetch_data.py

# 3. Fill in data/raw/YYYY-MM-DD/*.json with today's values

# 4. Generate the briefing prompt
python scripts/generate_briefing.py

# 5. Paste the prompt output into a Claude session
# 6. Paste the response into outputs/YYYY-MM-DD-briefing.md
```

## Project Structure

```
automation/
├── config/
│   ├── phase.txt          # Current delivery phase (1, 2, or 3)
│   └── sources.yaml       # Source URLs and commodity/currency lists
├── data/
│   ├── raw/               # Raw input data per date (YYYY-MM-DD/)
│   └── processed/         # Cleaned/transformed data (Phase 2+)
├── outputs/               # Generated briefings (YYYY-MM-DD-briefing.md)
├── scripts/
│   ├── fetch_data.py      # Data ingestion (stub in Phase 1)
│   ├── generate_briefing.py  # Prompt assembly and output scaffolding
│   └── utils.py           # Price conversion, path helpers
├── tests/
│   └── test_prices.py     # Unit tests for price formatting
├── CLAUDE.md              # Full project instructions for AI coding sessions
├── .env.example           # Environment variable template
└── requirements.txt
```

## Running Tests

```bash
pytest tests/
```

## Roadmap

| Phase | Description |
|-------|-------------|
| 1 | Manual data entry + prompt assembly |
| 2 | Live data fetching via APIs (Alpha Vantage, FRED, yfinance) |
| 3 | Fully scheduled: automated pipeline, email/API delivery |
