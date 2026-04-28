"""
Briefing generation — full pipeline with multi-provider LLM support.

Phase 2: fetches live market data + RSS news, calls Anthropic or OpenAI,
saves outputs (latest + archive + julio-brain), tracks cost.

CLI usage:
    python scripts/generate_briefing.py [YYYY-MM-DD] [--provider anthropic|openai]
    python scripts/generate_briefing.py --prompt-only  # preview prompt, no LLM call

Functions used by api.py:
    generate(run_date, provider)     — full pipeline, returns result dict
    build_prompt(run_date, extra_news) — prompt assembly only (backward-compat)
    OUTPUT_LATEST                    — Path to latest-briefing.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

from scripts.utils import today, data_dir, output_path, format_precious_metal

OUTPUT_LATEST = Path("outputs/latest-briefing.md")


# ---------------------------------------------------------------------------
# Config loaders
# ---------------------------------------------------------------------------

def _load_system_prompt() -> str:
    path = Path("config/briefing_prompt.md")
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return (
        "You are a senior economic journalist producing the Daily Global Economic "
        "Newspaper Briefing. Follow all editorial standards exactly. "
        "Write in continuous journalistic prose. No bullet lists in the final output."
    )


def _load_model_config(provider: str) -> dict:
    path = Path("config/models.yaml")
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if provider not in config:
        raise ValueError(
            f"Unknown provider '{provider}'. Must be one of: {list(config.keys())}"
        )
    return config[provider]


# ---------------------------------------------------------------------------
# LLM callers
# Each returns (briefing_text, {"input_tokens": int, "output_tokens": int})
# ---------------------------------------------------------------------------

def _call_anthropic(system_prompt: str, user_prompt: str, model: str) -> tuple[str, dict]:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text, {
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }


def _call_openai(system_prompt: str, user_prompt: str, model: str) -> tuple[str, dict]:
    import openai as openai_sdk

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")

    client = openai_sdk.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_completion_tokens=4096,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content, {
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
    }


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------

def _calculate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
    cfg = _load_model_config(provider)
    cost = (
        (input_tokens / 1_000_000) * cfg["cost_input_per_million"]
        + (output_tokens / 1_000_000) * cfg["cost_output_per_million"]
    )
    return round(cost, 6)


def _record_cost(
    run_date: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> None:
    log_path = Path("data/cost_log.json")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    if log_path.exists():
        try:
            entries = json.loads(log_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            entries = []

    entries.append({
        "date": run_date,
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
    })
    log_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def generate(run_date: str, provider: str = "anthropic") -> dict:
    """
    Full briefing pipeline:
      1. Fetch market data (Twelve Data + yfinance + NewsAPI)
      2. Fetch RSS news
      3. Build prompt
      4. Call LLM (Anthropic or OpenAI per provider arg)
      5. Record cost
      6. Save: outputs/latest-briefing.md + outputs/YYYY-MM-DD-briefing.md
      7. Sync to julio-brain (non-blocking on failure)

    Returns dict: date, markdown, provider, model, cost_usd, input_tokens, output_tokens
    """
    from scripts.fetch_data import run as fetch_run
    from scripts.news_sources import fetch_all_sources
    from scripts.sync_to_brain import sync as brain_sync

    print(f"\n[generate] Starting briefing for {run_date} via {provider}…")

    print("[generate] Fetching market data…")
    fetch_run(run_date)

    print("[generate] Fetching RSS feeds…")
    rss_items = fetch_all_sources(limit_per_source=5)

    print("[generate] Building prompt…")
    system_prompt = _load_system_prompt()
    user_prompt = build_prompt(run_date, extra_news=rss_items)

    model_cfg = _load_model_config(provider)
    model = model_cfg["default_model"]
    print(f"[generate] Calling {provider} ({model})…")

    if provider == "anthropic":
        briefing_text, usage = _call_anthropic(system_prompt, user_prompt, model)
    elif provider == "openai":
        briefing_text, usage = _call_openai(system_prompt, user_prompt, model)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    cost_usd = _calculate_cost(provider, usage["input_tokens"], usage["output_tokens"])
    _record_cost(run_date, provider, model, usage["input_tokens"], usage["output_tokens"], cost_usd)
    print(
        f"[generate] Cost: ${cost_usd:.4f} "
        f"({usage['input_tokens']} in / {usage['output_tokens']} out tokens)"
    )

    header = f"# Daily Global Economic Briefing — {run_date}\n\n"
    content = header + briefing_text

    OUTPUT_LATEST.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_LATEST.write_text(content, encoding="utf-8")

    archive = Path(output_path(run_date))
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_text(content, encoding="utf-8")
    print(f"[generate] Saved → {archive}")

    try:
        brain_sync(run_date, content)
    except Exception as e:
        print(f"[generate] Brain sync failed (non-blocking): {e}")

    return {
        "date": run_date,
        "markdown": content,
        "provider": provider,
        "model": model,
        "cost_usd": cost_usd,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
    }


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load(run_date: str, filename: str) -> dict:
    path = os.path.join(data_dir(run_date), filename)
    if not os.path.exists(path):
        print(f"[WARNING] Missing: {path} — section will be incomplete.")
        return {}
    with open(path) as f:
        return json.load(f)


def load_news(run_date: str) -> list:
    path = os.path.join(data_dir(run_date), "news.json")
    if not os.path.exists(path):
        print(f"[WARNING] Missing: {path} — news section will be empty.")
        return []
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Market interpretation signals
# ---------------------------------------------------------------------------

def _fmt(value, missing="[missing]") -> str:
    return f"{value:,.4f}".rstrip("0").rstrip(".") if value is not None else missing


def interpret_gold(price: float | None) -> dict:
    if price is None:
        return {"level": "unknown", "signals": ["No gold price data available."]}
    if price >= 3000:
        level = "historically elevated"
        signals = [
            f"Gold at ${price:,.0f}/oz is near or above all-time highs, reflecting acute safe-haven demand.",
            "Elevated gold prices typically signal investor concern about inflation persistence, USD weakness, or systemic financial risk.",
            "Central banks — particularly in emerging markets — may be accelerating reserve diversification away from USD assets.",
            "Real interest rates are likely perceived as low or negative, reducing the opportunity cost of holding non-yielding gold.",
        ]
    elif price >= 2500:
        level = "elevated"
        signals = [
            f"Gold at ${price:,.0f}/oz remains well above its long-run average, indicating a sustained risk-off or inflationary environment.",
            "Persistent buying from central banks and institutional investors suggests structural, not merely tactical, demand.",
            "A gold price at this level constrains aggressive Fed or ECB tightening narratives.",
        ]
    elif price >= 1900:
        level = "moderately elevated"
        signals = [
            f"Gold at ${price:,.0f}/oz is above historical norms but within recent trading ranges.",
            "This level reflects moderate inflation hedging and geopolitical risk premium without acute crisis pricing.",
        ]
    else:
        level = "subdued"
        signals = [
            f"Gold at ${price:,.0f}/oz is relatively low by recent standards, suggesting a risk-on environment.",
            "Low gold may indicate that real yields are attractive, reducing demand for non-yielding assets.",
        ]
    return {"level": level, "signals": signals}


def interpret_silver(price: float | None) -> dict:
    if price is None:
        return {"level": "unknown", "signals": ["No silver price data available."]}
    if price >= 35:
        level = "elevated"
        signals = [
            f"Silver at ${price:.2f}/oz is near multi-year highs, driven by both safe-haven demand and industrial use in solar panels and EVs.",
            "A high silver price signals simultaneous monetary hedging and green energy demand — a dual driver.",
        ]
    elif price >= 25:
        level = "moderate"
        signals = [
            f"Silver at ${price:.2f}/oz is within a neutral range, reflecting balanced industrial and investment demand.",
            "The gold/silver ratio is a key metric: a rising ratio indicates defensive positioning; falling points to industrial optimism.",
        ]
    else:
        level = "subdued"
        signals = [
            f"Silver at ${price:.2f}/oz is below recent norms, suggesting weak industrial demand or a risk-on environment.",
        ]
    return {"level": level, "signals": signals}


def interpret_brent(price: float | None) -> dict:
    if price is None:
        return {"level": "unknown", "signals": ["No Brent crude price data available."]}
    if price >= 100:
        level = "high — inflationary pressure"
        signals = [
            f"Brent at ${price:.2f}/bbl above $100 historically associates with demand destruction and central bank concern.",
            "High oil feeds directly into headline CPI, complicating the Fed's and ECB's ability to cut rates.",
            "Germany faces margin compression in industrial output; Brazil, as an oil exporter, benefits from improved fiscal revenues.",
        ]
    elif price >= 75:
        level = "moderate"
        signals = [
            f"Brent at ${price:.2f}/bbl is within a range generally considered manageable for developed economies.",
            "At this level, energy is unlikely to be a primary inflation driver, giving central banks more rate flexibility.",
        ]
    elif price >= 55:
        level = "low"
        signals = [
            f"Brent at ${price:.2f}/bbl is below the fiscal breakeven of most OPEC members, creating pressure for supply cuts.",
            "Low oil prices are disinflationary but signal weak global demand or supply surplus.",
        ]
    else:
        level = "very low — demand concern"
        signals = [
            f"Brent below $55/bbl signals either significant demand contraction or a supply shock.",
        ]
    return {"level": level, "signals": signals}


def interpret_natgas(price: float | None) -> dict:
    if price is None:
        return {"level": "unknown", "signals": ["No natural gas price data available."]}
    if price >= 4.0:
        level = "elevated"
        signals = [
            f"Natural gas at ${price:.2f}/MMBtu raises industrial energy costs in Germany and the EU.",
            "High gas prices feed into PPI and, with a lag, into consumer inflation — especially in Europe.",
        ]
    elif price >= 2.5:
        level = "moderate"
        signals = [
            f"Natural gas at ${price:.2f}/MMBtu is within a moderate range, providing some relief to European industrial users.",
            "US LNG export economics remain viable at this price, sustaining transatlantic energy trade flows.",
        ]
    else:
        level = "low"
        signals = [
            f"Natural gas at ${price:.2f}/MMBtu is historically low, reflecting strong storage levels or weak demand.",
            "Low gas prices reduce inflationary pressure but may signal broader industrial slowdown.",
        ]
    return {"level": level, "signals": signals}


def interpret_copper(price: float | None) -> dict:
    if price is None:
        return {"level": "unknown", "signals": ["No copper price data available."]}
    if price >= 4.5:
        level = "elevated — growth signal"
        signals = [
            f"Copper at ${price:.2f}/lb is high, consistent with strong global industrial demand.",
            "Elevated copper reflects optimism about Chinese infrastructure spending, global capex, and energy electrification.",
        ]
    elif price >= 3.5:
        level = "moderate — stable growth"
        signals = [
            f"Copper at ${price:.2f}/lb indicates steady industrial activity without overheating.",
            "This range supports a soft-landing narrative.",
        ]
    else:
        level = "low — growth concern"
        signals = [
            f"Copper below $3.50/lb is a warning signal for global industrial activity.",
            "Sustained weakness at these levels historically precedes or accompanies recessions.",
        ]
    return {"level": level, "signals": signals}


def interpret_eurusd(rate: float | None) -> dict:
    if rate is None:
        return {"level": "unknown", "signals": ["No EUR/USD data available."]}
    if rate >= 1.12:
        level = "strong euro"
        signals = [
            f"EUR/USD at {rate:.4f} — a strong euro reduces import costs, providing disinflationary relief in the eurozone.",
            "A strong euro compresses margins for European exporters in USD-denominated revenues.",
            "For Brazil, a weaker dollar generally supports commodity prices and eases pressure on BRL-denominated USD debt.",
        ]
    elif rate >= 1.05:
        level = "near parity — balanced"
        signals = [
            f"EUR/USD at {rate:.4f} is near its medium-term equilibrium, reflecting broadly balanced monetary policy expectations.",
            "Any shift in rate differentials — a Fed cut or ECB hold — could move this rate meaningfully in either direction.",
        ]
    elif rate >= 0.98:
        level = "weak euro / near parity"
        signals = [
            f"EUR/USD at {rate:.4f} — near parity significantly raises the cost of USD-priced imports, amplifying eurozone inflation.",
            "This rate reflects either aggressive Fed tightening relative to the ECB or European recession risk.",
        ]
    else:
        level = "weak euro"
        signals = [
            f"EUR/USD at {rate:.4f} represents a materially weak euro, last seen during periods of acute eurozone stress.",
            "Import inflation becomes a systemic concern, potentially forcing rate hikes amid economic weakness — a stagflationary bind.",
        ]
    return {"level": level, "signals": signals}


# ---------------------------------------------------------------------------
# News section routing
# ---------------------------------------------------------------------------

_SECTION_ORDER = [
    "Global Markets",
    "European Markets",
    "German Markets & Companies",
    "Tech & VC Pulse",
    "Macro & Geopolitics",
]


def _section_for(item: dict) -> str:
    cat = item.get("category", "general")
    region = item.get("region", "global")
    lang = item.get("language", "en")
    if cat in ("tech", "vc"):
        return "Tech & VC Pulse"
    if lang == "de" or region == "de":
        return "German Markets & Companies"
    if region in ("eu", "europe"):
        return "European Markets"
    if cat == "macro":
        return "Macro & Geopolitics"
    return "Global Markets"


def format_news_sections(articles: list) -> str:
    if not articles:
        return "[no news data]"

    buckets: dict[str, list] = {s: [] for s in _SECTION_ORDER}
    for a in articles:
        section = _section_for(a) if isinstance(a, dict) else "Global Markets"
        buckets.setdefault(section, []).append(a)

    lines = []
    for section in _SECTION_ORDER:
        items = buckets.get(section, [])
        if not items:
            continue
        lines.append(f"### {section}")
        for i, a in enumerate(items, 1):
            source = a.get("source", "Unknown")
            title = a.get("title", "No title")
            desc = a.get("description") or a.get("lead") or ""
            pub = (a.get("published_at") or a.get("publishedAt") or "")[:10]
            lang = a.get("language", "en")
            lang_tag = f" [{lang.upper()}]" if lang != "en" else ""
            lines.append(f"{i}. [{source}]{lang_tag} {title} ({pub})")
            if desc:
                lines.append(f"   {desc[:200]}")
        lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def _render_interpretation(label: str, interp: dict) -> str:
    lines = [f"**{label}** — {interp['level']}"]
    for s in interp["signals"]:
        lines.append(f"  • {s}")
    return "\n".join(lines)


def format_news(articles: list) -> str:
    if not articles:
        return "[no news data]"
    lines = []
    for i, a in enumerate(articles, 1):
        source = a.get("source", "Unknown")
        title = a.get("title", "No title")
        desc = a.get("description") or a.get("lead") or ""
        pub = (a.get("published_at") or a.get("publishedAt") or "")[:10]
        lines.append(f"{i}. [{source}] {title} ({pub})")
        if desc:
            lines.append(f"   {desc[:200]}")
    return "\n".join(lines)


def build_prompt(run_date: str, extra_news: list | None = None) -> str:
    """
    Assemble the user-facing prompt from market data files.
    extra_news: optional list of NewsItem objects from RSS feeds — merged into news block.
    """
    commodities = load(run_date, "commodities.json")
    currencies = load(run_date, "currencies.json")
    news = load_news(run_date)

    if extra_news:
        for item in extra_news:
            news.append({
                "title": item.title,
                "source": item.source,
                "published_at": item.published_at,
                "url": item.url,
                "description": item.lead,
                "language": getattr(item, "language", "en"),
                "region": getattr(item, "region", "global"),
                "category": getattr(item, "category", "general"),
            })

    gold   = commodities.get("gold_usd_oz")
    silver = commodities.get("silver_usd_oz")
    brent  = commodities.get("brent_usd_bbl")
    natgas = commodities.get("natgas_usd_mmbtu")
    copper = commodities.get("copper_usd_lb")
    eurusd = currencies.get("eurusd")

    gold_block   = format_precious_metal("Gold",   gold)   if gold   else "Gold: [data missing]"
    silver_block = format_precious_metal("Silver", silver) if silver else "Silver: [data missing]"

    interp_blocks = "\n\n".join([
        _render_interpretation("Gold",        interpret_gold(gold)),
        _render_interpretation("Silver",      interpret_silver(silver)),
        _render_interpretation("Brent Crude", interpret_brent(brent)),
        _render_interpretation("Natural Gas", interpret_natgas(natgas)),
        _render_interpretation("Copper",      interpret_copper(copper)),
        _render_interpretation("EUR/USD",     interpret_eurusd(eurusd)),
    ])

    news_block = format_news_sections(news if isinstance(news, list) else [])

    return f"""
