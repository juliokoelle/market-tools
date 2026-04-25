"""
Syncs a generated briefing to the julio-brain Obsidian vault.

Writes to ~/projects/julio-brain/10_Daily/YYYY-MM-DD.md:
  - If file exists: appends with --- separator
  - If new: creates fresh

Then commits locally. Pushes only if GIT_PUSH_ENABLED=true AND a remote is configured.

julio-brain currently has NO remote. To add one later:
    cd ~/projects/julio-brain
    git remote add origin git@github.com:juliokoelle/julio-brain-private.git
    git push -u origin main
Then set GIT_PUSH_ENABLED=true in your .env or Render env vars.

Designed to be non-blocking: caller wraps in try/except so a sync failure
never prevents the briefing from being saved.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BRAIN_DIR = Path.home() / "projects" / "julio-brain"
DAILY_DIR = BRAIN_DIR / "10_Daily"


def sync(run_date: str, content: str) -> None:
    """
    Write briefing to julio-brain daily note and commit.
    Raises on git errors — caller is responsible for catching.
    """
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    target = DAILY_DIR / f"{run_date}.md"

    if target.exists():
        existing = target.read_text(encoding="utf-8")
        target.write_text(existing + "\n\n---\n\n" + content, encoding="utf-8")
    else:
        target.write_text(content, encoding="utf-8")

    subprocess.run(
        ["git", "add", str(target)],
        cwd=BRAIN_DIR,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", f"briefing: daily briefing {run_date}"],
        cwd=BRAIN_DIR,
        check=True,
        capture_output=True,
    )

    push_enabled = os.getenv("GIT_PUSH_ENABLED", "").lower() in ("1", "true", "yes")
    if push_enabled:
        remotes = subprocess.run(
            ["git", "remote"],
            cwd=BRAIN_DIR,
            capture_output=True,
            text=True,
        )
        if remotes.stdout.strip():
            subprocess.run(["git", "push"], cwd=BRAIN_DIR, check=True, capture_output=True)
            print(f"  [brain] Pushed to remote.")
        else:
            print("  [brain] GIT_PUSH_ENABLED=true but no remote configured — skipping push.")

    print(f"  [brain] Committed briefing → {target}")


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-04-25"
    sync(date, f"# Test briefing {date}\n\nTest content from sync_to_brain.py smoke test.")
    print("Sync complete.")
