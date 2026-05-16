"""LLM-based item classifier for the Telegram capture bot."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

import anthropic

log = logging.getLogger(__name__)

VALID_TYPES = frozenset({
    "wishlist", "stock_pick", "gift_idea", "reminder",
    "task", "question", "idea", "note",
})

_SYSTEM = """\
You are a personal assistant classifier. Extract all distinct items from the user's message \
and classify each one. Return ONLY a JSON array, no markdown, no extra text.

Each element: {"type": "...", "text": "...", "metadata": {...}}

Types and rules:
- "wishlist": user wants to buy, own, or get something. \
metadata: {"name": "item name", "brand": "brand or null", "price": null_or_number}
- "stock_pick": company or ticker mentioned in investing context. \
metadata: {"ticker": "SYMBOL", "notes": "context or null"}
- "gift_idea": item intended for a named person. \
metadata: {"person": "Name", "item": "description"}
- "reminder": time-anchored or "don't forget". \
metadata: {"text": "reminder text", "date": "date string or null"}
- "task": concrete action to complete. metadata: {}
- "question": something to look up, research, or decide. metadata: {}
- "idea": concept, project idea, observation without direct action. metadata: {}
- "note": everything else. metadata: {}

One message may produce multiple items (e.g. shopping list + stock mention = 2 items). \
Never return an empty array. When unclear, use "note"."""


@dataclass
class CapturedItem:
    type: str
    text: str
    metadata: dict = field(default_factory=dict)


def classify_text(text: str) -> list[CapturedItem]:
    """Classify text into CapturedItems via Claude Haiku. Never raises — falls back to note."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        log.warning("ANTHROPIC_API_KEY not set — falling back to note")
        return [CapturedItem(type="note", text=text)]
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=_SYSTEM,
            messages=[{"role": "user", "content": text}],
        )
        raw = response.content[0].text.strip()
        parsed = json.loads(raw)
        result: list[CapturedItem] = []
        for item in parsed:
            t = str(item.get("type", "note")).lower()
            if t not in VALID_TYPES:
                t = "note"
            result.append(CapturedItem(
                type=t,
                text=str(item.get("text", text)).strip() or text,
                metadata=item.get("metadata") or {},
            ))
        return result or [CapturedItem(type="note", text=text)]
    except Exception as e:
        log.error("classify_text failed: %s", e)
        return [CapturedItem(type="note", text=text)]
