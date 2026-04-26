"""
Syncs a generated briefing to the julio-brain GitHub repo via Contents API.

On Render (GITHUB_TOKEN + JULIO_BRAIN_OWNER + JULIO_BRAIN_REPO_NAME set):
  - PUTs file to GitHub API: PUT /repos/{owner}/{repo}/contents/10_Daily/{date}.md
  - GETs existing file first to retrieve SHA (required for updates)

Locally (no GITHUB_TOKEN):
  - Falls back to local git commit in ~/projects/julio-brain
  - Skips push silently if no token

Non-blocking: caller wraps in try/except. Sync failure never crashes briefing save.
"""

from __future__ import annotations

import base64
import logging
import os
import subprocess
from pathlib import Path

import requests

log = logging.getLogger(__name__)

BRAIN_DIR = Path.home() / "projects" / "julio-brain"
DAILY_DIR = BRAIN_DIR / "10_Daily"


def _gh_config() -> tuple[str, str, str] | None:
    """Returns (token, owner, repo_name) or None if GITHUB_TOKEN is not set."""
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        return None
    owner = os.getenv("JULIO_BRAIN_OWNER", "juliokoelle").strip()
    repo  = os.getenv("JULIO_BRAIN_REPO_NAME", "julio-brain").strip()
    return token, owner, repo


def _github_put(token: str, owner: str, repo: str, run_date: str, content: str) -> None:
    """Create or update 10_Daily/{run_date}.md via GitHub Contents API."""
    api_url = (
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/contents/10_Daily/{run_date}.md"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # GET existing file to retrieve SHA (required for updates, omitted for creates)
    sha: str | None = None
    try:
        get_resp = requests.get(api_url, headers=headers, timeout=10)
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")
    except requests.RequestException as e:
        log.warning("[brain] GitHub GET for SHA failed: %s", e)

    body: dict = {
        "message": f"briefing: daily briefing {run_date}",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if sha:
        body["sha"] = sha

    put_resp = requests.put(api_url, headers=headers, json=body, timeout=30)
    if put_resp.status_code in (200, 201):
        action = "updated" if sha else "created"
        log.info("[brain] GitHub push OK — %s %s.md.", action, run_date)
    else:
        log.warning(
            "[brain] GitHub PUT failed: HTTP %s — %s",
            put_resp.status_code,
            put_resp.text[:300],
        )


def _local_commit(run_date: str, content: str) -> None:
    """Write briefing to local julio-brain vault and commit (dev machine only)."""
    if not BRAIN_DIR.exists():
        log.warning("[brain] Local BRAIN_DIR not found (%s) — skipping local commit.", BRAIN_DIR)
        return

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    target = DAILY_DIR / f"{run_date}.md"

    if target.exists():
        existing = target.read_text(encoding="utf-8")
        target.write_text(existing + "\n\n---\n\n" + content, encoding="utf-8")
    else:
        target.write_text(content, encoding="utf-8")

    subprocess.run(["git", "add", str(target)], cwd=BRAIN_DIR, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"briefing: daily briefing {run_date}"],
        cwd=BRAIN_DIR, check=True, capture_output=True,
    )
    log.info("[brain] Local commit: %s", target)


def sync(run_date: str, content: str) -> None:
    """
    Push briefing to GitHub (if token available) and commit locally (if path exists).
    Logs warnings on failure — never raises.
    """
    cfg = _gh_config()
    if cfg:
        token, owner, repo = cfg
        _github_put(token, owner, repo, run_date, content)
    else:
        log.warning("[brain] GITHUB_TOKEN not set — skipping GitHub push.")

    try:
        _local_commit(run_date, content)
    except subprocess.CalledProcessError as e:
        log.warning("[brain] Local commit failed (non-fatal): %s", e.stderr or e)
    except Exception as e:
        log.warning("[brain] Local sync error (non-fatal): %s", e)


if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-04-26"
    sync(date, f"# Test briefing {date}\n\nTest content from sync_to_brain.py smoke test.")
    print("Sync complete.")
