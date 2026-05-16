# Personal Intelligence OS v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the Telegram bot so every unstructured input (text, voice, photo) is auto-classified by Claude Haiku into typed items (wishlist, stock_pick, gift_idea, reminder, task, question, idea, note), confirmed via Telegram inline buttons, and routed to the correct integration (Obsidian vault, MyWardrobe API, Market Tools `/stock-watchlist`).

**Architecture:** Four new/modified Python files plus one new test file per module. `vault_utils.py` holds shared Obsidian mutation helpers (extracted from telegram_bot.py to avoid circular imports). `classifier.py` calls Claude Haiku and returns `list[CapturedItem]`. `capture_router.py` dispatches confirmed items to integrations. `telegram_bot.py` gains inline-keyboard confirmation flow and a 23:55 flush job. `api.py` gains `/stock-watchlist` CRUD backed by `data/stock_watchlist.json`.

**Tech Stack:** Python 3.11, python-telegram-bot v20 (job-queue), anthropic SDK (already installed), httpx (already installed), pytest-asyncio (add to requirements.txt), FastAPI, existing `github_read_modify_write` from sync_to_brain.py.

---

## File Map

| File | Change |
|------|--------|
| `scripts/vault_utils.py` | NEW — `insert_into_section`, `make_daily_note`, `note_entry` (moved from telegram_bot.py) |
| `scripts/classifier.py` | NEW — `CapturedItem` dataclass, `classify_text(text) → list[CapturedItem]` |
| `scripts/capture_router.py` | NEW — `async route_item(item)`, all per-type dispatch logic |
| `scripts/telegram_bot.py` | MODIFY — import vault_utils; plain_text/voice/photo → classifier → confirmation; `CallbackQueryHandler`; 23:55 flush job |
| `scripts/api.py` | MODIFY — `/stock-watchlist` GET/POST/DELETE |
| `data/stock_watchlist.json` | NEW — `[]` initial state |
| `tests/test_vault_utils.py` | NEW — section-insertion tests (moved from test_telegram_bot.py) |
| `tests/test_classifier.py` | NEW |
| `tests/test_capture_router.py` | NEW |
| `tests/test_api_stock_watchlist.py` | NEW |
| `requirements.txt` | MODIFY — add `pytest-asyncio` |

---

## Task 1: vault_utils.py — extract shared Obsidian helpers

Extract `insert_into_section`, `_make_daily_note`, and `_note_entry` from `telegram_bot.py` into a new shared module so `capture_router.py` can import them without circular dependencies.

**Files:**
- Create: `scripts/vault_utils.py`
- Modify: `scripts/telegram_bot.py` (replace definitions with imports)
- Create: `tests/test_vault_utils.py` (move existing section tests here)

- [ ] **Step 1: Add pytest-asyncio to requirements.txt**

Open `requirements.txt` and add `pytest-asyncio` on a new line at the end.

- [ ] **Step 2: Write tests/test_vault_utils.py**

```python
"""Tests for vault_utils shared helpers."""

def test_insert_into_existing_empty_section():
    from scripts.vault_utils import insert_into_section
    text = "# 2026-05-09\n\n## Tasks\n\n## Notes\n\n## Focus\n"
    result = insert_into_section(text, "Tasks", "- [ ] Buy milk")
    lines = result.splitlines()
    tasks_idx = lines.index("## Tasks")
    notes_idx = lines.index("## Notes")
    entry_idx = lines.index("- [ ] Buy milk")
    assert tasks_idx < entry_idx < notes_idx


def test_insert_into_section_appends_below_existing():
    from scripts.vault_utils import insert_into_section
    text = "# 2026-05-09\n\n## Tasks\n\n- [ ] First task\n\n## Notes\n"
    result = insert_into_section(text, "Tasks", "- [ ] Second task")
    lines = result.splitlines()
    first_idx = lines.index("- [ ] First task")
    second_idx = lines.index("- [ ] Second task")
    notes_idx = lines.index("## Notes")
    assert first_idx < second_idx < notes_idx


def test_insert_creates_section_if_missing():
    from scripts.vault_utils import insert_into_section
    text = "# 2026-05-09\n\n## Focus\n\nSome focus text.\n"
    result = insert_into_section(text, "Tasks", "- [ ] New task")
    assert "## Tasks" in result
    assert "- [ ] New task" in result


def test_make_daily_note_structure():
    from scripts.vault_utils import make_daily_note
    note = make_daily_note("2026-05-09")
    assert "date: 2026-05-09" in note
    assert "type: daily" in note
    tasks_pos = note.index("## Tasks")
    notes_pos = note.index("## Notes")
    focus_pos = note.index("## Focus")
    assert tasks_pos < notes_pos < focus_pos


def test_note_entry_includes_time():
    from scripts.vault_utils import note_entry
    entry = note_entry("hello")
    assert entry.startswith("- [")
    assert "hello" in entry
```

