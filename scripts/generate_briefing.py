"""
Briefing generation — prompt assembly with market interpretation.

Loads data from data/raw/YYYY-MM-DD/, formats price blocks, generates
structured economic interpretation signals, and prints a prompt ready
to be pasted into a Claude session.

Run:
    python scripts/generate_briefing.py [YYYY-MM-DD]
"""

import json
import os
import sys
from scripts.utils import today, data_dir, output_path, format_precious_metal


# ---------------------------------------------------------------------------
# Data loading
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
#
# Each function receives a price (float or None) and returns a dict with:
#   level   — qualitative label (e.g. "elevated", "depressed", "neutral")
#   signals — list of concise economic implication strings
#
# These are fed into the prompt so the model writes interpretation into
# the narrative, not the functions themselves.
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
            "Real interest rates (inflation-adjusted) are likely perceived as low or negative, reducing the opportunity cost of holding non-yielding gold.",
        ]
    elif price >= 2500:
        level = "elevated"
        signals = [
            f"Gold at ${price:,.0f}/oz remains well above its long-run average, indicating a sustained risk-off or inflationary environment.",
            "Persistent buying from central banks and institutional investors suggests structural, not merely tactical, demand.",
            "A gold price at this level constrains aggressive Fed or ECB tightening narratives — markets are pricing in rate cut expectations or fiscal risk.",
        ]
    elif price >= 1900:
        level = "moderately elevated"
        signals = [
            f"Gold at ${price:,.0f}/oz is above historical norms but within recent trading ranges.",
            "This level reflects moderate inflation hedging and geopolitical risk premium without acute crisis pricing.",
            "Directional movement matters more than the absolute level — watch for breakouts above or below recent range.",
        ]
    else:
        level = "subdued"
        signals = [
            f"Gold at ${price:,.0f}/oz is relatively low by recent standards, suggesting a risk-on environment or confidence in central bank inflation control.",
            "Low gold may indicate that real yields are attractive, reducing demand for non-yielding assets.",
        ]

    return {"level": level, "signals": signals}


def interpret_silver(price: float | None) -> dict:
    if price is None:
        return {"level": "unknown", "signals": ["No silver price data available."]}

    gold = None  # silver interpretation is standalone here
    if price >= 35:
        level = "elevated"
        signals = [
            f"Silver at ${price:.2f}/oz is near multi-year highs, driven by both safe-haven demand (mirroring gold) and industrial use in solar panels and EVs.",
            "A high silver price relative to its historical range signals simultaneous monetary hedging and green energy demand — a dual driver that can sustain elevated levels.",
        ]
    elif price >= 25:
        level = "moderate"
        signals = [
            f"Silver at ${price:.2f}/oz is within a neutral range, reflecting balanced industrial and investment demand.",
            "The gold/silver ratio is a key metric to watch: a rising ratio (gold outperforming) indicates defensive positioning; a falling ratio points to industrial optimism.",
        ]
    else:
        level = "subdued"
        signals = [
            f"Silver at ${price:.2f}/oz is below recent norms, suggesting weak industrial demand or a risk-on environment where precious metals attract less capital.",
        ]

    return {"level": level, "signals": signals}


