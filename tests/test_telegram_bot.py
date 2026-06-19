"""Unit tests for Telegram bot section-manipulation and summary logic."""


def test_insert_into_existing_empty_section():
    from scripts.telegram_bot import insert_into_section

    text = "# 2026-05-09\n\n## Tasks\n\n## Notes\n\n## Focus\n"
    result = insert_into_section(text, "Tasks", "- [ ] Buy milk")
    lines = result.splitlines()
    tasks_idx = lines.index("## Tasks")
    notes_idx = lines.index("## Notes")
    # entry must appear between ## Tasks and ## Notes
    entry_idx = lines.index("- [ ] Buy milk")
    assert tasks_idx < entry_idx < notes_idx


def test_insert_into_section_appends_below_existing():
    from scripts.telegram_bot import insert_into_section

    text = "# 2026-05-09\n\n## Tasks\n\n- [ ] First task\n\n## Notes\n"
    result = insert_into_section(text, "Tasks", "- [ ] Second task")
    lines = result.splitlines()
    first_idx  = lines.index("- [ ] First task")
    second_idx = lines.index("- [ ] Second task")
    notes_idx  = lines.index("## Notes")
    assert first_idx < second_idx < notes_idx


def test_insert_creates_section_if_missing():
    from scripts.telegram_bot import insert_into_section

    text = "# 2026-05-09\n\n## Focus\n\nSome focus text.\n"
    result = insert_into_section(text, "Tasks", "- [ ] New task")
    assert "## Tasks" in result
    assert "- [ ] New task" in result


def test_insert_into_notes_section():
    from scripts.telegram_bot import insert_into_section

    text = "# 2026-05-09\n\n## Tasks\n\n## Notes\n\n## Focus\n"
    result = insert_into_section(text, "Notes", "Quick thought")
    lines = result.splitlines()
    notes_idx = lines.index("## Notes")
    focus_idx = lines.index("## Focus")
    entry_idx = lines.index("Quick thought")
    assert notes_idx < entry_idx < focus_idx


def test_make_daily_note_structure():
    from scripts.telegram_bot import _make_daily_note

    note = _make_daily_note("2026-05-09")
    assert "date: 2026-05-09" in note
    assert "type: daily" in note
    # Tasks and Notes must appear before Focus
    tasks_pos = note.index("## Tasks")
    notes_pos = note.index("## Notes")
    focus_pos = note.index("## Focus")
    assert tasks_pos < notes_pos < focus_pos


def test_make_daily_note_all_sections_present():
    from scripts.telegram_bot import _make_daily_note

    note = _make_daily_note("2026-05-09")
    for section in ("Tasks", "Notes", "Focus", "Log", "Open Questions", "People", "Follow-ups"):
        assert f"## {section}" in note


def test_questions_mutator_creates_file():
    from scripts.telegram_bot import _questions_mutator

    path, mutate = _questions_mutator("- [ ] What is the capital of Mars? (2026-05-09)")
    result = mutate("")
    assert "# Open Questions" in result
    assert "What is the capital of Mars?" in result


def test_questions_mutator_appends_to_existing():
    from scripts.telegram_bot import _questions_mutator

    existing = "# Open Questions\n\n- [ ] First question (2026-05-08)\n"
    path, mutate = _questions_mutator("- [ ] Second question (2026-05-09)")
    result = mutate(existing)
    assert "First question" in result
    assert "Second question" in result
    assert result.index("First question") < result.index("Second question")


def test_daily_mutator_creates_note_if_missing():
    from unittest.mock import patch
    from scripts.telegram_bot import _daily_mutator

    with patch("scripts.telegram_bot.today", return_value="2026-05-09"):
        path, mutate = _daily_mutator("Tasks", "- [ ] Do something")

    assert path == "10_Daily/2026-05-09.md"
    result = mutate("")
    assert "date: 2026-05-09" in result
    assert "- [ ] Do something" in result


def test_daily_mutator_inserts_into_existing_note():
    from unittest.mock import patch
    from scripts.telegram_bot import _daily_mutator

    existing = (
        "---\ndate: 2026-05-09\ntype: daily\n---\n\n"
        "# 2026-05-09\n\n"
        "## Tasks\n\n"
        "## Notes\n\n"
        "## Focus\n\nWork on report.\n"
    )
    with patch("scripts.telegram_bot.today", return_value="2026-05-09"):
        _, mutate = _daily_mutator("Tasks", "- [ ] Call bank")

    result = mutate(existing)
    assert "- [ ] Call bank" in result
    assert "Work on report." in result


# ---------------------------------------------------------------------------
# _extract_open_items
# ---------------------------------------------------------------------------

def test_extract_open_items_returns_unchecked_only():
    from scripts.telegram_bot import _extract_open_items

    text = (
        "# 2026-05-09\n\n"
        "## Tasks\n\n"
        "- [ ] First task\n"
        "- [x] Done task\n"
        "- [ ] Second task\n\n"
        "## Notes\n\nSome note.\n"
    )
    result = _extract_open_items(text, "Tasks")
    assert result == ["- [ ] First task", "- [ ] Second task"]


