"""
Create or append today's daily note in julio-brain/10_Daily/.

Modes:
  --mode check   → prints "exists" or "new", exits
  --mode create  → writes fresh template (fails if file already exists)
  --mode append  → appends template with --- separator (safe when briefing is already in file)

Flags:
  --cloud        → GitHub Actions mode: skips AppleScript/osascript, skips local git commit,
                   creates the daily note via GitHub API only (idempotent — skips if exists).

Local git commit is done after write (unless --cloud). Push is handled by Obsidian Git plugin.
"""

from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

BRAIN_DIR = Path.home() / "projects" / "julio-brain"
DAILY_DIR = BRAIN_DIR / "10_Daily"
BACKEND_BASE = "https://market-tools-backend-my0v.onrender.com"

WEEKDAYS_DE = {
    0: "Montag", 1: "Dienstag", 2: "Mittwoch",
    3: "Donnerstag", 4: "Freitag", 5: "Samstag", 6: "Sonntag",
}


def _fetch_calendar_events() -> list[str]:
    """Run fetch_calendar_today.py via /bin/bash to inherit Calendar TCC permissions."""
    import os
    import tempfile
    script = Path(__file__).parent / "fetch_calendar_today.py"
    if not script.exists():
        return []
    try:
        out_file = tempfile.mktemp(suffix=".txt")
        ret = os.system(f'/bin/bash -c "{sys.executable} {script} > {out_file} 2>/dev/null"')
        if ret != 0 or not os.path.exists(out_file):
            return []
        lines = [l.strip() for l in Path(out_file).read_text().splitlines() if l.strip()]
        os.unlink(out_file)
        return [l for l in lines if not l.startswith("(")]
    except Exception:
        return []


def _briefing_exists(date_str: str) -> bool:
    """Check if today's briefing has been synced to the local vault."""
    path = DAILY_DIR / f"{date_str}.md"
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    return "Daily Global Economic Briefing" in content[:200]


def _build_template(date_str: str, calendar_events: list[str], has_briefing: bool) -> str:
    dt = datetime.date.fromisoformat(date_str)
    weekday = WEEKDAYS_DE[dt.weekday()]

    if calendar_events:
        cal_section = "\n".join(f"- {e}" for e in calendar_events)
    else:
        cal_section = "_keine Termine heute_"

    if has_briefing:
        briefing_line = "_Briefing bereits im Dokument (oben)_"
    else:
        briefing_line = "_noch nicht generiert_"

    return f"""\
## {date_str} — {weekday}

### Briefing des Tages

{briefing_line}

### Kalender heute

{cal_section}

### Tag-Reflexion

"""


def _build_cloud_template(date_str: str) -> str:
    """Build the canonical daily note template for cloud/GitHub Actions mode.

    Matches vault_utils.make_daily_note sections but with a GitHub Actions footer
    instead of the old briefing footer line.
    """
    return (
        f"---\ndate: {date_str}\ntype: daily\n---\n\n"
        f"# {date_str}\n\n"
        "## Tasks\n\n"
        "## Notes\n\n"
        "## Shopping List\n\n"
        "## Focus\n\n"
        "## Log\n\n"
        "## Open Questions\n\n"
        "## People\n\n"
        "## Follow-ups\n\n"
        "---\n\n"
        "*Daily Note auto-created by GitHub Actions.*\n"
    )


def _git_commit(target: Path, date_str: str) -> None:
    try:
        subprocess.run(["git", "add", str(target)], cwd=BRAIN_DIR, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"daily-note: {date_str}"],
            cwd=BRAIN_DIR, check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Warning: git commit failed (non-fatal): {e.stderr or e}", file=sys.stderr)


def _cloud_create(date_str: str) -> None:
    """Create the daily note via GitHub API (idempotent). Skips if the file already exists."""
    # Import here so local-only usage doesn't require sync_to_brain dependencies.
    import importlib.util
    import os

    sync_path = Path(__file__).parent / "sync_to_brain.py"
    spec = importlib.util.spec_from_file_location("sync_to_brain", sync_path)
    sync_mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(sync_mod)  # type: ignore[union-attr]

    gh_path = f"10_Daily/{date_str}.md"

    # Idempotency: check if the file already exists on GitHub.
    existing = sync_mod.github_read(gh_path)
    if existing is not None:
        print(f"Daily Note {date_str} already exists on GitHub — skipping.")
        sys.exit(0)

    template = _build_cloud_template(date_str)

    def _create_fresh(current: str) -> str:
        # github_read_modify_write calls this with "" when file doesn't exist.
        # If by a race condition it now exists, leave it untouched.
        if current.strip():
            return current
        return template

    sync_mod.github_read_modify_write(
        path=gh_path,
        mutate_fn=_create_fresh,
        commit_msg=f"daily-note: {date_str}",
    )
    print(f"Daily Note created on GitHub: {gh_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    parser.add_argument("--mode", choices=["check", "create", "append"], default="check")
    parser.add_argument(
        "--cloud",
        action="store_true",
        help=(
            "GitHub Actions mode: skip AppleScript/osascript and local git commit; "
            "create the daily note via GitHub API only (idempotent)."
        ),
    )
    args = parser.parse_args()

    # --cloud mode: entirely GitHub-API-based, no local filesystem needed.
    if args.cloud:
        _cloud_create(args.date)
        return

    # --- Local modes below (unchanged behaviour) ---

    if not BRAIN_DIR.exists():
        print(f"ERROR: julio-brain not found at {BRAIN_DIR}", file=sys.stderr)
        sys.exit(1)

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    target = DAILY_DIR / f"{args.date}.md"

    if args.mode == "check":
        print("exists" if target.exists() else "new")
        sys.exit(0)

    calendar_events = _fetch_calendar_events()
    has_briefing = _briefing_exists(args.date)
    template = _build_template(args.date, calendar_events, has_briefing)

    if args.mode == "create":
        if target.exists():
            print(
                f"ERROR: {target.name} already exists.\n"
                "Hint: use --mode append to add the daily note below the existing content.",
                file=sys.stderr,
            )
            sys.exit(1)
        target.write_text(template, encoding="utf-8")

    elif args.mode == "append":
        existing = target.read_text(encoding="utf-8") if target.exists() else ""

        # Guard: if today's date header is already in the file, skip to avoid duplicates.
        if f"## {args.date}" in existing:
            print(f"Daily Note für {args.date} bereits vorhanden — kein Append nötig.")
            sys.exit(0)

        separator = "\n\n---\n\n" if existing.strip() else ""
        target.write_text(existing + separator + template, encoding="utf-8")

    _git_commit(target, args.date)

    print(f"Daily Note saved: {target}")
    print(f"→ Öffne 10_Daily/{args.date}.md in Obsidian, Sektion 'Tag-Reflexion' wartet auf dich.")


if __name__ == "__main__":
    main()