- [ ] **Step 3: Run tests — expect FAIL (module doesn't exist yet)**

```
cd ~/projects/automation && python -m pytest tests/test_vault_utils.py -v
```
Expected: `ModuleNotFoundError: No module named 'scripts.vault_utils'`

- [ ] **Step 4: Create scripts/vault_utils.py**

```python
"""Shared helpers for writing to the Obsidian vault daily notes."""

from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo

_BERLIN = ZoneInfo("Europe/Berlin")


def insert_into_section(text: str, section: str, entry: str) -> str:
    """Append entry as last line of ## section content (before next ## heading)."""
    lines = text.splitlines()
    header = f"## {section}"

    try:
        idx = next(i for i, l in enumerate(lines) if l.rstrip() == header)
    except StopIteration:
        return text.rstrip("\n") + f"\n\n## {section}\n\n{entry}\n"

    end = len(lines)
    for i in range(idx + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    insert_pos = end
    while insert_pos > idx + 1 and not lines[insert_pos - 1].strip():
        insert_pos -= 1

    lines.insert(insert_pos, entry)
    return "\n".join(lines) + "\n"


def make_daily_note(run_date: str) -> str:
    return (
        f"---\ndate: {run_date}\ntype: daily\n---\n\n"
        f"# {run_date}\n\n"
        "## Tasks\n\n"
        "## Notes\n\n"
        "## Shopping List\n\n"
        "## Focus\n\n"
        "## Log\n\n"
        "## Open Questions\n\n"
        "## People\n\n"
        "## Follow-ups\n\n"
        "---\n\n"
        "*Briefing auto-synced from market-tools at ~08:15 CEST.*\n"
    )


def note_entry(text: str) -> str:
    return f"- [{datetime.now(_BERLIN).strftime('%H:%M')}] {text}"
```

- [ ] **Step 5: Run tests — expect PASS**

```
cd ~/projects/automation && python -m pytest tests/test_vault_utils.py -v
```
Expected: 5 tests PASS

- [ ] **Step 6: Update telegram_bot.py to import from vault_utils**

In `scripts/telegram_bot.py`, replace the three function definitions (`insert_into_section`, `_make_daily_note`, `_note_entry`) with imports:

Remove these three function definitions (lines ~44–90 containing `def insert_into_section`, `def _make_daily_note`, `def _note_entry`) and add at the top of the imports section:

```python
from scripts.vault_utils import insert_into_section, make_daily_note as _make_daily_note, note_entry as _note_entry
```

- [ ] **Step 7: Verify existing telegram_bot tests still pass**

```
cd ~/projects/automation && python -m pytest tests/test_telegram_bot.py -v
```
Expected: all existing tests PASS (they import `insert_into_section` and `_make_daily_note` from `telegram_bot` — which now re-exports them via the aliases)

Note: if tests import directly from `telegram_bot`, the aliases `_make_daily_note` and `_note_entry` keep them working. `insert_into_section` is imported without alias so it's available as `telegram_bot.insert_into_section`.

- [ ] **Step 8: Commit**

```bash
cd ~/projects/automation
git add scripts/vault_utils.py scripts/telegram_bot.py tests/test_vault_utils.py requirements.txt
git commit -m "refactor: extract vault_utils.py shared helpers from telegram_bot"
```

---

## Task 2: classifier.py — LLM item classifier

**Files:**
- Create: `scripts/classifier.py`
- Create: `tests/test_classifier.py`

- [ ] **Step 1: Write tests/test_classifier.py**

```python
"""Tests for the LLM classifier. All tests mock the Anthropic client."""
import os
from unittest.mock import MagicMock, patch


def _mock_anthropic_response(json_str: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=json_str)]
    return msg


def test_classify_wishlist_item():
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "wishlist", "text": "Arc\'teryx Jacke", '
            '"metadata": {"name": "Arc\'teryx Jacke", "brand": "Arc\'teryx", "price": null}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("ich will eine Arc'teryx Jacke kaufen")
    assert len(items) == 1
    assert items[0].type == "wishlist"
    assert items[0].metadata["name"] == "Arc'teryx Jacke"
    assert items[0].metadata["brand"] == "Arc'teryx"


def test_classify_stock_pick():
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "stock_pick", "text": "ASML interessant", '
            '"metadata": {"ticker": "ASML", "notes": "interessant"}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("ASML finde ich gerade sehr interessant")
    assert items[0].type == "stock_pick"
    assert items[0].metadata["ticker"] == "ASML"


def test_classify_multi_item_voice_note():
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "wishlist", "text": "Fahrradhelm", "metadata": {"name": "Fahrradhelm", "brand": null, "price": null}}, '
            '{"type": "stock_pick", "text": "ASML anschauen", "metadata": {"ticker": "ASML", "notes": null}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("ich brauche einen Fahrradhelm und ASML ist interessant")
    assert len(items) == 2
    assert items[0].type == "wishlist"
    assert items[1].type == "stock_pick"


def test_classify_gift_idea():
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "gift_idea", "text": "Buch für Mama", '
            '"metadata": {"person": "Mama", "item": "Buch"}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("für Mama wäre ein Buch schön")
    assert items[0].type == "gift_idea"
    assert items[0].metadata["person"] == "Mama"
    assert items[0].metadata["item"] == "Buch"


def test_classify_falls_back_to_note_on_invalid_json():
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            "not valid json at all"
        )
        from scripts.classifier import classify_text
        items = classify_text("some input")
    assert len(items) == 1
    assert items[0].type == "note"
    assert items[0].text == "some input"


def test_classify_falls_back_on_unknown_type():
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "invented_type", "text": "foo", "metadata": {}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("foo")
    assert items[0].type == "note"


def test_classify_falls_back_when_no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # Force re-import with cleared env
    import importlib, scripts.classifier as m
    importlib.reload(m)
    items = m.classify_text("test text")
    assert len(items) == 1
    assert items[0].type == "note"
    assert items[0].text == "test text"


def test_classify_never_returns_empty_array():
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response("[]")
        from scripts.classifier import classify_text
        items = classify_text("something")
    assert len(items) >= 1
```

- [ ] **Step 2: Run tests — expect FAIL**

```
cd ~/projects/automation && python -m pytest tests/test_classifier.py -v
```
Expected: `ModuleNotFoundError: No module named 'scripts.classifier'`

- [ ] **Step 3: Create scripts/classifier.py**

```python
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
```

- [ ] **Step 4: Run tests — expect PASS**

```
cd ~/projects/automation && python -m pytest tests/test_classifier.py -v
```
Expected: 8 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/projects/automation
git add scripts/classifier.py tests/test_classifier.py
git commit -m "feat: classifier.py — Claude Haiku LLM item classifier"
```

---

## Task 3: capture_router.py — routing confirmed items

**Files:**
- Create: `scripts/capture_router.py`
- Create: `tests/test_capture_router.py`

- [ ] **Step 1: Write tests/test_capture_router.py**

```python
"""Tests for capture_router. Mocks all external calls."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
from scripts.classifier import CapturedItem


@pytest.mark.asyncio
async def test_route_task_writes_to_obsidian():
    item = CapturedItem(type="task", text="Call dentist", metadata={})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    mock_gh.assert_called_once()
    path, mutate_fn, commit_msg = mock_gh.call_args[0]
    assert path.startswith("10_Daily/")
    mutated = mutate_fn("# Date\n\n## Tasks\n\n## Notes\n")
    assert "- [ ] Call dentist" in mutated


@pytest.mark.asyncio
async def test_route_question_writes_to_open_questions():
    item = CapturedItem(type="question", text="How does DCF work?", metadata={})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    path = mock_gh.call_args[0][0]
    assert path == "40_Knowledge/open-questions.md"


@pytest.mark.asyncio
async def test_route_idea_adds_lightbulb_prefix():
    item = CapturedItem(type="idea", text="Build a habit tracker", metadata={})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    path, mutate_fn, _ = mock_gh.call_args[0]
    mutated = mutate_fn("# Date\n\n## Notes\n\n## Focus\n")
    assert "💡" in mutated
    assert "Build a habit tracker" in mutated


@pytest.mark.asyncio
async def test_route_gift_idea_uses_person_filename():
    item = CapturedItem(type="gift_idea", text="Buch für Mama", metadata={"person": "Mama", "item": "Buch"})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    path = mock_gh.call_args[0][0]
    assert path == "50_People/mama.md"


@pytest.mark.asyncio
async def test_route_gift_idea_creates_new_person_file():
    item = CapturedItem(type="gift_idea", text="Wein für Klaus Müller", metadata={"person": "Klaus Müller", "item": "Wein"})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    path, mutate_fn, _ = mock_gh.call_args[0]
    assert path == "50_People/klaus-müller.md"
    created = mutate_fn("")  # empty = new file
    assert "## Geschenkideen" in created
    assert "Wein" in created


@pytest.mark.asyncio
async def test_route_wishlist_calls_both_obsidian_and_api():
    item = CapturedItem(
        type="wishlist", text="Arc'teryx Jacke",
        metadata={"name": "Arc'teryx Jacke", "brand": "Arc'teryx", "price": None}
    )
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh, \
         patch("scripts.capture_router.httpx.AsyncClient") as MockHttp:
        MockHttp.return_value.__aenter__ = AsyncMock(return_value=MockHttp.return_value)
        MockHttp.return_value.__aexit__ = AsyncMock(return_value=False)
        MockHttp.return_value.post = AsyncMock(return_value=mock_resp)
        from scripts.capture_router import route_item
        await route_item(item)
    mock_gh.assert_called_once()
    MockHttp.return_value.post.assert_called_once()
    call_args = MockHttp.return_value.post.call_args
    payload = call_args[1]["json"]
    assert payload["name"] == "Arc'teryx Jacke"
    assert payload["brand"] == "Arc'teryx"
    assert payload["priority"] == 2


@pytest.mark.asyncio
async def test_route_stock_pick_writes_obsidian_and_posts_to_market_tools():
    item = CapturedItem(type="stock_pick", text="ASML interessant", metadata={"ticker": "ASML", "notes": "AI play"})
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh, \
         patch("scripts.capture_router.httpx.AsyncClient") as MockHttp:
        MockHttp.return_value.__aenter__ = AsyncMock(return_value=MockHttp.return_value)
        MockHttp.return_value.__aexit__ = AsyncMock(return_value=False)
        MockHttp.return_value.post = AsyncMock(return_value=mock_resp)
        from scripts.capture_router import route_item
        await route_item(item)
    path, mutate_fn, _ = mock_gh.call_args[0]
    mutated = mutate_fn("# Date\n\n## Notes\n\n## Focus\n")
    assert "$ASML" in mutated
    assert "AI play" in mutated
    call_args = MockHttp.return_value.post.call_args
    assert "stock-watchlist" in call_args[0][0]
    assert call_args[1]["json"]["ticker"] == "ASML"


@pytest.mark.asyncio
async def test_route_item_never_raises_on_github_failure():
    item = CapturedItem(type="task", text="Something", metadata={})
    with patch("scripts.capture_router.github_read_modify_write", side_effect=Exception("network error")):
        from scripts.capture_router import route_item
        await route_item(item)  # must not raise


@pytest.mark.asyncio
async def test_route_reminder_writes_to_followups():
    item = CapturedItem(type="reminder", text="Arzttermin", metadata={"text": "Arzttermin", "date": "Montag"})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    path, mutate_fn, _ = mock_gh.call_args[0]
    mutated = mutate_fn("# Date\n\n## Follow-ups\n\n## Focus\n")
    assert "Arzttermin" in mutated
    assert "Montag" in mutated
```

- [ ] **Step 2: Run tests — expect FAIL**

```
cd ~/projects/automation && python -m pytest tests/test_capture_router.py -v
```
Expected: `ModuleNotFoundError: No module named 'scripts.capture_router'`

- [ ] **Step 3: Create scripts/capture_router.py**

```python
"""Routes confirmed CapturedItems to the appropriate integrations."""

from __future__ import annotations

import logging
import os
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from scripts.classifier import CapturedItem
from scripts.sync_to_brain import github_read_modify_write
from scripts.vault_utils import insert_into_section, make_daily_note, note_entry
from scripts.utils import today

log = logging.getLogger(__name__)
_BERLIN = ZoneInfo("Europe/Berlin")

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

async def route_item(item: CapturedItem) -> None:
    """Dispatch item to integrations. Never raises."""
    try:
        await _dispatch(item)
    except Exception as e:
        log.error("route_item failed for type=%s text=%r: %s", item.type, item.text, e)


async def _dispatch(item: CapturedItem) -> None:
    if item.type == "task":
        path, mutate = _daily_mutate("Tasks", f"- [ ] {item.text}")
        github_read_modify_write(path, mutate, f"capture: task ({today()})")

    elif item.type == "question":
        entry = f"- [ ] {item.text} ({today()})"

        def q_mutate(current: str) -> str:
            if not current:
                current = "# Open Questions\n\n"
            return current.rstrip("\n") + "\n" + entry + "\n"

        github_read_modify_write(
            "40_Knowledge/open-questions.md", q_mutate, f"capture: question ({today()})"
        )

    elif item.type == "reminder":
        text = item.metadata.get("text") or item.text
        date_hint = item.metadata.get("date")
        entry = f"- [ ] {text}" + (f" ({date_hint})" if date_hint else "")
        path, mutate = _daily_mutate("Follow-ups", entry)
        github_read_modify_write(path, mutate, f"capture: reminder ({today()})")

    elif item.type == "idea":
        path, mutate = _daily_mutate("Notes", f"- 💡 {item.text}")
        github_read_modify_write(path, mutate, f"capture: idea ({today()})")

    elif item.type == "gift_idea":
        person = item.metadata.get("person") or "Unknown"
        gift = item.metadata.get("item") or item.text
        path, mutate = _gift_mutate(person, gift)
        github_read_modify_write(path, mutate, f"capture: gift idea ({today()})")

    elif item.type == "wishlist":
        name = item.metadata.get("name") or item.text
        brand = item.metadata.get("brand") or None
        price = item.metadata.get("price") or None
        obs_entry = f"- [ ] {name}" + (f" ({brand})" if brand else "")
        path, mutate = _daily_mutate("Shopping List", obs_entry)
        github_read_modify_write(path, mutate, f"capture: wishlist ({today()})")
        payload: dict = {"name": name, "priority": 2, "currency": "EUR"}
        if brand:
            payload["brand"] = brand
        if price is not None:
            payload["price"] = float(price)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(_MYWARDROBE_API, json=payload)
            resp.raise_for_status()

    elif item.type == "stock_pick":
        ticker = (item.metadata.get("ticker") or item.text).upper()
        notes = item.metadata.get("notes") or ""
        obs_entry = f"- 📈 ${ticker}" + (f" — {notes}" if notes else "")
        path, mutate = _daily_mutate("Notes", obs_entry)
        github_read_modify_write(path, mutate, f"capture: stock pick ({today()})")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{_MARKET_TOOLS}/stock-watchlist",
                json={"ticker": ticker, "notes": notes, "added": today()},
            )
            resp.raise_for_status()

    else:  # note + fallback
        time_str = datetime.now(_BERLIN).strftime("%H:%M")
        path, mutate = _daily_mutate("Notes", f"- [{time_str}] {item.text}")
        github_read_modify_write(path, mutate, f"capture: note ({today()})")
```

- [ ] **Step 4: Run tests — expect PASS**

```
cd ~/projects/automation && python -m pytest tests/test_capture_router.py -v
```
Expected: 9 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/projects/automation
git add scripts/capture_router.py tests/test_capture_router.py
git commit -m "feat: capture_router.py — route confirmed items to Obsidian + external APIs"
```

---

## Task 4: /stock-watchlist endpoints in api.py

**Files:**
- Modify: `scripts/api.py`
- Create: `data/stock_watchlist.json`
- Create: `tests/test_api_stock_watchlist.py`

Note: `/watchlist` (GET, line 802 in api.py) already exists and serves the bull-score watchlist from `config/watchlist.yaml`. The new personal watchlist uses `/stock-watchlist` to avoid conflict.

- [ ] **Step 1: Write tests/test_api_stock_watchlist.py**

```python
"""Tests for /stock-watchlist CRUD endpoints."""
import json
import pytest
from pathlib import Path


@pytest.fixture
def client(tmp_path, monkeypatch):
    from scripts import api as api_module
    monkeypatch.setattr(api_module, "_STOCK_WATCHLIST_PATH", tmp_path / "sw.json")
    from fastapi.testclient import TestClient
    return TestClient(api_module.app)


def test_get_empty_watchlist(client):
    r = client.get("/stock-watchlist")
    assert r.status_code == 200
    assert r.json() == []


def test_add_stock_entry(client):
    r = client.post("/stock-watchlist", json={"ticker": "asml", "notes": "AI infrastructure"})
    assert r.status_code == 201
    data = r.json()
    assert len(data) == 1
    assert data[0]["ticker"] == "ASML"
    assert data[0]["notes"] == "AI infrastructure"


def test_add_stock_deduplicates(client):
    client.post("/stock-watchlist", json={"ticker": "NVDA", "notes": "first"})
    client.post("/stock-watchlist", json={"ticker": "nvda", "notes": "second"})
    r = client.get("/stock-watchlist")
    assert len(r.json()) == 1
    assert r.json()[0]["notes"] == "first"


def test_add_multiple_stocks(client):
    client.post("/stock-watchlist", json={"ticker": "ASML"})
    client.post("/stock-watchlist", json={"ticker": "NVDA"})
    r = client.get("/stock-watchlist")
    tickers = [e["ticker"] for e in r.json()]
    assert "ASML" in tickers
    assert "NVDA" in tickers


def test_delete_stock(client):
    client.post("/stock-watchlist", json={"ticker": "TSLA"})
    r = client.delete("/stock-watchlist/TSLA")
    assert r.status_code == 200
    assert r.json() == []


def test_delete_stock_case_insensitive(client):
    client.post("/stock-watchlist", json={"ticker": "TSLA"})
    r = client.delete("/stock-watchlist/tsla")
    assert r.json() == []


def test_delete_nonexistent_stock_returns_empty(client):
    r = client.delete("/stock-watchlist/NONEXISTENT")
    assert r.status_code == 200
    assert r.json() == []
```

- [ ] **Step 2: Run tests — expect FAIL**

```
cd ~/projects/automation && python -m pytest tests/test_api_stock_watchlist.py -v
```
Expected: 7 tests FAIL with `404 Not Found` for `/stock-watchlist`

- [ ] **Step 3: Create data/stock_watchlist.json**

```bash
echo "[]" > ~/projects/automation/data/stock_watchlist.json
```

- [ ] **Step 4: Add Pydantic model and endpoints to scripts/api.py**

Find the section `# Pydantic models` (around line 125) and add `StockWatchlistEntry` after the existing models:

```python
class StockWatchlistEntry(BaseModel):
    ticker: str
    notes: str = ""
    added: str = ""
```

Then find the section `# Stock Analyzer 2.0 — Watchlist + scoring endpoints` (around line 779) and add the new endpoints **before** the existing `@app.get("/watchlist")` at line 802:

```python
# ---------------------------------------------------------------------------
# Personal stock watchlist (persisted locally in data/stock_watchlist.json)
# ---------------------------------------------------------------------------

_STOCK_WATCHLIST_PATH = Path("data/stock_watchlist.json")


def _read_stock_watchlist() -> list[dict]:
    if not _STOCK_WATCHLIST_PATH.exists():
        return []
    try:
        return json.loads(_STOCK_WATCHLIST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _write_stock_watchlist(data: list[dict]) -> None:
    _STOCK_WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STOCK_WATCHLIST_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


@app.get("/stock-watchlist")
def stock_watchlist_get():
    return _read_stock_watchlist()


@app.post("/stock-watchlist", status_code=201)
def stock_watchlist_add(entry: StockWatchlistEntry):
    data = _read_stock_watchlist()
    ticker = entry.ticker.upper()
    if not any(e["ticker"] == ticker for e in data):
        from scripts.utils import today as _today
        data.append({
            "ticker": ticker,
            "notes": entry.notes,
            "added": entry.added or _today(),
        })
        _write_stock_watchlist(data)
    return data


@app.delete("/stock-watchlist/{ticker}")
def stock_watchlist_remove(ticker: str):
    data = _read_stock_watchlist()
    data = [e for e in data if e["ticker"] != ticker.upper()]
    _write_stock_watchlist(data)
    return data
```

- [ ] **Step 5: Run tests — expect PASS**

```
cd ~/projects/automation && python -m pytest tests/test_api_stock_watchlist.py -v
```
Expected: 7 tests PASS

- [ ] **Step 6: Commit**

```bash
cd ~/projects/automation
git add scripts/api.py data/stock_watchlist.json tests/test_api_stock_watchlist.py
git commit -m "feat: /stock-watchlist CRUD endpoints — personal stock picks persistence"
```

---

## Task 5: telegram_bot.py — inline keyboard confirmation flow

**Files:**
- Modify: `scripts/telegram_bot.py`

This task wires the classifier and router into the bot. Three handlers change (`plain_text`, `handle_voice`, `handle_photo`) and two new pieces are added (confirmation sender + `CallbackQueryHandler`).

- [ ] **Step 1: Add new imports to the top of scripts/telegram_bot.py**

Add after the existing imports block (after `from scripts.utils import today`):

```python
import time as _time_mod

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from scripts.classifier import classify_text, CapturedItem
from scripts.capture_router import route_item
```

- [ ] **Step 2: Add type display constants after existing module-level constants**

Add after `_BERLIN = ZoneInfo("Europe/Berlin")`:

```python
_TYPE_EMOJI: dict[str, str] = {
    "wishlist": "🛍️", "stock_pick": "📈", "gift_idea": "🎁",
    "reminder": "⏰", "task": "📋", "question": "❓",
    "idea": "💡", "note": "📝",
}
_TYPE_LABEL: dict[str, str] = {
    "wishlist": "Wishlist", "stock_pick": "Stock Pick", "gift_idea": "Geschenkidee",
    "reminder": "Reminder", "task": "Task", "question": "Frage",
    "idea": "Idee", "note": "Note",
}
```

- [ ] **Step 3: Add helper functions for keyboards and confirmation sending**

Add after the `_TYPE_LABEL` dict:

```python
def _confirmation_keyboard(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Speichern", callback_data=f"save:{key}"),
        InlineKeyboardButton("✏️ Typ ändern", callback_data=f"retype:{key}"),
        InlineKeyboardButton("❌ Verwerfen", callback_data=f"discard:{key}"),
    ]])


def _type_picker_keyboard(key: str) -> InlineKeyboardMarkup:
    types = [
        ("📋 Task", "task"), ("❓ Frage", "question"),
        ("🛍️ Wishlist", "wishlist"), ("📈 Stock", "stock_pick"),
        ("🎁 Geschenk", "gift_idea"), ("⏰ Reminder", "reminder"),
        ("💡 Idee", "idea"), ("📝 Note", "note"),
    ]
    rows = [
        [InlineKeyboardButton(label, callback_data=f"settype:{t}:{key}") for label, t in types[i:i+4]]
        for i in range(0, len(types), 4)
    ]
    return InlineKeyboardMarkup(rows)


async def _send_confirmations(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE, items: list[CapturedItem]
) -> None:
    """Send one confirmation message per item and store each in pending state."""
    pending: dict = ctx.application.bot_data.setdefault("pending", {})
    for item in items:
        key = str(_time_mod.monotonic_ns())
        pending[key] = {"item": item, "ts": _time_mod.time()}
        emoji = _TYPE_EMOJI.get(item.type, "📝")
        label = _TYPE_LABEL.get(item.type, "Note")
        text = f"{emoji} *{label} erkannt*\n{item.text}"
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=_confirmation_keyboard(key),
        )
```

- [ ] **Step 4: Add the CallbackQueryHandler function**

Add after `_send_confirmations`:

```python
async def handle_confirmation(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ✅/✏️/❌ and type-picker button taps."""
    query = update.callback_query
    await query.answer()
    data: str = query.data or ""
    pending: dict = ctx.application.bot_data.get("pending", {})

    if data.startswith("save:"):
        key = data[5:]
        entry = pending.pop(key, None)
        if entry is None:
            await query.edit_message_reply_markup(reply_markup=None)
            return
        item: CapturedItem = entry["item"]
        label = _TYPE_LABEL.get(item.type, "Note")
        await query.edit_message_text(f"✅ Gespeichert als {label}: {item.text}")
        await route_item(item)

    elif data.startswith("discard:"):
        key = data[8:]
        pending.pop(key, None)
        await query.edit_message_text("❌ Verworfen")

    elif data.startswith("retype:"):
        key = data[7:]
        if key not in pending:
            await query.edit_message_reply_markup(reply_markup=None)
            return
        item = pending[key]["item"]
        emoji = _TYPE_EMOJI.get(item.type, "📝")
        label = _TYPE_LABEL.get(item.type, "Note")
        await query.edit_message_text(
            f"{emoji} *{label} erkannt*\n{item.text}\n\nWelcher Typ?",
            parse_mode="Markdown",
            reply_markup=_type_picker_keyboard(key),
        )

    elif data.startswith("settype:"):
        parts = data.split(":", 2)
        if len(parts) != 3:
            return
        _, new_type, key = parts
        if key not in pending:
            await query.edit_message_reply_markup(reply_markup=None)
            return
        pending[key]["item"].type = new_type
        item = pending[key]["item"]
        emoji = _TYPE_EMOJI.get(new_type, "📝")
        label = _TYPE_LABEL.get(new_type, "Note")
        await query.edit_message_text(
            f"{emoji} *{label} erkannt*\n{item.text}",
            parse_mode="Markdown",
            reply_markup=_confirmation_keyboard(key),
        )
```

- [ ] **Step 5: Replace plain_text handler**

Replace the existing `async def plain_text(...)` function body with:

```python
async def plain_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    text = (update.message.text or "").strip()
    if not text:
        return
    await update.message.reply_text("🔍 Erkenne…")
    items = classify_text(text)
    await _send_confirmations(update, ctx, items)
```

- [ ] **Step 6: Replace handle_voice handler**

Replace the body of `async def handle_voice(...)` — keep the Whisper transcription block, but replace the final save with a classifier call:

```python
async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    await update.message.reply_text("🎙 Transkribiere…")
    try:
        tg_file = await update.message.voice.get_file()
        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        buf.seek(0)
        transcript = _get_openai().audio.transcriptions.create(
            model="whisper-1",
            file=("audio.ogg", buf, "audio/ogg"),
        )
        text = transcript.text.strip()
        if not text:
            await update.message.reply_text("Keine Sprache erkannt.")
            return
        await update.message.reply_text(f'🎙 Erkannt: "{text}"\n🔍 Klassifiziere…')
        items = classify_text(text)
        await _send_confirmations(update, ctx, items)
    except Exception as e:
        log.error("handle_voice failed: %s", e)
        await update.message.reply_text(f"Fehler: {e}")
```

- [ ] **Step 7: Replace handle_photo handler**

Replace the body of `async def handle_photo(...)` — keep the GPT-4o Vision block, but route through confirmation flow instead of saving directly:

```python
async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    await update.message.reply_text("📷 Analysiere…")
    try:
        tg_file = await update.message.photo[-1].get_file()
        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        prompt = _VISION_PROMPT
        if update.message.caption:
            prompt += f"\n\nUser caption: {update.message.caption}"

        response = _get_openai().chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=200,
        )
        raw = response.choices[0].message.content or ""
        type_, content = _parse_vision_response(raw)

        if type_ == "shopping_list":
            raw_items = [i.strip() for i in content.split(",") if i.strip()]
            items = [
                CapturedItem(type="wishlist", text=i, metadata={"name": i})
                for i in raw_items
            ]
        else:
            type_map = {"task": "task", "note": "note", "question": "question"}
            mapped = type_map.get(type_, "note")
            items = [CapturedItem(type=mapped, text=content, metadata={})]

        await _send_confirmations(update, ctx, items)
    except Exception as e:
        log.error("handle_photo failed: %s", e)
        await update.message.reply_text(f"Fehler: {e}")