def interpret_brent(price: float | None) -> dict:
    if price is None:
        return {"level": "unknown", "signals": ["No Brent crude price data available."]}

    if price >= 100:
        level = "high — inflationary pressure"
        signals = [
            f"Brent at ${price:.2f}/bbl is above $100, a threshold historically associated with demand destruction and central bank concern about energy-driven inflation.",
            "High oil directly feeds into headline CPI through fuel and transportation costs, complicating the Fed's and ECB's ability to cut rates.",
            "Germany and other energy-importing economies face margin compression in industrial output; Brazil, as an oil exporter, benefits from improved fiscal revenues.",
            "OPEC+ supply discipline is likely a key driver — assess whether cuts are voluntary or a response to demand weakness.",
        ]
    elif price >= 75:
        level = "moderate"
        signals = [
            f"Brent at ${price:.2f}/bbl is within a range generally considered manageable for developed economies.",
            "At this level, energy is unlikely to be a primary inflation driver, giving central banks more flexibility on rate policy.",
            "For oil-exporting emerging markets (Brazil, Gulf states), this price supports fiscal stability without triggering demand destruction globally.",
        ]
    elif price >= 55:
        level = "low"
        signals = [
            f"Brent at ${price:.2f}/bbl is below the fiscal breakeven of most OPEC members, creating pressure for supply cuts.",
            "Low oil prices are disinflationary — helpful for central banks fighting inflation — but signal weak global demand or supply surplus.",
            "Energy sector capex and investment tend to contract at these levels, with lagged effects on future supply.",
        ]
    else:
        level = "very low — demand concern"
        signals = [
            f"Brent below $55/bbl signals either a significant demand contraction (recession risk) or a supply shock.",
            "Such levels are typically unsustainable and precede either OPEC+ cuts or a recovery in demand expectations.",
        ]

    return {"level": level, "signals": signals}


def interpret_natgas(price: float | None) -> dict:
    if price is None:
        return {"level": "unknown", "signals": ["No natural gas price data available."]}

    if price >= 4.0:
        level = "elevated"
        signals = [
            f"Natural gas at ${price:.2f}/MMBtu is elevated, raising industrial energy costs particularly in Germany and the EU, where gas remains critical to manufacturing and heating.",
            "High gas prices feed directly into producer price indices (PPI) and, with a lag, into consumer inflation — especially in Europe.",
            "Energy-intensive industries (chemicals, steel, glass, ceramics) face margin pressure; some may reduce output or accelerate energy transition investments.",
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
            f"Natural gas at ${price:.2f}/MMBtu is historically low, reflecting strong storage levels, mild weather, or weak industrial demand.",
            "Low gas prices reduce inflationary pressure on energy-sensitive sectors but may also signal broader industrial slowdown.",
        ]

    return {"level": level, "signals": signals}


def interpret_copper(price: float | None) -> dict:
    if price is None:
        return {"level": "unknown", "signals": ["No copper price data available."]}

    if price >= 4.5:
        level = "elevated — growth signal"
        signals = [
            f"Copper at ${price:.2f}/lb is high, consistent with strong global industrial demand — copper is the most reliable leading indicator of manufacturing and construction activity.",
            "Elevated copper prices reflect optimism about Chinese infrastructure spending, global capex cycles, and the accelerating electrification of energy systems (EVs, grids, renewables).",
            "For commodity exporters like Chile and Peru, high copper supports export revenues; Brazil benefits indirectly through regional trade flows.",
        ]
    elif price >= 3.5:
        level = "moderate — stable growth"
        signals = [
            f"Copper at ${price:.2f}/lb indicates steady industrial activity without overheating.",
            "This range supports a soft-landing narrative: growth is continuing but not at a pace that would accelerate inflation.",
        ]
    else:
        level = "low — growth concern"
        signals = [
            f"Copper below $3.50/lb is a warning signal for global industrial activity — historically, sustained weakness at these levels precedes or accompanies recessions.",
            "Weak copper points to slowing Chinese demand (the world's largest copper consumer) or a broad pullback in manufacturing investment.",
        ]

    return {"level": level, "signals": signals}