def test_extract_open_items_ignores_done():
    from scripts.telegram_bot import _extract_open_items

    text = "## Tasks\n\n- [x] Already done\n\n## Notes\n"
    assert _extract_open_items(text, "Tasks") == []


def test_extract_open_items_missing_section():
    from scripts.telegram_bot import _extract_open_items

    assert _extract_open_items("# 2026-05-09\n\n## Notes\nSome note.\n", "Tasks") == []


def test_extract_open_items_does_not_leak_into_next_section():
    from scripts.telegram_bot import _extract_open_items

    text = (
        "## Tasks\n\n- [ ] Task only\n\n"
        "## Notes\n\n"
        "## Follow-ups\n\n- [ ] Follow-up only\n"
    )
    assert _extract_open_items(text, "Tasks")     == ["- [ ] Task only"]
    assert _extract_open_items(text, "Follow-ups") == ["- [ ] Follow-up only"]


# ---------------------------------------------------------------------------
# _format_summary
# ---------------------------------------------------------------------------

def test_format_summary_with_items():
    from scripts.telegram_bot import _format_summary

    msg = _format_summary(
        ["- [ ] Call bank", "- [ ] Review notes"],
        ["- [ ] What is a basis swap? (2026-05-09)"],
        "2026-05-09",
    )
    assert "Call bank" in msg
    assert "Review notes" in msg
    assert "basis swap" in msg
    assert "2 Tasks" in msg
    assert "1 Fragen" in msg


def test_format_summary_empty_lists():
    from scripts.telegram_bot import _format_summary

    msg = _format_summary([], [], "2026-05-09")
    assert "erledigt" in msg.lower()


def test_format_summary_strips_checkbox_prefix():
    from scripts.telegram_bot import _format_summary

    msg = _format_summary(["- [ ] Do something"], [], "2026-05-09")
    assert "Do something" in msg
    assert "- [ ]" not in msg


# ---------------------------------------------------------------------------
# _parse_vision_response
# ---------------------------------------------------------------------------

def test_parse_vision_json_task():
    from scripts.telegram_bot import _parse_vision_response

    t, c = _parse_vision_response('{"type": "task", "text": "Buy milk"}')
    assert t == "task"
    assert c == "Buy milk"


def test_parse_vision_json_note():
    from scripts.telegram_bot import _parse_vision_response

    t, c = _parse_vision_response('{"type": "note", "text": "Interesting article"}')
    assert t == "note"
    assert "Interesting" in c


def test_parse_vision_json_question():
    from scripts.telegram_bot import _parse_vision_response

    t, c = _parse_vision_response('{"type": "question", "text": "What is X?"}')
    assert t == "question"
    assert "What is X?" in c


def test_parse_vision_unknown_type_falls_back_to_note():
    from scripts.telegram_bot import _parse_vision_response

    t, _ = _parse_vision_response('{"type": "random", "text": "Something"}')
    assert t == "note"


def test_parse_vision_invalid_json_falls_back_to_note():
    from scripts.telegram_bot import _parse_vision_response

    t, c = _parse_vision_response("This is not JSON at all")
    assert t == "note"
    assert "not JSON" in c


def test_parse_vision_markdown_wrapped_json():
    from scripts.telegram_bot import _parse_vision_response

    t, c = _parse_vision_response(
        '```json\n{"type": "task", "text": "Do something"}\n```'
    )
    assert t == "task"
    assert c == "Do something"


def test_parse_vision_shopping_list():
    from scripts.telegram_bot import _parse_vision_response

    t, c = _parse_vision_response('{"type": "shopping_list", "text": "Milk, Eggs, Bread"}')
    assert t == "shopping_list"
    assert "Milk" in c


# ---------------------------------------------------------------------------
# _now_berlin and _note_entry
# ---------------------------------------------------------------------------

