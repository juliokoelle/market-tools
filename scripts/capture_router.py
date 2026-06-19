"""Routes confirmed CapturedItems to the appropriate integrations."""

from __future__ import annotations

import asyncio
import logging
import os
import unicodedata

import anthropic
import httpx

from scripts.classifier import CapturedItem
from scripts.sync_to_brain import github_read_modify_write
from scripts.vault_utils import insert_into_section, make_daily_note, mark_tasks_done, note_entry
from scripts.utils import today

log = logging.getLogger(__name__)

_MYWARDROBE_API = "https://mywardrobe-dun.vercel.app/api/wishlist"
_MARKET_TOOLS = os.getenv(
    "MARKET_TOOLS_BACKEND_URL", "https://market-tools-backend-my0v.onrender.com"
)


# ---------------------------------------------------------------------------
# Obsidian mutation helpers
# ---------------------------------------------------------------------------

def _daily_mutate(section: str, entry: str):
    run_date = today()

    def mutate(current: str) -> str:
        if not current:
            current = make_daily_note(run_date)
        return insert_into_section(current, section, entry)

    return f"10_Daily/{run_date}.md", mutate


def _person_filename(name: str) -> str:
    normalized = unicodedata.normalize("NFC", name).lower()
    return normalized.replace(" ", "-") + ".md"


def _make_person_note(name: str) -> str:
    return (
        f"---\nname: {name}\ntype: person\n---\n\n"
        f"# {name}\n\n"
        "## Geschenkideen\n\n"
    )


def _gift_mutate(person: str, item: str):
    filename = _person_filename(person)
    entry = f"- {item} ({today()})"

    def mutate(current: str) -> str:
        if not current:
            current = _make_person_note(person)
        return insert_into_section(current, "Geschenkideen", entry)

    return f"50_People/{filename}", mutate


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def route_item(item: CapturedItem) -> str | None:
    """Dispatch item to integrations. Returns optional follow-up message. Never raises."""
    try:
        return await _dispatch(item)
    except Exception as e:
        log.error("route_item failed for type=%s text=%r: %s", item.type, item.text, e)
        return f"⚠️ Speichern fehlgeschlagen ({item.type}): {type(e).__name__}. Tippe /health für Details."