def interpret_eurusd(rate: float | None) -> dict:
    if rate is None:
        return {"level": "unknown", "signals": ["No EUR/USD data available."]}

    if rate >= 1.12:
        level = "strong euro"
        signals = [
            f"EUR/USD at {rate:.4f} — a strong euro reduces the cost of euro-denominated imports (energy, commodities priced in USD), providing modest disinflationary relief in the eurozone.",
            "A strong euro compresses margins for European exporters — German automakers, industrial machinery, and luxury goods face headwinds on USD-denominated revenues.",
            "This level typically reflects either ECB hawkishness relative to the Fed, or USD weakness driven by US fiscal concerns or growth deceleration.",
            "For Brazil, a weaker dollar generally supports commodity prices and eases pressure on BRL-denominated USD debt.",
        ]
    elif rate >= 1.05:
        level = "near parity — balanced"
        signals = [
            f"EUR/USD at {rate:.4f} is near its medium-term equilibrium, reflecting broadly balanced monetary policy expectations between the Fed and ECB.",
            "At this level, European export competitiveness is not dramatically impaired, though it remains below the 1.10–1.15 range that historically provided more comfortable margins.",
            "Any shift in interest rate differentials — a Fed cut or ECB hold — could move this rate meaningfully in either direction.",
        ]
    elif rate >= 0.98:
        level = "weak euro / near parity"
        signals = [
            f"EUR/USD at {rate:.4f} — the euro near or below parity with the dollar significantly raises the cost of USD-priced imports, amplifying inflation in the eurozone.",
            "This rate reflects either aggressive Fed tightening relative to the ECB, European energy vulnerability, or recession risk in Germany.",
            "European corporate earnings in USD terms are boosted when reported back in euros, but input cost pressures offset this benefit.",
        ]
    else:
        level = "weak euro"
        signals = [
            f"EUR/USD at {rate:.4f} represents a materially weak euro, last seen during periods of acute eurozone stress.",
            "At this level, import inflation becomes a systemic concern for the ECB, potentially forcing rate hikes even amid economic weakness — a stagflationary bind.",
        ]

    return {"level": level, "signals": signals}


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
        desc = a.get("description") or ""
        pub = (a.get("published_at") or "")[:10]
        lines.append(f"{i}. [{source}] {title} ({pub})")
        if desc:
            lines.append(f"   {desc}")
    return "\n".join(lines)


def build_prompt(run_date: str) -> str:
    commodities = load(run_date, "commodities.json")
    currencies = load(run_date, "currencies.json")
    news = load_news(run_date)

    gold    = commodities.get("gold_usd_oz")
    silver  = commodities.get("silver_usd_oz")
    brent   = commodities.get("brent_usd_bbl")
    natgas  = commodities.get("natgas_usd_mmbtu")
    copper  = commodities.get("copper_usd_lb")
    eurusd  = currencies.get("eurusd")

    gold_block   = format_precious_metal("Gold", gold) if gold else "Gold: [data missing]"
    silver_block = format_precious_metal("Silver", silver) if silver else "Silver: [data missing]"

    interp_blocks = "\n\n".join([
        _render_interpretation("Gold",        interpret_gold(gold)),
        _render_interpretation("Silver",      interpret_silver(silver)),
        _render_interpretation("Brent Crude", interpret_brent(brent)),
        _render_interpretation("Natural Gas", interpret_natgas(natgas)),
        _render_interpretation("Copper",      interpret_copper(copper)),
        _render_interpretation("EUR/USD",     interpret_eurusd(eurusd)),
    ])

    news_block = format_news(news if isinstance(news, list) else [])

    prompt = f"""
--- DAILY BRIEFING PROMPT ({run_date}) ---

You are producing the Daily Global Economic Newspaper Briefing.
Follow all editorial standards in CLAUDE.md exactly.

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

The following signals are pre-computed economic context. Integrate them
into the briefing narrative — do not copy them verbatim. Use them as the
analytical foundation for the Commodities, Currency, and Macroeconomy
sections. Always connect signals across assets (e.g. copper + oil → growth
picture; gold + EUR/USD → monetary policy expectations).

{interp_blocks}

---

## Top News Headlines for {run_date}

{news_block}

---

Generate the full briefing now. Follow the seven mandatory sections.
Focus on Germany, US, and Brazil. Explain all cross-regional linkages.
Integrate the market interpretation signals into the narrative.
Maintain journalistic prose throughout — no bullet lists in the final output.
""".strip()

    return prompt


if __name__ == "__main__":
    run_date = sys.argv[1] if len(sys.argv) > 1 else today()
    prompt = build_prompt(run_date)
    print(prompt)

    out = output_path(run_date)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(f"# Briefing — {run_date}\n\n")
        f.write("<!-- Paste generated briefing below this line -->\n")
    print(f"\nOutput file ready: {out}")
