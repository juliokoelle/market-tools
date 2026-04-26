"""
Syncs a generated briefing to the julio-brain Obsidian vault.

Writes to ~/projects/julio-brain/10_Daily/YYYY-MM-DD.md:
  - If file exists: appends with --- separator
  - If new: creates fresh

Then commits locally. Pushes only if GIT_PUSH_ENABLED=true.

Push authentication:
  - Local: uses existing git credentials (Mac Keychain / SSH)
  - Render: uses GITHUB_TOKEN + JULIO_BRAIN_REPO env vars to build
    an authenticated HTTPS URL: https://x-access-token:{TOKEN}@{REPO}

Designed to be non-blocking: caller wraps in try/except so a sync failure
never prevents the briefing from being saved.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

BRAIN_DIR = Path.home() / "projects" / "julio-brain"
DAILY_DIR = BRAIN_DIR / "10_Daily"


def _push_url() -> str | None:
    """
    Build an authenticated push URL when GITHUB_TOKEN and JULIO_BRAIN_REPO are set.
    Returns None if token is not available (falls back to default remote).
    """
    token = os.getenv("GITHUB_TOKEN", "").strip()
    repo = os.getenv("JULIO_BRAIN_REPO", "").strip()
    if not token or not repo:
        return None
    repo = repo.removeprefix("https://").removeprefix("http://")
    return f"https://x-access-token:{token}@{repo}"


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

    log.info("[brain] Committed briefing → %s", target)

    push_enabled = os.getenv("GIT_PUSH_ENABLED", "").lower() in ("1", "true", "yes")
    if not push_enabled:
        return

    try:
        url = _push_url()
        if url:
            subprocess.run(
                ["git", "push", url, "main"],
                cwd=BRAIN_DIR,
                check=True,
                capture_output=True,
            )
            log.info("[brain] Pushed via token-authenticated URL.")
        else:
            remotes = subprocess.run(
                ["git", "remote"], cwd=BRAIN_DIR, capture_output=True, text=True
            )
            if remotes.stdout.strip():
                subprocess.run(
                    ["git", "push"], cwd=BRAIN_DIR, check=True, capture_output=True
                )
                log.info("[brain] Pushed via default remote.")
            else:
                log.warning("[brain] GIT_PUSH_ENABLED=true but no remote and no token — skipping push.")
    except subprocess.CalledProcessError as e:
        log.warning("[brain] Push failed (non-fatal): %s", e.stderr or e)


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-04-25"
    sync(date, f"# Test briefing {date}\n\nTest content from sync_to_brain.py smoke test.")
    print("Sync complete.")
