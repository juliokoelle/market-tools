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