def test_note_entry_format():
    from unittest.mock import patch
    from scripts.telegram_bot import _note_entry

    with patch("scripts.vault_utils.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "14:30"
        entry = _note_entry("Quick thought")
    assert entry == "- [14:30] Quick thought"


def test_note_entry_contains_timestamp_brackets():
    from unittest.mock import patch
    from scripts.telegram_bot import _note_entry

    with patch("scripts.vault_utils.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "09:05"
        entry = _note_entry("Reminder")
    assert entry.startswith("- [09:05]")


# ---------------------------------------------------------------------------
# _make_daily_note — Shopping List section
# ---------------------------------------------------------------------------

def test_make_daily_note_has_shopping_list():
    from scripts.telegram_bot import _make_daily_note

    note = _make_daily_note("2026-05-09")
    assert "## Shopping List" in note


def test_make_daily_note_shopping_list_between_notes_and_focus():
    from scripts.telegram_bot import _make_daily_note

    note = _make_daily_note("2026-05-09")
    notes_pos = note.index("## Notes")
    shopping_pos = note.index("## Shopping List")
    focus_pos = note.index("## Focus")
    assert notes_pos < shopping_pos < focus_pos


# ---------------------------------------------------------------------------
# _daily_mutator_entries
# ---------------------------------------------------------------------------

def test_daily_mutator_entries_inserts_multiple():
    from unittest.mock import patch
    from scripts.telegram_bot import _daily_mutator_entries

    existing = (
        "---\ndate: 2026-05-09\ntype: daily\n---\n\n"
        "# 2026-05-09\n\n"
        "## Tasks\n\n"
        "## Notes\n\n"
        "## Shopping List\n\n"
        "## Focus\n\n"
    )
    with patch("scripts.telegram_bot.today", return_value="2026-05-09"):
        _, mutate = _daily_mutator_entries("Tasks", ["- [ ] Buy milk", "- [ ] Call bank"])

    result = mutate(existing)
    lines = result.splitlines()
    assert "- [ ] Buy milk" in lines
    assert "- [ ] Call bank" in lines
    tasks_idx = lines.index("## Tasks")
    notes_idx = lines.index("## Notes")
    milk_idx = lines.index("- [ ] Buy milk")
    bank_idx = lines.index("- [ ] Call bank")
    assert tasks_idx < milk_idx < notes_idx
    assert tasks_idx < bank_idx < notes_idx


def test_daily_mutator_entries_shopping_section():
    from unittest.mock import patch
    from scripts.telegram_bot import _daily_mutator_entries

    with patch("scripts.telegram_bot.today", return_value="2026-05-09"):
        path, mutate = _daily_mutator_entries("Shopping List", ["- [ ] Milk", "- [ ] Eggs"])

    result = mutate("")
    assert "## Shopping List" in result
    assert "- [ ] Milk" in result
    assert "- [ ] Eggs" in result


# ---------------------------------------------------------------------------
# _card_text — MarkdownV2 escaping (regression for broken confirmation cards)
# ---------------------------------------------------------------------------

def test_card_text_escapes_markdown_special_chars():
    from scripts.telegram_bot import _card_text

    out = _card_text("📈", "Stock Pick", "buy $MNDY_X now *cheap* (link)")
    # The dynamic text must have every MarkdownV2 special char backslash-escaped.
    assert r"\_" in out
    assert r"\*" in out
    assert r"\(" in out and r"\)" in out
    # The static label header stays bold (its surrounding asterisks unescaped).
    assert "*Stock Pick erkannt*" in out


def test_card_text_with_suffix_escapes_suffix():
    from scripts.telegram_bot import _card_text

    out = _card_text("📋", "Task", "do it", "Pick a type!")
    assert r"Pick a type\!" in out


# ---------------------------------------------------------------------------
# Pending store — in-memory fallback path (no REDIS_URL in test env)
# ---------------------------------------------------------------------------

def test_pending_item_serialization_roundtrip():
    from scripts.telegram_bot import _ser_item, _deser_item
    from scripts.classifier import CapturedItem

    item = CapturedItem(type="stock_pick", text="MNDY", metadata={"ticker": "MNDY"})
    back = _deser_item(_ser_item(item))
    assert back.type == "stock_pick"
    assert back.text == "MNDY"
    assert back.metadata == {"ticker": "MNDY"}


def test_pending_put_get_pop_in_memory():
    from scripts.telegram_bot import _pending_put, _pending_get, _pending_pop
    from scripts.classifier import CapturedItem

    bot_data: dict = {}
    item = CapturedItem(type="task", text="call bank", metadata={})
    _pending_put(bot_data, "k1", item)

    got = _pending_get(bot_data, "k1")
    assert got is not None and got[0].text == "call bank"

    popped = _pending_pop(bot_data, "k1")
    assert popped is not None and popped[0].type == "task"
    # Gone after pop.
    assert _pending_get(bot_data, "k1") is None


def test_pending_set_type_in_memory():
    from scripts.telegram_bot import _pending_put, _pending_set_type
    from scripts.classifier import CapturedItem

    bot_data: dict = {}
    _pending_put(bot_data, "k2", CapturedItem(type="note", text="x", metadata={}))
    item = _pending_set_type(bot_data, "k2", "question")
    assert item is not None and item.type == "question"
    assert _pending_set_type(bot_data, "missing", "task") is None


def test_recap_set_get_in_memory():
    from scripts.telegram_bot import _recap_set, _recap_get

    bot_data: dict = {}
    assert _recap_get(bot_data) is None
    _recap_set(bot_data, 4242)
    assert _recap_get(bot_data) == 4242


# ---------------------------------------------------------------------------
# redis_state — graceful degradation when Redis is unavailable
# ---------------------------------------------------------------------------

def test_redis_state_degrades_without_redis(monkeypatch):
    import scripts.redis_state as rs

    monkeypatch.delenv("REDIS_URL", raising=False)
    rs._reset_for_tests()
    assert rs.get_redis() is None
    assert rs.read_recent_logs("telegram-bot", 24) == ([], [])
    assert rs.last_heartbeat("telegram-bot") is None
    rs.heartbeat("telegram-bot")  # must not raise
    rs._reset_for_tests()
