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


def mark_tasks_done(task_refs: list[str], note_text: str) -> tuple[str, list[str]]:
    """Mark tasks matching task_refs as done ([ ] → [x]). Returns (updated_text, matched_texts)."""
    lines = note_text.splitlines()
    matched: list[str] = []

    for ref in task_refs:
        ref_words = {w.lower() for w in ref.split() if len(w) > 2}
        if not ref_words:
            continue
        threshold = max(1, (len(ref_words) + 1) // 2)

        best_idx: int | None = None
        best_score = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith("- [ ]"):
                continue
            line_lower = stripped.lower()
            score = sum(1 for w in ref_words if w in line_lower)
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx is not None and best_score >= threshold:
            lines[best_idx] = lines[best_idx].replace("- [ ]", "- [x]", 1)
            matched.append(lines[best_idx].strip()[6:])  # strip "- [x] " prefix

    return "\n".join(lines) + "\n", matched
