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