```

- [ ] **Step 8: Register CallbackQueryHandler in main()**

In the `main()` function, add after `app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text))`:

```python
app.add_handler(CallbackQueryHandler(handle_confirmation))
```

- [ ] **Step 9: Smoke-test the bot imports without errors**

```
cd ~/projects/automation && python -c "from scripts.telegram_bot import main; print('OK')"
```
Expected: `OK`

- [ ] **Step 10: Run the full test suite to catch regressions**

```
cd ~/projects/automation && python -m pytest tests/ -v --ignore=tests/test_render_pdf.py
```
Expected: all previously passing tests still PASS; no import errors

- [ ] **Step 11: Commit**

```bash
cd ~/projects/automation
git add scripts/telegram_bot.py
git commit -m "feat: telegram_bot inline confirmation flow — classifier + CallbackQueryHandler"
```

---

## Task 6: telegram_bot.py — 23:55 pending-items flush job

**Files:**
- Modify: `scripts/telegram_bot.py`

- [ ] **Step 1: Add flush_pending function to telegram_bot.py**

Add after `send_evening_summary`:

```python
async def flush_pending(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Flush unconfirmed items older than 24 h as notes. Runs daily at 23:55."""
    pending: dict = ctx.application.bot_data.get("pending", {})
    cutoff = _time_mod.time() - 86400
    to_flush = [k for k, v in list(pending.items()) if v.get("ts", 0) < cutoff]
    for key in to_flush:
        entry = pending.pop(key, None)
        if entry:
            item: CapturedItem = entry["item"]
            item.type = "note"
            try:
                await route_item(item)
            except Exception as e:
                log.error("flush_pending: failed to save item %r: %s", item.text, e)
    if to_flush:
        log.info("flush_pending: flushed %d expired items as notes", len(to_flush))
        try:
            await ctx.bot.send_message(
                chat_id=_OWNER_ID,
                text=f"🗑 {len(to_flush)} unbestätigte Item(s) automatisch als Note gespeichert.",
            )
        except Exception:
            pass
```

- [ ] **Step 2: Register flush_pending job in main()**

In `main()`, add after the `send_evening_summary` job registration:

```python
app.job_queue.run_daily(
    flush_pending,
    time=time(23, 55, tzinfo=_BERLIN),
)
```

- [ ] **Step 3: Verify import still clean**

```
cd ~/projects/automation && python -c "from scripts.telegram_bot import flush_pending; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Run full test suite**

```
cd ~/projects/automation && python -m pytest tests/ -v --ignore=tests/test_render_pdf.py
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/projects/automation
git add scripts/telegram_bot.py
git commit -m "feat: telegram_bot 23:55 flush job — auto-save unconfirmed items as notes"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| Classifier: Claude Haiku, array output, 8 types, fallback | Task 2 |
| Confirmation: inline buttons ✅/✏️/❌ per item | Task 5 |
| "Typ ändern" secondary keyboard → re-confirm | Task 5 |
| State in `bot_data["pending"]`, 24h timeout flush | Task 6 |
| Routing: task → Daily Note Tasks | Task 3 |
| Routing: question → open-questions.md | Task 3 |
| Routing: reminder → Daily Note Follow-ups | Task 3 |
| Routing: idea → Daily Note Notes with 💡 | Task 3 |
| Routing: gift_idea → 50_People/{person}.md create if missing | Task 3 |
| Routing: wishlist → Obsidian + MyWardrobe API | Task 3 |
| Routing: stock_pick → Obsidian + Market Tools `/stock-watchlist` | Task 3 + 4 |
| `/stock-watchlist` GET/POST/DELETE local JSON | Task 4 |
| Existing /task /note /frage commands unchanged | Task 5 (not touched) |
| plain_text, handle_voice, handle_photo → classifier | Task 5 |

**No placeholders found.** All steps contain full code.

**Type consistency:** `CapturedItem` defined in Task 2, imported in Tasks 3, 5, 6. `classify_text` defined in Task 2, imported in Task 5. `route_item` defined in Task 3, imported in Tasks 5, 6. All consistent.