--- DAILY BRIEFING PROMPT ({run_date}) ---

## Market Data for {run_date}

### Precious Metals (mandatory tri-unit format)
{gold_block}

{silver_block}

### Other Commodities
Brent Oil:    {_fmt(brent)} USD/bbl
Natural Gas:  {_fmt(natgas)} USD/MMBtu
Copper:       {_fmt(copper)} USD/lb

### Currencies
EUR/USD: {_fmt(eurusd)}

---

## Market Interpretation Signals

{interp_blocks}

---

## News Input — Organized by Section

{news_block}

---

Generate the full briefing now. Follow the seven mandatory sections.
Focus on Germany, US, and Brazil. Explain all cross-regional linkages.
Integrate the market interpretation signals into the narrative.
For news items tagged [DE] or [PT], translate and synthesize key points naturally into English.
Maintain journalistic prose throughout — no bullet lists in the final output.
""".strip()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate daily economic briefing.")
    parser.add_argument("date", nargs="?", default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument(
        "--provider", choices=["anthropic", "openai"], default="anthropic",
        help="LLM provider (default: anthropic)"
    )
    parser.add_argument(
        "--prompt-only", action="store_true",
        help="Print assembled prompt without calling LLM"
    )
    args = parser.parse_args()

    run_date = args.date or today()

    if args.prompt_only:
        print(build_prompt(run_date))
        sys.exit(0)

    result = generate(run_date, provider=args.provider)
    print(f"\nBriefing complete.")
    print(f"  Provider : {result['provider']} ({result['model']})")
    print(f"  Words    : {len(result['markdown'].split())}")
    print(f"  Cost     : ${result['cost_usd']:.4f}")
    print(f"  Tokens   : {result['input_tokens']} in / {result['output_tokens']} out")