def _answer_question(question: str) -> str:
    """Answer a question via Claude Haiku. Returns empty string on failure."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return ""
    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=20.0)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=(
                "Du bist ein präziser persönlicher Assistent. "
                "Beantworte die Frage knapp und klar auf Deutsch. "
                "Maximal 4 Sätze oder eine kurze Liste. Direkt zur Antwort, kein Intro."
            ),
            messages=[{"role": "user", "content": question}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        log.warning("_answer_question failed: %s", e)
        return ""


def _format_stock_snapshot(data: dict) -> str:
    ticker  = data["ticker"]
    company = data.get("company", ticker)
    price   = data["current_price"]
    r30     = data.get("return_30d")
    trend   = data.get("trend", "—")
    t_str   = data.get("trend_strength", "")
    risk    = data.get("risk_level", "—")
    vol     = data.get("volatility", 0)
    sent    = data.get("sentiment", "neutral")
    summary = data.get("summary", "")

    r30_str = f"  {'+' if r30 >= 0 else ''}{r30*100:.1f}% / 30T" if r30 is not None else ""
    trend_icon = "📈" if trend == "bullish" else "📉"
    sent_icon  = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}.get(sent, "🟡")
    risk_icon  = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "🟡")

    lines = [
        f"📊 *{ticker}*" + (f" ({company})" if company != ticker else ""),
        "",
        f"💰 Preis: ${price:.2f}{r30_str}",
        f"{trend_icon} Trend: {trend.capitalize()} ({t_str})",
        f"{risk_icon} Risiko: {risk.capitalize()} (Vol {vol*100:.0f}%/Jahr)",
        f"{sent_icon} Sentiment: {sent.capitalize()}",
    ]
    if summary:
        lines += ["", f"_{summary}_"]
    return "\n".join(lines)


async def _dispatch(item: CapturedItem) -> str | None:
    if item.type == "task_done":
        task_ref = item.metadata.get("task_ref") or item.text
        run_date = today()
        matched: list[str] = []
        no_note = [False]

        def task_done_mutate(current: str) -> str:
            if not current:
                no_note[0] = True
                return make_daily_note(run_date)
            updated, found = mark_tasks_done([task_ref], current)
            matched.extend(found)
            return updated

        await asyncio.to_thread(
            github_read_modify_write,
            f"10_Daily/{run_date}.md",
            task_done_mutate,
            f"capture: task done ({run_date})",
        )
        if no_note[0]:
            return f"⚠️ Noch keine Daily Note für heute — kein Task markiert."
        if matched:
            return f"✅ Erledigt: _{matched[0]}_"

        # Fallback: search OPEN_TASKS.md
        backlog_matched: list[str] = []

        def backlog_mutate(current: str) -> str:
            if not current:
                return current
            updated, found = mark_tasks_done([task_ref], current)
            backlog_matched.extend(found)
            return updated

        await asyncio.to_thread(
            github_read_modify_write,
            "00_Inbox/OPEN_TASKS.md",
            backlog_mutate,
            f"capture: task done in backlog ({run_date})",
        )
        if backlog_matched:
            return f"✅ Erledigt (Backlog): _{backlog_matched[0]}_"
        return f"⚠️ Kein passender Task gefunden für: _{task_ref}_"

    elif item.type == "task":
        path, mutate = _daily_mutate("Tasks", f"- [ ] {item.text}")
        await asyncio.to_thread(github_read_modify_write, path, mutate, f"capture: task ({today()})")

    elif item.type == "question":
        # Save to global open-questions.md
        entry = f"- [ ] {item.text} ({today()})"

        def q_mutate(current: str) -> str:
            if not current:
                current = "# Open Questions\n\n"
            return current.rstrip("\n") + "\n" + entry + "\n"

        await asyncio.to_thread(
            github_read_modify_write,
            "40_Knowledge/open-questions.md", q_mutate, f"capture: question ({today()})"
        )

        # Answer immediately + save Q&A to daily note
        answer = await asyncio.to_thread(_answer_question, item.text)
        if answer:
            qa_entry = f"- ❓ {item.text}\n  → {answer}"
            path, mutate = _daily_mutate("Open Questions", qa_entry)
            await asyncio.to_thread(github_read_modify_write, path, mutate, f"capture: Q&A ({today()})")
            return f"💡 *Antwort:*\n\n{answer}"

    elif item.type == "reminder":
        text = item.metadata.get("text") or item.text
        date_hint = item.metadata.get("date")
        entry = f"- [ ] {text}" + (f" ({date_hint})" if date_hint else "")
        path, mutate = _daily_mutate("Follow-ups", entry)
        await asyncio.to_thread(github_read_modify_write, path, mutate, f"capture: reminder ({today()})")

    elif item.type == "idea":
        path, mutate = _daily_mutate("Notes", f"- 💡 {item.text}")
        await asyncio.to_thread(github_read_modify_write, path, mutate, f"capture: idea ({today()})")

    elif item.type == "gift_idea":
        person = item.metadata.get("person") or ""
        if not person:
            log.warning("gift_idea item has no person metadata, using 'Unknown': %r", item.text)
            person = "Unknown"
        gift = item.metadata.get("item") or item.text
        path, mutate = _gift_mutate(person, gift)
        await asyncio.to_thread(github_read_modify_write, path, mutate, f"capture: gift idea ({today()})")

    elif item.type == "wishlist":
        name = item.metadata.get("name") or item.text
        brand = item.metadata.get("brand") or None
        price_raw = item.metadata.get("price")
        price = price_raw if price_raw is not None else None
        obs_entry = f"- [ ] {name}" + (f" ({brand})" if brand else "")
        path, mutate = _daily_mutate("Shopping List", obs_entry)
        await asyncio.to_thread(github_read_modify_write, path, mutate, f"capture: wishlist ({today()})")
        payload: dict = {"name": name, "priority": 2, "currency": "EUR"}
        if brand:
            payload["brand"] = brand
        if price is not None:
            payload["price"] = float(price)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(_MYWARDROBE_API, json=payload)
            resp.raise_for_status()

    elif item.type == "stock_pick":
        ticker = (item.metadata.get("ticker") or item.text).upper().strip()
        company = item.metadata.get("company") or ticker
        notes = item.metadata.get("notes") or ""
        obs_entry = f"- 📈 ${ticker}" + (f" ({company})" if company != ticker else "") + (f" — {notes}" if notes else "")
        path, mutate = _daily_mutate("Notes", obs_entry)
        await asyncio.to_thread(github_read_modify_write, path, mutate, f"capture: stock pick ({today()})")

        # Post to watchlist backend (non-fatal if down)
        # 35s timeout to survive Render cold starts (~30s)
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                resp = await client.post(
                    f"{_MARKET_TOOLS}/stock-watchlist",
                    json={"ticker": ticker, "company": company, "notes": notes, "added": today()},
                )
                resp.raise_for_status()
        except Exception as e:
            log.warning("stock watchlist backend unavailable (%s) — saved to Obsidian only", e)

        # Run quick analysis and return as follow-up message
        try:
            from scripts.stock_analyzer import analyze_stock
            data = await asyncio.to_thread(analyze_stock, ticker)
            data["company"] = company
            return _format_stock_snapshot(data)
        except Exception as e:
            log.warning("stock analysis for %s failed: %s", ticker, e)
            return f"📈 *{ticker}* zur Watchlist hinzugefügt."

    else:  # note + fallback
        path, mutate = _daily_mutate("Notes", note_entry(item.text))
        await asyncio.to_thread(github_read_modify_write, path, mutate, f"capture: note ({today()})")
    return None
